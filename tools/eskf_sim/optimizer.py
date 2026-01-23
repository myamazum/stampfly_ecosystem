"""
ESKF Parameter Optimizer
ESKFパラメータ最適化

Supports multiple optimization methods:
- Simulated Annealing (SA) - recommended for global search
- Gradient Descent (GD) - for local refinement
- Grid Search - for single parameter analysis
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable
import os
import sys

import numpy as np

# Try to import scipy for optimization
try:
    from scipy.optimize import dual_annealing
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False

from .eskf import ESKF, ESKFConfig
from .loader import load_csv
from .metrics import compute_metrics, MetricsResult


# Parameter definitions with search bounds
# パラメータ定義と探索範囲
PARAMS = {
    'gyro_noise':       {'min': 0.0001, 'max': 0.1,   'default': 0.009655},
    'accel_noise':      {'min': 0.01,   'max': 0.5,   'default': 0.062885},
    'gyro_bias_noise':  {'min': 1e-6,   'max': 0.01,  'default': 0.000013},
    'accel_bias_noise': {'min': 1e-5,   'max': 0.01,  'default': 0.0001},
    'flow_noise':       {'min': 0.001,  'max': 0.5,   'default': 0.005232},
    'tof_noise':        {'min': 0.0001, 'max': 0.1,   'default': 0.00254},
    'accel_att_noise':  {'min': 0.001,  'max': 1.0,   'default': 0.02},
}

PARAM_NAMES = list(PARAMS.keys())


@dataclass
class OptimizationResult:
    """Optimization result
    最適化結果
    """
    params: Dict[str, float]            # Best parameters
    cost: float                          # Best cost
    iterations: int                      # Number of iterations
    evaluations: int                     # Number of cost evaluations
    results_per_file: List[dict] = field(default_factory=list)  # Per-file results


class ESKFOptimizer:
    """ESKF parameter optimizer
    ESKFパラメータ最適化器
    """

    def __init__(
        self,
        data_files: List[str],
        cost_fn: str = 'rmse',
        quiet: bool = False,
    ):
        """Initialize optimizer

        Args:
            data_files: List of CSV log files to optimize against
            cost_fn: Cost function type ('rmse', 'mae', 'position')
            quiet: Suppress progress output
        """
        self.data_files = data_files
        self.cost_fn_type = cost_fn
        self.quiet = quiet

        self.eval_count = 0
        self.best_cost = float('inf')
        self.best_params: Optional[Dict[str, float]] = None
        self.best_results: List[dict] = []

        # Load all data files
        self.datasets = []
        for f in data_files:
            try:
                data = load_csv(f)
                self.datasets.append({
                    'path': f,
                    'name': Path(f).name,
                    'data': data,
                })
            except Exception as e:
                print(f"Warning: Failed to load {f}: {e}", file=sys.stderr)

        if not self.datasets:
            raise ValueError("No valid data files loaded")

    def _params_dict_to_config(self, params_dict: Dict[str, float]) -> ESKFConfig:
        """Convert parameter dictionary to ESKFConfig"""
        config = ESKFConfig()
        for name, value in params_dict.items():
            if hasattr(config, name):
                setattr(config, name, value)
        return config

    def _run_eskf_replay(self, config: ESKFConfig, dataset: dict) -> Tuple[List[dict], List[dict]]:
        """Run ESKF replay on a dataset

        Returns:
            Tuple of (estimated_states, reference_states)
        """
        eskf = ESKF(config)
        eskf.init()

        data = dataset['data']
        estimated_states = []
        reference_states = []

        prev_timestamp_us = None

        for sample in data.samples:
            # Compute dt
            if prev_timestamp_us is None:
                dt = 0.0025  # Default 400Hz
            else:
                dt = (sample.timestamp_us - prev_timestamp_us) / 1e6
            prev_timestamp_us = sample.timestamp_us

            # Skip if dt is invalid
            if dt <= 0 or dt > 0.1:
                continue

            # ESKF prediction
            eskf.predict(sample.accel, sample.gyro, dt)

            # Measurement updates
            if sample.tof_distance is not None and sample.tof_distance > 0.02:
                eskf.update_tof(sample.tof_distance)

            if sample.baro_altitude is not None:
                eskf.update_baro(sample.baro_altitude)

            if sample.flow_dx is not None and sample.tof_distance is not None:
                eskf.update_flow_raw(
                    sample.flow_dx,
                    sample.flow_dy or 0,
                    sample.tof_distance,
                    dt,
                    sample.gyro[0],
                    sample.gyro[1],
                )

            # Attitude correction
            eskf.update_accel_attitude(sample.accel)

            # Record states
            state = eskf.get_state()
            euler = state.euler

            estimated_states.append({
                'position': state.position.tolist(),
                'velocity': state.velocity.tolist(),
                'euler_deg': [np.rad2deg(e) for e in euler],
            })

            if sample.eskf_position is not None:
                ref_euler = self._quat_to_euler_deg(sample.eskf_quat) if sample.eskf_quat is not None else [0, 0, 0]
                reference_states.append({
                    'position': sample.eskf_position.tolist(),
                    'velocity': sample.eskf_velocity.tolist() if sample.eskf_velocity is not None else [0, 0, 0],
                    'euler_deg': ref_euler,
                })

        return estimated_states, reference_states

    def _compute_cost(self, params_dict: Dict[str, float]) -> Tuple[float, List[dict]]:
        """Compute total cost for all datasets

        Returns:
            Tuple of (total_cost, per_file_results)
        """
        self.eval_count += 1

        config = self._params_dict_to_config(params_dict)
        total_cost = 0.0
        results = []

        for dataset in self.datasets:
            try:
                est_states, ref_states = self._run_eskf_replay(config, dataset)

                if not est_states or not ref_states:
                    # No valid data
                    total_cost += 1e6
                    results.append({
                        'file': dataset['name'],
                        'cost': 1e6,
                        'error': 'No valid states',
                    })
                    continue

                metrics, _ = compute_metrics(est_states, ref_states)

                # Compute cost based on selected function
                if self.cost_fn_type == 'position':
                    cost = np.sqrt(np.sum(metrics.position_rmse ** 2))
                elif self.cost_fn_type == 'mae':
                    cost = np.mean(metrics.position_mae) + np.mean(metrics.attitude_mae) * 0.01
                else:  # rmse
                    cost = np.sqrt(np.sum(metrics.position_rmse ** 2)) + np.mean(metrics.attitude_rmse) * 0.01

                total_cost += cost
                results.append({
                    'file': dataset['name'],
                    'cost': cost,
                    'pos_rmse': metrics.position_rmse.tolist(),
                    'att_rmse': metrics.attitude_rmse.tolist(),
                })

            except Exception as e:
                total_cost += 1e6
                results.append({
                    'file': dataset['name'],
                    'cost': 1e6,
                    'error': str(e),
                })

        # Update best
        if total_cost < self.best_cost:
            self.best_cost = total_cost
            self.best_params = params_dict.copy()
            self.best_results = results

        # Progress output
        if not self.quiet and self.eval_count % 50 == 0:
            print(f"  [{self.eval_count:4d}] cost={total_cost:.4f}")

        return total_cost, results

    def _cost_function_array(self, x: np.ndarray) -> float:
        """Cost function for scipy optimizers (log-scale input)"""
        params_dict = {}
        for i, name in enumerate(PARAM_NAMES):
            val = np.exp(x[i])
            val = np.clip(val, PARAMS[name]['min'], PARAMS[name]['max'])
            params_dict[name] = val
        cost, _ = self._compute_cost(params_dict)
        return cost

    def optimize_sa(self, max_iter: int = 500) -> Optional[Dict[str, float]]:
        """Simulated Annealing optimization
        焼きなまし法による最適化

        Args:
            max_iter: Maximum iterations

        Returns:
            Best parameters dictionary or None on failure
        """
        if not HAS_SCIPY:
            print("Error: scipy is required for SA method", file=sys.stderr)
            return None

        if not self.quiet:
            print(f"\n=== Simulated Annealing Optimization ===")
            print(f"Datasets: {[d['name'] for d in self.datasets]}")
            print(f"Max iterations: {max_iter}")
            print("-" * 50)

        # Bounds in log-space
        bounds = [
            (np.log(PARAMS[name]['min']), np.log(PARAMS[name]['max']))
            for name in PARAM_NAMES
        ]

        result = dual_annealing(
            self._cost_function_array,
            bounds,
            maxiter=max_iter,
            seed=42,
            no_local_search=False,
        )

        # Convert result back
        best_params = {}
        for i, name in enumerate(PARAM_NAMES):
            best_params[name] = np.clip(
                np.exp(result.x[i]),
                PARAMS[name]['min'],
                PARAMS[name]['max']
            )

        return best_params

    def optimize_gd(self, max_iter: int = 80, learning_rate: float = 0.08) -> Optional[Dict[str, float]]:
        """Gradient Descent optimization
        勾配降下法による最適化

        Args:
            max_iter: Maximum iterations
            learning_rate: Initial learning rate

        Returns:
            Best parameters dictionary or None on failure
        """
        if not self.quiet:
            print(f"\n=== Gradient Descent Optimization ===")
            print(f"Datasets: {[d['name'] for d in self.datasets]}")
            print(f"Max iterations: {max_iter}")
            print("-" * 50)

        # Initialize with default values (log scale)
        log_params = {name: np.log(info['default']) for name, info in PARAMS.items()}

        for iteration in range(max_iter):
            # Compute gradient using central difference
            gradient = {}
            epsilon = 0.05

            for name in log_params:
                log_plus = log_params.copy()
                log_minus = log_params.copy()
                log_plus[name] += epsilon
                log_minus[name] -= epsilon

                params_plus = {
                    n: np.clip(np.exp(v), PARAMS[n]['min'], PARAMS[n]['max'])
                    for n, v in log_plus.items()
                }
                params_minus = {
                    n: np.clip(np.exp(v), PARAMS[n]['min'], PARAMS[n]['max'])
                    for n, v in log_minus.items()
                }

                cost_plus, _ = self._compute_cost(params_plus)
                cost_minus, _ = self._compute_cost(params_minus)
                gradient[name] = (cost_plus - cost_minus) / (2 * epsilon)

            # Current cost
            params = {
                n: np.clip(np.exp(v), PARAMS[n]['min'], PARAMS[n]['max'])
                for n, v in log_params.items()
            }
            cost, _ = self._compute_cost(params)

            if not self.quiet and iteration % 10 == 0:
                print(f"  Iter {iteration}: cost={cost:.4f}")

            # Line search
            alpha = learning_rate
            for _ in range(5):
                new_log_params = {}
                for name in log_params:
                    new_log_params[name] = log_params[name] - alpha * gradient[name]
                    log_min = np.log(PARAMS[name]['min'])
                    log_max = np.log(PARAMS[name]['max'])
                    new_log_params[name] = np.clip(new_log_params[name], log_min, log_max)

                new_params = {
                    n: np.clip(np.exp(v), PARAMS[n]['min'], PARAMS[n]['max'])
                    for n, v in new_log_params.items()
                }
                new_cost, _ = self._compute_cost(new_params)

                if new_cost < cost:
                    log_params = new_log_params
                    break
                alpha *= 0.5
            else:
                # Small step if line search fails
                for name in log_params:
                    log_params[name] -= 0.01 * gradient[name]
                    log_min = np.log(PARAMS[name]['min'])
                    log_max = np.log(PARAMS[name]['max'])
                    log_params[name] = np.clip(log_params[name], log_min, log_max)

        return self.best_params

    def print_results(self) -> None:
        """Print optimization results"""
        if self.best_params is None:
            print("No optimization results available")
            return

        print("\n" + "=" * 60)
        print("OPTIMIZATION COMPLETE")
        print("=" * 60)
        print(f"Total evaluations: {self.eval_count}")
        print(f"Best total cost: {self.best_cost:.6f}")

        print("\n" + "-" * 60)
        print("Results per dataset:")
        print("-" * 60)
        for r in self.best_results:
            if 'error' in r:
                print(f"  {r['file']}: ERROR - {r['error']}")
            else:
                pos_rmse = r.get('pos_rmse', [0, 0, 0])
                att_rmse = r.get('att_rmse', [0, 0, 0])
                print(f"  {r['file']}:")
                print(f"    Position RMSE: X={pos_rmse[0]:.4f}, Y={pos_rmse[1]:.4f}, Z={pos_rmse[2]:.4f} m")
                print(f"    Attitude RMSE: R={att_rmse[0]:.2f}, P={att_rmse[1]:.2f}, Y={att_rmse[2]:.2f} deg")

        print("\n" + "-" * 60)
        print("Optimized Parameters:")
        print("-" * 60)
        for name in PARAM_NAMES:
            print(f"  {name:<20} = {self.best_params[name]:.8f}")

        print("\n" + "-" * 60)
        print("C++ format (for eskf.hpp):")
        print("-" * 60)
        for name in PARAM_NAMES:
            print(f"cfg.{name} = {self.best_params[name]:.8f}f;")

    def _quat_to_euler_deg(self, quat) -> List[float]:
        """Convert quaternion to euler angles in degrees"""
        if quat is None:
            return [0, 0, 0]

        w, x, y, z = quat

        # Roll
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)

        # Pitch
        sinp = 2.0 * (w * y - z * x)
        if np.abs(sinp) >= 1:
            pitch = np.sign(sinp) * np.pi / 2
        else:
            pitch = np.arcsin(sinp)

        # Yaw
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)

        return [np.rad2deg(roll), np.rad2deg(pitch), np.rad2deg(yaw)]
