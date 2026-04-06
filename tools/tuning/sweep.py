#!/usr/bin/env python3
"""
Parameter Sweep Engine for StampFly Tuning
パラメータスイープエンジン

Supports both:
1. ESKF tuning via log replay (NIS-based evaluation)
2. PID tuning via closed-loop simulation (step response metrics)

All parameters are referenced through config.hpp (SSOT).

Usage:
    python -m tools.tuning.sweep --target eskf --log logs/latest.jsonl
    python -m tools.tuning.sweep --target position --disturbance 0.3
    sf tune eskf --log latest
    sf tune position
"""

import sys
import os
import json
import itertools
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path

# Add tools/ to path
_tools_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

import numpy as np
from common.config_parser import load_config


@dataclass
class SweepParam:
    """Single parameter to sweep.
    スイープする単一パラメータ。
    """
    namespace: str          # e.g., 'eskf', 'position_control'
    name: str               # e.g., 'ACCEL_NOISE', 'POS_KP'
    values: List[float]     # Values to try
    current: float = 0.0    # Current value from config.hpp

    @property
    def key(self) -> str:
        return f"{self.namespace}.{self.name}"


@dataclass
class SweepResult:
    """Result of a single parameter combination.
    単一パラメータ組み合わせの結果。
    """
    params: Dict[str, float]      # {namespace.NAME: value}
    metrics: Dict[str, float]     # Performance metrics
    score: float                  # Composite score (lower is better)
    is_current: bool = False      # True if this is the current config


def sweep_eskf(log_path: str, params: Optional[List[SweepParam]] = None,
               config_path: Optional[str] = None) -> List[SweepResult]:
    """Sweep ESKF parameters using log replay and NIS evaluation.
    ログリプレイと NIS 評価で ESKF パラメータをスイープ。
    """
    from eskf_sim.eskf import ESKF, ESKFConfig
    from eskf_sim.loader import load_log
    from eskf_sim.metrics import compute_self_consistency

    config = load_config(config_path)

    # Default sweep parameters if not specified
    if params is None:
        eskf = config.get('eskf', {})
        params = [
            SweepParam('eskf', 'ACCEL_NOISE',
                      [0.1, 0.2, 0.3, 0.5], eskf.get('ACCEL_NOISE', 0.3)),
            SweepParam('eskf', 'FLOW_NOISE',
                      [0.1, 0.2, 0.3, 0.5], eskf.get('FLOW_NOISE', 0.3)),
        ]

    # Load log
    log = load_log(log_path)

    results = []
    total = 1
    for p in params:
        total *= len(p.values)
    print(f"Sweeping {len(params)} params, {total} combinations...")

    # Generate all combinations
    param_grids = [p.values for p in params]
    for combo in itertools.product(*param_grids):
        # Build config override
        overrides = {}
        param_dict = {}
        is_current = True
        for p, val in zip(params, combo):
            overrides[p.key] = val
            param_dict[p.key] = val
            if abs(val - p.current) > 1e-8:
                is_current = False

        # Create ESKFConfig with overrides
        cfg = ESKFConfig.from_firmware(config_path)
        for p, val in zip(params, combo):
            attr_map = {
                'ACCEL_NOISE': 'accel_noise',
                'FLOW_NOISE': 'flow_noise',
                'ACCEL_BIAS_NOISE': 'accel_bias_noise',
                'TOF_NOISE': 'tof_noise',
                'ACCEL_ATT_NOISE': 'accel_att_noise',
            }
            attr = attr_map.get(p.name)
            if attr:
                setattr(cfg, attr, val)

        # Run ESKF replay
        eskf = ESKF(cfg)
        eskf.init()

        # Initialize from first sample
        first_sample = None
        for s in log.samples:
            if s.eskf_quat is not None:
                first_sample = s
                break

        if first_sample:
            eskf.state.quat = first_sample.eskf_quat.copy()
            if first_sample.eskf_gyro_bias is not None:
                eskf.state.gyro_bias = first_sample.eskf_gyro_bias.copy()
            if first_sample.eskf_accel_bias is not None:
                eskf.state.accel_bias = first_sample.eskf_accel_bias.copy()

        state_history = []
        p_trace_history = []

        prev_ts = None
        for s in log.samples:
            ts = s.timestamp_us / 1e6
            eskf._diag_timestamp = ts

            if prev_ts is not None:
                dt = ts - prev_ts
                if 0.001 < dt < 0.05:
                    eskf.predict(s.gyro, s.accel, dt)

                    # Subsample accel attitude update
                    if len(state_history) % 4 == 0:
                        eskf.update_accel_attitude(s.accel)

            prev_ts = ts

            # Flow update
            if s.flow_dx is not None and s.tof_distance is not None:
                if s.flow_quality is not None and s.flow_quality >= 25:
                    eskf.update_flow_raw(
                        s.flow_dx, s.flow_dy, s.tof_distance,
                        0.01, s.gyro[0], s.gyro[1])

            # ToF update
            if s.tof_distance is not None and s.tof_distance > 0.02:
                eskf.update_tof(s.tof_distance)

            # Record state every 40 samples (~10Hz)
            if len(state_history) % 40 == 0 or len(state_history) == 0:
                state_history.append((ts, eskf.state))
                p_trace_history.append(float(np.trace(eskf.P)))

            # Increment even if not recorded
            if len(state_history) == 0:
                state_history.append((ts, eskf.state))

        # Evaluate
        sc = compute_self_consistency(
            eskf.diagnostics, state_history, p_trace_history)

        results.append(SweepResult(
            params=param_dict,
            metrics=sc.to_dict(),
            score=sc.compute_score(),
            is_current=is_current,
        ))

    results.sort(key=lambda r: r.score)
    return results


def sweep_position(params: Optional[List[SweepParam]] = None,
                   config_path: Optional[str] = None,
                   disturbance: float = 0.3) -> List[SweepResult]:
    """Sweep position control parameters using closed-loop simulation.
    閉ループシミュレーションで位置制御パラメータをスイープ。
    """
    from sim.closed_loop import ClosedLoopSim

    config = load_config(config_path)

    if params is None:
        pc = config.get('position_control', {})
        params = [
            SweepParam('position_control', 'POS_KP',
                      [0.5, 1.0, 1.5, 2.0], pc.get('POS_KP', 1.0)),
            SweepParam('position_control', 'VEL_KP',
                      [0.15, 0.3, 0.5], pc.get('VEL_KP', 0.3)),
        ]

    results = []
    total = 1
    for p in params:
        total *= len(p.values)
    print(f"Sweeping {len(params)} params, {total} combinations...")

    for combo in itertools.product(*[p.values for p in params]):
        overrides = {}
        param_dict = {}
        is_current = True
        for p, val in zip(params, combo):
            overrides[p.key] = val
            param_dict[p.key] = val
            if abs(val - p.current) > 1e-8:
                is_current = False

        try:
            sim = ClosedLoopSim(config_path, overrides)
            result = sim.run(
                duration=10.0,
                disturbance_pos=np.array([disturbance, 0.0]),
                mode='position',
            )
            m = result.metrics()

            # Score: weighted combination
            score = (
                m['pos_x_rms'] * 10 +
                m['settle_time'] * 0.5 +
                m['pitch_max_deg'] * 0.1
            )

            results.append(SweepResult(
                params=param_dict,
                metrics=m,
                score=score,
                is_current=is_current,
            ))
        except Exception as e:
            print(f"  Error with {param_dict}: {e}")

    results.sort(key=lambda r: r.score)
    return results


def print_results(results: List[SweepResult], top_n: int = 10):
    """Print sweep results summary."""
    print(f"\n{'='*70}")
    print(f"Top {min(top_n, len(results))} results (lower score = better)")
    print(f"{'='*70}")

    for i, r in enumerate(results[:top_n]):
        marker = " <-- CURRENT" if r.is_current else ""
        params_str = ", ".join(f"{k.split('.')[-1]}={v}" for k, v in r.params.items())
        print(f"#{i+1}  score={r.score:.4f}  {params_str}{marker}")

        # Key metrics
        for mk in ['pos_x_rms', 'settle_time', 'pitch_max_deg',
                    'flow_nis', 'accel_bias_drift_rate', 'position_span_xy']:
            if mk in r.metrics:
                val = r.metrics[mk]
                if isinstance(val, dict):
                    val = val.get('mean', val)
                print(f"    {mk}: {val}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='StampFly Parameter Sweep')
    parser.add_argument('--target', choices=['eskf', 'position', 'altitude', 'attitude', 'rate'],
                       default='position', help='Tuning target')
    parser.add_argument('--log', help='Log file for ESKF replay')
    parser.add_argument('--disturbance', type=float, default=0.3,
                       help='Position disturbance [m]')
    parser.add_argument('--top', type=int, default=10, help='Show top N results')
    args = parser.parse_args()

    if args.target == 'eskf':
        if not args.log:
            print("Error: --log required for ESKF sweep")
            sys.exit(1)
        results = sweep_eskf(args.log)
    elif args.target == 'position':
        results = sweep_position(disturbance=args.disturbance)
    else:
        print(f"Target '{args.target}' not yet implemented")
        sys.exit(1)

    print_results(results, args.top)
