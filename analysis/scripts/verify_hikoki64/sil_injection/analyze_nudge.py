#!/usr/bin/env python3
"""
Analyze the 4 small-nudge SIL runs (hikoki64 3.3 backing experiment, revision 2).
Small-signal test: a brief ~150ms roll tap nudges the position by a few cm from a
settled hover, then a 40s hold. Cross-checked against analysis/scripts/
poshold_loop_design.py's linear model (K~0.41g, tau~0 -> growing pole at
omega~0.70, sigma~+0.077 for the OLD gains; K=g -> sigma~-0.124, stable).

Metric: py(t) - py(hold_start) in the post-nudge window. Find local peaks
(alternating sign, i.e. successive extrema of the oscillation) and fit an
exponential envelope through their |amplitude| vs time (least-squares on
log|peak|), reporting the growth/decay rate sigma_hat [1/s] and period from the
median peak-to-peak spacing (x2, since each full cycle has one + and one - peak).
"""
import csv
import json
import math
from pathlib import Path

NUDGE_END_T = 12.65   # scenario: nudge tap ends at t = 6+1.5+1+6+0.15 = 14.65s... (see note)
WIN_T0 = 15.0          # start looking for the transient response after nudge+settle
WIN_T1 = 55.0


def load(path):
    with open(path, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        for k in r:
            r[k] = float(r[k])
    return rows


def find_peaks(t, y):
    """Local extrema (both maxima and minima) of y(t), returned as (t, |y|) pairs."""
    peaks = []
    for i in range(1, len(y) - 1):
        if (y[i] - y[i - 1]) * (y[i + 1] - y[i]) < 0:  # sign change in slope
            peaks.append((t[i], abs(y[i])))
    return peaks


def analyze(path, label):
    rows = load(path)
    win = [r for r in rows if WIN_T0 <= r["t"] <= WIN_T1]
    if not win:
        return {"label": label, "error": "empty window"}
    # reference: py at the START of this window (post-nudge, whatever residual offset
    # remains) so we measure the OSCILLATION about the (possibly nonzero) settled point.
    base_py = win[0]["py"]
    t = [r["t"] for r in win]
    dy = [r["py"] - base_py for r in win]

    peaks = find_peaks(t, dy)
    # drop the very first peak or two (transient right after the nudge, not yet in the
    # steady oscillatory regime) — use peaks from the second half of the found set to
    # bias toward the settled behavior, but keep all for the envelope fit.
    amp_max = max(a for _, a in peaks) if peaks else max(abs(v) for v in dy)
    final_amp = abs(dy[-1])

    # Envelope growth/decay rate: least-squares slope of ln(|peak|) vs t (only peaks
    # with amplitude > 1mm, to avoid log(~0) noise).
    usable = [(tp, a) for tp, a in peaks if a > 0.001]
    sigma_hat = None
    if len(usable) >= 3:
        ts = [tp for tp, _ in usable]
        logs = [math.log(a) for _, a in usable]
        n = len(ts)
        mean_t = sum(ts) / n
        mean_l = sum(logs) / n
        num = sum((ts[i] - mean_t) * (logs[i] - mean_l) for i in range(n))
        den = sum((ts[i] - mean_t) ** 2 for i in range(n))
        sigma_hat = num / den if den > 1e-9 else None

    # Period: 2x median spacing between consecutive extrema (peak+trough = half cycle).
    period = None
    if len(peaks) >= 2:
        spacings = [peaks[i + 1][0] - peaks[i][0] for i in range(len(peaks) - 1)]
        spacings.sort()
        med = spacings[len(spacings) // 2]
        period = 2 * med

    verdict = "UNKNOWN"
    if sigma_hat is not None:
        if sigma_hat > 0.01:
            verdict = "GROWING (unstable-like)"
        elif sigma_hat < -0.01:
            verdict = "DECAYING (stable)"
        else:
            verdict = "SUSTAINED (marginal / limit cycle)"

    return {
        "label": label,
        "window_s": [WIN_T0, WIN_T1],
        "n_extrema": len(peaks),
        "amp_max_m": round(amp_max, 4),
        "amp_final_m": round(final_amp, 4),
        "sigma_hat_per_s": (round(sigma_hat, 4) if sigma_hat is not None else None),
        "period_s": (round(period, 2) if period is not None else None),
        "verdict": verdict,
    }


def main():
    base = Path(__file__).parent
    runs = [
        ("nudge_oldgain_ideal.csv", "old_gain + ideal_plant (control)"),
        ("nudge_oldgain_deficient.csv", "old_gain + deficient_plant (torque_authority=0.55, flow_scale=0.66)"),
        ("nudge_newgain_deficient.csv", "new_gain(default) + deficient_plant"),
        ("nudge_newgain_ideal.csv", "new_gain(default) + ideal_plant (control)"),
    ]
    results = []
    for fname, label in runs:
        p = base / fname
        if not p.exists():
            results.append({"label": label, "error": f"missing {fname}"})
            continue
        results.append(analyze(p, label))
    print(json.dumps(results, indent=2, ensure_ascii=False))
    with open(base / "results_nudge.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    main()
