#!/usr/bin/env python3
"""
Analyze the 4 SIL gain-deficit injection runs (hikoki64 3.3 backing experiment).
4条件（旧/新ゲイン x 理想/欠損プラント）の trajectory.csv を解析し、
POS_HOLD窓内の水平ドリフト・duty飽和・成長性から「保持成立/発散」を判定する。

Window: POS_HOLD engages at t=7.6s (matches pos_roll.scn/.expect convention:
A(4s)+B(1s)+C(2s)+C2(0.6s)=7.6s), hold_ms=40000 -> window end = 47.6s.
"""
import csv
import json
import math
import sys
from pathlib import Path

WINDOW_T0 = 7.6
WINDOW_T1 = 47.6
DIVERGE_DRIFT_M = 1.5   # horizontal_drift_max beyond this = clearly diverged (craft is 37g/9cm arm; 1.5m is >>hold tolerance)
DIVERGE_DUTY = 0.98     # duty pinned near 1.0 = motor saturated, loss of control authority


def load_traj(path):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in r:
            r[k] = float(r[k])
    return rows


def analyze(path, label):
    rows = load_traj(path)
    win = [r for r in rows if WINDOW_T0 <= r["t"] <= WINDOW_T1]
    if not win:
        return {"label": label, "error": "empty window"}

    cx, cy = win[0]["px"], win[0]["py"]
    radial = [(r["t"], math.hypot(r["px"] - cx, r["py"] - cy)) for r in win]
    drift_max = max(r for _, r in radial)
    drift_final = radial[-1][1]
    duty_max = max(max(r["m0"], r["m1"], r["m2"], r["m3"]) for r in win)
    tilt_max = max(math.hypot(r["roll"], r["pitch"]) for r in win)

    # Growth check: compare max radial distance in the FIRST half of the window
    # vs the SECOND half. A clearly growing oscillation/drift has second-half max
    # markedly larger than first-half max; a converging/stable hold does not.
    # 成長判定: 窓前半と後半の最大半径を比較。成長中の発散は後半が明確に大きい。
    tmid = (WINDOW_T0 + WINDOW_T1) / 2.0
    first_half = [r for t, r in radial if t < tmid]
    second_half = [r for t, r in radial if t >= tmid]
    max_first = max(first_half) if first_half else float("nan")
    max_second = max(second_half) if second_half else float("nan")

    # First time the radial distance crosses the divergence threshold (if ever) —
    # "time to divergence" reported below.
    # 発散しきい値を最初に超えた時刻（あれば）— 発散までの時間として報告。
    t_diverge = None
    for t, r in radial:
        if r > DIVERGE_DRIFT_M:
            t_diverge = t
            break
    if t_diverge is None:
        for r in win:
            if max(r["m0"], r["m1"], r["m2"], r["m3"]) > DIVERGE_DUTY:
                t_diverge = r["t"]
                break

    diverged = (drift_max > DIVERGE_DRIFT_M) or (duty_max > DIVERGE_DUTY)
    growing = (max_second > 1.3 * max_first) if max_first > 1e-6 else (max_second > 0.05)

    return {
        "label": label,
        "window_s": [WINDOW_T0, WINDOW_T1],
        "drift_max_m": round(drift_max, 4),
        "drift_final_m": round(drift_final, 4),
        "duty_max": round(duty_max, 4),
        "tilt_max_deg_proxy": round(math.degrees(tilt_max), 2),
        "max_radial_first_half_m": round(max_first, 4),
        "max_radial_second_half_m": round(max_second, 4),
        "amplitude_growing": growing,
        "diverged": diverged,
        "time_to_divergence_s": (round(t_diverge - WINDOW_T0, 2) if t_diverge is not None else None),
        "verdict": "DIVERGED" if diverged else ("STABLE" if not growing else "MARGINAL/GROWING"),
    }


def main():
    base = Path(__file__).parent
    runs = [
        ("traj_oldgain_idealplant.csv", "old_gain + ideal_plant (control)"),
        ("traj_oldgain_deficientplant.csv", "old_gain + deficient_plant"),
        ("traj_newgain_deficientplant.csv", "new_gain(default) + deficient_plant"),
        ("traj_newgain_idealplant.csv", "new_gain(default) + ideal_plant (control)"),
    ]
    results = []
    for fname, label in runs:
        p = base / fname
        if not p.exists():
            results.append({"label": label, "error": f"missing {fname}"})
            continue
        results.append(analyze(p, label))

    print(json.dumps(results, indent=2, ensure_ascii=False))
    with open(base / "results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
