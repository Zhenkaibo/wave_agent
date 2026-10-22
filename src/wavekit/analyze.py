"""Command-line Elliott wave analysis.

Examples
--------
python -m wavekit.analyze --csv data/sample/wti_daily.csv --pivots 74,88.5,80.5,106,89.5 --symbol WTI
python -m wavekit.analyze --csv data/sample/wti_daily.csv --auto --threshold 6 --symbol WTI
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

import pandas as pd

from .data import load_csv
from .fib import retracements, wave5_targets
from .indicators import add_indicators
from .rules import ImpulseCheck, check_impulse
from .zigzag import zigzag

DISCLAIMER = "> 技术分析框架，不构成投资建议。"


# ---------------------------------------------------------------- helpers
def _nearest_bar(df: pd.DataFrame, price: float, col: str) -> int:
    return int((df[col] - price).abs().idxmin())


def locate_manual(df: pd.DataFrame, p: list[float]) -> dict:
    """Map manual wave-3 / wave-4 prices to bars to read momentum and both overlap bases."""
    d = 1 if p[1] > p[0] else -1
    hi_col, lo_col = ("high", "low") if d == 1 else ("low", "high")
    i3 = _nearest_bar(df, p[3], hi_col)
    after3 = df.iloc[i3 + 1:]
    if len(p) == 6:
        i5 = _nearest_bar(df.iloc[i3 + 1:], p[5], hi_col) if len(after3) else i3
        after3 = df.iloc[i3 + 1:i5]
    if after3.empty:
        return {"i3": i3}
    if d == 1:
        i4w, i4c = int(after3[lo_col].idxmin()), int(after3["close"].idxmin())
    else:
        i4w, i4c = int(after3[lo_col].idxmax()), int(after3["close"].idxmax())
    return {
        "i3": i3,
        "i4_wick": i4w, "w4_wick": float(df.at[i4w, lo_col]),
        "i4_close": i4c, "w4_close": float(df.at[i4c, "close"]),
    }


def momentum_compare(df: pd.DataFrame, i3: int, i4: int, d: int) -> dict:
    """Compare MACD/RSI at the wave-3 peak with the leg after wave 4."""
    w3 = df.iloc[max(0, i3 - 5): i3 + 1]
    w5 = df.iloc[i4 + 1:]
    if w5.empty:
        return {}
    pick = (lambda s: s.max()) if d == 1 else (lambda s: s.min())
    out = {
        "w3_macd": float(pick(w3["macd"])), "w5_macd": float(pick(w5["macd"])),
        "w3_rsi": float(pick(w3["rsi"])), "w5_rsi": float(pick(w5["rsi"])),
        "w5_extreme": float(w5["high"].max() if d == 1 else w5["low"].min()),
        "w5_extreme_date": (w5["high"].idxmax() if d == 1 else w5["low"].idxmin()),
        "last_hist": float(df["hist"].iloc[-1]), "last_rsi": float(df["rsi"].iloc[-1]),
        "last_close": float(df["close"].iloc[-1]), "last_date": df["date"].iloc[-1],
    }
    out["w5_extreme_date"] = df.at[out["w5_extreme_date"], "date"]
    out["weaker"] = (out["w5_macd"] < out["w3_macd"]) if d == 1 else (out["w5_macd"] > out["w3_macd"])
    out["cross_down"] = out["last_hist"] < 0 if d == 1 else out["last_hist"] > 0
    return out


def _fmt(x: float) -> str:
    return f"{x:,.2f}"


# ---------------------------------------------------------------- report
def report_count(chk: ImpulseCheck, title: str, mom: dict | None, loc: dict | None, overlap: str) -> list[str]:
    p, d = chk.prices, chk.direction
    L = [f"### {title}", ""]
    L.append("各浪价格：" + "，".join(f"{i}={_fmt(v)}" for i, v in enumerate(p)))
    L.append("")
    L.append("| 规则 | 结果 | 说明 |")
    L.append("|---|---|---|")
    for r in chk.rules:
        L.append(f"| {r.code} | {'通过' if r.ok else '**违反**'} | {r.detail} |")
    if loc and "w4_wick" in loc and overlap in ("both", "wick", "close"):
        for basis in (["close", "wick"] if overlap == "both" else [overlap]):
            px = loc[f"w4_{basis}"]
            ok = (px - p[1]) * d > 0
            L.append(f"| R3（{basis}口径，数据中第4浪 {_fmt(px)}） | {'通过' if ok else '**重叠**'} | 与第1浪顶 {_fmt(p[1])} 比较 |")
    L.append("")
    rt = chk.ratios
    L.append(f"比例：第2浪回撤 {rt['w2_retrace_w1']:.0%}，第3浪/第1浪 {rt['w3_over_w1']:.2f}，"
             f"第4浪回撤第3浪 {rt['w4_retrace_w3']:.0%}" +
             (f"，第5浪/第1浪 {rt['w5_over_w1']:.2f}" if "w5_over_w1" in rt else "") +
             f"。经验分 {chk.score:.0f}/6")
    for n in chk.notes:
        L.append(f"- {n}")
    L.append("")

    if len(p) == 5:
        L.append("**第5浪目标**（从第4浪终点起算）")
        L.append("")
        for name, v in wave5_targets(p):
            tag = ""
            if mom and ((mom["w5_extreme"] - v) * d >= 0):
                tag = "（已触及）"
            L.append(f"- {name}：{_fmt(v)}{tag}")
        L.append(f"- 第3浪顶：{_fmt(p[3])}（突破则第5浪正常延伸）")
        L.append(f"- 作废位：第4浪终点 {_fmt(p[4])}（跌破则第5浪结束或数浪需修正）")
        L.append("")
        top = mom["w5_extreme"] if mom else p[3]
        L.append(f"**假设第5浪在 {_fmt(top)} 见顶的回撤目标**（0→5 全程）：" +
                 "，".join(f"{n} {_fmt(v)}" for n, v in retracements(p[0], top)))
    else:
        L.append("**整轮回撤目标**（0→5）：" + "，".join(f"{n} {_fmt(v)}" for n, v in retracements(p[0], p[5])))
    L.append("")

    if mom:
        L.append("**动能对比**（MACD 12/26/9，RSI 14，收盘价）")
        L.append("")
        L.append("| | 第3浪顶附近 | 第4浪之后 |")
        L.append("|---|---|---|")
        L.append(f"| MACD 线 | {mom['w3_macd']:.2f} | {mom['w5_macd']:.2f} |")
        L.append(f"| RSI | {mom['w3_rsi']:.1f} | {mom['w5_rsi']:.1f} |")
        L.append("")
        L.append(f"- 第4浪之后的极值：{_fmt(mom['w5_extreme'])}（{mom['w5_extreme_date']:%Y-%m-%d}）")
        L.append(f"- 动能{'弱于' if mom['weaker'] else '不弱于'}第3浪" +
                 ("：符合第5浪动能衰竭" if mom["weaker"] else ""))
        L.append(f"- 最新（{mom['last_date']:%Y-%m-%d}，收盘 {_fmt(mom['last_close'])}）："
                 f"MACD 柱 {mom['last_hist']:.2f}，RSI {mom['last_rsi']:.1f} → "
                 + (("已死叉，见顶信号增强" if mom["cross_down"] else "尚未死叉，见顶未确认") if d == 1 else
                    ("MACD 柱已翻正，见底信号增强" if mom["cross_down"] else "MACD 柱仍为负，见底未确认")))
        L.append("")
    return L


# ---------------------------------------------------------------- modes
def run_manual(df: pd.DataFrame, prices: list[float], overlap: str) -> list[str]:
    chk = check_impulse(prices)
    loc = locate_manual(df, prices) if len(df) else None
    mom = None
    if loc and "i4_close" in loc:
        i4 = loc["i4_wick"] if overlap == "wick" else loc["i4_close"]
        mom = momentum_compare(df, loc["i3"], i4, chk.direction)
    status = "所有铁律通过" if chk.valid else "存在违反铁律的地方"
    return [f"## 手动数浪验证（{status}）", ""] + report_count(chk, "用户数浪", mom, loc, overlap)


def run_auto(df: pd.DataFrame, threshold: float, basis: str, top: int, min_bars: int = 2) -> list[str]:
    piv = zigzag(df, threshold, basis)
    L = [f"## 自动数浪（ZigZag {threshold}%，{basis}口径）", "",
         "转折点：" + " → ".join(f"{p.kind}{_fmt(p.price)}({p.date:%m-%d})" for p in piv), ""]
    cands = []
    n = len(piv)
    for size in (6, 5):
        for start in range(max(0, n - 8), n - size + 1):
            seg = piv[start:start + size]
            if any(seg[i + 1].idx - seg[i].idx < min_bars for i in range(len(seg) - 1)):
                continue  # ignore waves that are too short to count
            try:
                chk = check_impulse([p.price for p in seg])
            except ValueError:
                continue
            d = chk.direction
            if size == 5:
                # wave 4 may have extended after the pivot: use the deepest counter-trend
                # extreme seen after wave 3 if it went beyond the detected wave-4 pivot
                after3 = df.iloc[seg[3].idx + 1:]
                if not after3.empty:
                    j = int(after3["low"].idxmin() if d == 1 else after3["high"].idxmax())
                    px = float(df.at[j, "low" if d == 1 else "high"])
                    if (px - seg[4].price) * d < 0:
                        seg = seg[:4] + [type(seg[4])(j, df.at[j, "date"], px, seg[4].kind)]
                        chk = check_impulse([p.price for p in seg])
                        chk.notes.insert(0, f"原第4浪点位之后又出现更深的 {px:g}，按延伸的第4浪重算")
            if not chk.valid:
                if any(r.code == "R3" and not r.ok for r in chk.rules) and all(
                        r.ok for r in chk.rules if r.code != "R3"):
                    chk.notes.append("仅 R3 不满足：作为楔形（ending diagonal）候选保留，降分")
                    chk.score -= 1.5
                else:
                    continue
            if size == 6 and (seg[5].price - seg[3].price) * d < 0:
                chk.score -= 2  # truncated fifth: keep, but rank lower
            recency = start + size  # prefer counts ending at the latest pivots
            key = tuple(round(p.price, 2) for p in seg)
            cands.append((chk.score + 0.5 * recency, chk, seg, key))
    if not cands:
        L.append("没有找到满足铁律的五浪候选。可以调整 --threshold，或改用 --pivots 手动指定。")
        return L
    cands.sort(key=lambda x: -x[0])
    seen, uniq = set(), []
    for c in cands:
        if c[3] not in seen:
            seen.add(c[3])
            uniq.append(c[:3])
    for k, (_, chk, seg) in enumerate(uniq[:top], 1):
        mom = momentum_compare(df, seg[3].idx, seg[4].idx, chk.direction)
        dates = "，".join(f"{i}:{p.date:%m-%d}" for i, p in enumerate(seg))
        state = "已完成五浪" if len(seg) == 6 else "第5浪进行中"
        L += report_count(chk, f"候选 {k}：{state}（{dates}）", mom, None, "none")
    return L


def save_chart(df: pd.DataFrame, prices: list[float] | None, path: Path, symbol: str) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(df["date"], df["close"], color="#555", lw=1.2, label="close")
    if prices and len(prices) == 5:
        for name, v in wave5_targets(prices):
            ax.axhline(v, ls="--", lw=0.8, color="#1D9E75")
            label = name.replace("第1浪", "W1").replace("×", "x")  # ASCII labels avoid missing CJK fonts
            ax.text(df["date"].iloc[0], v, f" W5 target {label} {v:.2f}", va="bottom", fontsize=8, color="#0F6E56")
        ax.axhline(prices[4], ls=":", lw=1, color="#D85A30")
        ax.text(df["date"].iloc[0], prices[4], f" invalidation {prices[4]:.2f}", va="top", fontsize=8, color="#993C1D")
        ax.axhline(prices[3], ls="-", lw=0.6, color="#888")
    ax.set_title(f"{symbol} daily")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Elliott wave analysis")
    ap.add_argument("--csv", required=True, help="daily OHLC csv: date,open,high,low,close")
    ap.add_argument("--symbol", default="SYMBOL")
    ap.add_argument("--pivots", help="manual prices 0,1,2,3,4[,5]")
    ap.add_argument("--auto", action="store_true", help="detect pivots with ZigZag")
    ap.add_argument("--threshold", type=float, default=6.0, help="ZigZag reversal percent")
    ap.add_argument("--basis", choices=["wick", "close"], default="wick")
    ap.add_argument("--overlap", choices=["both", "wick", "close"], default="both")
    ap.add_argument("--top", type=int, default=3)
    ap.add_argument("--min-bars", type=int, default=2, help="minimum bars per wave in auto mode")
    ap.add_argument("--out", default="reports", help="folder for report and chart")
    a = ap.parse_args(argv)

    df = add_indicators(load_csv(a.csv))
    lines = [f"# {a.symbol} 波浪分析", "",
             f"数据：{a.csv}，{df['date'].iloc[0]:%Y-%m-%d} 至 {df['date'].iloc[-1]:%Y-%m-%d}，共 {len(df)} 根日线", ""]
    prices = None
    if a.pivots:
        prices = [float(x) for x in a.pivots.split(",")]
        lines += run_manual(df, prices, a.overlap)
    if a.auto:
        lines += run_auto(df, a.threshold, a.basis, a.top, a.min_bars)
    if not a.pivots and not a.auto:
        ap.error("use --pivots and/or --auto")
    lines += ["", DISCLAIMER]

    text = "\n".join(lines)
    print(text)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d-%H%M")
    (out / f"{a.symbol}-{stamp}.md").write_text(text, encoding="utf-8")
    save_chart(df, prices, out / f"{a.symbol}-{stamp}.png", a.symbol)


if __name__ == "__main__":
    main()
