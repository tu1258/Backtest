from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(
    prices: pd.DataFrame,
    *,
    pivot_left: int = 1,
    pivot_right: int = 1,
    atr_period: int = 14,
    n_day_low_period: int = 5,
) -> pd.DataFrame:
    """Add daily indicators for RSI2-focused backtests.

    Anti-lookahead rules:
    - RSI2 next-open entry uses setup_rsi2 = yesterday's RSI2.
    - n_day_low_1..5 are shifted by one bar, so today's stop uses only known lows.
    - intraday RSI2 trigger price is computed from yesterday's Wilder/RMA state.
    """
    required = {"ticker", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"missing required price columns: {sorted(missing)}")

    df = prices.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)
    g = df.groupby("ticker", group_keys=False)

    # Moving averages and liquidity/range filters.
    df["ma5"] = g["close"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    df["ma20"] = g["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    df["ma50"] = g["close"].transform(lambda s: s.rolling(50, min_periods=50).mean())
    df["dollar_volume"] = df["volume"].astype(float) * df["close"].astype(float)
    df["avg_value_10"] = g["dollar_volume"].transform(lambda s: s.rolling(10, min_periods=10).mean()) / 1_000_000
    df["dr"] = (df["high"].astype(float) / df["low"].astype(float) - 1.0) * 100.0
    df["adr5"] = g["dr"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    df["adr10"] = g["dr"].transform(lambda s: s.rolling(10, min_periods=10).mean())
    df["adr20"] = g["dr"].transform(lambda s: s.rolling(20, min_periods=20).mean())

    # RSI2 with Wilder/RMA components. Components are needed to compute the exact live-daily
    # price that would make RSI2 fall below 5 during the session.
    rsi_parts = g["close"].apply(lambda s: rsi_wilder_with_components(s, 2)).reset_index(level=0, drop=True)
    df["rsi2"] = rsi_parts["rsi"].to_numpy()
    df["rsi2_avg_gain"] = rsi_parts["avg_gain"].to_numpy()
    df["rsi2_avg_loss"] = rsi_parts["avg_loss"].to_numpy()
    df["prev_rsi2_avg_gain"] = g["rsi2_avg_gain"].shift(1)
    df["prev_rsi2_avg_loss"] = g["rsi2_avg_loss"].shift(1)

    df["prev_close"] = g["close"].shift(1)
    df["prev_low"] = g["low"].shift(1)
    df["setup_low"] = df["prev_low"]
    df["setup_rsi2"] = g["rsi2"].shift(1)

    # Entry-day filters must use only information available before the entry day.
    # Example: if trading on 12/31, these columns are based on 12/30 close/indicators.
    df["entry_filter_avg_value_10"] = g["avg_value_10"].shift(1)
    df["entry_filter_adr20"] = g["adr20"].shift(1)
    df["entry_filter_close"] = g["close"].shift(1)
    df["entry_filter_ma50"] = g["ma50"].shift(1)

    # Theoretical limit-buy trigger where today's still-forming daily RSI2 becomes <= 5.
    # For RSI2, alpha=1/2. If price is below prev_close, gain_today=0 and loss_today=prev_close-price.
    # RSI <= 5 => RS <= 5/95 = 1/19.
    # prev_avg_gain / (prev_close - price + prev_avg_loss) <= 1/19
    # price <= prev_close + prev_avg_loss - 19 * prev_avg_gain
    df["rsi2_5_trigger_price"] = (
        df["prev_close"].astype(float)
        + df["prev_rsi2_avg_loss"].astype(float)
        - 19.0 * df["prev_rsi2_avg_gain"].astype(float)
    )
    # Only meaningful when trigger is below previous close and positive.
    df.loc[df["rsi2_5_trigger_price"] <= 0, "rsi2_5_trigger_price"] = np.nan
    df.loc[df["rsi2_5_trigger_price"] >= df["prev_close"], "rsi2_5_trigger_price"] = np.nan

    # ATR, shifted stop levels.
    tr1 = df["high"].astype(float) - df["low"].astype(float)
    tr2 = (df["high"].astype(float) - df["prev_close"].astype(float)).abs()
    tr3 = (df["low"].astype(float) - df["prev_close"].astype(float)).abs()
    df["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = g["true_range"].transform(lambda s: s.rolling(atr_period, min_periods=atr_period).mean())

    for n in range(1, 6):
        df[f"n_day_low_{n}"] = g["low"].transform(lambda s, n=n: s.rolling(n, min_periods=n).min().shift(1))

    df.attrs["atr_period"] = atr_period
    return df


def rsi_wilder_with_components(close: pd.Series, period: int = 2) -> pd.DataFrame:
    close = close.astype(float)
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.where(avg_loss != 0, 100)
    rsi = rsi.where(avg_gain != 0, 0)
    return pd.DataFrame({"rsi": rsi, "avg_gain": avg_gain, "avg_loss": avg_loss}, index=close.index)


def rsi_wilder(close: pd.Series, period: int = 2) -> pd.Series:
    return rsi_wilder_with_components(close, period)["rsi"]
