#!/usr/bin/env python3
"""
Task 1 v4 — direct comparison of envelope-decay estimate between:
  (A) the "early stable oscillation" sub-window t in [t_to, 13.0]s (before the
      terminal divergence that starts at t~13.1s, visible as y crossing zero and
      diving monotonically to -0.7m by end of flight window)
  (B) the full flight window (includes the terminal divergence)
on BOTH x and y (not just x), using the same Hilbert/bandpass methodology as v3,
plus coarse 2-4 point peak/trough log-slope for direct cross-check.
Log: stampfly_udp_20260622T161055.jsonl
"""
import json
import numpy as np
from scipy import signal, stats
import sys
sys.path.insert(0, "/private/tmp/claude-501/-Users-kouhei-tmp-github-stampfly-ecosystem/5e87008a-97a4-42d5-9e0e-02387c2a8022/scratchpad/verify_A")
from task1_v3_final import load, arr, exp_fit, LOG

OUT = "/private/tmp/claude-501/-Users-kouhei-tmp-github-stampfly-ecosystem/5e87008a-97a4-42d5-9e0e-02387c2a8022/scratchpad/verify_A"


def periodogram_peak(sig_dt, fs, order=3):
    f, P = signal.periodogram(sig_dt, fs=fs, window="hann", detrend="linear")
    mask = (f > 0.02) & (f <= 5.0)
    idxl = signal.argrelmax(P[mask], order=order)[0]
    if len(idxl) == 0:
        return None, f, P
    fc = f[mask][idxl[np.argmax(P[mask][idxl])]]
    return fc, f, P


def hilbert_envelope_fit(sig_dt, t_u, fs, f_center, label, trim_frac=0.05):
    f_lo, f_hi = f_center * 0.5, f_center * 2.2
    sos = signal.butter(4, [f_lo, f_hi], btype="bandpass", fs=fs, output="sos")
    bp = signal.sosfiltfilt(sos, sig_dt)
    env = np.abs(signal.hilbert(bp))
    edge = max(int(trim_frac * len(t_u)), 5)
    t_fit = t_u[edge:-edge]
    env_fit = env[edge:-edge]
    return exp_fit(t_fit, env_fit, label), (f_lo, f_hi)


def main():
    S = load(LOG)
    t0 = S["imu"][0]["ts"]
    t_cr = (arr(S["ctrl_ref"], "ts") - t0) / 1e6
    thrust = arr(S["ctrl_ref"], "total_thrust")
    live = thrust > 0.02
    i_to = int(np.argmax(live))
    i_end = len(live) - 1 - int(np.argmax(live[::-1]))
    t_to, t_end = t_cr[i_to], t_cr[i_end]

    t_pv = (arr(S["posvel"], "ts") - t0) / 1e6
    pos = arr(S["posvel"], "pos")
    m = (t_pv >= t_to) & (t_pv <= t_end)
    t = t_pv[m]
    x = pos[m, 0]
    y = pos[m, 1]
    r = np.hypot(x, y)
    dt_med = float(np.median(np.diff(t)))
    fs = 1.0 / dt_med
    t_u = np.arange(t[0], t[-1], dt_med)
    x_u = np.interp(t_u, t, x)
    y_u = np.interp(t_u, t, y)
    r_u = np.interp(t_u, t, r)

    windows = {
        "full_window": (t_to, t_end),
        "early_stable_t_to_13.0": (t_to, 13.0),
    }

    results = {}
    for wname, (lo, hi) in windows.items():
        mm = (t_u >= lo) & (t_u <= hi)
        tt = t_u[mm]
        xx = signal.detrend(x_u[mm], type="linear")
        yy = signal.detrend(y_u[mm], type="linear")
        print(f"\n########## window={wname}  t=[{lo},{hi}]  n={mm.sum()} ##########")
        fcx, fx, Px = periodogram_peak(xx, fs)
        fcy, fyf, Py = periodogram_peak(yy, fs)
        print(f"periodogram dominant local-max freq: x={fcx}, y={fcy}")
        res_w = {"n": int(mm.sum()), "fcx_hz": fcx, "fcy_hz": fcy}
        if fcx:
            fit_x, band_x = hilbert_envelope_fit(xx, tt, fs, fcx, f"{wname}: x Hilbert env")
            res_w["hilbert_x"] = fit_x
            res_w["band_x"] = band_x
        if fcy:
            fit_y, band_y = hilbert_envelope_fit(yy, tt, fs, fcy, f"{wname}: y Hilbert env")
            res_w["hilbert_y"] = fit_y
            res_w["band_y"] = band_y
        results[wname] = res_w

    # ---- coarse peak/trough log-slope, x-only and radial, early_stable window ----
    mm = (t_u >= t_to) & (t_u <= 13.0)
    tt, rr, xx_raw = t_u[mm], r_u[mm], x_u[mm]
    peaks_r, _ = signal.find_peaks(rr, distance=int(0.6 * 4.84 * fs))
    troughs_r, _ = signal.find_peaks(-rr, distance=int(0.6 * 4.84 * fs))
    print(f"\nearly_stable radial coarse peaks: t={tt[peaks_r]}  r={rr[peaks_r]}")
    print(f"early_stable radial coarse troughs: t={tt[troughs_r]}  r={rr[troughs_r]}")
    if len(peaks_r) >= 2:
        t1, t2 = tt[peaks_r][0], tt[peaks_r][-1]
        r1, r2 = rr[peaks_r][0], rr[peaks_r][-1]
        sigma_pk = np.log(r2 / r1) / (t2 - t1)
        print(f"  2-point peak-to-peak sigma (radial) = {sigma_pk:.5f} /s  "
              f"(from r={r1:.4f}@t={t1:.2f} to r={r2:.4f}@t={t2:.2f})")
    if len(troughs_r) >= 2:
        t1, t2 = tt[troughs_r][-2], tt[troughs_r][-1]
        r1, r2 = rr[troughs_r][-2], rr[troughs_r][-1]
        if r1 > 1e-4:
            sigma_tr = np.log(r2 / r1) / (t2 - t1)
            print(f"  2-point trough-to-trough sigma (radial, excl. t=0 start) = {sigma_tr:.5f} /s "
                  f"(from r={r1:.4f}@t={t1:.2f} to r={r2:.4f}@t={t2:.2f})")

    with open(f"{OUT}/task1_v4_subwindow_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nsaved: {OUT}/task1_v4_subwindow_results.json")


if __name__ == "__main__":
    main()
