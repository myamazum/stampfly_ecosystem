#!/usr/bin/env python3
"""
Task 2 — linear cascade model pole computation, reusing functions from
analysis/scripts/poshold_loop_design.py (imported, not reimplemented).

Sweeps the tilt->accel plant gain K (script's variable name `K`, units m/s^2/rad,
used as `a = K*tilt_cmd(t-tau)` in the plant) from 2.0 to 10.0, for two gain
configurations:
  O (script CURRENT-style): pos_kp=1.0 (Task1b could not recover position-loop
     gains from the log, so this is the "assumed period-value" per task
     instructions), pos_ti=5.0, pos_td=0.0, vel_kp=0.8, vel_ti=2.0, vel_td=0.0
     [ti/td taken from the script's own CURRENT tuple, since the task only
     specifies kp for O/N]
  N: pos_kp=0.4, pos_ti=5.0, pos_td=0.0, vel_kp=3.0, vel_ti=2.0, vel_td=0.0

tau (loop delay) uses the script's own declared default constants:
  primary: tau = 0.15 s (middle of the script's TAU_RANGE=[0.05,0.15,0.30])
  cross-check: tau = 0 s (the script's own self-calibration output when run
  unmodified: "nominal plant: K=4.0 (0.41 g), tau=0 ms")
Both are reported.

Pole extraction uses the script's own `fit_pole()` (peak/zero-crossing based
omega, log-amplitude-slope sigma) via `lin_pole()`, called with a small initial
offset x0=0.03m to stay in the (mostly) linear/non-saturated regime, exactly as
the script's own `robust_worst_sigma()` does.
"""
import sys
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, "/Users/kouhei/tmp/github/stampfly_ecosystem/analysis/scripts")
import poshold_loop_design as M  # noqa: E402

OUT = "/private/tmp/claude-501/-Users-kouhei-tmp-github-stampfly-ecosystem/5e87008a-97a4-42d5-9e0e-02387c2a8022/scratchpad/verify_A"

GAINS_O = (1.0, 5.0, 0.0, 0.8, 2.0, 0.0)   # pos_kp,pos_ti,pos_td, vel_kp,vel_ti,vel_td
GAINS_N = (0.4, 5.0, 0.0, 3.0, 2.0, 0.0)

K_SWEEP = np.arange(2.0, 10.01, 0.2)
TAU_PRIMARY = 0.15
TAU_ALT = 0.0


def sweep(gains, tau):
    sig, om = [], []
    for K in K_SWEEP:
        p = M.lin_pole(gains, K, tau)
        if p is None:
            sig.append(np.nan)
            om.append(np.nan)
        else:
            o, s, z = p
            sig.append(s)
            om.append(o)
    return np.array(sig), np.array(om)


def main():
    print(f"K sweep: {K_SWEEP[0]} to {K_SWEEP[-1]}, n={len(K_SWEEP)} points")
    print(f"gains O = {GAINS_O}")
    print(f"gains N = {GAINS_N}")

    results = {"K_sweep": K_SWEEP.tolist(), "gains_O": GAINS_O, "gains_N": GAINS_N,
               "tau_primary_s": TAU_PRIMARY, "tau_alt_s": TAU_ALT}

    for tau_label, tau in [("tau_0.15s", TAU_PRIMARY), ("tau_0.0s", TAU_ALT)]:
        sig_O, om_O = sweep(GAINS_O, tau)
        sig_N, om_N = sweep(GAINS_N, tau)
        results[tau_label] = dict(
            sigma_O=sig_O.tolist(), omega_O=om_O.tolist(),
            sigma_N=sig_N.tolist(), omega_N=om_N.tolist(),
        )
        print(f"\n=== tau={tau}s ===")
        print(f"{'K':>6}{'sigma_O':>10}{'omega_O':>10}{'sigma_N':>10}{'omega_N':>10}")
        for K, sO, oO, sN, oN in zip(K_SWEEP, sig_O, om_O, sig_N, om_N):
            print(f"{K:6.2f}{sO:10.4f}{oO:10.4f}{sN:10.4f}{oN:10.4f}")

    # ---- required numeric table: K=3.9 and K=9.81 ----
    print("\n=== required table: K=3.9, K=9.81 ===")
    table = {}
    for tau_label, tau in [("tau_0.15s", TAU_PRIMARY), ("tau_0.0s", TAU_ALT)]:
        table[tau_label] = {}
        for Kval in [3.9, 9.81]:
            pO = M.lin_pole(GAINS_O, Kval, tau)
            pN = M.lin_pole(GAINS_N, Kval, tau)
            table[tau_label][f"K={Kval}"] = dict(
                O=dict(omega=pO[0], sigma=pO[1], zeta=pO[2]) if pO else None,
                N=dict(omega=pN[0], sigma=pN[1], zeta=pN[2]) if pN else None,
            )
            print(f"tau={tau}s K={Kval}: "
                  f"O -> omega={pO[0]:.4f} sigma={pO[1]:+.4f} zeta={pO[2]:+.4f}  |  "
                  f"N -> omega={pN[0]:.4f} sigma={pN[1]:+.4f} zeta={pN[2]:+.4f}")

    with open(f"{OUT}/task2_results.json", "w") as f:
        json.dump(results | {"table_K3.9_K9.81": table}, f, indent=2, default=float)

    # ---- figure: pole trajectory (sigma, omega) vs K, both configs, both tau ----
    fig, axes = plt.subplots(2, 2, figsize=(12, 9))
    for ax_row, (tau_label, tau) in zip(axes, [("tau=0.15s", TAU_PRIMARY), ("tau=0s", TAU_ALT)]):
        sig_O, om_O = sweep(GAINS_O, tau)
        sig_N, om_N = sweep(GAINS_N, tau)
        ax = ax_row[0]
        ax.plot(K_SWEEP, sig_O, "o-", label="config O (pos_kp=1.0, vel_kp=0.8)", ms=3)
        ax.plot(K_SWEEP, sig_N, "s-", label="config N (pos_kp=0.4, vel_kp=3.0)", ms=3)
        ax.axhline(0, color="k", lw=0.7, ls=":")
        ax.set_xlabel("K [m/s^2/rad]"); ax.set_ylabel("sigma [1/s]")
        ax.set_title(f"dominant pole real part sigma vs K ({tau_label})")
        ax.legend(fontsize=8); ax.grid(alpha=0.3)

        ax2 = ax_row[1]
        ax2.plot(K_SWEEP, om_O, "o-", label="config O", ms=3)
        ax2.plot(K_SWEEP, om_N, "s-", label="config N", ms=3)
        ax2.set_xlabel("K [m/s^2/rad]"); ax2.set_ylabel("omega [rad/s]")
        ax2.set_title(f"dominant pole imag part omega vs K ({tau_label})")
        ax2.legend(fontsize=8); ax2.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUT}/task2_pole_sweep.png", dpi=130)
    plt.close(fig)

    # ---- complementary: pole locus in s-plane (sigma, omega) ----
    fig2, ax = plt.subplots(figsize=(7, 6))
    for tau_label, tau, marker in [("tau=0.15s", TAU_PRIMARY, "o"), ("tau=0s", TAU_ALT, "^")]:
        sig_O, om_O = sweep(GAINS_O, tau)
        sig_N, om_N = sweep(GAINS_N, tau)
        ax.plot(sig_O, om_O, marker + "-", label=f"O, {tau_label}", ms=3, alpha=0.8)
        ax.plot(sig_N, om_N, marker + "-", label=f"N, {tau_label}", ms=3, alpha=0.8)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("sigma [1/s] (Re)"); ax.set_ylabel("omega [rad/s] (Im)")
    ax.set_title("dominant closed-loop pole locus as K sweeps 2.0->10.0")
    ax.legend(fontsize=8); ax.grid(alpha=0.3)
    fig2.tight_layout()
    fig2.savefig(f"{OUT}/task2_pole_locus.png", dpi=130)
    plt.close(fig2)

    print(f"\nsaved: {OUT}/task2_results.json")
    print(f"saved: {OUT}/task2_pole_sweep.png")
    print(f"saved: {OUT}/task2_pole_locus.png")


if __name__ == "__main__":
    main()
