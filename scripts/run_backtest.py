from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs90_backtester.config import load_config, deep_get
from rs90_backtester.data import load_prices
from rs90_backtester.indicators import add_indicators
from rs90_backtester.universe import add_point_in_time_rs, recent_rs90
from rs90_backtester.engine import BacktestConfig, run_backtest, save_outputs

ENTRY_STRATEGIES = ("breakout", "rsi2")
EXIT_MODES = ("ma10", "atr_trail")


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
        pivot_left=args.pivot_left if args.pivot_left is not None else int(deep_get(cfg, "backtest.pivot_left", 1)),
        pivot_right=args.pivot_right if args.pivot_right is not None else int(deep_get(cfg, "backtest.pivot_right", 1)),
        atr_period=args.atr_period if args.atr_period is not None else int(deep_get(cfg, "backtest.atr_period", 14)),
        atr_multiple=args.atr_multiple if args.atr_multiple is not None else float(deep_get(cfg, "backtest.atr_multiple", 1.0)),
    )


def _run_one(df: pd.DataFrame, output_dir: Path, rs90: pd.DataFrame, cfg: BacktestConfig) -> dict:
    print(f"Running: strategies={cfg.strategies}, exit_mode={cfg.exit_mode}, output={output_dir}")
    trades, equity, report = run_backtest(df, cfg)
    save_outputs(output_dir, trades, equity, report, rs90)
    print(f"  trades={len(trades):,}, final_equity={report.get('final_equity')}, max_dd={report.get('max_drawdown')}")
    return report


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
    parser.add_argument("--pivot-left", type=int, default=None, help="Pivot left bars L. Default from config is 1.")
    parser.add_argument("--pivot-right", type=int, default=None, help="Pivot right bars R. Default from config is 1.")
    parser.add_argument("--atr-period", type=int, default=None, help="ATR period for atr_trail exit. Default from config is 14.")
    parser.add_argument("--atr-multiple", type=float, default=None, help="ATR multiple for atr_trail exit. Default from config is 1.0.")
    parser.add_argument("--matrix", action="store_true", help="Run all 2 entry strategies x 2 exit modes as separate reports.")
    args = parser.parse_args()

    cfg_dict = load_config(args.config)
    price_csv = args.price_csv or deep_get(cfg_dict, "data.price_csv", "data/stock_data.csv")
    base_cfg = _base_config(args, cfg_dict)

    print(f"Loading prices: {price_csv}")
    prices = load_prices(price_csv)
    print(f"Rows={len(prices):,}, tickers={prices['ticker'].nunique():,}, dates={prices['date'].nunique():,}")

    print(f"Computing indicators with pivot_left={base_cfg.pivot_left}, pivot_right={base_cfg.pivot_right}, atr_period={base_cfg.atr_period}...")
    df = add_indicators(prices, pivot_left=base_cfg.pivot_left, pivot_right=base_cfg.pivot_right, atr_period=base_cfg.atr_period)
    print("Computing point-in-time RS ranks...")
    df = add_point_in_time_rs(df)
    rs90 = recent_rs90(df, recent_days=base_cfg.recent_days, threshold=base_cfg.rs_threshold)

    # Critical semantics:
    # The RS90 membership table itself defines where entries are allowed.
    # Entries are allowed only when the exact (date, ticker) pair exists in rs90.
    # If rs90 contains only the latest N trading days, older dates have no
    # membership rows and therefore cannot generate entries. Exits remain
    # unrestricted after entry as long as price data exists.
    df = df.copy()
    df["in_rs90_full_history"] = df["in_rs90"]
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

    # IMPORTANT: overwrite in_rs90 with the actual tradable membership.
    # This means _generate_entries() can only trade exact date+ticker pairs
    # from outputs/backtest/rs90_daily_recent.csv, not historical RS90 rows.
    df["in_rs90"] = df["entry_universe_member"]

    eligible_entry_dates = sorted(pd.to_datetime(rs90["date"]).unique()) if not rs90.empty else []
    print("Eligible entry dates from RS90 membership:", [str(pd.Timestamp(d).date()) for d in eligible_entry_dates])
    print(f"Allowed RS90 membership pairs: {int(df['entry_universe_member'].sum()):,}")
    print(f"Entries are restricted to exact date+ticker pairs in rs90 membership. Exits remain unrestricted within available price data.")

    out_root = Path(args.output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    rs90.to_csv(out_root / "rs90_daily_recent.csv", index=False)

    if args.matrix:
        summary_rows = []
        reports = {}
        for entry_strategy in ENTRY_STRATEGIES:
            for exit_mode in EXIT_MODES:
                combo_name = f"{entry_strategy}_{exit_mode}"
                combo_cfg = BacktestConfig(**{**base_cfg.__dict__, "strategies": (entry_strategy,), "exit_mode": exit_mode})
                report = _run_one(df, out_root / combo_name, rs90, combo_cfg)
                reports[combo_name] = report
                summary_rows.append({
                    "strategy_combo": combo_name,
                    "entry_strategy": entry_strategy,
                    "exit_mode": exit_mode,
                    "pivot_left": report.get("pivot_left"),
                    "pivot_right": report.get("pivot_right"),
                    "atr_period": report.get("atr_period"),
                    "atr_multiple": report.get("atr_multiple"),
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
        print(f"\nSaved matrix outputs to {out_root}")
        return

    print("Running single backtest...")
    report = _run_one(df, out_root, rs90, base_cfg)

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
