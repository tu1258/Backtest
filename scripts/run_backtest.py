from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs90_backtester.config import load_config, deep_get
from rs90_backtester.data import load_prices
from rs90_backtester.indicators import add_indicators
from rs90_backtester.universe import add_point_in_time_rs, recent_rs90
from rs90_backtester.engine import BacktestConfig, run_backtest, save_outputs


def _strategies(value):
    if value is None:
        return None
    if isinstance(value, str):
        return tuple(x.strip() for x in value.split(",") if x.strip())
    return tuple(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run RS90 daily backtest.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--price-csv", default=None)
    parser.add_argument("--output-dir", default="outputs/backtest")
    parser.add_argument("--initial-capital", type=float, default=None)
    parser.add_argument("--position-pct", type=float, default=None)
    parser.add_argument("--rs-threshold", type=float, default=None)
    parser.add_argument("--recent-days", type=int, default=None)
    parser.add_argument("--exit-mode", choices=["ma10", "pivot_low", "either"], default=None)
    parser.add_argument("--start-date", default=None)
    parser.add_argument("--end-date", default=None)
    parser.add_argument("--strategies", default=None, help="Comma list: breakout,rsi2")
    args = parser.parse_args()

    cfg = load_config(args.config)
    price_csv = args.price_csv or deep_get(cfg, "data.price_csv", "data/stock_data.csv")

    btcfg = BacktestConfig(
        initial_capital=args.initial_capital or float(deep_get(cfg, "backtest.initial_capital", 1_000_000)),
        position_pct=args.position_pct if args.position_pct is not None else float(deep_get(cfg, "backtest.position_pct", 0.01)),
        rs_threshold=args.rs_threshold if args.rs_threshold is not None else float(deep_get(cfg, "backtest.rs_threshold", 90)),
        recent_days=args.recent_days if args.recent_days is not None else int(deep_get(cfg, "backtest.recent_days", 7)),
        exit_mode=args.exit_mode or deep_get(cfg, "backtest.exit_mode", "either"),
        max_open_positions=int(deep_get(cfg, "backtest.max_open_positions", 100)),
        max_new_positions_per_day=int(deep_get(cfg, "backtest.max_new_positions_per_day", 100)),
        allow_same_ticker_overlap=bool(deep_get(cfg, "backtest.allow_same_ticker_overlap", False)),
        slippage_bps=float(deep_get(cfg, "costs.slippage_bps", 0)),
        commission_per_trade=float(deep_get(cfg, "costs.commission_per_trade", 0)),
        max_stop_pct=deep_get(cfg, "risk.max_stop_pct", None),
        start_date=args.start_date or deep_get(cfg, "backtest.start_date", None),
        end_date=args.end_date or deep_get(cfg, "backtest.end_date", None),
        strategies=_strategies(args.strategies) or _strategies(deep_get(cfg, "backtest.strategies", ["breakout", "rsi2"])),
    )

    print(f"Loading prices: {price_csv}")
    prices = load_prices(price_csv)
    print(f"Rows={len(prices):,}, tickers={prices['ticker'].nunique():,}, dates={prices['date'].nunique():,}")

    print("Computing indicators...")
    df = add_indicators(prices)
    print("Computing point-in-time RS ranks...")
    df = add_point_in_time_rs(df)
    rs90 = recent_rs90(df, recent_days=btcfg.recent_days, threshold=btfg_rs_threshold(btcfg))

    print("Running backtest...")
    trades, equity, report = run_backtest(df, btcfg)
    save_outputs(args.output_dir, trades, equity, report, rs90)

    print("\nPerformance report")
    for k, v in report.items():
        if k != "by_strategy":
            print(f"  {k}: {v}")
    if "by_strategy" in report:
        print("  by_strategy:")
        for k, v in report["by_strategy"].items():
            print(f"    {k}: {v}")
    print(f"\nSaved outputs to {args.output_dir}")


def btfg_rs_threshold(cfg: BacktestConfig) -> float:
    return cfg.rs_threshold


if __name__ == "__main__":
    main()
