#!/usr/bin/env python3
"""
Task 1 — final consolidation. Runs the full pipeline once more end-to-end,
producing the two required figures (position+envelope, PSD) plus one
model-free sliding-window amplitude figure, and writes a single
task1_results_FINAL.json with every method's raw numbers (no selection /
no comparison to any expected value).
"""
import json
import numpy as np
from scipy import signal, stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

LOG = "/Users/kouhei/tmp/github/stampfly_ecosystem/logs/stampfly_udp_20260622T161055.jsonl"
OUT = "/private/tmp/claude-501/-Users-kouhei-tmp-github-stampfly-ecosystem/5e87008a-97a4-42d5-9e0e-02387c2a8022/scratchpad/verify_A"


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


def exp_fit(t_arr, val_arr, label, verbose=True):
    t_arr = np.asarray(t_arr, dtype=float)
    val_arr = np.asarray(val_arr, dtype=float)
    log_v = np.log(np.clip(val_arr, 1e-9, None))
    n_pts = len(t_arr)
    res = stats.linregress(t_arr, log_v)
    sigma = res.slope
    sigma_se = res.stderr if res.stderr is not None else float("nan")
    if n_pts > 2 and not np.isnan(sigma_se):
        tval = stats.t.ppf(0.975, df=n_pts - 2)
        ci = (sigma - tval * sigma_se, sigma + tval * sigma_se)
    else:
        ci = (float("nan"), float("nan"))
    A = float(np.exp(res.intercept))
    pred = res.intercept + res.slope * t_arr
    resid = log_v - pred
    rss_lin = float(np.sum(resid ** 2))
    aic_lin = n_pts * np.log(rss_lin / n_pts) + 2 * 2 if rss_lin > 0 else float("-inf")
    mean_log = np.mean(log_v)
    rss_const = float(np.sum((log_v - mean_log) ** 2))
    aic_const = n_pts * np.log(rss_const / n_pts) + 2 * 1 if rss_const > 0 else float("-inf")
    if verbose:
        print(f"--- exp fit [{label}] n={n_pts} ---")
        print(f"  sigma = {sigma:.5f} 1/s   95% CI = [{ci[0]:.5f}, {ci[1]:.5f}]")
        print(f"  AIC linear={aic_lin:.3f}  AIC const={aic_const:.3f}  "
              f"deltaAIC(const-linear)={aic_const-aic_lin:.3f}")
    return dict(sigma=float(sigma), sigma_se=float(sigma_se), ci95=[float(ci[0]), float(ci[1])],
                A=A, r_value=float(res.rvalue), p_value=float(res.pvalue),
                aic_linear=float(aic_lin), aic_const=float(aic_const), n=n_pts)


def main():
    S = load(LOG)
    t0 = S["imu"][0]["ts"]
    t_cr = (arr(S["ctrl_ref"], "ts") - t0) / 1e6
    thrust = arr(S["ctrl_ref"], "total_thrust")
    duty = arr(S["ctrl_ref"], "motor_duty")
    mode = arr(S["ctrl_ref"], "mode")
    live = thrust > 0.02
    if not live.any():
        live = duty.max(axis=1) > 0.02
    i_to = int(np.argmax(live))
    i_end = len(live) - 1 - int(np.argmax(live[::-1]))
    t_to, t_end = t_cr[i_to], t_cr[i_end]

    t_pv = (arr(S["posvel"], "ts") - t0) / 1e6
    pos = arr(S["posvel"], "pos")
    m = (t_pv >= t_to) & (t_pv <= t_end)
    t = t_pv[m]
    x, y = pos[m, 0], pos[m, 1]
    r = np.hypot(x, y)
    dt_med = float(np.median(np.diff(t)))
    fs = 1.0 / dt_med
    t_u = np.arange(t[0], t[-1], dt_med)
    x_u = np.interp(t_u, t, x)
    y_u = np.interp(t_u, t, y)
    r_u = np.interp(t_u, t, r)
    x_dt = signal.detrend(x_u, type="linear")
    y_dt = signal.detrend(y_u, type="linear")

    # ---- 1. dominant frequency: full-window periodogram, genuine local maxima only ----
    f_x, Pxx = signal.periodogram(x_dt, fs=fs, window="hann", detrend="linear")
    f_y, Pyy = signal.periodogram(y_dt, fs=fs, window="hann", detrend="linear")
    df = f_x[1] - f_x[0]
    maskb = (f_x > 0.02) & (f_x <= 5.0)
    idx_lx = signal.argrelmax(Pxx[maskb], order=3)[0]
    f_center = f_x[maskb][idx_lx[np.argmax(Pxx[maskb][idx_lx])]]
    T_center = 1.0 / f_center
    omega_center = 2 * np.pi * f_center
    print(f"Dominant freq (x periodogram genuine local max): f={f_center:.4f} Hz  T={T_center:.4f} s  "
          f"omega={omega_center:.4f} rad/s  (periodogram df={df:.4f} Hz)")

    # zero-crossing cross-check
    def zero_cross_full_periods(sig_arr, t_arr):
        s = sig_arr - np.mean(sig_arr)
        signs = np.sign(s); signs[signs == 0] = 1
        cidx = np.where(np.diff(signs) != 0)[0]
        ct = []
        for i in cidx:
            frac = -s[i] / (s[i+1]-s[i])
            ct.append(t_arr[i] + frac*(t_arr[i+1]-t_arr[i]))
        ct = np.array(ct)
        hp = np.diff(ct)
        fp = hp[hp > 0.5] * 2  # drop spurious near-simultaneous crossings (<0.5s half-period)
        return fp
    fp_x = zero_cross_full_periods(x_dt, t_u)
    print(f"zero-crossing full-period estimates (x, spurious<0.5s excluded): {fp_x}, "
          f"median={np.median(fp_x):.4f} s, mean={np.mean(fp_x):.4f} s")

    # ---- 2. Hilbert envelope fit (x, full window) ----
    f_lo, f_hi = f_center * 0.5, f_center * 2.2
    sos = signal.butter(4, [f_lo, f_hi], btype="bandpass", fs=fs, output="sos")
    x_bp = signal.sosfiltfilt(sos, x_dt)
    env_x = np.abs(signal.hilbert(x_bp))
    edge = max(int(0.05 * len(t_u)), 5)
    t_fit, env_fit = t_u[edge:-edge], env_x[edge:-edge]
    fit_hilbert_x = exp_fit(t_fit, env_fit, "Hilbert envelope x, full window, band-verified")

    # ---- 3. coarse large-scale radial extrema (least filter-dependent) ----
    min_dist = int(0.6 * T_center * fs)
    peaks_r, _ = signal.find_peaks(r_u, distance=min_dist)
    troughs_r, _ = signal.find_peaks(-r_u, distance=min_dist)
    fit_peaks = exp_fit(t_u[peaks_r], r_u[peaks_r], "radial coarse local maxima (full window, incl startup)") if len(peaks_r) >= 3 else None
    fit_troughs = exp_fit(t_u[troughs_r], np.clip(r_u[troughs_r], 1e-4, None),
                           "radial coarse local minima (full window, incl startup)") if len(troughs_r) >= 3 else None

    # 2-point clean comparison excluding startup (~r=0 at motor spin-up) and the
    # near-duplicate pair at the very end (<0.5s apart, terminal-transient noise)
    good_peaks = [(tt, rr) for tt, rr in zip(t_u[peaks_r], r_u[peaks_r]) if tt > 3.3]
    # drop a peak if within 0.5s of another peak (keep first)
    clean_peaks = []
    for tt, rr in good_peaks:
        if clean_peaks and tt - clean_peaks[-1][0] < 0.5:
            continue
        clean_peaks.append((tt, rr))
    good_troughs = [(tt, rr) for tt, rr in zip(t_u[troughs_r], r_u[troughs_r]) if tt > 3.3 and rr > 1e-3]
    clean_troughs = []
    for tt, rr in good_troughs:
        if clean_troughs and tt - clean_troughs[-1][0] < 0.5:
            continue
        clean_troughs.append((tt, rr))
    print(f"clean (startup/terminal-dup excluded) peaks: {clean_peaks}")
    print(f"clean (startup/terminal-dup excluded) troughs: {clean_troughs}")
    two_pt_peak_sigma = None
    if len(clean_peaks) >= 2:
        (t1, r1), (t2, r2) = clean_peaks[0], clean_peaks[-1]
        two_pt_peak_sigma = float(np.log(r2/r1)/(t2-t1))
        print(f"2-point peak-to-peak sigma = {two_pt_peak_sigma:.5f} /s")
    two_pt_trough_sigma = None
    if len(clean_troughs) >= 2:
        (t1, r1), (t2, r2) = clean_troughs[0], clean_troughs[-1]
        two_pt_trough_sigma = float(np.log(r2/r1)/(t2-t1))
        print(f"2-point trough-to-trough sigma = {two_pt_trough_sigma:.5f} /s")

    # ---- 4. model-free sliding-window peak-to-peak amplitude ----
    win = T_center
    step = T_center / 4
    starts = np.arange(t_u[0], t_u[-1] - win, step)
    centers, ptp_x, ptp_r = [], [], []
    for s0 in starts:
        mm = (t_u >= s0) & (t_u < s0 + win)
        if mm.sum() < 10:
            continue
        centers.append(s0 + win / 2)
        ptp_x.append(x_dt[mm].max() - x_dt[mm].min())
        ptp_r.append(r_u[mm].max() - r_u[mm].min())
    centers, ptp_x, ptp_r = np.array(centers), np.array(ptp_x), np.array(ptp_r)
    fit_slide_x = exp_fit(centers, ptp_x, "sliding-window peak-to-peak x amplitude (model-free)")
    fit_slide_r = exp_fit(centers, ptp_r, "sliding-window peak-to-peak radial amplitude (model-free)")

    # ---- terminal divergence description (t>13.0s) ----
    idx13 = np.searchsorted(t_u, 13.0)
    print(f"\nterminal segment: y at t=13.0s -> {y_u[idx13]:.4f} m; y at t_end={t_u[-1]:.3f}s -> {y_u[-1]:.4f} m")
    print(f"radial at t=13.0s -> {r_u[idx13]:.4f} m; radial at t_end -> {r_u[-1]:.4f} m")

    # ================= REQUIRED FIGURE 1: position time series + envelope fit =================
    fig, ax = plt.subplots(3, 1, figsize=(11, 11))
    ax[0].plot(t_u, x_u, label="pos x (N, NED)", lw=0.7)
    ax[0].plot(t_u, y_u, label="pos y (E, NED)", lw=0.7)
    ax[0].plot(t_u, r_u, "k", label="radial |xy|", lw=1.2)
    ax[0].plot(t_u[peaks_r], r_u[peaks_r], "r^", ms=9, label="radial coarse local max")
    ax[0].plot(t_u[troughs_r], r_u[troughs_r], "gv", ms=9, label="radial coarse local min")
    ax[0].axvline(13.0, color="gray", ls="--", lw=1, label="terminal-divergence onset (~13.0s)")
    ax[0].legend(fontsize=7, ncol=3); ax[0].grid(alpha=0.3)
    ax[0].set_ylabel("position [m]"); ax[0].set_xlabel("time [s]")
    ax[0].set_title(f"{LOG.split('/')[-1]}: horizontal position, flight window "
                     f"[{t_to:.2f},{t_end:.2f}]s")

    ax[1].plot(t_u, x_dt, lw=0.5, color="tab:blue", label="x detrended")
    ax[1].plot(t_u, x_bp, lw=0.8, color="tab:purple", label=f"x bandpassed [{f_lo:.2f},{f_hi:.2f}] Hz")
    ax[1].plot(t_u, env_x, color="tab:red", lw=1.4, label="Hilbert envelope |x|")
    ax[1].plot(t_fit, fit_hilbert_x["A"] * np.exp(fit_hilbert_x["sigma"] * t_fit), "k--",
               label=f"Hilbert exp fit sigma={fit_hilbert_x['sigma']:.4f}/s")
    ax[1].legend(fontsize=7); ax[1].grid(alpha=0.3)
    ax[1].set_ylabel("x [m]"); ax[1].set_xlabel("time [s]")
    ax[1].set_title("x detrended + bandpass(verified freq) + Hilbert envelope fit")

    ax[2].plot(centers, ptp_x, "o-", label="sliding-window peak-to-peak x")
    ax[2].plot(centers, ptp_r, "s-", label="sliding-window peak-to-peak radial")
    ax[2].plot(centers, fit_slide_x["A"]*np.exp(fit_slide_x["sigma"]*centers), "--",
               label=f"exp fit x sigma={fit_slide_x['sigma']:.4f}/s")
    ax[2].plot(centers, fit_slide_r["A"]*np.exp(fit_slide_r["sigma"]*centers), "--",
               label=f"exp fit radial sigma={fit_slide_r['sigma']:.4f}/s")
    ax[2].legend(fontsize=7); ax[2].grid(alpha=0.3)
    ax[2].set_ylabel("peak-to-peak amplitude [m]"); ax[2].set_xlabel("window-center time [s]")
    ax[2].set_title(f"model-free sliding-window (win=T={T_center:.2f}s) peak-to-peak amplitude")

    fig.tight_layout()
    fig.savefig(f"{OUT}/task1_position_envelope_FINAL.png", dpi=130)
    plt.close(fig)

    # ================= REQUIRED FIGURE 2: PSD =================
    fig2, ax2 = plt.subplots(figsize=(8, 5))
    ax2.semilogy(f_x, Pxx, label="periodogram x (N)")
    ax2.semilogy(f_y, Pyy, label="periodogram y (E)")
    ax2.axvline(f_center, color="k", ls=":", label=f"x dominant local-max {f_center:.4f} Hz")
    ax2.set_xlim(0, 3)
    ax2.set_xlabel("freq [Hz]"); ax2.set_ylabel("PSD [m^2/Hz]")
    ax2.legend(); ax2.grid(alpha=0.3)
    ax2.set_title(f"full-window periodogram (df={df:.4f} Hz), {LOG.split('/')[-1]}")
    fig2.tight_layout()
    fig2.savefig(f"{OUT}/task1_psd_FINAL.png", dpi=130)
    plt.close(fig2)

    results = dict(
        log=LOG.split("/")[-1],
        flight_window=dict(t_to_s=float(t_to), t_end_s=float(t_end), duration_s=float(t_end - t_to)),
        sampling=dict(n=int(len(t_u)), fs_hz=float(fs), periodogram_df_hz=float(df)),
        dominant_frequency=dict(
            method="full-window Hann periodogram, genuine local maximum (argrelmax, order=3) on x-position spectrum",
            f_hz=float(f_center), T_s=float(T_center), omega_rad_s=float(omega_center),
        ),
        zero_crossing_crosscheck=dict(full_periods_s=fp_x.tolist(),
                                       median_s=float(np.median(fp_x)) if len(fp_x) else None,
                                       mean_s=float(np.mean(fp_x)) if len(fp_x) else None),
        envelope_hilbert_x_full_window=fit_hilbert_x,
        radial_coarse_peaks_full_window=dict(t=t_u[peaks_r].tolist(), r=r_u[peaks_r].tolist(), fit=fit_peaks),
        radial_coarse_troughs_full_window=dict(t=t_u[troughs_r].tolist(), r=r_u[troughs_r].tolist(), fit=fit_troughs),
        two_point_clean_peak_to_peak_sigma_per_s=two_pt_peak_sigma,
        two_point_clean_trough_to_trough_sigma_per_s=two_pt_trough_sigma,
        sliding_window_modelfree=dict(
            window_s=float(win), step_s=float(step),
            centers_s=centers.tolist(), ptp_x_m=ptp_x.tolist(), ptp_radial_m=ptp_r.tolist(),
            fit_x=fit_slide_x, fit_radial=fit_slide_r,
        ),
        terminal_divergence=dict(
            onset_s_approx=13.0,
            y_at_13s_m=float(y_u[idx13]), y_at_end_m=float(y_u[-1]),
            radial_at_13s_m=float(r_u[idx13]), radial_at_end_m=float(r_u[-1]),
            note="y crosses zero near t=13.1s and falls monotonically to negative "
                 "values through end of flight window; no return/turn-back observed "
                 "before thrust drops below live-motor gate at t_end.",
        ),
        method_disagreement_note=(
            "Sign and magnitude of the envelope growth/decay rate sigma is NOT "
            "consistent across methods: Hilbert/bandpass envelope on x (full window) "
            "gives negative sigma (decay) with narrow nominal CI (but n=5224 highly "
            "autocorrelated samples, so nominal CI is likely far too narrow / "
            "overconfident); coarse radial local-extrema log-slope and model-free "
            "sliding-window peak-to-peak amplitude mostly give positive sigma (growth), "
            "with substantial sensitivity to whether the startup transient and the "
            "terminal divergence (t>13s) are included/excluded from each fit."
        ),
    )
    with open(f"{OUT}/task1_results_FINAL.json", "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nsaved: {OUT}/task1_results_FINAL.json")
    print(f"saved: {OUT}/task1_position_envelope_FINAL.png")
    print(f"saved: {OUT}/task1_psd_FINAL.png")


if __name__ == "__main__":
    main()
