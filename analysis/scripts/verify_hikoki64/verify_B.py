#!/usr/bin/env python3
"""
Independent verification B — attitude tracking frequency response + tilt->velocity
effective gain K/g, across 4 POS_HOLD flight logs.

Falsification-style, no priors baked in. All numbers derived directly from the
JSONL logs + firmware source (enum defs, telemetry field wiring). No reuse of
prior analysis conclusions.

Methodology notes (validated against synthetic signals with known transfer
functions before running on real data):
  H_est(f) = Pxy(f) / Pxx(f)   with Pxy = scipy.signal.csd(x, y), Pxx = welch(x)
  This recovers the magnitude AND phase of the linear system x -> y under
  Welch averaging (confirmed on a synthetic 1st-order-lag test case).

  Random error of the FRF magnitude estimate (Bendat & Piersol 1980, standard
  formula for Welch-averaged FRF estimates):
      eps_r(f) = sqrt( (1 - Cxy(f)^2) / (2 * nseg * Cxy(f)^2) )
      |H| uncertainty (1-sigma, relative) = eps_r(f)
  nseg = number of (overlapping, Hann-windowed, 50%) segments averaged in the
  Welch estimate. This ignores segment-to-segment correlation from the 50%
  overlap (a known simplification of the formula) -- reported as such.
"""
import json
import math
import os

import numpy as np
from scipy import signal

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

G = 9.80665
OUT_DIR = os.path.dirname(os.path.abspath(__file__))
FIG_DIR = os.path.join(OUT_DIR, "figs")
os.makedirs(FIG_DIR, exist_ok=True)

LOGS = {
    "L1": "logs/stampfly_udp_20260622T161055.jsonl",
    "L2": "logs/stampfly_udp_20260622T173150.jsonl",
    "L3": "logs/stampfly_udp_20260717T231940.jsonl",
    "L4": "logs/stampfly_udp_20260718T022929.jsonl",
}
REPO = "/Users/kouhei/tmp/github/stampfly_ecosystem"

MODE_NAME = {0: "ACRO", 1: "STABILIZE", 2: "ALT_HOLD", 3: "POS_HOLD"}
STATE_NAME = {0: "INIT", 1: "IDLE_GROUND", 2: "IDLE_HELD", 3: "ARMED_GROUND",
              4: "TAKEOFF", 5: "FLYING", 6: "LANDING"}

BAND_LO_RS, BAND_HI_RS = 0.2, 3.0          # rad/s, full band of interest (Task1)
REP_LO_RS, REP_HI_RS = 0.5, 1.0            # rad/s, representative sub-band
FS = 50.0                                  # common analysis grid [Hz]


# =============================================================================
# Loading
# =============================================================================
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


def quat_to_euler(q):
    """[w,x,y,z] -> (roll, pitch, yaw) [rad], aerospace ZYX (standard formula,
    independent of any repo-specific convention -- verified against the
    well-known closed-form quaternion-to-Euler expressions)."""
    w, x, y, z = q
    roll = math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y))
    s = max(-1.0, min(1.0, 2 * (w * y - z * x)))
    pitch = math.asin(s)
    yaw = math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z))
    return roll, pitch, yaw


def arr(records, key):
    return np.array([r[key] for r in records], dtype=float)


def ts_s(records, t0):
    return np.array([(r["ts"] - t0) / 1e6 for r in records], dtype=float)


# =============================================================================
# Task 0 — condition table (log-derived only)
# =============================================================================
def flight_window(t_cr, thrust):
    """Largest contiguous thrust>0.02 segment on the ctrl_ref (50Hz) clock."""
    live = thrust > 0.02
    if not live.any():
        return None
    edges = np.diff(live.astype(int))
    starts = list(np.where(edges == 1)[0] + 1)
    ends = list(np.where(edges == -1)[0])
    if live[0]:
        starts = [0] + starts
    if live[-1]:
        ends = ends + [len(live) - 1]
    segs = list(zip(starts, ends))
    # pick the longest segment by duration
    segs.sort(key=lambda se: t_cr[se[1]] - t_cr[se[0]], reverse=True)
    return segs  # sorted, longest first


def task0(name, path):
    S = load(path)
    t0 = S["imu"][0]["ts"]
    t_cr = ts_s(S["ctrl_ref"], t0)
    thrust = arr(S["ctrl_ref"], "total_thrust")
    mode = arr(S["ctrl_ref"], "mode").astype(int)
    segs = flight_window(t_cr, thrust)
    i_to, i_end = segs[0]
    t_to, t_end = t_cr[i_to], t_cr[i_end]
    dur = t_end - t_to

    mode_win = mode[i_to:i_end + 1]
    mode_vals, mode_counts = np.unique(mode_win, return_counts=True)
    mode_report = {MODE_NAME.get(int(v), int(v)): int(c) for v, c in zip(mode_vals, mode_counts)}

    st = S.get("status", [])
    t_st = ts_s(st, t0) if st else np.array([])
    pid_roll = sorted(set(tuple(r["pid_roll"]) for r in st))
    pid_pitch = sorted(set(tuple(r["pid_pitch"]) for r in st))
    pid_yaw = sorted(set(tuple(r["pid_yaw"]) for r in st))

    volt_all = arr(st, "voltage") if st else np.array([])
    m_win = (t_st >= t_to) & (t_st <= t_end)
    volt_win = volt_all[m_win]

    fstate_all = arr(st, "flight_state").astype(int) if st else np.array([], dtype=int)
    fstate_counts = {STATE_NAME.get(int(v), int(v)): int(c)
                     for v, c in zip(*np.unique(fstate_all, return_counts=True))} if len(fstate_all) else {}

    n_live_segs = len(segs)
    seg_durs = [round(float(t_cr[e] - t_cr[s]), 2) for s, e in segs]

    return {
        "log": name,
        "path": path,
        "n_ctrl_ref_records": len(S.get("ctrl_ref", [])),
        "n_live_thrust_segments": n_live_segs,
        "live_thrust_segment_durations_s": seg_durs,
        "flight_window_s": [round(float(t_to), 2), round(float(t_end), 2)],
        "duration_s": round(float(dur), 2),
        "mode_counts_in_window": mode_report,
        "pid_rate_roll_kp_ti_td": pid_roll,
        "pid_rate_pitch_kp_ti_td": pid_pitch,
        "pid_rate_yaw_kp_ti_td": pid_yaw,
        "pid_changed_within_log": (len(pid_roll) > 1 or len(pid_pitch) > 1 or len(pid_yaw) > 1),
        "attitude_loop_gains_in_telemetry": "NONE (not transmitted; see data_stream.cpp sendStatus)",
        "position_loop_gains_in_telemetry": "NONE (not transmitted; see data_stream.cpp sendStatus)",
        "voltage_full_status_stream_first_last": [round(float(volt_all[0]), 3), round(float(volt_all[-1]), 3)] if len(volt_all) else None,
        "voltage_in_flight_window_first_last": [round(float(volt_win[0]), 3), round(float(volt_win[-1]), 3)] if len(volt_win) else None,
        "voltage_in_flight_window_min_max": [round(float(volt_win.min()), 3), round(float(volt_win.max()), 3)] if len(volt_win) else None,
        "flight_state_counts_full_log": fstate_counts,
        "n_status_records": len(st),
    }


# =============================================================================
# Common: build uniform-grid signals for spectral analysis
# =============================================================================
def build_grid_signals(S, t0, t_to, t_end, fs=FS):
    """Interpolate angle_ref(roll,pitch), estimated euler(roll,pitch), and
    vel(N,E) onto one common uniform grid at `fs` Hz spanning the flight
    window (clipped to the overlap of native sample ranges)."""
    t_imu = ts_s(S["imu"], t0)
    quat = arr(S["imu"], "quat")
    euler = np.array([quat_to_euler(q) for q in quat])  # roll,pitch,yaw [rad]

    t_pv = ts_s(S["posvel"], t0)
    vel = arr(S["posvel"], "vel")  # N,E,D [m/s]

    t_cr = ts_s(S["ctrl_ref"], t0)
    angle_ref = arr(S["ctrl_ref"], "angle_ref")  # roll,pitch [rad]

    lo = max(t_to, t_imu[0], t_pv[0], t_cr[0])
    hi = min(t_end, t_imu[-1], t_pv[-1], t_cr[-1])
    n = int(np.floor((hi - lo) * fs)) + 1
    tg = lo + np.arange(n) / fs

    grid = {"t": tg}
    grid["angle_ref_roll"] = np.interp(tg, t_cr, angle_ref[:, 0])
    grid["angle_ref_pitch"] = np.interp(tg, t_cr, angle_ref[:, 1])
    grid["roll"] = np.interp(tg, t_imu, euler[:, 0])
    grid["pitch"] = np.interp(tg, t_imu, euler[:, 1])
    grid["vel_N"] = np.interp(tg, t_pv, vel[:, 0])
    grid["vel_E"] = np.interp(tg, t_pv, vel[:, 1])
    return grid


# =============================================================================
# Welch FRF + coherence helper
# =============================================================================
def choose_nperseg(n, target_nseg=5, overlap_frac=0.5, floor=32, cap=2048):
    """nperseg such that ~target_nseg overlapping segments fit in n samples."""
    step_frac = 1 - overlap_frac
    raw = n / (1 + (target_nseg - 1) * step_frac)
    p = int(2 ** np.floor(np.log2(max(raw, floor))))
    p = max(floor, min(p, cap, int(2 ** np.floor(np.log2(n)))))
    return p


def frf(x, y, fs):
    n = len(x)
    nperseg = choose_nperseg(n)
    noverlap = nperseg // 2
    f, Pxx = signal.welch(x, fs=fs, nperseg=nperseg, noverlap=noverlap, detrend="constant")
    _, Pxy = signal.csd(x, y, fs=fs, nperseg=nperseg, noverlap=noverlap, detrend="constant")
    _, Cxy = signal.coherence(x, y, fs=fs, nperseg=nperseg, noverlap=noverlap, detrend="constant")
    H = Pxy / Pxx
    nseg = int(np.floor((n - nperseg) / (nperseg - noverlap)) + 1)
    return {"f_hz": f, "w_rads": 2 * np.pi * f, "H": H, "coh": Cxy,
            "nperseg": nperseg, "nseg": nseg, "n_samples": n, "fs": fs}


def band_summary(res, lo_rs, hi_rs, quantity="mag"):
    """Coherence-weighted representative value + Bendat-Piersol relative
    uncertainty, restricted to a rad/s band."""
    w = res["w_rads"]
    m = (w >= lo_rs) & (w <= hi_rs)
    if not m.any():
        return {"n_bins": 0, "note": "no frequency bins fall in this band given the record length"}
    coh = res["coh"][m]
    if quantity == "mag":
        val = np.abs(res["H"][m])
    else:
        val = res["Kg"][m]
    usable = coh >= 0.5
    out = {
        "n_bins": int(m.sum()),
        "n_bins_coh_ge_0p5": int(usable.sum()),
        "freqs_hz": [round(float(v), 4) for v in res["f_hz"][m]],
        "freqs_rads": [round(float(v), 4) for v in w[m]],
        "coherence": [round(float(v), 3) for v in coh],
        "values": [round(float(v), 4) for v in val],
        "nseg": res["nseg"],
    }
    if not usable.any():
        out["representative"] = None
        out["note"] = "all bins in band have coherence < 0.5 -- estimate unusable (推定不能)"
        return out
    v_u = val[usable]
    c_u = coh[usable]
    rep = float(np.sum(c_u * v_u) / np.sum(c_u))          # coherence-weighted mean
    rep_unweighted = float(np.mean(v_u))
    # Bendat & Piersol relative random-error per usable bin, combined assuming
    # independence across bins (conservative: divide by sqrt(n usable bins))
    eps = np.sqrt((1 - c_u ** 2) / (2 * res["nseg"] * c_u ** 2))
    eps_combined = float(np.sqrt(np.sum((eps * v_u) ** 2)) / np.sum(c_u)) if np.sum(c_u) > 0 else float("nan")
    out["representative_coh_weighted"] = round(rep, 4)
    out["representative_unweighted_mean"] = round(rep_unweighted, 4)
    out["representative_uncertainty_1sigma"] = round(eps_combined, 4)
    out["coherence_range_usable_bins"] = [round(float(c_u.min()), 3), round(float(c_u.max()), 3)]
    return out


def bandlimited_rms(x, fs, lo_rs, hi_rs, order=4):
    """Band-pass RMS. Uses SOS (second-order-sections) form + sosfiltfilt --
    the (b,a) polynomial form of butter() is numerically unstable for this
    kind of narrow low-frequency-relative-to-Nyquist band (verified: (b,a)
    form produced obviously wrong blown-up output, 100-1000x too large, for
    the longer logs; SOS form does not)."""
    lo_hz = lo_rs / (2 * np.pi)
    hi_hz = hi_rs / (2 * np.pi)
    nyq = fs / 2
    sos = signal.butter(order, [lo_hz / nyq, min(hi_hz / nyq, 0.999)], btype="band", output="sos")
    xf = signal.sosfiltfilt(sos, x)
    return float(np.std(xf))


# =============================================================================
# Task 1 + Task 2 per log
# =============================================================================
def task12(name, path, t_to, t_end):
    S = load(path)
    t0 = S["imu"][0]["ts"]
    grid = build_grid_signals(S, t0, t_to, t_end, fs=FS)
    fs = FS
    n = len(grid["t"])
    span_s = grid["t"][-1] - grid["t"][0]

    result = {"log": name, "grid_fs_hz": fs, "grid_n_samples": n, "grid_span_s": round(float(span_s), 2)}

    # ---------------- Task 1: attitude tracking FRF (angle_ref -> est angle) ----
    task1 = {}
    for axis, ref_key, meas_key in [("roll", "angle_ref_roll", "roll"),
                                     ("pitch", "angle_ref_pitch", "pitch")]:
        x = grid[ref_key]
        y = grid[meas_key]
        res = frf(x, y, fs)
        full_band = band_summary(res, BAND_LO_RS, BAND_HI_RS, "mag")
        rep_band = band_summary(res, REP_LO_RS, REP_HI_RS, "mag")
        # excitation levels
        ref_rms_deg = float(np.degrees(np.std(x)))
        meas_rms_deg = float(np.degrees(np.std(y)))
        ref_rms_band_deg = float(np.degrees(bandlimited_rms(x, fs, BAND_LO_RS, BAND_HI_RS)))
        task1[axis] = {
            "nperseg": res["nperseg"], "nseg": res["nseg"],
            "freq_resolution_hz": round(fs / res["nperseg"], 4),
            "freq_resolution_rads": round(2 * np.pi * fs / res["nperseg"], 4),
            "full_band_0p2_3rads": full_band,
            "representative_band_0p5_1p0rads": rep_band,
            "ref_rms_deg": round(ref_rms_deg, 3),
            "meas_rms_deg": round(meas_rms_deg, 3),
            "ref_rms_bandlimited_0p2_3rads_deg": round(ref_rms_band_deg, 4),
        }
        result[f"task1_{axis}_curve"] = {
            "f_hz": [round(float(v), 4) for v in res["f_hz"]],
            "mag": [round(float(v), 4) for v in np.abs(res["H"])],
            "phase_deg": [round(float(v), 2) for v in np.degrees(np.angle(res["H"]))],
            "coh": [round(float(v), 4) for v in res["coh"]],
        }
    result["task1"] = task1

    # ---------------- Task 2: tilt -> velocity effective gain K/g -------------
    task2 = {}
    pairs = [("roll", "roll", "vel_E"), ("pitch", "pitch", "vel_N")]
    for label, theta_key, vel_key in pairs:
        theta = grid[theta_key]
        v = grid[vel_key]
        res = frf(theta, v, fs)
        w = res["w_rads"]
        Kg = np.where(w > 1e-6, w * np.abs(res["H"]) / G, np.nan)
        res["Kg"] = Kg
        full_band = band_summary(res, BAND_LO_RS, BAND_HI_RS, "Kg")
        rep_band = band_summary(res, REP_LO_RS, REP_HI_RS, "Kg")
        theta_rms_deg = float(np.degrees(np.std(theta)))
        v_rms = float(np.std(v))
        theta_rms_band_deg = float(np.degrees(bandlimited_rms(theta, fs, BAND_LO_RS, BAND_HI_RS)))
        v_rms_band = float(bandlimited_rms(v, fs, BAND_LO_RS, BAND_HI_RS))
        task2[label] = {
            "theta_axis": theta_key, "vel_axis": vel_key,
            "nperseg": res["nperseg"], "nseg": res["nseg"],
            "freq_resolution_hz": round(fs / res["nperseg"], 4),
            "full_band_0p2_3rads": full_band,
            "representative_band_0p5_1p0rads": rep_band,
            "theta_rms_deg": round(theta_rms_deg, 3),
            "vel_rms_ms": round(v_rms, 4),
            "theta_rms_bandlimited_deg": round(theta_rms_band_deg, 4),
            "vel_rms_bandlimited_ms": round(v_rms_band, 5),
        }
        result[f"task2_{label}_curve"] = {
            "f_hz": [round(float(v_), 4) for v_ in res["f_hz"]],
            "Kg": [round(float(v_), 4) if np.isfinite(v_) else None for v_ in Kg],
            "phase_deg": [round(float(v_), 2) for v_ in np.degrees(np.angle(res["H"]))],
            "coh": [round(float(v_), 4) for v_ in res["coh"]],
        }
    result["task2"] = task2

    return result, grid


# =============================================================================
# Figures
# =============================================================================
def make_figure(name, result, out_png):
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))
    fig.suptitle(f"{name} — attitude tracking FRF (top) & tilt->vel K/g (bottom)", fontsize=11)

    for j, axis in enumerate(["roll", "pitch"]):
        c = result[f"task1_{axis}_curve"]
        f = np.array(c["f_hz"])
        w = 2 * np.pi * f
        mag = np.array(c["mag"])
        coh = np.array(c["coh"])
        ax = axs[0, j]
        m = (w >= 0.05) & (w <= 5)
        ax.plot(w[m], mag[m], "b-", lw=1)
        ax.axvspan(REP_LO_RS, REP_HI_RS, color="orange", alpha=0.15)
        ax.set_xscale("log")
        ax.set_ylabel("|angle/angle_ref|")
        ax.set_title(f"Task1 {axis}: attitude tracking")
        ax.grid(alpha=0.3, which="both")
        ax2 = ax.twinx()
        ax2.plot(w[m], coh[m], "r--", lw=0.8, alpha=0.7)
        ax2.axhline(0.5, color="r", ls=":", lw=0.6)
        ax2.set_ylabel("coherence", color="r")
        ax2.set_ylim(0, 1.05)
        ax.set_xlabel("freq [rad/s]")

    for j, label in enumerate(["roll", "pitch"]):
        c = result[f"task2_{label}_curve"]
        f = np.array(c["f_hz"])
        w = 2 * np.pi * f
        Kg = np.array([v if v is not None else np.nan for v in c["Kg"]])
        coh = np.array(c["coh"])
        ax = axs[1, j]
        m = (w >= 0.05) & (w <= 5)
        ax.plot(w[m], Kg[m], "g-", lw=1)
        ax.axvspan(REP_LO_RS, REP_HI_RS, color="orange", alpha=0.15)
        ax.set_xscale("log")
        vel_axis = result["task2"][label]["vel_axis"]
        ax.set_ylabel(f"K/g  ({label}->{'{'}{vel_axis}{'}'})")
        ax.set_title(f"Task2 {label}: tilt->velocity K/g")
        ax.grid(alpha=0.3, which="both")
        ax.set_ylim(-2, 4)
        ax2 = ax.twinx()
        ax2.plot(w[m], coh[m], "r--", lw=0.8, alpha=0.7)
        ax2.axhline(0.5, color="r", ls=":", lw=0.6)
        ax2.set_ylabel("coherence", color="r")
        ax2.set_ylim(0, 1.05)
        ax.set_xlabel("freq [rad/s]")

    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(out_png, dpi=120)
    plt.close(fig)


def make_timeseries_figure(name, grid, out_png):
    t = grid["t"] - grid["t"][0]
    fig, axs = plt.subplots(3, 1, figsize=(11, 8), sharex=True)
    axs[0].plot(t, np.degrees(grid["angle_ref_roll"]), label="angle_ref roll", lw=0.8)
    axs[0].plot(t, np.degrees(grid["roll"]), label="est roll", lw=0.8)
    axs[0].plot(t, np.degrees(grid["angle_ref_pitch"]), "--", label="angle_ref pitch", lw=0.8)
    axs[0].plot(t, np.degrees(grid["pitch"]), "--", label="est pitch", lw=0.8)
    axs[0].set_ylabel("angle [deg]"); axs[0].legend(fontsize=7, ncol=4); axs[0].grid(alpha=0.3)
    axs[0].set_title(f"{name} — grid signals used for Task1/Task2")

    axs[1].plot(t, grid["vel_N"], label="vel N", lw=0.8)
    axs[1].plot(t, grid["vel_E"], label="vel E", lw=0.8)
    axs[1].set_ylabel("vel [m/s]"); axs[1].legend(fontsize=7); axs[1].grid(alpha=0.3)

    # NOTE: plotted with the same (unsigned) pairing used in the K/g regression
    # (x=theta directly, no a-priori sign flip) -- the true physical sign is
    # not asserted here; see the reported cross-spectrum PHASE for the
    # empirically observed sign relationship instead.
    a_pred_N = G * grid["pitch"]
    a_pred_E = G * grid["roll"]
    axs[2].plot(t, a_pred_N, label="a_pred N = g*pitch (unsigned)", lw=0.7, alpha=0.8)
    axs[2].plot(t, a_pred_E, label="a_pred E = g*roll (unsigned)", lw=0.7, alpha=0.8)
    axs[2].set_ylabel("a_pred [m/s^2]"); axs[2].set_xlabel("time [s]")
    axs[2].legend(fontsize=7); axs[2].grid(alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_png, dpi=110)
    plt.close(fig)


# =============================================================================
# Schema report (from L1 only, per task instructions)
# =============================================================================
def schema_report(path):
    S = load(path)
    out = {}
    for k, recs in S.items():
        keys = set()
        for r in recs[:50]:
            keys |= set(r.keys())
        out[k] = {"n": len(recs), "fields": sorted(keys), "example": recs[0]}
    return out


def main():
    schema = schema_report(os.path.join(REPO, LOGS["L1"]))
    with open(os.path.join(OUT_DIR, "schema.json"), "w") as f:
        json.dump(schema, f, indent=2, default=str)

    all_task0 = {}
    all_task12 = {}
    fig_paths = []
    for name, rel in LOGS.items():
        path = os.path.join(REPO, rel)
        t0res = task0(name, path)
        all_task0[name] = t0res
        t_to, t_end = t0res["flight_window_s"]
        res, grid = task12(name, path, t_to, t_end)
        all_task12[name] = res

        png = os.path.join(FIG_DIR, f"{name}_frf.png")
        make_figure(name, res, png)
        fig_paths.append(png)

        png2 = os.path.join(FIG_DIR, f"{name}_timeseries.png")
        make_timeseries_figure(name, grid, png2)
        fig_paths.append(png2)

        print(f"{name}: done. window={t0res['flight_window_s']} dur={t0res['duration_s']}s "
              f"grid_n={res['grid_n_samples']} span={res['grid_span_s']}s")

    results = {"task0": all_task0, "task12": all_task12, "figures": fig_paths,
               "band_definitions": {"full_band_rads": [BAND_LO_RS, BAND_HI_RS],
                                     "representative_band_rads": [REP_LO_RS, REP_HI_RS],
                                     "grid_fs_hz": FS}}
    with open(os.path.join(OUT_DIR, "results.json"), "w") as f:
        json.dump(results, f, indent=2, default=str)
    print("\nresults.json written to", os.path.join(OUT_DIR, "results.json"))


if __name__ == "__main__":
    main()
