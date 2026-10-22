"""Fibonacci projections for wave 5 and retracements after a completed impulse."""
from __future__ import annotations


def wave5_targets(p: list[float]) -> list[tuple[str, float]]:
    """Common wave-5 targets measured from the end of wave 4."""
    d = 1 if p[1] > p[0] else -1
    w1 = abs(p[1] - p[0])
    w03 = abs(p[3] - p[0])
    out = [
        ("0.618 × 第1浪", p[4] + d * 0.618 * w1),
        ("0.382 × (0→3)", p[4] + d * 0.382 * w03),
        ("1.000 × 第1浪", p[4] + d * 1.0 * w1),
        ("0.618 × (0→3)", p[4] + d * 0.618 * w03),
    ]
    return sorted(out, key=lambda x: x[1] * d)


def retracements(start: float, end: float, levels=(0.382, 0.5, 0.618)) -> list[tuple[str, float]]:
    """Retracement levels of the move start→end."""
    return [(f"{lv:.1%}", end - (end - start) * lv) for lv in levels]
