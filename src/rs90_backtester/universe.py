from __future__ import annotations

import numpy as np
import pandas as pd


def add_point_in_time_rs(df: pd.DataFrame, months: range = range(1, 13)) -> pd.DataFrame:
    """Add point-in-time RS score/rank using only information known at each date.

    Memory-optimized version:
    - Does not materialize a 12-column concat table for monthly components.
    - Accumulates sum/count arrays directly.
    - Computes daily percentile rank with a vectorized groupby rank.

    Formula:
        For each n in 1..12 months, use n*21 trading-day return.
        Convert cumulative return to geometric monthly return.
        RS score = average of available monthly geometric returns.
        RS rank = daily percentile rank bucket 0..99.
    """
    required = {"ticker", "date", "close"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"missing required columns for RS ranking: {sorted(missing)}")

    out = df.sort_values(["ticker", "date"]).copy()
    out["ticker"] = out["ticker"].astype(str).str.upper()
    out["date"] = pd.to_datetime(out["date"])

    close = out["close"].astype("float64")
    g = out.groupby("ticker", sort=False)["close"]

    score_sum = np.zeros(len(out), dtype="float64")
    score_count = np.zeros(len(out), dtype="int16")

    for n in months:
        shift_n = int(n) * 21
        prev = g.shift(shift_n).astype("float64")
        ret = close / prev - 1.0
        valid = ret.notna() & ((1.0 + ret) > 0.0)
        geo = np.empty(len(out), dtype="float64")
        geo[:] = np.nan
        vals = ret.to_numpy(dtype="float64", copy=False)
        valid_np = valid.to_numpy(dtype=bool, copy=False)
        geo[valid_np] = np.power(1.0 + vals[valid_np], 1.0 / int(n)) - 1.0
        score_sum[valid_np] += geo[valid_np]
        score_count[valid_np] += 1

    rs_score = np.full(len(out), np.nan, dtype="float64")
    valid_score = score_count > 0
    rs_score[valid_score] = (score_sum[valid_score] / score_count[valid_score]) * 100.0
    out["rs_score"] = rs_score

    # Vectorized daily percentile ranking. pct=True gives rank in (0,1].
    # floor(pct*100) can become 100 for the top rank, so clip to 99.
    pct_rank = out.groupby("date", sort=False)["rs_score"].rank(method="average", pct=True)
    out["rs_rank"] = np.floor(pct_rank * 100.0).clip(lower=0, upper=99)
    out.loc[out["rs_score"].isna(), "rs_rank"] = np.nan
    out["in_rs90"] = out["rs_rank"] >= 90
    return out


def recent_rs90(df: pd.DataFrame, recent_days: int = 7, threshold: float = 90) -> pd.DataFrame:
    dates = sorted(pd.to_datetime(df["date"].dropna()).unique())
    use_dates = dates[-int(recent_days):]
    cols = ["date", "ticker", "rs_rank", "rs_score", "close", "volume"]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns for recent_rs90: {missing}")
    out = df[(df["date"].isin(use_dates)) & (df["rs_rank"] >= float(threshold))][cols].copy()
    return out.sort_values(["date", "rs_rank", "rs_score"], ascending=[True, False, False])
