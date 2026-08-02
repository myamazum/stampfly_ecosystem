#!/usr/bin/env python3
"""
paper_figs.py -- camera-ready figures for the 第64回飛行機シンポジウム原稿
(docs/hikoki64/manuscript/). One-column width target: 82 mm (A4 two-column
proceedings layout).

Run:
    cd /Users/kouhei/tmp/github/stampfly_ecosystem
    python3 analysis/scripts/verify_hikoki64/paper_figs.py

Outputs (PDF + PNG, both written):
    docs/hikoki64/manuscript/figs/fig_stability_boundary.{pdf,png}
    docs/hikoki64/manuscript/figs/fig_divergence_timeseries.{pdf,png}

===========================================================================
Figure 1 -- fig_stability_boundary : K-sweep stability-boundary map
===========================================================================
Closed-loop model, firmware-exact discrete PID replica, and the pole
extraction method (fit_pole: zero-crossing spacing -> omega, log-amplitude
slope of successive peaks -> sigma) are NOT reimplemented here -- they are
imported unmodified from
    analysis/scripts/poshold_loop_design.py   (PID, simulate, fit_pole,
                                                 lin_pole)
which is itself the module reused (also unmodified) by
    analysis/scripts/verify_hikoki64/task2_pole_sweep.py

Numeric provenance for every value drawn in Figure 1:
  - Gain tuples (script's own names):
      GAINS_O (OLD, current-firmware-style):
          pos_kp=1.0, pos_ti=5.0, pos_td=0.0, vel_kp=0.8, vel_ti=2.0, vel_td=0.0
      GAINS_N (NEW):
          pos_kp=0.4, pos_ti=5.0, pos_td=0.0, vel_kp=3.0, vel_ti=2.0, vel_td=0.0
      Both tuples copied verbatim from task2_pole_sweep.py GAINS_O / GAINS_N.
  - K sweep range 2.0 - 10.0 m/s^2/rad and tau_primary = 0.15 s: copied from
    task2_pole_sweep.py K_SWEEP / TAU_PRIMARY (its own stated default, "middle
    of the script's TAU_RANGE=[0.05,0.15,0.30]"). Only tau=0.15 s is plotted
    here (task2_pole_sweep.py's "primary" case); the script also has a
    tau=0 s cross-check, not reproduced in this figure.
  - K=3.9 m/s^2/rad ("実機同定値" / real-machine identified tilt->accel
    gain): coherence-weighted representative K/g * g value from the Task 2
    FRF analysis (0.5-1.0 rad/s band) in
    analysis/scripts/verify_hikoki64/verify_B.py, cross-checked against the
    table["tau_0.15s"]["K=3.9"] entry already present in
    analysis/scripts/verify_hikoki64/task2_results.json (this script
    recomputes it independently via the same lin_pole() call rather than
    reading that json, and the two agree: sigma_O(K=3.9,tau=0.15)=+0.1057).
  - K=9.81 m/s^2/rad ("理想=SILS" / ideal 1g tilt->accel gain, a=g*theta
    small-angle, also the nominal SIL plant gain): g = 9.80665 m/s^2 (module
    constant M.G), used directly as the K value (not g rounded).
  - NEW-gain "fit not possible" region (K >= ~3.55 m/s^2/rad, tau=0.15s):
    fit_pole() needs >=3 peak amplitudes above a 1e-4 m floor to fit the
    log-amplitude decay slope (sigma); for these K values the linearized
    response damps below that floor before 3 usable peaks accumulate, i.e.
    the dominant pole is real / heavily overdamped rather than a complex
    oscillatory pair, so fit_pole() returns sigma=NaN even though omega is
    still numerically defined from the (very few, very early) zero
    crossings. This NaN is a *known limitation of the peak-ratio fit
    method*, not evidence of instability -- confirmed against
    task2_results.json table["tau_0.15s"]["K=3.9"]["N"] and ["K=9.81"]["N"],
    both sigma=NaN there too. Physically this K range is MORE stable than
    the last K with a valid fit (visible from the monotonically more
    negative sigma trend for K=2.0-3.5 immediately below the cutoff), so it
    is drawn as an explicit hatched "strongly stable" band rather than a
    gap, per task instructions.

===========================================================================
Figure 2 -- fig_divergence_timeseries : real-flight divergence
===========================================================================
Source log: logs/stampfly_udp_20260622T161055.jsonl
  id="posvel" records -> fields pos=[N,E,D] [m], ts [us]
  id="ctrl_ref" records -> field total_thrust, ts [us] (flight-window detect)
  id="imu" records -> first record's ts used as t0 (same convention as
  verify_B.py's ts_s()).

Flight-window detection is copied (not reimplemented) from verify_B.py's
task0()/flight_window(): the largest contiguous total_thrust > 0.02 segment
on the 50 Hz ctrl_ref clock. For this log that segment is
[t_to, t_end] = [2.22, 16.73] s (relative to first imu sample), duration
14.51 s -- matches verify_B_results.json task0.L1.flight_window_s /
duration_s.

Terminal divergence numbers (computed directly in this script from the raw
log, printed to stdout when this script runs):
  radial(t) = hypot(x(t), y(t))  over the flight window
  max radial = 0.746 m at t = 16.31 s (14.09 s into the window)
  -> reported/rounded as "radial ~ 0.75 m" in the figure annotation.
  status.flight_state (same STATE_NAME enum as verify_B.py) leaves
  FLYING(5) for IDLE_HELD(2) at t=16.98s, i.e. immediately after this peak
  -- the pilot recovered/landed the vehicle right at the divergence peak,
  which is what "記録終了" (recording effectively ends here) refers to.
"""
import json
import os
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker as mticker  # noqa: E402

REPO = "/Users/kouhei/tmp/github/stampfly_ecosystem"
sys.path.insert(0, os.path.join(REPO, "analysis/scripts"))
import poshold_loop_design as M  # noqa: E402  (PID / simulate / fit_pole / lin_pole -- reused, not reimplemented)

FIG_DIR = os.path.join(REPO, "docs/hikoki64/manuscript/figs")
os.makedirs(FIG_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# Common one-column (82 mm) print style
# ---------------------------------------------------------------------------
MM = 1 / 25.4
COL_W_IN = 82 * MM          # one-column width, A4 two-column proceedings
plt.rcParams.update({
    "font.size": 9,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 8,
    "ytick.labelsize": 8,
    "legend.fontsize": 7.5,
    "axes.linewidth": 0.9,
    "lines.linewidth": 2.0,
    "font.family": "sans-serif",
})
# NOTE: all in-figure annotation text is kept ASCII/English-only on purpose.
# matplotlib's PDF backend cannot embed macOS's Hiragino Sans (a .ttc font
# collection) as vector glyphs -- it raises UnicodeEncodeError while writing
# glyph names for CJK characters. The Japanese context/explanation belongs
# in the LaTeX caption around \includegraphics, not baked into the raster
# text, which also keeps the figure reusable for an English venue.

O_COLOR = "#1f4e8c"   # dark blue  -- OLD gains
N_COLOR = "#c1440e"   # dark red/orange -- NEW gains
GRID_KW = dict(alpha=0.35, linewidth=0.5)


# ===========================================================================
# Figure 1 -- K-sweep stability boundary
# ===========================================================================
GAINS_O = (1.0, 5.0, 0.0, 0.8, 2.0, 0.0)   # pos_kp,pos_ti,pos_td, vel_kp,vel_ti,vel_td (task2_pole_sweep.py)
GAINS_N = (0.4, 5.0, 0.0, 3.0, 2.0, 0.0)
TAU_PRIMARY = 0.15          # s (task2_pole_sweep.py TAU_PRIMARY)
K_LO, K_HI = 2.0, 10.0      # m/s^2/rad (task2_pole_sweep.py K_SWEEP range)
K_ID = 3.9                  # m/s^2/rad, real-machine identified K (verify_B.py Task2, see docstring)
K_IDEAL = M.G                # m/s^2/rad, ideal 1g gain == nominal SIL plant gain


def sweep_sigma(gains, K_grid, tau):
    sig = np.full_like(K_grid, np.nan, dtype=float)
    for i, K in enumerate(K_grid):
        p = M.lin_pole(gains, float(K), tau)
        if p is not None:
            sig[i] = p[1]   # (omega, sigma, zeta)
    return sig


def make_fig1():
    K_grid = np.arange(K_LO, K_HI + 1e-9, 0.05)
    sig_O = sweep_sigma(GAINS_O, K_grid, TAU_PRIMARY)
    sig_N = sweep_sigma(GAINS_N, K_grid, TAU_PRIMARY)

    # cross-check the two required table points against task2_results.json
    for Kval in (K_ID, round(K_IDEAL, 2)):
        pO = M.lin_pole(GAINS_O, Kval, TAU_PRIMARY)
        pN = M.lin_pole(GAINS_N, Kval, TAU_PRIMARY)
        print(f"[check] K={Kval:.3f}  O: sigma={pO[1]:+.4f}  "
              f"N: sigma={'NaN (fit unavailable, see docstring)' if (pN is None or not np.isfinite(pN[1])) else f'{pN[1]:+.4f}'}")

    valid_N = np.isfinite(sig_N)
    k_cutoff = K_grid[valid_N][-1] if valid_N.any() else K_LO   # last K with a usable N fit
    print(f"[fig1] NEW-gain pole-fit cutoff: K >= {k_cutoff + 0.05:.2f} m/s^2/rad -> sigma unfittable (strongly stable)")

    fig, ax = plt.subplots(figsize=(COL_W_IN, COL_W_IN * 0.86))

    y_lo, y_hi = -0.30, 0.16

    # hatched "pole fit unavailable -> strongly stable" band for NEW gains.
    # Label placed at mid-height (y=-0.10): within [K>=3.6,10] the OLD curve
    # stays above -0.076 (checked numerically), so this height never touches
    # either data line -- verified by eye after rendering, not just assumed.
    band_lo = k_cutoff + 0.025
    ax.axvspan(band_lo, K_HI, facecolor="0.90", edgecolor="0.55",
               hatch="////", linewidth=0.0, zorder=0)
    ax.text((band_lo + K_HI) / 2, -0.10,
            "NEW: pole fit\nunavailable\n(strongly stable)",
            ha="center", va="center", fontsize=6.8, color="0.25", zorder=4,
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="0.55", lw=0.5, alpha=0.85))

    ax.axhline(0.0, color="k", lw=1.0, ls=":", zorder=1)

    ax.plot(K_grid, sig_O, "-", color=O_COLOR, lw=2.2, zorder=3)
    ax.plot(K_grid[valid_N], sig_N[valid_N], "--", color=N_COLOR, lw=2.2, zorder=3)
    # small markers, sparse, for a B/W-safe visual cue beyond linestyle alone
    ax.plot(K_grid[valid_N][::8], sig_N[valid_N][::8], "s", color=N_COLOR,
            ms=4.0, zorder=3)
    ax.plot(K_grid[::8], sig_O[::8], "o", color=O_COLOR, ms=3.5, zorder=3)

    # direct curve-end labels (no legend box -- avoids overlap with the
    # K-target lines / hatch band in this narrow one-column figure).
    # OLD labeled near its right (K~10) end, clear of the K=9.81 marker line;
    # NEW labeled near its left (K=2) end, since its right end (K~3.5) sits
    # right next to the K=3.9 marker line and its rotated label.
    ax.annotate("OLD\n$k_{p,\\mathrm{pos}}$=1.0, $k_{p,\\mathrm{vel}}$=0.8",
                xy=(K_grid[-1], sig_O[-1]), xytext=(K_IDEAL - 0.35, sig_O[-1] - 0.075),
                ha="right", va="top", fontsize=6.8, color=O_COLOR, zorder=5)
    ax.annotate("NEW\n$k_{p,\\mathrm{pos}}$=0.4, $k_{p,\\mathrm{vel}}$=3.0",
                xy=(K_grid[0], sig_N[0]), xytext=(K_LO + 0.05, sig_N[0] + 0.05),
                ha="left", va="bottom", fontsize=6.8, color=N_COLOR, zorder=5)

    # target K markers -- labels placed near the bottom axis, clear of both
    # curves and the hatch-band text above them
    for Kx, label, ls in [(K_ID, f"K={K_ID:.1f} (identified)", "-."),
                           (K_IDEAL, f"K={K_IDEAL:.2f} (ideal = SIL)", "-.")]:
        ax.axvline(Kx, color="0.25", lw=1.1, ls=ls, zorder=2)
        ax.text(Kx, y_lo + 0.012, label, rotation=90, ha="left", va="bottom",
                fontsize=6.6, color="0.15", zorder=5,
                bbox=dict(boxstyle="round,pad=0.1", fc="white", ec="0.6", lw=0.4, alpha=0.9))

    ax.set_xlim(K_LO, K_HI)
    ax.set_ylim(y_lo, y_hi)
    ax.set_xlabel(r"$K$  [m/s$^2$/rad]  (tilt$\rightarrow$accel plant gain)")
    ax.set_ylabel(r"$\sigma$  [1/s]  (dominant pole real part)")
    ax.xaxis.set_major_locator(mticker.MultipleLocator(1.0))
    ax.grid(True, which="major", **GRID_KW)

    fig.tight_layout(pad=0.4)
    for ext in ("pdf", "png"):
        out = os.path.join(FIG_DIR, f"fig_stability_boundary.{ext}")
        fig.savefig(out, dpi=300 if ext == "png" else None)
        print("saved", out)
    plt.close(fig)


# ===========================================================================
# Figure 2 -- real-flight divergence time series
# ===========================================================================
LOG_PATH = os.path.join(REPO, "logs/stampfly_udp_20260622T161055.jsonl")
STATE_NAME = {0: "INIT", 1: "IDLE_GROUND", 2: "IDLE_HELD", 3: "ARMED_GROUND",
              4: "TAKEOFF", 5: "FLYING", 6: "LANDING"}


def load_jsonl(path):
    S = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            S.setdefault(d.get("id", "?"), []).append(d)
    return S


def flight_window(t_cr, thrust):
    """Largest contiguous thrust>0.02 segment -- copied from verify_B.py."""
    live = thrust > 0.02
    edges = np.diff(live.astype(int))
    starts = list(np.where(edges == 1)[0] + 1)
    ends = list(np.where(edges == -1)[0])
    if live[0]:
        starts = [0] + starts
    if live[-1]:
        ends = ends + [len(live) - 1]
    segs = sorted(zip(starts, ends), key=lambda se: t_cr[se[1]] - t_cr[se[0]], reverse=True)
    return segs[0]


def make_fig2():
    S = load_jsonl(LOG_PATH)
    t0 = S["imu"][0]["ts"]

    t_cr = np.array([(r["ts"] - t0) / 1e6 for r in S["ctrl_ref"]])
    thrust = np.array([r["total_thrust"] for r in S["ctrl_ref"]])
    i_to, i_end = flight_window(t_cr, thrust)
    t_to, t_end = t_cr[i_to], t_cr[i_end]
    print(f"[fig2] flight window: [{t_to:.2f}, {t_end:.2f}] s, dur={t_end - t_to:.2f} s")

    t_pv = np.array([(r["ts"] - t0) / 1e6 for r in S["posvel"]])
    pos = np.array([r["pos"] for r in S["posvel"]])
    m = (t_pv >= t_to) & (t_pv <= t_end)
    t = t_pv[m] - t_to
    x = pos[m, 0]
    y = pos[m, 1]
    radial = np.hypot(x, y)
    i_max = int(np.argmax(radial))
    t_max, r_max = t[i_max], radial[i_max]
    print(f"[fig2] max radial = {r_max:.3f} m at t={t_max:.2f} s "
          f"(t_abs={t_max + t_to:.2f} s)")

    # flight_state transition, for the "recording effectively ends" note
    st = S.get("status", [])
    t_st = np.array([(r["ts"] - t0) / 1e6 for r in st])
    fstate = np.array([r["flight_state"] for r in st])
    leave_flying = None
    for ti, fi in zip(t_st, fstate):
        if ti > t_max + t_to and fi != 5:
            leave_flying = ti
            break
    if leave_flying is not None:
        print(f"[fig2] flight_state leaves FLYING(5) at t_abs={leave_flying:.2f} s "
              f"({STATE_NAME.get(int(fi), fi)})")

    fig, ax = plt.subplots(figsize=(COL_W_IN, COL_W_IN * 0.9))

    y_data_lo = min(x.min(), y.min())
    y_data_hi = max(x.max(), y.max())
    y_lo = y_data_lo - 0.30   # extra headroom below the data so the
    y_hi = y_data_hi + 0.10   # annotation box never touches the axis edge

    ax.plot(t, x, "-", color=O_COLOR, lw=2.0, label=r"$x$  (N)")
    ax.plot(t, y, "--", color=N_COLOR, lw=2.0, label=r"$y$  (E)")
    ax.plot(t[::40], x[::40], "o", color=O_COLOR, ms=3.0)
    ax.plot(t[::40], y[::40], "s", color=N_COLOR, ms=3.0)

    ax.plot([t_max], [x[i_max]], "o", color=O_COLOR, ms=5.5, mec="k", mew=0.6, zorder=5)
    ax.plot([t_max], [y[i_max]], "s", color=N_COLOR, ms=5.5, mec="k", mew=0.6, zorder=5)
    ax.axvline(t_max, color="0.3", lw=1.0, ls=":", zorder=1)
    ax.annotate(f"radial $\\approx$ {r_max:.2f} m\n(divergence, log ends)",
                xy=(t_max, y[i_max]),
                xytext=(t_max - 7.6, y_lo + 0.03),
                fontsize=7, ha="left", va="bottom",
                arrowprops=dict(arrowstyle="-|>", color="0.25", lw=1.0, mutation_scale=8),
                bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="0.6", lw=0.5))

    ax.axhline(0.0, color="k", lw=0.7, alpha=0.5, zorder=0)
    ax.set_xlabel(r"$t$  [s]  (flight window, $t{=}0$ at liftoff)")
    ax.set_ylabel(r"position  [m]")
    ax.set_xlim(t[0], t[-1])
    ax.set_ylim(y_lo, y_hi)
    ax.grid(True, **GRID_KW)
    ax.legend(loc="upper left", framealpha=0.9, handlelength=2.4)

    fig.tight_layout(pad=0.4)
    for ext in ("pdf", "png"):
        out = os.path.join(FIG_DIR, f"fig_divergence_timeseries.{ext}")
        fig.savefig(out, dpi=300 if ext == "png" else None)
        print("saved", out)
    plt.close(fig)


if __name__ == "__main__":
    make_fig1()
    make_fig2()
