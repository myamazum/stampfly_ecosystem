#!/usr/bin/env python3
"""
Task 2: divergence scan over 27 flights (2026-06-22T165808 .. 2026-07-18).
Blind re-derivation — criteria defined BEFORE computation, see DIVERGENCE
CRITERIA block below.

r(t) = sqrt(pos_N(t)^2 + pos_E(t)^2)  — raw horizontal radius from the ESKF
origin (pos is [0,0,0] at estimator start; not referenced to the hold
setpoint, since the task asks for r(t) itself, not drift-from-setpoint).

DIVERGENCE CRITERIA (fixed before running on any file):
  1. Flight window = [t_to, t_end] where total_thrust > 0.02 N (motors live),
     first live sample to last live sample (same definition as
     poshold_analysis.py's `live` mask).
  2. If duration < 3.0 s: too short for envelope statistics -> judged
     "N/A(short)". (arm blips / bench tests, not real flights)
  3. Otherwise split [t_to, t_end] at the midpoint t_mid into first half /
     second half.
  4. envelope_early = 90th percentile of r(t) over first half
     envelope_late  = 90th percentile of r(t) over second half
     growth_ratio   = envelope_late / max(envelope_early, 1e-6)
  5. term_r = mean of r(t) over the LAST 1.0 s of the flight window
     (or all samples in the window if window < 1.0 s long)
  6. GROWTH flag  := growth_ratio >= 1.5  AND  (envelope_late - envelope_early) >= 0.10 m
     TERM flag    := term_r > 0.5 m
  7. Judgement:
       "DIVERGENT"  if GROWTH and TERM
       "GROWTH_ONLY" if GROWTH and not TERM  (grew but did not end past 0.5 m)
       "TERM_ONLY"   if TERM and not GROWTH  (ended past 0.5 m but no significant
                       late-half growth vs early-half, e.g. sustained large-radius flight)
       "none"        otherwise
"""
import json, os, glob
import numpy as np

LOGDIR = "/Users/kouhei/tmp/github/stampfly_ecosystem/logs"
LO_NAME = "stampfly_udp_20260622T165808.jsonl"
HI_NAME = "stampfly_udp_20260718T235959.jsonl"


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


def analyze_one(path):
    name = os.path.basename(path)
    S = load(path)
    if "imu" not in S or "ctrl_ref" not in S or "posvel" not in S:
        return dict(log=name, status="missing_streams")

    t0 = S["imu"][0]["ts"]
    t_cr = ts_s(S["ctrl_ref"], t0)
    thrust = arr(S["ctrl_ref"], "total_thrust")
    t_pv = ts_s(S["posvel"], t0)
    pos = arr(S["posvel"], "pos")
    r_all = np.hypot(pos[:, 0], pos[:, 1])

    live = thrust > 0.02
    if not live.any():
        return dict(log=name, status="never_spun", dur_s=0.0, r_max=float(r_all.max()) if len(r_all) else float("nan"))

    i_to = int(np.argmax(live))
    i_end = len(live) - 1 - int(np.argmax(live[::-1]))
    t_to, t_end = t_cr[i_to], t_cr[i_end]
    dur = t_end - t_to

    m = (t_pv >= t_to) & (t_pv <= t_end)
    if not m.any():
        return dict(log=name, status="no_posvel_in_window", dur_s=round(dur, 2))

    tt = t_pv[m]
    rr = r_all[m]
    r_max = float(rr.max())

    if dur < 3.0:
        return dict(log=name, status="N/A(short)", dur_s=round(dur, 2), r_max=round(r_max, 3))

    t_mid = 0.5 * (t_to + t_end)
    m_early = tt < t_mid
    m_late = tt >= t_mid
    if m_early.sum() < 2 or m_late.sum() < 2:
        return dict(log=name, status="N/A(sparse)", dur_s=round(dur, 2), r_max=round(r_max, 3))

    env_early = float(np.percentile(rr[m_early], 90))
    env_late = float(np.percentile(rr[m_late], 90))
    growth_ratio = env_late / max(env_early, 1e-6)
    growth_abs = env_late - env_early

    term_lo = max(t_to, t_end - 1.0)
    m_term = tt >= term_lo
    term_r = float(rr[m_term].mean()) if m_term.any() else float("nan")

    growth_flag = (growth_ratio >= 1.5) and (growth_abs >= 0.10)
    term_flag = term_r > 0.5

    if growth_flag and term_flag:
        verdict = "DIVERGENT"
    elif growth_flag and not term_flag:
        verdict = "GROWTH_ONLY"
    elif term_flag and not growth_flag:
        verdict = "TERM_ONLY"
    else:
        verdict = "none"

    return dict(log=name, status="ok", dur_s=round(dur, 2), r_max=round(r_max, 3),
                env_early=round(env_early, 3), env_late=round(env_late, 3),
                growth_ratio=round(growth_ratio, 2), term_r=round(term_r, 3),
                verdict=verdict)


def main():
    files = sorted(glob.glob(os.path.join(LOGDIR, "stampfly_udp_2026*.jsonl")))
    sel = [f for f in files if LO_NAME <= os.path.basename(f) <= HI_NAME]
    print(f"selected {len(sel)} files")
    rows = []
    for p in sel:
        r = analyze_one(p)
        rows.append(r)

    hdr = f"{'log':40s} {'dur_s':>8} {'r_max':>7} {'verdict':>12}  remark"
    print(hdr)
    print("-" * len(hdr))
    n_divergent = 0
    n_growth_only = 0
    n_term_only = 0
    for r in rows:
        log = r["log"]
        status = r["status"]
        if status == "ok":
            v = r["verdict"]
            if v == "DIVERGENT":
                n_divergent += 1
            elif v == "GROWTH_ONLY":
                n_growth_only += 1
            elif v == "TERM_ONLY":
                n_term_only += 1
            remark = (f"env_early={r['env_early']} env_late={r['env_late']} "
                      f"growth_ratio={r['growth_ratio']} term_r={r['term_r']}")
            print(f"{log:40s} {r['dur_s']:8.2f} {r['r_max']:7.3f} {v:>12}  {remark}")
        else:
            dur = r.get("dur_s", float("nan"))
            rmax = r.get("r_max", float("nan"))
            print(f"{log:40s} {dur:8.2f} {rmax:7.3f} {status:>12}  -")

    print(f"\nn_files = {len(rows)}")
    print(f"n_DIVERGENT   = {n_divergent}")
    print(f"n_GROWTH_ONLY = {n_growth_only}")
    print(f"n_TERM_ONLY   = {n_term_only}")


if __name__ == "__main__":
    main()
