#!/usr/bin/env python3
"""
Task 1: 2026-06-27 3-minute flight — battery voltage vs altitude-std / motor-duty
window correlation, blind re-derivation (no report reading).
"""
import json, sys
import numpy as np

LOG = "/Users/kouhei/tmp/github/stampfly_ecosystem/logs/stampfly_udp_20260627T020137.jsonl"


def load(path):
    S = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            S.setdefault(d.get("id", "?"), []).append(d)
    return S


def arr(records, key):
    return np.array([r[key] for r in records], dtype=float)


def ts_s(records, t0):
    return np.array([(r["ts"] - t0) / 1e6 for r in records], dtype=float)


def main():
    S = load(LOG)
    for k in S:
        print(k, len(S[k]))

    t0 = S["imu"][0]["ts"]

    t_cr = ts_s(S["ctrl_ref"], t0)
    thrust = arr(S["ctrl_ref"], "total_thrust")
    duty = arr(S["ctrl_ref"], "motor_duty")  # shape (N,4) presumably

    t_pv = ts_s(S["posvel"], t0)
    pos = arr(S["posvel"], "pos")
    alt = -pos[:, 2]  # NED: D component -> altitude = -D

    t_st = ts_s(S["status"], t0)
    volt = arr(S["status"], "voltage")

    # ---- flight window: thrust > 0.02 ----
    live = thrust > 0.02
    if not live.any():
        print("no live thrust samples")
        return
    i_to = int(np.argmax(live))
    i_end = len(live) - 1 - int(np.argmax(live[::-1]))
    t_to, t_end = t_cr[i_to], t_cr[i_end]
    dur = t_end - t_to
    print(f"flight window: takeoff={t_to:.2f}s end={t_end:.2f}s duration={dur:.2f}s")

    duty_mean_all = duty.mean(axis=1)  # mean over 4 motors, per sample

    def analyze_windows(win_s):
        edges = np.arange(t_to, t_end, win_s)
        rows = []
        for lo in edges:
            hi = lo + win_s
            if hi > t_end:
                # keep partial trailing window only if it has enough span (>= 50% of win_s)
                if (t_end - lo) < 0.5 * win_s:
                    continue
                hi = t_end
            # voltage window mean
            mv = (t_st >= lo) & (t_st < hi)
            # altitude window std
            ma = (t_pv >= lo) & (t_pv < hi)
            # duty window mean
            md = (t_cr >= lo) & (t_cr < hi)
            if mv.sum() == 0 or ma.sum() < 2 or md.sum() == 0:
                continue
            v_mean = volt[mv].mean()
            a_std = alt[ma].std()
            d_mean = duty_mean_all[md].mean()
            rows.append((lo, hi, v_mean, a_std, d_mean, mv.sum(), ma.sum(), md.sum()))
        return rows

    for win_s in (20, 30):
        rows = analyze_windows(win_s)
        print(f"\n=== window = {win_s}s  (n_windows={len(rows)}) ===")
        print(f"{'lo':>6} {'hi':>6} {'V_mean':>8} {'alt_std':>9} {'duty_mean':>10} {'n_v':>5} {'n_a':>5} {'n_d':>5}")
        for r in rows:
            lo, hi, v, a, d, nv, na, nd = r
            print(f"{lo:6.1f} {hi:6.1f} {v:8.4f} {a:9.5f} {d:10.5f} {nv:5d} {na:5d} {nd:5d}")
        if len(rows) >= 3:
            vs = np.array([r[2] for r in rows])
            as_ = np.array([r[3] for r in rows])
            ds = np.array([r[4] for r in rows])
            corr_va = np.corrcoef(vs, as_)[0, 1]
            corr_vd = np.corrcoef(vs, ds)[0, 1]
            print(f"corr(V_mean, alt_std)   = {corr_va:.4f}   (n={len(rows)})")
            print(f"corr(V_mean, duty_mean) = {corr_vd:.4f}   (n={len(rows)})")
        else:
            print("not enough windows for correlation (n<3)")


if __name__ == "__main__":
    main()
