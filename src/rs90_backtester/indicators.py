from __future__ import annotations

import numpy as np
import pandas as pd


def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["ticker", "date"]).copy()
    g = df.groupby("ticker", group_keys=False)
    df["ma10"] = g["close"].transform(lambda s: s.rolling(10, min_periods=10).mean())
    df["ma50"] = g["close"].transform(lambda s: s.rolling(50, min_periods=50).mean())
    df["rsi2"] = g["close"].transform(lambda s: rsi_wilder(s, 2))
    df["pivot_high_raw"] = g.apply(lambda x: pivot_high_11(x["high"])).reset_index(level=0, drop=True)
    df["pivot_low_raw"] = g.apply(lambda x: pivot_low_11(x["low"])).reset_index(level=0, drop=True)

    # A pivot at day t is confirmed only after t+1 closes. It becomes tradable from t+2.
    df["confirmed_pivot_high"] = g["pivot_high_raw"].transform(lambda s: s.shift(2).ffill())
    df["confirmed_pivot_low"] = g["pivot_low_raw"].transform(lambda s: s.shift(2).ffill())
    df["prev_low"] = g["low"].shift(1)
    df["prev_close"] = g["close"].shift(1)
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


def pivot_high_11(high: pd.Series) -> pd.Series:
    h = high.astype(float)
    out = pd.Series(np.nan, index=h.index, dtype=float)
    mask = (h > h.shift(1)) & (h > h.shift(-1))
    out.loc[mask] = h.loc[mask]
    return out


def pivot_low_11(low: pd.Series) -> pd.Series:
    l = low.astype(float)
    out = pd.Series(np.nan, index=l.index, dtype=float)
    mask = (l < l.shift(1)) & (l < l.shift(-1))
    out.loc[mask] = l.loc[mask]
    return out
