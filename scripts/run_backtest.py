from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs90_backtester.data import load_prices
from rs90_backtester.indicators import add_indicators
from rs90_backtester.universe import add_point_in_time_rs
from rs90_backtester.engine import BacktestConfig, run_backtest, save_outputs

ENTRY_VARIANTS = {
    "rsi2_next_open": {"entry_name": "rsi2_next_open"},
    "rsi2_intraday_limit": {"entry_name": "rsi2_intraday_limit"},
}

EXIT_VARIANTS = {
    "trail_0_5atr": {"exit_name": "trail_0_5atr"},
    "trail_1atr": {"exit_name": "trail_1atr"},
    "hold_1d_open": {"exit_name": "hold_1d_open"},
    "hold_2d_open": {"exit_name": "hold_2d_open"},
    "hold_3d_open": {"exit_name": "hold_3d_open"},
    "hold_4d_open": {"exit_name": "hold_4d_open"},
    "hold_5d_open": {"exit_name": "hold_5d_open"},
    "hold_0d_close": {"exit_name": "hold_0d_close"},
    "hold_1d_close": {"exit_name": "hold_1d_close"},
    "hold_2d_close": {"exit_name": "hold_2d_close"},
    "hold_3d_close": {"exit_name": "hold_3d_close"},
    "hold_4d_close": {"exit_name": "hold_4d_close"},
    "hold_5d_close": {"exit_name": "hold_5d_close"},
    "1_day_low": {"exit_name": "1_day_low"},
    "2_day_low": {"exit_name": "2_day_low"},
    "3_day_low": {"exit_name": "3_day_low"},
    "4_day_low": {"exit_name": "4_day_low"},
    "5_day_low": {"exit_name": "5_day_low"},
    "rsi2_gt_50": {"exit_name": "rsi2_gt_50"},
    "rsi2_gt_60": {"exit_name": "rsi2_gt_60"},
    "rsi2_gt_70": {"exit_name": "rsi2_gt_70"},
    "rsi2_gt_80": {"exit_name": "rsi2_gt_80"},
}

DEFAULT_ENTRIES = "rsi2_next_open"
DEFAULT_EXITS = "hold_1d_open,hold_2d_open,hold_3d_open,hold_4d_open,hold_5d_open,rsi2_gt_50,rsi2_gt_60,rsi2_gt_70,rsi2_gt_80"
DEFAULT_RS_BUCKETS = "90_100"


def _parse_list(value: str | None, default: str) -> list[str]:
    raw = value if value is not None and value.strip() else default
    out: list[str] = []
    seen = set()
    for item in raw.split(","):
        item = item.strip()
        if item and item not in seen:
            out.append(item)
            seen.add(item)
    return out


def _parse_rs_bucket(label: str) -> tuple[float, float]:
    try:
        lo, hi = label.split("_")
        return float(lo), float(hi)
    except Exception as exc:
        raise ValueError(f"Invalid RS bucket '{label}'. Use labels like 0_10,70_80,90_100") from exc


def _make_rs_membership(df: pd.DataFrame, recent_days: int, bucket: str) -> pd.DataFrame:
    """Build an entry-date membership table from the previous completed daily bar.

    If a trade can enter on date D, RS bucket membership is computed from D-1.
    This avoids using D's final close/RS rank before the trade exists.
    """
    lo, hi = _parse_rs_bucket(bucket)
    dates = sorted(pd.to_datetime(df["date"].dropna().unique()))
    if len(dates) < 2:
        return pd.DataFrame(columns=["date", "decision_date", "ticker", "rs_rank", "rs_score", "rs_bucket"])

    selected_trade_dates = dates[-recent_days:] if recent_days and recent_days > 0 else dates[1:]
    date_map = pd.DataFrame({"date": dates})
    date_map["trade_date"] = date_map["date"].shift(-1)
    date_map = date_map.rename(columns={"date": "decision_date"}).dropna(subset=["trade_date"])
    date_map = date_map[date_map["trade_date"].isin(selected_trade_dates)]

    part = df.merge(date_map, left_on="date", right_on="decision_date", how="inner")
    if hi >= 100:
        mask = (part["rs_rank"] >= lo) & (part["rs_rank"] <= hi)
    else:
        mask = (part["rs_rank"] >= lo) & (part["rs_rank"] < hi)

    membership = part.loc[mask, ["trade_date", "decision_date", "ticker", "rs_rank", "rs_score"]].copy()
    membership = membership.rename(columns={"trade_date": "date"})
    membership = membership.drop_duplicates(["date", "ticker"])
    membership["rs_bucket"] = bucket
    return membership


def _apply_membership(df: pd.DataFrame, membership: pd.DataFrame) -> pd.DataFrame:
    keys = membership[["date", "decision_date", "ticker", "rs_rank", "rs_score", "rs_bucket"]].drop_duplicates(["date", "ticker"]).copy()
    keys = keys.rename(columns={"rs_rank": "entry_rs_rank", "rs_score": "entry_rs_score"})
    keys["in_rs_universe"] = True
    out = df.merge(keys, on=["date", "ticker"], how="left")
    out["in_rs_universe"] = out["in_rs_universe"].fillna(False)
    # Keep compatibility with older engine/report names.
    out["in_rs90"] = out["in_rs_universe"]
    return out


def _summarize_membership(membership: pd.DataFrame) -> None:
    print(f"membership_rows={len(membership)}")
    if not membership.empty:
        print("membership_dates=", [pd.Timestamp(x).strftime("%Y-%m-%d") for x in sorted(membership["date"].unique())[:3]], "...", [pd.Timestamp(x).strftime("%Y-%m-%d") for x in sorted(membership["date"].unique())[-3:]])
        print("membership_count_by_bucket=")
        print(membership.groupby("rs_bucket").size().to_string())
        print("membership_recent_count_by_date=")
        print(membership.groupby("date").size().tail(10).to_string())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--price-csv", default="data/stock_data.csv")
    parser.add_argument("--output-dir", default="outputs/backtest")
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--position-pct", type=float, default=0.01)
    parser.add_argument("--recent-days", type=int, default=7)
    parser.add_argument("--entries", default=DEFAULT_ENTRIES)
    parser.add_argument("--exits", default=DEFAULT_EXITS)
    parser.add_argument("--rs-buckets", default=DEFAULT_RS_BUCKETS)
    parser.add_argument("--slippage-bps", type=float, default=1.0)
    parser.add_argument("--atr-period", type=int, default=14)
    parser.add_argument("--max-open-positions", type=int, default=100000)
    parser.add_argument("--max-new-positions-per-day", type=int, default=100000)
    args = parser.parse_args()

    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"Loading prices: {args.price_csv}")
    prices = load_prices(args.price_csv)
    print(f"Rows={len(prices):,}, tickers={prices['ticker'].nunique():,}, dates={prices['date'].nunique():,}")

    print("Computing indicators...")
    df = add_indicators(prices, atr_period=args.atr_period)

    print("Computing point-in-time RS ranks...")
    df = add_point_in_time_rs(df)

    entries = _parse_list(args.entries, DEFAULT_ENTRIES)
    exits = _parse_list(args.exits, DEFAULT_EXITS)
    buckets = _parse_list(args.rs_buckets, DEFAULT_RS_BUCKETS)

    invalid_entries = [x for x in entries if x not in ENTRY_VARIANTS]
    invalid_exits = [x for x in exits if x not in EXIT_VARIANTS]
    if invalid_entries:
        raise ValueError(f"Invalid entries: {invalid_entries}. Available: {sorted(ENTRY_VARIANTS)}")
    if invalid_exits:
        raise ValueError(f"Invalid exits: {invalid_exits}. Available: {sorted(EXIT_VARIANTS)}")

    print(f"Selected entries={entries}")
    print(f"Selected exits={exits}")
    print(f"Selected rs_buckets={buckets}")

    all_reports: dict[str, dict] = {}
    summary_rows: list[dict] = []
    all_memberships: list[pd.DataFrame] = []

    base_cfg = BacktestConfig(
        initial_capital=args.initial_capital,
        position_pct=args.position_pct,
        recent_days=args.recent_days,
        slippage_bps=args.slippage_bps,
        atr_period=args.atr_period,
        max_open_positions=args.max_open_positions,
        max_new_positions_per_day=args.max_new_positions_per_day,
    )

    for bucket in buckets:
        membership = _make_rs_membership(df, args.recent_days, bucket)
        all_memberships.append(membership)
        _summarize_membership(membership)
        sim_df = _apply_membership(df, membership)
        if not membership.empty:
            first_entry_date = membership["date"].min()
            sim_df = sim_df[sim_df["date"] >= first_entry_date].copy()
            print(f"Simulation window for {bucket}: >= {pd.Timestamp(first_entry_date).strftime('%Y-%m-%d')}; rows={len(sim_df):,}")

        for entry in entries:
            for exit_name in exits:
                combo_name = f"rs{bucket}_{entry}_{exit_name}"
                print(f"\n=== Running {combo_name} ===")
                cfg = replace(
                    base_cfg,
                    rs_bucket=f"rs{bucket}",
                    entry_name=ENTRY_VARIANTS[entry]["entry_name"],
                    exit_name=EXIT_VARIANTS[exit_name]["exit_name"],
                )
                trades, equity, report = run_backtest(sim_df, cfg)
                save_outputs(out_root / combo_name, trades, equity, report, membership)
                all_reports[combo_name] = report
                summary_rows.append({
                    "strategy_combo": combo_name,
                    "rs_bucket": bucket,
                    "entry": entry,
                    "exit": exit_name,
                    "trade_count": report.get("trade_count"),
                    "win_rate": report.get("win_rate"),
                    "profit_factor": report.get("profit_factor"),
                    "avg_r": report.get("avg_r"),
                    "median_r": report.get("median_r"),
                    "final_equity": report.get("final_equity"),
                    "total_return": report.get("total_return"),
                    "max_drawdown": report.get("max_drawdown"),
                    "avg_exposure_pct": report.get("avg_exposure_pct"),
                    "max_exposure_pct": report.get("max_exposure_pct"),
                    "avg_holding_days": report.get("avg_holding_days"),
                })
                print(pd.DataFrame([summary_rows[-1]]).to_string(index=False))

    if all_memberships:
        pd.concat(all_memberships, ignore_index=True).to_csv(out_root / "rs_membership_recent.csv", index=False)
    summary = pd.DataFrame(summary_rows)
    summary.to_csv(out_root / "strategy_summary.csv", index=False)
    with (out_root / "all_reports.json").open("w", encoding="utf-8") as f:
        json.dump(all_reports, f, ensure_ascii=False, indent=2)

    print("\nstrategy_summary=")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
