from wavekit.fib import wave5_targets
from wavekit.rules import check_impulse


def test_user_wti_count_passes_rules():
    chk = check_impulse([74, 88.5, 80.5, 106, 89.5])
    assert chk.valid
    assert round(chk.ratios["w3_over_w1"], 2) == 1.76


def test_wave4_overlap_is_flagged():
    chk = check_impulse([74, 88.5, 80.5, 106, 86.9])
    assert not chk.valid
    assert any(r.code == "R3" and not r.ok for r in chk.rules)


def test_wave2_below_origin_is_invalid():
    chk = check_impulse([74, 88.5, 72, 106, 89.5])
    assert not chk.valid


def test_wave3_shortest_is_invalid_when_complete():
    chk = check_impulse([100, 120, 110, 125, 118, 140])
    assert not chk.valid


def test_wave5_targets_match_manual_analysis():
    t = dict(wave5_targets([74, 88.5, 80.5, 106, 89.5]))
    assert round(t["0.382 × (0→3)"], 1) == 101.7
    assert round(t["1.000 × 第1浪"], 1) == 104.0
    assert round(t["0.618 × (0→3)"], 1) == 109.3


def test_wave4_beyond_wave3_start_is_invalid():
    chk = check_impulse([106.71, 88.73, 96.78, 86.90, 101.91])
    assert any(r.code == "R4" and not r.ok for r in chk.rules)


def test_auto_finds_user_like_count_on_sample():
    from pathlib import Path
    from wavekit.analyze import run_auto
    from wavekit.data import load_csv
    from wavekit.indicators import add_indicators

    csv = Path(__file__).resolve().parents[1] / "data" / "sample" / "wti_daily.csv"
    text = "\n".join(run_auto(add_indicators(load_csv(str(csv))), 8, "wick", 3))
    assert "0=77.01，1=87.69，2=79.65，3=106.71，4=86.90" in text


def test_downtrend_symmetry():
    chk = check_impulse([100, 80, 90, 50, 70])
    assert chk.valid and chk.direction == -1
