from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
import time
import warnings

import pandas as pd
import yfinance as yf

REQUIRED_PRICE_COLUMNS = ["ticker", "date", "open", "high", "low", "close", "volume"]


@dataclass(frozen=True)
class DownloadConfig:
    ticker_csv: str = "data/stock_ticker.csv"
    price_csv: str = "data/stock_data.csv"
    years: int = 2
    benchmark: str = "^GSPC"
    auto_adjust: bool = True
    batch_size: int = 80
    sleep_seconds: float = 1.0
    max_tickers: int | None = None


def read_tickers(ticker_csv: str | Path) -> list[str]:
    path = Path(ticker_csv)
    if not path.exists():
        raise FileNotFoundError(f"Ticker CSV not found: {path}")
    df = pd.read_csv(path)
    col = "ticker" if "ticker" in df.columns else df.columns[0]
    tickers = (
        df[col]
        .dropna()
        .astype(str)
        .str.strip()
        .str.upper()
        .replace("", pd.NA)
        .dropna()
        .drop_duplicates()
        .tolist()
    )
    return tickers


def _flatten_yf_download(raw: pd.DataFrame, tickers: list[str]) -> pd.DataFrame:
    if raw.empty:
        return pd.DataFrame(columns=REQUIRED_PRICE_COLUMNS)

    frames: list[pd.DataFrame] = []
    if isinstance(raw.columns, pd.MultiIndex):
        # yfinance can return either Price x Ticker or Ticker x Price depending on version/options.
        level0 = set(map(str, raw.columns.get_level_values(0)))
        price_names = {"Open", "High", "Low", "Close", "Adj Close", "Volume"}
        price_first = len(level0 & price_names) > 0
        for ticker in tickers:
            try:
                part = raw.xs(ticker, level=1, axis=1) if price_first else raw.xs(ticker, level=0, axis=1)
            except (KeyError, ValueError):
                continue
            part = part.copy()
            part["ticker"] = ticker
            frames.append(part)
    else:
        if len(tickers) != 1:
            return pd.DataFrame(columns=REQUIRED_PRICE_COLUMNS)
        part = raw.copy()
        part["ticker"] = tickers[0]
        frames.append(part)

    if not frames:
        return pd.DataFrame(columns=REQUIRED_PRICE_COLUMNS)

    df = pd.concat(frames)
    df = df.reset_index()
    rename = {
        "Date": "date",
        "Datetime": "date",
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Adj Close": "adj_close",
        "Volume": "volume",
    }
    df = df.rename(columns=rename)
    keep = [c for c in ["ticker", "date", "open", "high", "low", "close", "volume"] if c in df.columns]
    df = df[keep]
    for col in REQUIRED_PRICE_COLUMNS:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[REQUIRED_PRICE_COLUMNS]
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["ticker", "date", "open", "high", "low", "close"])
    df = df[df["volume"].fillna(0) >= 0]
    return df


def download_daily_prices(cfg: DownloadConfig) -> pd.DataFrame:
    tickers = read_tickers(cfg.ticker_csv)
    if cfg.max_tickers:
        tickers = tickers[: cfg.max_tickers]
    if not tickers:
        raise ValueError("No tickers found.")

    end = date.today() + timedelta(days=1)
    start = date.today() - timedelta(days=int(cfg.years * 365.25) + 20)
    output_path = Path(cfg.price_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    all_frames: list[pd.DataFrame] = []
    total_batches = (len(tickers) + cfg.batch_size - 1) // cfg.batch_size
    print(f"Downloading {len(tickers)} tickers from {start} to {end} in {total_batches} batches")

    for batch_idx in range(0, len(tickers), cfg.batch_size):
        batch = tickers[batch_idx : batch_idx + cfg.batch_size]
        print(f"[{batch_idx // cfg.batch_size + 1}/{total_batches}] {batch[0]} ... {batch[-1]}", flush=True)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                raw = yf.download(
                    tickers=" ".join(batch),
                    start=start.isoformat(),
                    end=end.isoformat(),
                    auto_adjust=cfg.auto_adjust,
                    group_by="column",
                    progress=False,
                    threads=True,
                )
            df = _flatten_yf_download(raw, batch)
            if not df.empty:
                all_frames.append(df)
                print(f"  rows={len(df)}")
            else:
                print("  no rows")
        except Exception as exc:
            print(f"  failed: {exc}")
        if cfg.sleep_seconds:
            time.sleep(cfg.sleep_seconds)

    if not all_frames:
        raise RuntimeError("No price data downloaded.")

    result = pd.concat(all_frames, ignore_index=True)
    result = result.drop_duplicates(["ticker", "date"]).sort_values(["ticker", "date"])
    result["date"] = pd.to_datetime(result["date"]).dt.strftime("%Y-%m-%d")
    result.to_csv(output_path, index=False)
    print(f"Saved {output_path} rows={len(result)} tickers={result['ticker'].nunique()}")
    return result


def load_prices(price_csv: str | Path) -> pd.DataFrame:
    path = Path(price_csv)
    if not path.exists():
        raise FileNotFoundError(f"Price CSV not found: {path}. Run scripts/build_data.py first.")
    df = pd.read_csv(path, parse_dates=["date"])
    missing = set(REQUIRED_PRICE_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"Price CSV missing columns: {sorted(missing)}")
    df["ticker"] = df["ticker"].astype(str).str.upper().str.strip()
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["ticker", "date", "open", "high", "low", "close"])
    return df.sort_values(["ticker", "date"]).reset_index(drop=True)
