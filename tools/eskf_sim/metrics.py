"""
ESKF Error Metrics Calculation
ESKF誤差メトリクス計算

Computes error metrics between estimated and reference states.
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np


@dataclass
class MetricsResult:
    """Error metrics result
    誤差メトリクス結果
    """
    # Position metrics [m]
    position_rmse: np.ndarray = field(default_factory=lambda: np.zeros(3))
    position_mae: np.ndarray = field(default_factory=lambda: np.zeros(3))
    position_max: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Velocity metrics [m/s]
    velocity_rmse: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity_mae: np.ndarray = field(default_factory=lambda: np.zeros(3))
    velocity_max: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Attitude metrics [deg]
    attitude_rmse: np.ndarray = field(default_factory=lambda: np.zeros(3))
    attitude_mae: np.ndarray = field(default_factory=lambda: np.zeros(3))
    attitude_max: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Gyro bias metrics [deg/s]
    gyro_bias_rmse: np.ndarray = field(default_factory=lambda: np.zeros(3))
    gyro_bias_mae: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Accel bias metrics [m/s^2]
    accel_bias_rmse: np.ndarray = field(default_factory=lambda: np.zeros(3))
    accel_bias_mae: np.ndarray = field(default_factory=lambda: np.zeros(3))

    # Summary
    total_samples: int = 0
    duration_s: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON output"""
        return {
            'position': {
                'rmse': self.position_rmse.tolist(),
                'mae': self.position_mae.tolist(),
                'max': self.position_max.tolist(),
            },
            'velocity': {
                'rmse': self.velocity_rmse.tolist(),
                'mae': self.velocity_mae.tolist(),
                'max': self.velocity_max.tolist(),
            },
            'attitude_deg': {
                'rmse': self.attitude_rmse.tolist(),
                'mae': self.attitude_mae.tolist(),
                'max': self.attitude_max.tolist(),
            },
            'gyro_bias_deg_s': {
                'rmse': self.gyro_bias_rmse.tolist(),
                'mae': self.gyro_bias_mae.tolist(),
            },
            'accel_bias_m_s2': {
                'rmse': self.accel_bias_rmse.tolist(),
                'mae': self.accel_bias_mae.tolist(),
            },
            'summary': {
                'total_rmse': float(np.sqrt(np.sum(self.position_rmse**2))),
                'samples': self.total_samples,
                'duration_s': self.duration_s,
            }
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=indent)

    def print_summary(self) -> None:
        """Print summary to console"""
        print("=" * 60)
        print("ESKF Error Metrics Summary")
        print("=" * 60)
        print(f"Samples: {self.total_samples}, Duration: {self.duration_s:.2f}s")
        print()

        print("Position [m]:")
        print(f"  RMSE: X={self.position_rmse[0]:.4f}, Y={self.position_rmse[1]:.4f}, Z={self.position_rmse[2]:.4f}")
        print(f"  MAE:  X={self.position_mae[0]:.4f}, Y={self.position_mae[1]:.4f}, Z={self.position_mae[2]:.4f}")
        print(f"  Max:  X={self.position_max[0]:.4f}, Y={self.position_max[1]:.4f}, Z={self.position_max[2]:.4f}")
        print()

        print("Velocity [m/s]:")
        print(f"  RMSE: X={self.velocity_rmse[0]:.4f}, Y={self.velocity_rmse[1]:.4f}, Z={self.velocity_rmse[2]:.4f}")
        print()

        print("Attitude [deg]:")
        print(f"  RMSE: R={self.attitude_rmse[0]:.2f}, P={self.attitude_rmse[1]:.2f}, Y={self.attitude_rmse[2]:.2f}")
        print(f"  MAE:  R={self.attitude_mae[0]:.2f}, P={self.attitude_mae[1]:.2f}, Y={self.attitude_mae[2]:.2f}")
        print(f"  Max:  R={self.attitude_max[0]:.2f}, P={self.attitude_max[1]:.2f}, Y={self.attitude_max[2]:.2f}")
        print()

        total_rmse = np.sqrt(np.sum(self.position_rmse**2))
        print(f"Total Position RMSE: {total_rmse:.4f} m")
        print("=" * 60)


@dataclass
class TimeSeriesError:
    """Time series error data for detailed analysis
    詳細解析用の時系列誤差データ
    """
    timestamps_us: np.ndarray       # [us]
    position_error: np.ndarray      # Nx3 [m]
    velocity_error: np.ndarray      # Nx3 [m/s]
    attitude_error_deg: np.ndarray  # Nx3 [deg]

    def to_csv_rows(self) -> List[dict]:
        """Convert to CSV row dictionaries"""
        rows = []
        for i in range(len(self.timestamps_us)):
            rows.append({
                'timestamp_us': int(self.timestamps_us[i]),
                'pos_err_x': self.position_error[i, 0],
                'pos_err_y': self.position_error[i, 1],
                'pos_err_z': self.position_error[i, 2],
                'vel_err_x': self.velocity_error[i, 0],
                'vel_err_y': self.velocity_error[i, 1],
                'vel_err_z': self.velocity_error[i, 2],
                'att_err_roll': self.attitude_error_deg[i, 0],
                'att_err_pitch': self.attitude_error_deg[i, 1],
                'att_err_yaw': self.attitude_error_deg[i, 2],
            })
        return rows


def compute_metrics(
    estimated_states: List[dict],
    reference_states: List[dict],
    timestamps_us: Optional[List[int]] = None,
) -> Tuple[MetricsResult, Optional[TimeSeriesError]]:
    """Compute error metrics between estimated and reference states
    推定と参照状態間の誤差メトリクスを計算

    Args:
        estimated_states: List of estimated state dictionaries
        reference_states: List of reference state dictionaries
        timestamps_us: Optional list of timestamps

    Returns:
        Tuple of (MetricsResult, TimeSeriesError or None)
    """
    n = min(len(estimated_states), len(reference_states))
    if n == 0:
        return MetricsResult(), None

    # Collect errors
    pos_errors = []
    vel_errors = []
    att_errors = []
    gb_errors = []
    ab_errors = []

    for i in range(n):
        est = estimated_states[i]
        ref = reference_states[i]

        # Position error
        if 'position' in est and 'position' in ref:
            pos_e = np.array(est['position']) - np.array(ref['position'])
            pos_errors.append(pos_e)
        elif all(k in est for k in ['pos_x', 'pos_y', 'pos_z']):
            pos_e = np.array([
                est['pos_x'] - ref.get('pos_x', 0),
                est['pos_y'] - ref.get('pos_y', 0),
                est['pos_z'] - ref.get('pos_z', 0),
            ])
            pos_errors.append(pos_e)

        # Velocity error
        if 'velocity' in est and 'velocity' in ref:
            vel_e = np.array(est['velocity']) - np.array(ref['velocity'])
            vel_errors.append(vel_e)
        elif all(k in est for k in ['vel_x', 'vel_y', 'vel_z']):
            vel_e = np.array([
                est['vel_x'] - ref.get('vel_x', 0),
                est['vel_y'] - ref.get('vel_y', 0),
                est['vel_z'] - ref.get('vel_z', 0),
            ])
            vel_errors.append(vel_e)

        # Attitude error (in degrees)
        if 'euler_deg' in est and 'euler_deg' in ref:
            att_e = np.array(est['euler_deg']) - np.array(ref['euler_deg'])
        elif all(k in est for k in ['roll_deg', 'pitch_deg', 'yaw_deg']):
            att_e = np.array([
                est['roll_deg'] - ref.get('roll_deg', 0),
                est['pitch_deg'] - ref.get('pitch_deg', 0),
                est['yaw_deg'] - ref.get('yaw_deg', 0),
            ])
        else:
            att_e = np.zeros(3)

        # Wrap yaw error to [-180, 180]
        att_e[2] = _wrap_angle_deg(att_e[2])
        att_errors.append(att_e)

        # Gyro bias error (convert to deg/s for display)
        if 'gyro_bias' in est and 'gyro_bias' in ref:
            gb_e = np.rad2deg(np.array(est['gyro_bias']) - np.array(ref['gyro_bias']))
            gb_errors.append(gb_e)

        # Accel bias error
        if 'accel_bias' in est and 'accel_bias' in ref:
            ab_e = np.array(est['accel_bias']) - np.array(ref['accel_bias'])
            ab_errors.append(ab_e)

    # Convert to arrays
    pos_errors = np.array(pos_errors) if pos_errors else np.zeros((1, 3))
    vel_errors = np.array(vel_errors) if vel_errors else np.zeros((1, 3))
    att_errors = np.array(att_errors) if att_errors else np.zeros((1, 3))
    gb_errors = np.array(gb_errors) if gb_errors else np.zeros((1, 3))
    ab_errors = np.array(ab_errors) if ab_errors else np.zeros((1, 3))

    # Compute metrics
    result = MetricsResult(
        position_rmse=_rmse(pos_errors),
        position_mae=_mae(pos_errors),
        position_max=_max_abs(pos_errors),
        velocity_rmse=_rmse(vel_errors),
        velocity_mae=_mae(vel_errors),
        velocity_max=_max_abs(vel_errors),
        attitude_rmse=_rmse(att_errors),
        attitude_mae=_mae(att_errors),
        attitude_max=_max_abs(att_errors),
        gyro_bias_rmse=_rmse(gb_errors),
        gyro_bias_mae=_mae(gb_errors),
        accel_bias_rmse=_rmse(ab_errors),
        accel_bias_mae=_mae(ab_errors),
        total_samples=n,
    )

    # Duration
    if timestamps_us and len(timestamps_us) > 1:
        result.duration_s = (timestamps_us[-1] - timestamps_us[0]) / 1e6

    # Time series error
    ts_error = None
    if timestamps_us:
        ts_error = TimeSeriesError(
            timestamps_us=np.array(timestamps_us[:n]),
            position_error=pos_errors,
            velocity_error=vel_errors,
            attitude_error_deg=att_errors,
        )

    return result, ts_error


def compare_eskf_states(
    estimated: dict,
    reference: dict,
) -> dict:
    """Compare two ESKF state dictionaries
    2つのESKF状態辞書を比較

    Args:
        estimated: Estimated state dictionary
        reference: Reference state dictionary

    Returns:
        Dictionary with error values
    """
    errors = {}

    # Position
    if 'position' in estimated and 'position' in reference:
        pos_e = np.array(estimated['position']) - np.array(reference['position'])
        errors['position_error'] = pos_e.tolist()
        errors['position_error_norm'] = float(np.linalg.norm(pos_e))

    # Velocity
    if 'velocity' in estimated and 'velocity' in reference:
        vel_e = np.array(estimated['velocity']) - np.array(reference['velocity'])
        errors['velocity_error'] = vel_e.tolist()
        errors['velocity_error_norm'] = float(np.linalg.norm(vel_e))

    # Attitude
    if 'euler_deg' in estimated and 'euler_deg' in reference:
        att_e = np.array(estimated['euler_deg']) - np.array(reference['euler_deg'])
        att_e[2] = _wrap_angle_deg(att_e[2])
        errors['attitude_error_deg'] = att_e.tolist()

    return errors


def _rmse(errors: np.ndarray) -> np.ndarray:
    """Root Mean Square Error per axis"""
    return np.sqrt(np.mean(errors ** 2, axis=0))


def _mae(errors: np.ndarray) -> np.ndarray:
    """Mean Absolute Error per axis"""
    return np.mean(np.abs(errors), axis=0)


def _max_abs(errors: np.ndarray) -> np.ndarray:
    """Maximum Absolute Error per axis"""
    return np.max(np.abs(errors), axis=0)


def _wrap_angle_deg(angle: float) -> float:
    """Wrap angle to [-180, 180] degrees"""
    while angle > 180:
        angle -= 360
    while angle < -180:
        angle += 360
    return angle


@dataclass
class SelfConsistencyResult:
    """Self-consistency metrics for ESKF tuning without ground truth
    グラウンドトゥルースなしの ESKF チューニング用自己一貫性メトリクス
    """
    # NIS (Normalized Innovation Squared) per sensor
    # 各センサの正規化イノベーション二乗値
    flow_nis_mean: float = 0.0      # Target: 2.0 (dof=2)
    flow_nis_std: float = 0.0
    tof_nis_mean: float = 0.0       # Target: 1.0 (dof=1)
    tof_nis_std: float = 0.0
    accel_att_nis_mean: float = 0.0  # Target: 3.0 (dof=3)
    accel_att_nis_std: float = 0.0

    # Bias stability
    # バイアス安定性
    accel_bias_drift_rate: float = 0.0  # [m/s²/s] — should be < 0.001

    # Innovation autocorrelation (whiteness test)
    # イノベーション自己相関（白色性テスト）
    flow_innov_autocorr: float = 0.0  # |autocorr at lag=1| — should be < 0.1

    # Position/velocity quality
    # 位置・速度の品質
    position_span_xy: float = 0.0    # max-min of pos_x/y [m]
    velocity_rms_xy: float = 0.0     # RMS of vel_x/y [m/s]

    # P matrix health
    # P行列の健全性
    p_trace_final: float = 0.0       # Final trace of P
    p_diverged: bool = False         # True if trace increased monotonically

    # Sample counts
    flow_samples: int = 0
    tof_samples: int = 0
    accel_att_samples: int = 0

    def compute_score(self, weights: Optional[Dict[str, float]] = None) -> float:
        """Compute composite tuning score (lower is better)
        複合チューニングスコアを計算（低いほど良い）
        """
        w = weights or {
            'nis': 1.0,
            'drift': 10.0,
            'autocorr': 1.0,
            'span': 1.0,
            'diverge': 100.0,
        }

        # NIS deviation from expected degrees of freedom
        nis_cost = 0.0
        if self.flow_samples > 0:
            nis_cost += abs(self.flow_nis_mean - 2.0) / 2.0
        if self.tof_samples > 0:
            nis_cost += abs(self.tof_nis_mean - 1.0) / 1.0

        score = (
            w['nis'] * nis_cost +
            w['drift'] * self.accel_bias_drift_rate +
            w['autocorr'] * abs(self.flow_innov_autocorr) +
            w['span'] * self.position_span_xy +
            w['diverge'] * (1.0 if self.p_diverged else 0.0)
        )
        return score

    def print_summary(self) -> None:
        """Print self-consistency evaluation summary"""
        print("=" * 60)
        print("ESKF Self-Consistency Evaluation (no ground truth)")
        print("=" * 60)

        def status(val, target, tol):
            return "✅" if abs(val - target) < tol else "⚠️"

        if self.flow_samples > 0:
            s = status(self.flow_nis_mean, 2.0, 1.0)
            print(f"Flow NIS:      {self.flow_nis_mean:.2f} ± {self.flow_nis_std:.2f}  "
                  f"(target: 2.0) {s}  [{self.flow_samples} samples]")

        if self.tof_samples > 0:
            s = status(self.tof_nis_mean, 1.0, 0.5)
            print(f"ToF NIS:       {self.tof_nis_mean:.2f} ± {self.tof_nis_std:.2f}  "
                  f"(target: 1.0) {s}  [{self.tof_samples} samples]")

        if self.accel_att_samples > 0:
            s = status(self.accel_att_nis_mean, 3.0, 1.5)
            print(f"AccelAtt NIS:  {self.accel_att_nis_mean:.2f} ± {self.accel_att_nis_std:.2f}  "
                  f"(target: 3.0) {s}  [{self.accel_att_samples} samples]")

        s = "✅" if self.accel_bias_drift_rate < 0.01 else "⚠️"
        print(f"BA drift rate: {self.accel_bias_drift_rate:.4f} m/s²/s  "
              f"(target: <0.01) {s}")

        s = "✅" if abs(self.flow_innov_autocorr) < 0.1 else "⚠️"
        print(f"Flow autocorr: {self.flow_innov_autocorr:.3f}  "
              f"(target: <0.1) {s}")

        print(f"Pos span XY:   {self.position_span_xy:.3f} m")
        print(f"Vel RMS XY:    {self.velocity_rms_xy:.4f} m/s")
        print(f"P trace:       {self.p_trace_final:.4f}  "
              f"{'⚠️ DIVERGED' if self.p_diverged else '✅'}")

        print(f"\nComposite score: {self.compute_score():.3f} (lower is better)")
        print("=" * 60)

    def to_dict(self) -> dict:
        return {
            'flow_nis': {'mean': self.flow_nis_mean, 'std': self.flow_nis_std, 'samples': self.flow_samples},
            'tof_nis': {'mean': self.tof_nis_mean, 'std': self.tof_nis_std, 'samples': self.tof_samples},
            'accel_att_nis': {'mean': self.accel_att_nis_mean, 'std': self.accel_att_nis_std, 'samples': self.accel_att_samples},
            'accel_bias_drift_rate': self.accel_bias_drift_rate,
            'flow_innov_autocorr': self.flow_innov_autocorr,
            'position_span_xy': self.position_span_xy,
            'velocity_rms_xy': self.velocity_rms_xy,
            'p_trace_final': self.p_trace_final,
            'p_diverged': self.p_diverged,
            'score': self.compute_score(),
        }


def compute_self_consistency(
    diagnostics: Dict,
    state_history: Optional[List] = None,
    p_trace_history: Optional[List[float]] = None,
) -> SelfConsistencyResult:
    """Compute self-consistency metrics from ESKF diagnostics.
    ESKF 診断データから自己一貫性メトリクスを計算。

    Args:
        diagnostics: ESKF.diagnostics dict with 'flow', 'tof', 'accel_att' keys.
                     Each is a list of (timestamp, innovation, S_inv, NIS, dof).
        state_history: Optional list of (timestamp, ESKFState) for bias/position analysis.
        p_trace_history: Optional list of P matrix trace values over time.

    Returns:
        SelfConsistencyResult
    """
    result = SelfConsistencyResult()

    # NIS statistics per sensor
    for sensor, dof_expected in [('flow', 2), ('tof', 1), ('accel_att', 3)]:
        entries = diagnostics.get(sensor, [])
        if not entries:
            continue

        nis_values = [e[3] for e in entries]  # NIS is index 3
        mean_nis = np.mean(nis_values)
        std_nis = np.std(nis_values)

        if sensor == 'flow':
            result.flow_nis_mean = mean_nis
            result.flow_nis_std = std_nis
            result.flow_samples = len(entries)

            # Innovation autocorrelation (whiteness check)
            if len(entries) > 10:
                innovs = np.array([e[1] for e in entries])  # innovation vectors
                if innovs.ndim == 2 and innovs.shape[1] >= 1:
                    # Use first component for autocorrelation
                    x = innovs[:, 0]
                    x = x - np.mean(x)
                    if np.var(x) > 1e-12:
                        autocorr = np.correlate(x[:-1], x[1:], mode='valid')[0]
                        autocorr /= np.var(x) * (len(x) - 1)
                        result.flow_innov_autocorr = float(autocorr)

        elif sensor == 'tof':
            result.tof_nis_mean = mean_nis
            result.tof_nis_std = std_nis
            result.tof_samples = len(entries)

        elif sensor == 'accel_att':
            result.accel_att_nis_mean = mean_nis
            result.accel_att_nis_std = std_nis
            result.accel_att_samples = len(entries)

    # Bias drift rate from state history
    if state_history and len(state_history) > 10:
        timestamps = [s[0] for s in state_history]
        ba_x = [s[1].accel_bias[0] if hasattr(s[1], 'accel_bias') else s[1].get('accel_bias', [0,0,0])[0] for s in state_history]

        dt = timestamps[-1] - timestamps[0]
        if dt > 0:
            # Linear regression slope
            t_arr = np.array(timestamps) - timestamps[0]
            ba_arr = np.array(ba_x)
            if len(t_arr) > 2:
                slope = np.polyfit(t_arr, ba_arr, 1)[0]
                result.accel_bias_drift_rate = abs(slope)

    # Position/velocity quality from state history
    if state_history and len(state_history) > 10:
        positions = []
        velocities = []
        for _, state in state_history:
            if hasattr(state, 'position'):
                positions.append(state.position[:2])
                velocities.append(state.velocity[:2])
            elif isinstance(state, dict):
                positions.append([state.get('pos_x', 0), state.get('pos_y', 0)])
                velocities.append([state.get('vel_x', 0), state.get('vel_y', 0)])

        if positions:
            pos_arr = np.array(positions)
            vel_arr = np.array(velocities)
            span_x = np.ptp(pos_arr[:, 0])
            span_y = np.ptp(pos_arr[:, 1])
            result.position_span_xy = max(span_x, span_y)
            result.velocity_rms_xy = float(np.sqrt(np.mean(vel_arr**2)))

    # P matrix health
    if p_trace_history and len(p_trace_history) > 10:
        result.p_trace_final = p_trace_history[-1]
        # Check if trace monotonically increased in last 50% of samples
        half = len(p_trace_history) // 2
        if half > 0:
            diffs = np.diff(p_trace_history[half:])
            result.p_diverged = np.mean(diffs > 0) > 0.8  # 80% increasing = diverged

    return result


def quat_to_euler_deg(quat: np.ndarray) -> np.ndarray:
    """Convert quaternion [w, x, y, z] to Euler angles [roll, pitch, yaw] in degrees"""
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

    return np.rad2deg(np.array([roll, pitch, yaw]))
