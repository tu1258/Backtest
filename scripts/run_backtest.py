from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs90_backtester.config import load_config, deep_get
from rs90_backtester.data import load_prices
from rs90_backtester.indicators import add_indicators
from rs90_backtester.universe import add_point_in_time_rs, recent_rs90
from rs90_backtester.engine import BacktestConfig, run_backtest, save_outputs

# Fixed 15-combo matrix requested by user:
# 3 entries: breakout 1,1 / breakout 2,2 / RSI2
# 4 exits: 0.5 ATR trail / 1 ATR trail / MA10 / 5-day low
ENTRY_VARIANTS = (
    {"name": "breakout_1_1", "strategy": "breakout", "pivot_left": 1, "pivot_right": 1},
    {"name": "breakout_2_2", "strategy": "breakout", "pivot_left": 2, "pivot_right": 2},
    {"name": "rsi2", "strategy": "rsi2", "pivot_left": 1, "pivot_right": 1},
)

EXIT_VARIANTS = (
    {"name": "trail_0_5atr", "exit_mode": "atr_trail", "atr_multiple": 0.5, "n_day_low_period": None},
    {"name": "trail_1atr", "exit_mode": "atr_trail", "atr_multiple": 1.0, "n_day_low_period": None},
    {"name": "ma10", "exit_mode": "ma10", "atr_multiple": None, "n_day_low_period": None},
    {"name": "5_day_low", "exit_mode": "n_day_low", "atr_multiple": None, "n_day_low_period": 5},
    {"name": "prev_day_low", "exit_mode": "prev_day_low", "atr_multiple": None, "n_day_low_period": None},
)

EXIT_MODES = ("ma10", "atr_trail", "n_day_low", "prev_day_low")


def _strategies(value):
    if value is None:
        return None
    if isinstance(value, str):
        return tuple(x.strip() for x in value.split(",") if x.strip())
    return tuple(value)


def _base_config(args: argparse.Namespace, cfg: dict) -> BacktestConfig:
    max_stop_pct = deep_get(cfg, "risk.max_stop_pct", None)
    if max_stop_pct is not None:
        max_stop_pct = float(max_stop_pct)

    return BacktestConfig(
        initial_capital=args.initial_capital if args.initial_capital is not None else float(deep_get(cfg, "backtest.initial_capital", 1_000_000)),
        position_pct=args.position_pct if args.position_pct is not None else float(deep_get(cfg, "backtest.position_pct", 0.01)),
        rs_threshold=args.rs_threshold if args.rs_threshold is not None else float(deep_get(cfg, "backtest.rs_threshold", 90)),
        recent_days=args.recent_days if args.recent_days is not None else int(deep_get(cfg, "backtest.recent_days", 7)),
        exit_mode=args.exit_mode or deep_get(cfg, "backtest.exit_mode", "ma10"),
        max_open_positions=int(deep_get(cfg, "backtest.max_open_positions", 100)),
        max_new_positions_per_day=int(deep_get(cfg, "backtest.max_new_positions_per_day", 100)),
        allow_same_ticker_overlap=bool(deep_get(cfg, "backtest.allow_same_ticker_overlap", False)),
        slippage_bps=float(deep_get(cfg, "costs.slippage_bps", 0)),
        commission_per_trade=float(deep_get(cfg, "costs.commission_per_trade", 0)),
        max_stop_pct=max_stop_pct,
        start_date=args.start_date or deep_get(cfg, "backtest.start_date", None),
        end_date=args.end_date or deep_get(cfg, "backtest.end_date", None),
        strategies=_strategies(args.strategies) or _strategies(deep_get(cfg, "backtest.strategies", ["breakout", "rsi2"])),
        pivot_left=int(deep_get(cfg, "backtest.pivot_left", 1)),
        pivot_right=int(deep_get(cfg, "backtest.pivot_right", 1)),
        atr_period=args.atr_period if args.atr_period is not None else int(deep_get(cfg, "backtest.atr_period", 14)),
        atr_multiple=args.atr_multiple if args.atr_multiple is not None else float(deep_get(cfg, "backtest.atr_multiple", 1.0)),
        n_day_low_period=args.n_day_low_period if args.n_day_low_period is not None else int(deep_get(cfg, "backtest.n_day_low_period", 5)),
    )


def _apply_entry_membership(df: pd.DataFrame, rs90: pd.DataFrame) -> pd.DataFrame:
    """Restrict entries to exact date+ticker pairs in the exported RS90 table.

    This is the critical semantics: if RS90 membership only exists for recent N
    trading days, older dates cannot generate entries even if full-history RS
    ranks were computed for indicator purposes. Exits remain unrestricted.
    """
    df = df.copy()
    df["in_rs90_full_history"] = df.get("in_rs90", False)
    if rs90.empty:
        print("WARNING: no RS90 membership rows found. No entries will be generated.")
        df["entry_universe_member"] = False
    else:
        membership = rs90[["date", "ticker"]].drop_duplicates().copy()
        membership["date"] = pd.to_datetime(membership["date"])
        membership["ticker"] = membership["ticker"].astype(str).str.upper()
        membership["entry_universe_member"] = True
        df = df.merge(membership, on=["date", "ticker"], how="left")
        df["entry_universe_member"] = df["entry_universe_member"].fillna(False).astype(bool)
    df["in_rs90"] = df["entry_universe_member"]
    return df


def _prepare_df(
    prices: pd.DataFrame,
    *,
    pivot_left: int,
    pivot_right: int,
    atr_period: int,
    n_day_low_period: int,
) -> pd.DataFrame:
    df = add_indicators(
        prices,
        pivot_left=pivot_left,
        pivot_right=pivot_right,
        atr_period=atr_period,
        n_day_low_period=n_day_low_period,
    )
    df = add_point_in_time_rs(df)
    return df


def _run_one(df: pd.DataFrame, output_dir: Path, rs90: pd.DataFrame, cfg: BacktestConfig) -> dict:
    print(
        f"Running: entry={cfg.entry_name or cfg.strategies}, exit={cfg.exit_mode}, "
        f"pivot=({cfg.pivot_left},{cfg.pivot_right}), atr_multiple={cfg.atr_multiple}, "
        f"n_day_low_period={cfg.n_day_low_period}, output={output_dir}"
    )
    trades, equity, report = run_backtest(df, cfg)
    save_outputs(output_dir, trades, equity, report, rs90)
    print(f"  trades={len(trades):,}, final_equity={report.get('final_equity')}, max_dd={report.get('max_drawdown')}")
    return report


def _combo_name(entry: dict, exit_variant: dict) -> str:
    return f"{entry['name']}_{exit_variant['name']}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RS90 daily backtest.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--price-csv", default=None)
    parser.add_argument("--output-dir", default="outputs/backtest")
    parser.add_argument("--initial-capital", type=float, default=None)
    parser.add_argument("--position-pct", type=float, default=None)
    parser.add_argument("--rs-threshold", type=float, default=None)
    parser.add_argument("--recent-days", type=int, default=None)
    parser.add_argument("--exit-mode", choices=list(EXIT_MODES), default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--strategies", default=None, help="Comma list: breakout,rsi2")
    parser.add_argument("--atr-period", type=int, default=None, help="ATR period for atr_trail exits. Matrix uses multiples 0.5 and 1.0.")
    parser.add_argument("--atr-multiple", type=float, default=None, help="Single-run ATR multiple. Matrix ignores this and runs 0.5 plus 1.0.")
    parser.add_argument("--n-day-low-period", type=int, default=None, help="Single-run N-day low period. Matrix uses 5-day low.")
    parser.add_argument("--pivot-left", type=int, default=None, help="Single-run pivot L. Matrix ignores this and runs breakout 1,1 plus 2,2.")
    parser.add_argument("--pivot-right", type=int, default=None, help="Single-run pivot R. Matrix ignores this and runs breakout 1,1 plus 2,2.")
    parser.add_argument("--entry-name", default=None, help="Optional label for single-run trade logs.")
    parser.add_argument("--matrix", action="store_true", help="Run fixed 15-combo matrix: breakout 1,1 / breakout 2,2 / RSI2 x 4 exits.")
    args = parser.parse_args()

    cfg_dict = load_config(args.config)
    price_csv = args.price_csv or deep_get(cfg_dict, "data.price_csv", "data/stock_data.csv")
    base_cfg = _base_config(args, cfg_dict)

    print(f"Loading prices: {price_csv}")
    prices = load_prices(price_csv)
    print(f"Rows={len(prices):,}, tickers={prices['ticker'].nunique():,}, dates={prices['date'].nunique():,}")

    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    print("Computing base indicators and point-in-time RS ranks for RS90 membership...")
    base_df = _prepare_df(
        prices,
        pivot_left=1,
        pivot_right=1,
        atr_period=base_cfg.atr_period,
        n_day_low_period=5,
    )
    rs90 = recent_rs90(base_df, recent_days=base_cfg.recent_days, threshold=base_cfg.rs_threshold)
    rs90.to_csv(out_root / "rs90_daily_recent.csv", index=False)

    eligible_entry_dates = sorted(pd.to_datetime(rs90["date"]).unique()) if not rs90.empty else []
    print("Eligible entry dates from RS90 membership:", [str(pd.Timestamp(d).date()) for d in eligible_entry_dates])
    print(f"Allowed RS90 membership pairs: {len(rs90):,}")
    print("Entries are restricted to exact date+ticker pairs in rs90 membership. Exits remain unrestricted within available price data.")

    if args.matrix:
        summary_rows = []
        reports = {}
        prepared_cache: dict[tuple[int, int, int, int], pd.DataFrame] = {}

        for entry in ENTRY_VARIANTS:
            for exit_variant in EXIT_VARIANTS:
                combo_name = _combo_name(entry, exit_variant)
                n_day = int(exit_variant["n_day_low_period"] or 5)
                key = (entry["pivot_left"], entry["pivot_right"], base_cfg.atr_period, n_day)
                if key not in prepared_cache:
                    print(
                        f"Computing indicators for combo family: pivot=({key[0]},{key[1]}), "
                        f"atr_period={key[2]}, n_day_low_period={key[3]}"
                    )
                    df = _prepare_df(
                        prices,
                        pivot_left=key[0],
                        pivot_right=key[1],
                        atr_period=key[2],
                        n_day_low_period=key[3],
                    )
                    prepared_cache[key] = _apply_entry_membership(df, rs90)

                combo_df = prepared_cache[key]
                combo_cfg = replace(
                    base_cfg,
                    strategies=(entry["strategy"],),
                    entry_name=entry["name"],
                    pivot_left=entry["pivot_left"],
                    pivot_right=entry["pivot_right"],
                    exit_mode=exit_variant["exit_mode"],
                    atr_multiple=float(exit_variant["atr_multiple"] if exit_variant["atr_multiple"] is not None else base_cfg.atr_multiple),
                    n_day_low_period=n_day,
                )
                report = _run_one(combo_df, out_root / combo_name, rs90, combo_cfg)
                reports[combo_name] = report
                summary_rows.append({
                    "strategy_combo": combo_name,
                    "entry_strategy": entry["name"],
                    "exit_mode": exit_variant["name"],
                    "pivot_left": report.get("pivot_left"),
                    "pivot_right": report.get("pivot_right"),
                    "atr_period": report.get("atr_period"),
                    "atr_multiple": report.get("atr_multiple"),
                    "n_day_low_period": report.get("n_day_low_period"),
                    "trade_count": report.get("trade_count"),
                    "win_rate": report.get("win_rate"),
                    "profit_factor": report.get("profit_factor"),
                    "avg_r": report.get("avg_r"),
                    "median_r": report.get("median_r"),
                    "avg_win_loss_ratio": report.get("avg_win_loss_ratio"),
                    "max_consecutive_losses": report.get("max_consecutive_losses"),
                    "final_equity": report.get("final_equity"),
                    "total_return": report.get("total_return"),
                    "max_drawdown": report.get("max_drawdown"),
                    "avg_holding_days": report.get("avg_holding_days"),
                })

        summary = pd.DataFrame(summary_rows)
        summary.to_csv(out_root / "strategy_summary.csv", index=False)
        with (out_root / "all_reports.json").open("w", encoding="utf-8") as f:
            json.dump(reports, f, ensure_ascii=False, indent=2)

        print("\nStrategy matrix summary")
        print(summary.to_string(index=False))
        print(f"\nSaved 15-combo matrix outputs to {out_root}")
        return

    # Single-run mode remains available for debugging.
    pivot_left = args.pivot_left if args.pivot_left is not None else base_cfg.pivot_left
    pivot_right = args.pivot_right if args.pivot_right is not None else base_cfg.pivot_right
    n_day_low_period = args.n_day_low_period if args.n_day_low_period is not None else base_cfg.n_day_low_period
    df = _prepare_df(
        prices,
        pivot_left=pivot_left,
        pivot_right=pivot_right,
        atr_period=base_cfg.atr_period,
        n_day_low_period=n_day_low_period,
    )
    df = _apply_entry_membership(df, rs90)
    single_cfg = replace(
        base_cfg,
        pivot_left=pivot_left,
        pivot_right=pivot_right,
        n_day_low_period=n_day_low_period,
        entry_name=args.entry_name,
    )
    print("Running single backtest...")
    report = _run_one(df, out_root, rs90, single_cfg)

    print("\nPerformance report")
    for k, v in report.items():
        if k != "by_strategy":
            print(f"  {k}: {v}")
    if "by_strategy" in report:
        print("  by_strategy:")
        for k, v in report["by_strategy"].items():
            print(f"    {k}: {v}")
    print(f"\nSaved outputs to {out_root}")


if __name__ == "__main__":
    main()
