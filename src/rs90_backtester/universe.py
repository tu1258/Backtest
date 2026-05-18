from __future__ import annotations

import numpy as np
import pandas as pd


def add_point_in_time_rs(df: pd.DataFrame, months: range = range(1, 13)) -> pd.DataFrame:
    """Add point-in-time RS score/rank using only data up to each row date.

    Formula mirrors the user's current rs_ranking.py idea: average geometric monthly
    returns over 1..12 months, using 21 trading days per month.
    """
    df = df.sort_values(["ticker", "date"]).copy()
    g = df.groupby("ticker", group_keys=False)
    components: list[pd.Series] = []
    for n in months:
        shift_n = n * 21
        ret = g["close"].transform(lambda s, n=n: (s / s.shift(n * 21) - 1))
        geo = np.sign(1 + ret) * np.power(np.abs(1 + ret), 1 / n) - 1
        # Invalid if return <= -100%; should not happen in adjusted OHLCV, but keep safe.
        geo = geo.where((1 + ret) > 0)
        components.append(geo)
    score = pd.concat(components, axis=1).mean(axis=1, skipna=True)
    df["rs_score"] = score * 100

    def rank_one_day(s: pd.Series) -> pd.Series:
        valid = s.notna()
        out = pd.Series(np.nan, index=s.index, dtype=float)
        if valid.sum() < 2:
            return out
        pct = s[valid].rank(method="average", pct=True)
        out.loc[valid] = np.floor(pct * 100).clip(0, 99)
        return out

    df["rs_rank"] = df.groupby("date", group_keys=False)["rs_score"].apply(rank_one_day)
    df["in_rs90"] = df["rs_rank"] >= 90
    return df


def recent_rs90(df: pd.DataFrame, recent_days: int = 7, threshold: float = 90) -> pd.DataFrame:
    dates = sorted(df["date"].dropna().unique())
    use_dates = dates[-recent_days:]
    cols = ["date", "ticker", "rs_rank", "rs_score", "close", "volume"]
    out = df[(df["date"].isin(use_dates)) & (df["rs_rank"] >= threshold)][cols].copy()
    return out.sort_values(["date", "rs_rank", "rs_score"], ascending=[True, False, False])
