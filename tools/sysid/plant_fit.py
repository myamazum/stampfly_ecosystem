"""
Plant Model Fitting from Closed-Loop Flight Data
閉ループフライトデータからのプラントモデル同定

Identifies open-loop plant parameters from P-control flight data:
  G_p(s) = K / (s * (tau_m * s + 1))

Where:
  K    : Plant gain [rad/s^2 per duty]
  tau_m: Motor time constant [s]

Algorithm:
  Since Kp is known, plant I/O can be reconstructed from telemetry:
    target(t) = ctrl_axis(t) * rate_max
    u_plant(t) = Kp * (target(t) - gyro(t))
    y_plant(t) = gyro(t)

  The open-loop model is fitted directly via MSE minimization:
    u_plant -> G_p(s) -> y_simulated
    minimize |y_simulated - y_plant|^2  ->  K, tau_m
"""

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from scipy.optimize import minimize

from .defaults import get_flat_defaults


# Reference plant gains from L06 System Modeling
# L06 システムモデリングからの参照プラントゲイン
REFERENCE_PLANT_GAINS: Dict[str, float] = {
    'roll': 102.0,    # [rad/s^2 per duty]
    'pitch': 70.0,
    'yaw': 19.0,
}

# Axis mapping: axis name -> (ctrl attribute, gyro array index)
# 軸マッピング: 軸名 -> (制御入力属性名, ジャイロ配列インデックス)
_AXIS_CONFIG = {
    'roll':  {'ctrl_attr': 'ctrl_roll',  'gyro_idx': 0},
    'pitch': {'ctrl_attr': 'ctrl_pitch', 'gyro_idx': 1},
    'yaw':   {'ctrl_attr': 'ctrl_yaw',   'gyro_idx': 2},
}


@dataclass
class PlantFitResult:
    """Plant model identification result / プラントモデル同定結果

    Model: G_p(s) = K / (s * (tau_m * s + 1))
    """
    K: float              # Plant gain [rad/s^2 per duty]
    tau_m: float          # Motor time constant [s]
    K_std: float          # K uncertainty (std dev across segments)
    tau_m_std: float      # tau_m uncertainty (std dev across segments)
    r_squared: float      # Fit quality (mean R^2 across segments)
    rmse: float           # RMSE [rad/s] (mean across segments)
    axis: str             # 'roll', 'pitch', or 'yaw'
    kp_used: float        # Kp used for plant input reconstruction
    n_segments: int       # Number of segments used for fitting

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        defaults = get_flat_defaults()
        ref_K = REFERENCE_PLANT_GAINS.get(self.axis, 0.0)
        ref_tau_m = defaults['tau_m']

        result: Dict[str, Any] = {
            'method': 'plant_fit',
            'timestamp': datetime.now().isoformat(),
            'model': 'K / (s * (tau_m * s + 1))',
            'axis': self.axis,
            'kp_used': self.kp_used,
            'n_segments': self.n_segments,
            'estimated': {
                'K': round(self.K, 2),
                'K_uncertainty': round(self.K_std, 2),
                'tau_m': round(self.tau_m, 4),
                'tau_m_uncertainty': round(self.tau_m_std, 4),
            },
            'fit_quality': {
                'r_squared': round(self.r_squared, 4),
                'rmse': round(self.rmse, 4),
            },
            'reference': {
                'K': ref_K,
                'tau_m': ref_tau_m,
            },
            'comparison': {},
        }

        # Comparison with reference values
        # 参照値との比較
        if ref_K > 0:
            K_err = abs(self.K - ref_K) / ref_K * 100
            result['comparison']['K'] = {
                'error_percent': round(K_err, 1),
                'status': 'OK' if K_err < 30 else 'CHECK',
            }
        if ref_tau_m > 0:
            tau_err = abs(self.tau_m - ref_tau_m) / ref_tau_m * 100
            result['comparison']['tau_m'] = {
                'error_percent': round(tau_err, 1),
                'status': 'OK' if tau_err < 30 else 'CHECK',
            }

        # Derived: design Kp for zeta=0.7
        # Closed-loop: Kp = 1 / (4 * zeta^2 * K * tau_m)
        zeta = 0.7
        if self.K > 0 and self.tau_m > 0:
            Kp_design = 1.0 / (4.0 * zeta**2 * self.K * self.tau_m)
            result['derived'] = {
                'design_Kp_zeta_0_7': round(Kp_design, 4),
            }
            if ref_K > 0:
                Kp_ref = 1.0 / (4.0 * zeta**2 * ref_K * ref_tau_m)
                result['derived']['reference_Kp_zeta_0_7'] = round(Kp_ref, 4)

        return result


def _simulate_plant(
    K: float,
    tau_m: float,
    u: np.ndarray,
    dt: float,
    omega0: float,
    z0: float = 0.0,
) -> np.ndarray:
    """
    Simulate plant G_p(s) = K / (s * (tau_m * s + 1))
    プラントをシミュレート

    State space representation:
        x1_dot = x2               (omega_dot = z)
        x2_dot = -x2/tau_m + K*u/tau_m  (motor first-order dynamics)
        y      = x1               (output = angular velocity)

    Uses exact discretization for motor dynamics (x2)
    and trapezoidal integration for the integrator (x1).

    Args:
        K: Plant gain [rad/s^2 per duty]
        tau_m: Motor time constant [s]
        u: Plant input array (duty)
        dt: Sample period [s]
        omega0: Initial angular velocity [rad/s]
        z0: Initial motor-filtered acceleration [rad/s^2]

    Returns:
        Simulated angular velocity [rad/s]
    """
    n = len(u)
    alpha = np.exp(-dt / tau_m)
    gain = K * (1.0 - alpha)

    # Motor-filtered acceleration (x2 state)
    # 1次遅れ（モータ動特性）の厳密離散化
    z = np.empty(n)
    z[0] = z0
    for i in range(1, n):
        z[i] = alpha * z[i - 1] + gain * u[i - 1]

    # Integrate to angular velocity (trapezoidal rule)
    # 台形積分で角速度を計算
    omega = np.empty(n)
    omega[0] = omega0
    omega[1:] = omega0 + np.cumsum((z[:-1] + z[1:]) * 0.5 * dt)

    return omega


def _fit_segment(
    u_seg: np.ndarray,
    y_seg: np.ndarray,
    dt: float,
    K_init: float = 100.0,
    tau_m_init: float = 0.02,
) -> Optional[Tuple[float, float, float, float]]:
    """
    Fit K and tau_m for a single data segment
    単一セグメントの K, tau_m をフィット

    Args:
        u_seg: Plant input for segment
        y_seg: Measured output (gyro) for segment
        dt: Sample period [s]
        K_init: Initial guess for K
        tau_m_init: Initial guess for tau_m

    Returns:
        (K, tau_m, r_squared, rmse) or None if fitting fails
    """
    if len(u_seg) < 20:
        return None

    omega0 = y_seg[0]
    # Estimate initial angular acceleration from first few samples
    # 最初の数サンプルから初期角加速度を推定
    n_init = min(10, len(y_seg) - 1)
    z0 = float(y_seg[n_init] - y_seg[0]) / (n_init * dt)

    def objective(params):
        K = params[0]
        tau_m = np.exp(params[1])  # log transform ensures tau_m > 0
        y_sim = _simulate_plant(K, tau_m, u_seg, dt, omega0, z0)
        return np.mean((y_sim - y_seg) ** 2)

    try:
        result = minimize(
            objective,
            x0=[K_init, np.log(tau_m_init)],
            method='L-BFGS-B',
            bounds=[(1.0, 1000.0), (np.log(0.003), np.log(0.5))],
            options={'maxiter': 200},
        )
    except Exception:
        return None

    if not result.success and result.fun > 1.0:
        return None

    K_opt = result.x[0]
    tau_m_opt = np.exp(result.x[1])

    # Compute fit quality metrics
    # フィット品質の計算
    y_sim = _simulate_plant(K_opt, tau_m_opt, u_seg, dt, omega0, z0)
    residuals = y_seg - y_sim
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((y_seg - np.mean(y_seg)) ** 2)
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 1e-12 else 0.0
    rmse = float(np.sqrt(np.mean(residuals ** 2)))

    return K_opt, tau_m_opt, r_squared, rmse


def _load_axis_data(
    filepath: str | Path,
    axis: str,
    fs: float = 400.0,
    time_range: Optional[Tuple[float, float]] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """
    Load and extract axis-specific data from CSV
    CSVから軸固有のデータを読み込み・抽出

    Returns:
        (time_s, ctrl, gyro, throttle, dt)
    """
    import sys
    from pathlib import Path as P

    if axis not in _AXIS_CONFIG:
        raise ValueError(
            f"Unknown axis: {axis}. Choose from: {list(_AXIS_CONFIG.keys())}"
        )
    config = _AXIS_CONFIG[axis]

    # Load CSV using eskf_sim loader
    # CSV読み込み
    tools_path = P(__file__).parent.parent
    added = False
    if str(tools_path) not in sys.path:
        sys.path.insert(0, str(tools_path))
        added = True
    try:
        from eskf_sim.loader import load_csv
    finally:
        if added and str(tools_path) in sys.path:
            sys.path.remove(str(tools_path))

    log_data = load_csv(filepath)
    samples = log_data.samples

    if len(samples) < 100:
        raise ValueError(f"Too few samples: {len(samples)}")

    # Use detected sample rate if available
    # 検出されたサンプルレートがあれば使用
    if log_data.sample_rate_hz > 0:
        fs = log_data.sample_rate_hz
    dt = 1.0 / fs

    # Extract time
    timestamps_us = np.array([s.timestamp_us for s in samples])
    time_s = (timestamps_us - timestamps_us[0]) / 1e6

    # Control input for this axis
    ctrl_attr = config['ctrl_attr']
    ctrl = np.array([
        getattr(s, ctrl_attr) if getattr(s, ctrl_attr) is not None else 0.0
        for s in samples
    ])

    # Gyro output (prefer corrected)
    gyro_idx = config['gyro_idx']
    if samples[0].gyro_corrected is not None:
        gyro = np.array([s.gyro_corrected[gyro_idx] for s in samples])
    else:
        gyro = np.array([s.gyro[gyro_idx] for s in samples])

    # Throttle for flight detection
    throttle = np.array([
        s.ctrl_throttle if s.ctrl_throttle is not None else 0.0
        for s in samples
    ])

    # Apply time range filter
    # 時間範囲フィルタを適用
    if time_range is not None:
        t_start, t_end = time_range
        mask = (time_s >= t_start) & (time_s <= t_end)
        time_s = time_s[mask]
        ctrl = ctrl[mask]
        gyro = gyro[mask]
        throttle = throttle[mask]

    return time_s, ctrl, gyro, throttle, dt


def _find_flight_segments(
    throttle: np.ndarray,
    seg_samples: int,
    throttle_threshold: float = 0.3,
) -> List[Tuple[int, int]]:
    """
    Find flight segments where throttle > threshold
    スロットルが閾値以上の飛行区間を検出

    Returns:
        List of (start_idx, end_idx) tuples for analysis segments
    """
    in_flight = throttle > throttle_threshold

    # Find contiguous flight regions
    # 連続的な飛行区間を検出
    flight_starts = []
    flight_ends = []
    in_region = False
    for i in range(len(in_flight)):
        if in_flight[i] and not in_region:
            flight_starts.append(i)
            in_region = True
        elif not in_flight[i] and in_region:
            flight_ends.append(i)
            in_region = False
    if in_region:
        flight_ends.append(len(in_flight))

    # Split flight regions into analysis segments
    # 飛行区間を分析セグメントに分割
    min_seg = seg_samples // 2
    segments = []
    for start, end in zip(flight_starts, flight_ends):
        if end - start < min_seg:
            continue
        for seg_start in range(start, end - min_seg, seg_samples):
            seg_end = min(seg_start + seg_samples, end)
            if seg_end - seg_start >= min_seg:
                segments.append((seg_start, seg_end))

    return segments


def fit_plant(
    filepath: str | Path,
    axis: str = 'roll',
    kp: float = 0.5,
    rate_max: float = 1.0,
    fs: float = 400.0,
    time_range: Optional[Tuple[float, float]] = None,
    segment_length: float = 3.0,
    min_activity: float = 0.01,
) -> PlantFitResult:
    """
    Fit open-loop plant model from closed-loop flight data
    閉ループフライトデータから開ループプラントモデルを同定

    Args:
        filepath: Path to CSV flight log
        axis: 'roll', 'pitch', or 'yaw'
        kp: P gain used during flight (must match firmware value)
        rate_max: Maximum angular rate [rad/s] (maps ctrl [-1,+1] to rate)
        fs: Sample rate [Hz] (default: 400)
        time_range: Optional (start, end) in seconds to restrict analysis
        segment_length: Segment duration [s] for fitting (default: 3.0)
        min_activity: Minimum std of plant input to include segment

    Returns:
        PlantFitResult with identified K, tau_m and fit metrics

    Raises:
        ValueError: If data is insufficient or fitting fails
    """
    # Load data
    # データ読み込み
    time_s, ctrl, gyro, throttle, dt = _load_axis_data(
        filepath, axis, fs, time_range,
    )

    # Reconstruct plant I/O
    # Kp 既知のためプラント入出力を復元
    #   target(t) = ctrl(t) * rate_max
    #   u_plant(t) = Kp * (target(t) - gyro(t))
    #   y_plant(t) = gyro(t)
    target = ctrl * rate_max
    u_plant = kp * (target - gyro)
    y_plant = gyro

    # Find flight segments
    # 飛行区間の検出
    seg_samples = int(segment_length * (1.0 / dt))
    segments = _find_flight_segments(throttle, seg_samples)

    if not segments:
        raise ValueError(
            "No valid flight segments found. "
            "Check that throttle > 0.3 during flight."
        )

    # Filter segments by control activity level
    # 制御入力が十分な区間のみ抽出
    active_segments = []
    for seg_start, seg_end in segments:
        if np.std(u_plant[seg_start:seg_end]) > min_activity:
            active_segments.append((seg_start, seg_end))

    if not active_segments:
        raise ValueError(
            f"No segments with sufficient control activity (std > {min_activity}). "
            "Ensure the pilot made stick inputs during flight."
        )

    # Fit each segment
    # 各セグメントをフィット
    ref_K = REFERENCE_PLANT_GAINS.get(axis, 100.0)
    K_estimates: List[float] = []
    tau_m_estimates: List[float] = []
    r2_values: List[float] = []
    rmse_values: List[float] = []

    for seg_start, seg_end in active_segments:
        u_seg = u_plant[seg_start:seg_end]
        y_seg = y_plant[seg_start:seg_end]

        fit = _fit_segment(u_seg, y_seg, dt, K_init=ref_K, tau_m_init=0.02)
        if fit is not None:
            K, tau_m, r2, rmse = fit
            # Filter out unreasonable fits
            # 不合理なフィット結果を除外
            if r2 > 0.3 and K > 1.0 and 0.003 < tau_m < 0.5:
                K_estimates.append(K)
                tau_m_estimates.append(tau_m)
                r2_values.append(r2)
                rmse_values.append(rmse)

    if not K_estimates:
        raise ValueError(
            "Fitting failed for all segments. "
            "Check data quality and Kp value."
        )

    # Aggregate results using median (robust to outliers)
    # 中央値で集約（外れ値に頑健）
    K_final = float(np.median(K_estimates))
    tau_m_final = float(np.median(tau_m_estimates))
    K_std = float(np.std(K_estimates)) if len(K_estimates) > 1 else 0.0
    tau_m_std = float(np.std(tau_m_estimates)) if len(tau_m_estimates) > 1 else 0.0
    r2_mean = float(np.mean(r2_values))
    rmse_mean = float(np.mean(rmse_values))

    return PlantFitResult(
        K=K_final,
        tau_m=tau_m_final,
        K_std=K_std,
        tau_m_std=tau_m_std,
        r_squared=r2_mean,
        rmse=rmse_mean,
        axis=axis,
        kp_used=kp,
        n_segments=len(K_estimates),
    )


def compute_fit_timeseries(
    filepath: str | Path,
    result: PlantFitResult,
    rate_max: float = 1.0,
    fs: float = 400.0,
    time_range: Optional[Tuple[float, float]] = None,
) -> Dict[str, np.ndarray]:
    """
    Compute time series data for plotting fit results
    フィット結果のプロット用時系列データを計算

    Args:
        filepath: Path to CSV flight log (same file used for fitting)
        result: PlantFitResult from fit_plant()
        rate_max: Maximum angular rate [rad/s]
        fs: Sample rate [Hz]
        time_range: Optional (start, end) in seconds

    Returns:
        Dictionary with keys:
            'time': Time array [s]
            'u_plant': Reconstructed plant input
            'y_measured': Measured angular velocity (gyro)
            'y_simulated': Simulated angular velocity
            'residual': y_measured - y_simulated
    """
    time_s, ctrl, gyro, throttle, dt = _load_axis_data(
        filepath, result.axis, fs, time_range,
    )

    # Reconstruct plant I/O
    target = ctrl * rate_max
    u_plant = result.kp_used * (target - gyro)
    y_measured = gyro

    # Simulate full time series with identified parameters
    # 同定パラメータで全時系列をシミュレート
    omega0 = y_measured[0]
    n_init = min(10, len(y_measured) - 1)
    z0 = float(y_measured[n_init] - y_measured[0]) / (n_init * dt)

    y_simulated = _simulate_plant(
        result.K, result.tau_m, u_plant, dt, omega0, z0,
    )

    return {
        'time': time_s,
        'u_plant': u_plant,
        'y_measured': y_measured,
        'y_simulated': y_simulated,
        'residual': y_measured - y_simulated,
    }
