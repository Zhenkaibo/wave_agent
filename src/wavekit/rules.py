"""Elliott wave hard rules and guideline scoring for an impulse 0-1-2-3-4[-5]."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RuleResult:
    code: str
    ok: bool
    detail: str


@dataclass
class ImpulseCheck:
    direction: int  # +1 up, -1 down
    prices: list[float]
    rules: list[RuleResult] = field(default_factory=list)
    ratios: dict[str, float] = field(default_factory=dict)
    score: float = 0.0
    notes: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return all(r.ok for r in self.rules)


def _len(a: float, b: float) -> float:
    return abs(b - a)


def check_impulse(prices: list[float], wave4_extreme: float | None = None) -> ImpulseCheck:
    """Validate 5 (in progress: 0..4) or 6 (complete: 0..5) pivot prices.

    ``wave4_extreme`` optionally overrides the wave-4 price used for the R3 overlap test
    (for example the intraday low when the count itself used closes).
    """
    if len(prices) not in (5, 6):
        raise ValueError("need 5 prices (0-4) or 6 prices (0-5)")
    p = prices
    d = 1 if p[1] > p[0] else -1
    chk = ImpulseCheck(direction=d, prices=list(p))

    # shape: alternate up/down in the trend direction
    shape_ok = all((p[i + 1] - p[i]) * d * (1 if i % 2 == 0 else -1) > 0 for i in range(len(p) - 1))
    chk.rules.append(RuleResult("SHAPE", shape_ok, "各点须交替：顺势-逆势-顺势…"))

    w1, w2, w3, w4 = _len(p[0], p[1]), _len(p[1], p[2]), _len(p[2], p[3]), _len(p[3], p[4])
    r1 = (p[2] - p[0]) * d > 0
    chk.rules.append(RuleResult("R1", r1, f"第2浪终点 {p[2]:g} 不得越过起点 {p[0]:g}"))

    w4_px = p[4] if wave4_extreme is None else wave4_extreme
    r3 = (w4_px - p[1]) * d > 0
    chk.rules.append(RuleResult("R3", r3, f"第4浪 {w4_px:g} 不得进入第1浪区间（第1浪顶 {p[1]:g}）"))
    if not r3:
        chk.notes.append("第4浪与第1浪重叠：标准推动浪不成立，可考虑楔形（ending diagonal）")
    r4 = w4 < w3
    chk.rules.append(RuleResult("R4", r4, "第4浪不能回撤超过整个第3浪（不越过第3浪起点）"))

    chk.ratios = {
        "w2_retrace_w1": w2 / w1 if w1 else float("nan"),
        "w3_over_w1": w3 / w1 if w1 else float("nan"),
        "w4_retrace_w3": w4 / w3 if w3 else float("nan"),
    }
    if len(p) == 6:
        w5 = _len(p[4], p[5])
        r2 = not (w3 < w1 and w3 < w5)
        chk.rules.append(RuleResult("R2", r2, "第3浪不能是 1、3、5 中最短"))
        chk.ratios["w5_over_w1"] = w5 / w1 if w1 else float("nan")
        if (p[5] - p[3]) * d < 0:
            chk.notes.append("第5浪未越过第3浪顶：截断（失败）的第5浪")
    else:
        r2 = w3 >= w1  # 0..4 only: if w3 < w1, w5 must stay shorter than w3
        chk.rules.append(RuleResult(
            "R2", True,
            "第3浪长于第1浪，第5浪长度不受限" if r2 else f"第3浪短于第1浪：第5浪长度必须 < {w3:g}",
        ))

    # guideline score
    s = 0.0
    r = chk.ratios["w2_retrace_w1"]
    s += 2 if 0.5 <= r <= 0.618 else (1 if 0.382 <= r <= 0.786 else 0)
    r = chk.ratios["w3_over_w1"]
    s += 2 if r >= 1.618 else (1 if r >= 1.0 else 0)
    if r >= 1.618:
        chk.notes.append(f"第3浪为延长浪（{r:.2f} × 第1浪）→ 第5浪常见长度 ≈ 第1浪")
    r = chk.ratios["w4_retrace_w3"]
    s += 1 if 0.236 <= r <= 0.5 else 0
    if r > 0.5:
        chk.notes.append(f"第4浪回撤第3浪 {r:.0%}，偏深")
    if abs(chk.ratios["w2_retrace_w1"] - chk.ratios["w4_retrace_w3"]) > 0.15:
        s += 1  # alternation in depth
    chk.score = s
    return chk
