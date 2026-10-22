"""ZigZag pivot detection with a percentage reversal threshold."""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class Pivot:
    idx: int
    date: pd.Timestamp
    price: float
    kind: str  # "H" or "L"


def zigzag(df: pd.DataFrame, threshold_pct: float = 5.0, basis: str = "wick") -> list[Pivot]:
    """Return alternating swing highs/lows.

    A swing is confirmed once price reverses at least ``threshold_pct`` percent from the
    running extreme. ``basis`` is "wick" (high/low) or "close". The final pivot is the
    running, still-unconfirmed extreme.
    """
    if basis not in ("wick", "close"):
        raise ValueError("basis must be 'wick' or 'close'")
    hi = (df["high"] if basis == "wick" else df["close"]).to_numpy()
    lo = (df["low"] if basis == "wick" else df["close"]).to_numpy()
    dates = df["date"].to_numpy()
    th = threshold_pct / 100.0
    n = len(df)
    if n < 2:
        return []

    def mk(i: int, kind: str) -> Pivot:
        return Pivot(i, pd.Timestamp(dates[i]), float(hi[i] if kind == "H" else lo[i]), kind)

    pivots: list[Pivot] = []
    # find the initial direction
    i_hi = i_lo = 0
    direction = 0
    start = 1
    for i in range(1, n):
        if hi[i] > hi[i_hi]:
            i_hi = i
        if lo[i] < lo[i_lo]:
            i_lo = i
        if hi[i_hi] >= lo[i_lo] * (1 + th) and i_hi > i_lo:
            pivots.append(mk(i_lo, "L"))
            direction, cand, start = 1, i_hi, i + 1
            break
        if lo[i_lo] <= hi[i_hi] * (1 - th) and i_lo > i_hi:
            pivots.append(mk(i_hi, "H"))
            direction, cand, start = -1, i_lo, i + 1
            break
    if direction == 0:
        return []

    for i in range(start, n):
        if direction == 1:
            if hi[i] >= hi[cand]:
                cand = i
            elif lo[i] <= hi[cand] * (1 - th):
                pivots.append(mk(cand, "H"))
                direction, cand = -1, i
        else:
            if lo[i] <= lo[cand]:
                cand = i
            elif hi[i] >= lo[cand] * (1 + th):
                pivots.append(mk(cand, "L"))
                direction, cand = 1, i
    pivots.append(mk(cand, "H" if direction == 1 else "L"))
    return pivots
