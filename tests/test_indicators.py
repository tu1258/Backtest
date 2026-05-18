import pandas as pd

from rs90_backtester.indicators import pivot_high_11, pivot_low_11


def test_pivot_high_11():
    s = pd.Series([1, 3, 2, 4, 3])
    out = pivot_high_11(s)
    assert pd.isna(out.iloc[0])
    assert out.iloc[1] == 3
    assert out.iloc[3] == 4


def test_pivot_low_11():
    s = pd.Series([3, 1, 2, 0, 2])
    out = pivot_low_11(s)
    assert out.iloc[1] == 1
    assert out.iloc[3] == 0
