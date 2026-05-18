from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame, pivot_left: int = 1, pivot_right: int = 1) -> pd.DataFrame:
    if pivot_left < 1 or pivot_right < 1:
        raise ValueError("pivot_left and pivot_right must both be >= 1")

    df = df.sort_values(["ticker", "date"]).copy()
    g = df.groupby("ticker", group_keys=False)

    # Moving averages
    df["ma5"] = g["close"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    df["ma10"] = g["close"].transform(lambda s: s.rolling(10, min_periods=10).mean())
    df["ma50"] = g["close"].transform(lambda s: s.rolling(50, min_periods=50).mean())

    # Liquidity / volatility filters.
    # DR/ADR are expressed in percent, e.g. 3.5 means 3.5%.
    df["dr"] = (df["high"].astype(float) / df["low"].astype(float) - 1.0) * 100.0
    df["adr5"] = g["dr"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    df["adr10"] = g["dr"].transform(lambda s: s.rolling(10, min_periods=10).mean())
    df["adr20"] = g["dr"].transform(lambda s: s.rolling(20, min_periods=20).mean())

    # Average 10-day dollar volume in USD millions.
    # This is avg(volume * close), not avg(volume) * current close.
    df["dollar_volume"] = df["volume"].astype(float) * df["close"].astype(float)
    df["avg_value_10"] = g["dollar_volume"].transform(lambda s: s.rolling(10, min_periods=10).mean()) / 1_000_000.0

    # Breakout consolidation filter:
    # abs(avg_bar - ma5) < adr10 / 100 * close
    df["avg_bar"] = (df["close"].astype(float) + df["high"].astype(float) + df["low"].astype(float)) / 3.0
    df["distance_to_ma5"] = (df["avg_bar"] - df["ma5"]).abs()
    df["adr10_price"] = df["adr10"] / 100.0 * df["close"].astype(float)

    # RSI and pivots
    df["rsi2"] = g["close"].transform(lambda s: rsi_wilder(s, 2))
    df["pivot_high_raw"] = g.apply(lambda x: pivot_high(x["high"], left=pivot_left, right=pivot_right)).reset_index(level=0, drop=True)
    df["pivot_low_raw"] = g.apply(lambda x: pivot_low(x["low"], left=pivot_left, right=pivot_right)).reset_index(level=0, drop=True)

    # A pivot at day t is confirmed only after t + right closes.
    # It becomes tradable from t + right + 1.
    confirmation_shift = pivot_right + 1
    df["confirmed_pivot_high"] = g["pivot_high_raw"].transform(lambda s: s.shift(confirmation_shift).ffill())
    df["confirmed_pivot_low"] = g["pivot_low_raw"].transform(lambda s: s.shift(confirmation_shift).ffill())

    df["pivot_left"] = int(pivot_left)
    df["pivot_right"] = int(pivot_right)

    df["prev_low"] = g["low"].shift(1)
    df["prev_close"] = g["close"].shift(1)

    # RSI2 setup uses the previous completed daily bar, then enters next open.
    df["setup_low"] = g["low"].shift(1)
    df["setup_rsi2"] = g["rsi2"].shift(1)
    df["setup_ma50"] = g["ma50"].shift(1)
    df["setup_close"] = g["close"].shift(1)

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


def pivot_high(high: pd.Series, left: int = 1, right: int = 1) -> pd.Series:
    h = high.astype(float)
    out = pd.Series(np.nan, index=h.index, dtype=float)
    mask = pd.Series(True, index=h.index)
    for i in range(1, left + 1):
        mask &= h > h.shift(i)
    for i in range(1, right + 1):
        mask &= h > h.shift(-i)
    out.loc[mask] = h.loc[mask]
    return out


def pivot_low(low: pd.Series, left: int = 1, right: int = 1) -> pd.Series:
    l = low.astype(float)
    out = pd.Series(np.nan, index=l.index, dtype=float)
    mask = pd.Series(True, index=l.index)
    for i in range(1, left + 1):
        mask &= l < l.shift(i)
    for i in range(1, right + 1):
        mask &= l < l.shift(-i)
    out.loc[mask] = l.loc[mask]
    return out


# Backward-compatible names for existing tests/imports.
def pivot_high_11(high: pd.Series) -> pd.Series:
    return pivot_high(high, left=1, right=1)


def pivot_low_11(low: pd.Series) -> pd.Series:
    return pivot_low(low, left=1, right=1)
