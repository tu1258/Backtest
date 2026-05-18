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
    """Add daily indicators used by the RS90 backtester.

    Important anti-lookahead rules:
    - Confirmed pivot high/low is shifted by pivot_right + 1 bars so it can only
      be traded after the right-side confirmation bar has closed.
    - n_day_low is shifted by 1 bar, so today's stop only uses lows known before
      today's session.
    """
    if pivot_left < 1 or pivot_right < 1:
        raise ValueError("pivot_left and pivot_right must be >= 1")
    if atr_period < 1:
        raise ValueError("atr_period must be >= 1")
    if n_day_low_period < 1:
        raise ValueError("n_day_low_period must be >= 1")

    required = {"ticker", "date", "open", "high", "low", "close", "volume"}
    missing = required - set(prices.columns)
    if missing:
        raise ValueError(f"missing required price columns: {sorted(missing)}")

    df = prices.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["ticker"] = df["ticker"].astype(str).str.upper()
    df = df.sort_values(["ticker", "date"]).reset_index(drop=True)

    g = df.groupby("ticker", group_keys=False)

    # Moving averages
    df["ma5"] = g["close"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    df["ma10"] = g["close"].transform(lambda s: s.rolling(10, min_periods=10).mean())
    df["ma20"] = g["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    df["ma50"] = g["close"].transform(lambda s: s.rolling(50, min_periods=50).mean())

    # Dollar volume filter: average of daily volume * close, USD millions.
    df["dollar_volume"] = df["volume"].astype(float) * df["close"].astype(float)
    df["avg_value_10"] = g["dollar_volume"].transform(lambda s: s.rolling(10, min_periods=10).mean()) / 1_000_000

    # Daily range / ADR filters.
    df["dr"] = (df["high"].astype(float) / df["low"].astype(float) - 1.0) * 100.0
    df["adr5"] = g["dr"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    df["adr10"] = g["dr"].transform(lambda s: s.rolling(10, min_periods=10).mean())
    df["adr20"] = g["dr"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    df["avg_bar"] = (df["close"].astype(float) + df["high"].astype(float) + df["low"].astype(float)) / 3.0
    df["distance_to_ma5"] = (df["avg_bar"] - df["ma5"]).abs()
    df["adr10_price"] = df["adr10"] / 100.0 * df["close"].astype(float)

    # RSI(2)
    df["rsi2"] = g["close"].transform(lambda s: rsi_wilder(s, 2))

    # ATR
    df["prev_close"] = g["close"].shift(1)
    tr1 = df["high"].astype(float) - df["low"].astype(float)
    tr2 = (df["high"].astype(float) - df["prev_close"].astype(float)).abs()
    tr3 = (df["low"].astype(float) - df["prev_close"].astype(float)).abs()
    df["true_range"] = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df["atr"] = g["true_range"].transform(lambda s: s.rolling(atr_period, min_periods=atr_period).mean())

    # Pivot L,R raw points and confirmed tradable levels.
    df["pivot_high_raw"] = g["high"].transform(lambda s: pivot_high_lr(s, pivot_left, pivot_right))
    df["pivot_low_raw"] = g["low"].transform(lambda s: pivot_low_lr(s, pivot_left, pivot_right))

    # A pivot at t is only known after t + R closes; use it from t + R + 1.
    pivot_shift = pivot_right + 1
    df["confirmed_pivot_high"] = g["pivot_high_raw"].transform(lambda s: s.shift(pivot_shift).ffill())
    df["confirmed_pivot_low"] = g["pivot_low_raw"].transform(lambda s: s.shift(pivot_shift).ffill())

    # Setup / stop fields.
    df["prev_low"] = g["low"].shift(1)
    df["setup_low"] = g["low"].shift(1)
    df["setup_rsi2"] = g["rsi2"].shift(1)
    df["setup_ma50"] = g["ma50"].shift(1)
    df["setup_close"] = g["close"].shift(1)
    df["n_day_low"] = g["low"].transform(lambda s: s.rolling(n_day_low_period, min_periods=n_day_low_period).min().shift(1))

    df.attrs["pivot_left"] = pivot_left
    df.attrs["pivot_right"] = pivot_right
    df.attrs["atr_period"] = atr_period
    df.attrs["n_day_low_period"] = n_day_low_period
    return df


def rsi_wilder(close: pd.Series, period: int = 2) -> pd.Series:
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
    return rsi


def pivot_high_lr(high: pd.Series, left: int = 1, right: int = 1) -> pd.Series:
    h = high.astype(float)
    out = pd.Series(np.nan, index=h.index, dtype=float)
    mask = pd.Series(True, index=h.index)
    for i in range(1, left + 1):
        mask &= h > h.shift(i)
    for i in range(1, right + 1):
        mask &= h > h.shift(-i)
    out.loc[mask] = h.loc[mask]
    return out


def pivot_low_lr(low: pd.Series, left: int = 1, right: int = 1) -> pd.Series:
    l = low.astype(float)
    out = pd.Series(np.nan, index=l.index, dtype=float)
    mask = pd.Series(True, index=l.index)
    for i in range(1, left + 1):
        mask &= l < l.shift(i)
    for i in range(1, right + 1):
        mask &= l < l.shift(-i)
    out.loc[mask] = l.loc[mask]
    return out
