from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from rs90_backtester.config import load_config, deep_get
from rs90_backtester.data import DownloadConfig, download_daily_prices


def main() -> None:
    parser = argparse.ArgumentParser(description="Download daily OHLCV data from yfinance.")
    parser.add_argument("--config", default="configs/config.yaml")
    parser.add_argument("--years", type=int, default=None)
    parser.add_argument("--max-tickers", type=int, default=None)
    parser.add_argument("--price-csv", default=None)
    args = parser.parse_args()

    cfg = load_config(args.config)
    dcfg = DownloadConfig(
        ticker_csv=deep_get(cfg, "data.ticker_csv", "data/stock_ticker.csv"),
        price_csv=args.price_csv or deep_get(cfg, "data.price_csv", "data/stock_data.csv"),
        years=args.years or int(deep_get(cfg, "data.years", 2)),
        benchmark=deep_get(cfg, "data.benchmark", "^GSPC"),
        auto_adjust=bool(deep_get(cfg, "data.auto_adjust", True)),
        batch_size=int(deep_get(cfg, "data.batch_size", 80)),
        sleep_seconds=float(deep_get(cfg, "data.sleep_seconds", 1)),
        max_tickers=args.max_tickers if args.max_tickers is not None else deep_get(cfg, "data.max_tickers", None),
    )
    download_daily_prices(dcfg)


if __name__ == "__main__":
    main()
