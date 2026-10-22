"""Load OHLC data from CSV."""
from __future__ import annotations

import pandas as pd

REQUIRED = ["date", "open", "high", "low", "close"]


def load_csv(path: str) -> pd.DataFrame:
    """Read a daily OHLC CSV with columns date,open,high,low,close (case-insensitive)."""
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"CSV is missing columns: {missing}. Expected {REQUIRED}.")
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").drop_duplicates("date").reset_index(drop=True)
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["high", "low", "close"]).reset_index(drop=True)
