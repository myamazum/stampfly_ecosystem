"""
ESKF (Error-State Kalman Filter) Python Implementation
ESKFのPython実装

This module provides a pure Python/NumPy implementation of the 15-state ESKF
used in the StampFly vehicle firmware. It enables offline replay and parameter
tuning from logged sensor data.

Ported from: firmware/vehicle/components/sf_algo_eskf/eskf.cpp

State vector (15 states):
    [position (3), velocity (3), attitude_error (3), gyro_bias (3), accel_bias (3)]
"""

from dataclasses import dataclass, field
from typing import Optional
import numpy as np


@dataclass
class ESKFConfig:
    """ESKF configuration parameters
    ESKFの設定パラメータ
    """
    # Process noise (Q)
    # プロセスノイズ
    gyro_noise: float = 0.009655        # rad/s/sqrt(Hz)
    accel_noise: float = 0.062885       # m/s^2/sqrt(Hz)
    gyro_bias_noise: float = 0.000013   # rad/s/sqrt(s)
    accel_bias_noise: float = 0.0001    # m/s^2/sqrt(s)

    # Measurement noise (R)
    # 観測ノイズ
    baro_noise: float = 0.1             # m
    tof_noise: float = 0.00254          # m
    mag_noise: float = 2.0              # uT
    flow_noise: float = 0.005232        # m/s
    accel_att_noise: float = 0.02       # m/s^2

    # Initial covariance
    # 初期共分散
    init_pos_std: float = 1.0
    init_vel_std: float = 0.5
    init_att_std: float = 0.1
    init_gyro_bias_std: float = 0.01
    init_accel_bias_std: float = 0.1

    # Reference values
    # 参照値
    mag_ref: np.ndarray = field(default_factory=lambda: np.array([20.0, 0.0, 40.0]))
    gravity: float = 9.81

    # Thresholds
    # 閾値
    mahalanobis_threshold: float = 15.0
    tof_tilt_threshold: float = 0.70     # ~40 deg
    tof_chi2_gate: float = 3.84          # chi^2(1, 0.95)
    accel_motion_threshold: float = 1.0  # m/s^2
    flow_min_height: float = 0.02        # m
    flow_max_height: float = 4.0         # m
    flow_tilt_cos_threshold: float = 0.866  # cos(30 deg)

    # Optical flow calibration
    # オプティカルフローキャリブレーション
    flow_rad_per_pixel: float = 0.00222
    flow_cam_to_body: np.ndarray = field(default_factory=lambda: np.array([
        [0.943, 0.0],
        [0.0, 1.015]
    ]))
    flow_gyro_scale: float = 1.0
    flow_offset: np.ndarray = field(default_factory=lambda: np.array([0.0, 0.0]))

    # Feature flags
    # 機能フラグ
    mag_enabled: bool = False
    yaw_estimation_enabled: bool = True

    # Bias estimation switches
    # バイアス推定スイッチ
    estimate_gyro_bias_xy: bool = True
    estimate_accel_bias_xy: bool = False
    estimate_accel_bias_z: bool = True

    # Attitude update mode
    # 姿勢補正モード
    att_update_mode: int = 0
    k_adaptive: float = 0.0
    gyro_att_threshold: float = 0.5

    def to_dict(self) -> dict:
        """Convert config to dictionary for serialization"""
        return {
            'process_noise': {
                'gyro_noise': self.gyro_noise,
                'accel_noise': self.accel_noise,
                'gyro_bias_noise': self.gyro_bias_noise,
                'accel_bias_noise': self.accel_bias_noise,
            },
            'measurement_noise': {
                'baro_noise': self.baro_noise,
                'tof_noise': self.tof_noise,
                'mag_noise': self.mag_noise,
                'flow_noise': self.flow_noise,
                'accel_att_noise': self.accel_att_noise,
            },
            'options': {
                'mag_enabled': self.mag_enabled,
                'estimate_gyro_bias_xy': self.estimate_gyro_bias_xy,
                'estimate_accel_bias_z': self.estimate_accel_bias_z,
            }
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ESKFConfig':
        """Create config from dictionary"""
        cfg = cls()
        if 'process_noise' in d:
            pn = d['process_noise']
            cfg.gyro_noise = pn.get('gyro_noise', cfg.gyro_noise)
            cfg.accel_noise = pn.get('accel_noise', cfg.accel_noise)
            cfg.gyro_bias_noise = pn.get('gyro_bias_noise', cfg.gyro_bias_noise)
            cfg.accel_bias_noise = pn.get('accel_bias_noise', cfg.accel_bias_noise)
        if 'measurement_noise' in d:
            mn = d['measurement_noise']
            cfg.baro_noise = mn.get('baro_noise', cfg.baro_noise)
            cfg.tof_noise = mn.get('tof_noise', cfg.tof_noise)
            cfg.mag_noise = mn.get('mag_noise', cfg.mag_noise)
            cfg.flow_noise = mn.get('flow_noise', cfg.flow_noise)
            cfg.accel_att_noise = mn.get('accel_att_noise', cfg.accel_att_noise)
        if 'options' in d:
            opt = d['options']
            cfg.mag_enabled = opt.get('mag_enabled', cfg.mag_enabled)
            cfg.estimate_gyro_bias_xy = opt.get('estimate_gyro_bias_xy', cfg.estimate_gyro_bias_xy)
            cfg.estimate_accel_bias_z = opt.get('estimate_accel_bias_z', cfg.estimate_accel_bias_z)
        return cfg


@dataclass
class ESKFState:
    """ESKF state vector
    ESKF状態ベクトル
    """
    position: np.ndarray = field(default_factory=lambda: np.zeros(3))  # [m] NED
    velocity: np.ndarray = field(default_factory=lambda: np.zeros(3))  # [m/s]
    quat: np.ndarray = field(default_factory=lambda: np.array([1.0, 0.0, 0.0, 0.0]))  # [w, x, y, z]
    gyro_bias: np.ndarray = field(default_factory=lambda: np.zeros(3))  # [rad/s]
    accel_bias: np.ndarray = field(default_factory=lambda: np.zeros(3))  # [m/s^2]

    @property
    def roll(self) -> float:
        """Roll angle [rad]"""
        return self._quat_to_euler()[0]

    @property
    def pitch(self) -> float:
        """Pitch angle [rad]"""
        return self._quat_to_euler()[1]

    @property
    def yaw(self) -> float:
        """Yaw angle [rad]"""
        return self._quat_to_euler()[2]

    @property
    def euler(self) -> np.ndarray:
        """Euler angles [roll, pitch, yaw] in [rad]"""
        return self._quat_to_euler()

    def _quat_to_euler(self) -> np.ndarray:
        """Convert quaternion to Euler angles (roll, pitch, yaw)"""
        w, x, y, z = self.quat

        # Roll (x-axis rotation)
        sinr_cosp = 2.0 * (w * x + y * z)
        cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
        roll = np.arctan2(sinr_cosp, cosr_cosp)

        # Pitch (y-axis rotation)
        sinp = 2.0 * (w * y - z * x)
        if np.abs(sinp) >= 1:
            pitch = np.sign(sinp) * np.pi / 2
        else:
            pitch = np.arcsin(sinp)

        # Yaw (z-axis rotation)
        siny_cosp = 2.0 * (w * z + x * y)
        cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
        yaw = np.arctan2(siny_cosp, cosy_cosp)

        return np.array([roll, pitch, yaw])

    def copy(self) -> 'ESKFState':
        """Create a deep copy"""
        return ESKFState(
            position=self.position.copy(),
            velocity=self.velocity.copy(),
            quat=self.quat.copy(),
            gyro_bias=self.gyro_bias.copy(),
            accel_bias=self.accel_bias.copy(),
        )

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        euler = self.euler
        return {
            'position': self.position.tolist(),
            'velocity': self.velocity.tolist(),
            'quat': self.quat.tolist(),
            'euler_deg': np.rad2deg(euler).tolist(),
            'gyro_bias': self.gyro_bias.tolist(),
            'accel_bias': self.accel_bias.tolist(),
        }


# State indices
# 状態インデックス
class StateIdx:
    POS_X, POS_Y, POS_Z = 0, 1, 2
    VEL_X, VEL_Y, VEL_Z = 3, 4, 5
    ATT_X, ATT_Y, ATT_Z = 6, 7, 8
    BG_X, BG_Y, BG_Z = 9, 10, 11
    BA_X, BA_Y, BA_Z = 12, 13, 14


class ESKF:
    """Error-State Kalman Filter (15-state)
    エラー状態カルマンフィルタ（15状態）

    15 states:
        - Position (3): NED frame [m]
        - Velocity (3): NED frame [m/s]
        - Attitude error (3): rotation vector [rad]
        - Gyro bias (3): [rad/s]
        - Accel bias (3): [m/s^2]
    """

    def __init__(self, config: Optional[ESKFConfig] = None):
        self.config = config or ESKFConfig()
        self.state = ESKFState()
        self.P = np.eye(15)  # Covariance matrix
        self.initialized = False
        self.freeze_accel_bias = True  # Start with frozen accel bias

    def init(self, config: Optional[ESKFConfig] = None) -> None:
        """Initialize the filter
        フィルタを初期化
        """
        if config is not None:
            self.config = config
        self.reset()
        self.initialized = True

    def reset(self) -> None:
        """Reset state and covariance
        状態と共分散をリセット
        """
        self.state = ESKFState()
        self._reset_covariance()

    def _reset_covariance(self) -> None:
        """Reset covariance matrix to initial values"""
        self.P = np.zeros((15, 15))
        cfg = self.config

        pos_var = cfg.init_pos_std ** 2
        vel_var = cfg.init_vel_std ** 2
        att_var = cfg.init_att_std ** 2
        bg_var = cfg.init_gyro_bias_std ** 2
        ba_var = cfg.init_accel_bias_std ** 2

        # Position
        self.P[0, 0] = self.P[1, 1] = self.P[2, 2] = pos_var
        # Velocity
        self.P[3, 3] = self.P[4, 4] = self.P[5, 5] = vel_var
        # Attitude
        self.P[6, 6] = self.P[7, 7] = self.P[8, 8] = att_var
        # Gyro bias
        self.P[9, 9] = self.P[10, 10] = self.P[11, 11] = bg_var
        # Accel bias
        self.P[12, 12] = self.P[13, 13] = self.P[14, 14] = ba_var

    def predict(self, accel: np.ndarray, gyro: np.ndarray, dt: float,
                skip_position: bool = False) -> None:
        """Prediction step with IMU input
        IMU入力による予測ステップ

        Args:
            accel: Acceleration [m/s^2] (body frame)
            gyro: Angular rate [rad/s] (body frame)
            dt: Time step [s]
            skip_position: Skip position/velocity update (for ground contact)
        """
        if not self.initialized or dt <= 0:
            return

        cfg = self.config

        # Bias correction
        # バイアス補正
        gyro_corrected = gyro - self.state.gyro_bias
        accel_corrected = accel - self.state.accel_bias

        # Disable yaw rate if yaw estimation is disabled
        # ヨー推定無効時はヨーレートを0に
        if not cfg.yaw_estimation_enabled:
            gyro_corrected[2] = 0.0

        # Rotation matrix from quaternion (body -> NED)
        # クォータニオンから回転行列（ボディ→NED）
        R = self._quat_to_rotation_matrix(self.state.quat)

        # Position/velocity update
        # 位置・速度の更新
        if not skip_position:
            accel_world = R @ accel_corrected + np.array([0, 0, cfg.gravity])
            half_dt_sq = 0.5 * dt * dt
            self.state.position += self.state.velocity * dt + accel_world * half_dt_sq
            self.state.velocity += accel_world * dt

        # Attitude update: q = q * exp(omega * dt)
        # 姿勢更新
        dtheta = gyro_corrected * dt
        dq = self._rotation_vector_to_quat(dtheta)
        self.state.quat = self._quat_multiply(self.state.quat, dq)
        self.state.quat = self.state.quat / np.linalg.norm(self.state.quat)

        # Fix yaw if disabled
        if not cfg.yaw_estimation_enabled:
            euler = self.state.euler
            self.state.quat = self._euler_to_quat(euler[0], euler[1], 0.0)

        # Covariance propagation: P' = F * P * F^T + Q
        # 共分散伝播
        self._propagate_covariance(R, accel_corrected, dt)

    def _propagate_covariance(self, R: np.ndarray, accel: np.ndarray, dt: float) -> None:
        """Propagate covariance matrix"""
        cfg = self.config

        # Build F matrix (state transition) - sparse structure
        # F行列（状態遷移）- 疎構造
        F = np.eye(15)

        # dp/dv = I * dt
        F[0:3, 3:6] = np.eye(3) * dt

        # dv/dtheta = -R * skew(a) * dt
        ax, ay, az = accel
        skew_a = np.array([
            [0, -az, ay],
            [az, 0, -ax],
            [-ay, ax, 0]
        ])
        F[3:6, 6:9] = -R @ skew_a * dt

        # dv/dba = -R * dt
        F[3:6, 12:15] = -R * dt

        # dtheta/dbg = -I * dt
        F[6:9, 9:12] = -np.eye(3) * dt

        # Process noise Q (diagonal)
        # プロセスノイズQ（対角）
        Q = np.zeros((15, 15))
        gyro_var = cfg.gyro_noise ** 2 * dt
        accel_var = cfg.accel_noise ** 2 * dt
        bg_var = cfg.gyro_bias_noise ** 2 * dt
        ba_var = cfg.accel_bias_noise ** 2 * dt

        # Velocity noise
        Q[3, 3] = Q[4, 4] = Q[5, 5] = accel_var
        # Attitude noise
        Q[6, 6] = Q[7, 7] = Q[8, 8] = gyro_var
        # Gyro bias noise (Z only if mag enabled)
        Q[9, 9] = Q[10, 10] = bg_var
        Q[11, 11] = bg_var if cfg.mag_enabled else 0.0
        # Accel bias noise
        Q[12, 12] = Q[13, 13] = Q[14, 14] = ba_var

        # P' = F * P * F^T + Q
        self.P = F @ self.P @ F.T + Q

    def update_baro(self, altitude: float) -> None:
        """Barometer altitude update
        気圧高度更新

        Args:
            altitude: Altitude from barometer [m] (positive up)
        """
        if not self.initialized:
            return

        # Observation: z = -altitude (NED: down is positive)
        # Innovation: y = z - h = -altitude - pos_z
        y = -altitude - self.state.position[2]

        R_val = self.config.baro_noise ** 2

        # H matrix: only H[0, 2] = 1
        # S = P[2, 2] + R
        S = self.P[2, 2] + R_val
        if S < 1e-10:
            return

        # Kalman gain K = P[:, 2] / S
        K = self.P[:, 2] / S

        # State update
        dx = K * y
        self._inject_error_state(dx)

        # Joseph form covariance update
        IKH = np.eye(15)
        IKH[:, 2] -= K
        self.P = IKH @ self.P @ IKH.T + np.outer(K, K) * R_val

    def update_tof(self, distance: float) -> None:
        """ToF distance update
        ToF距離更新

        Args:
            distance: ToF distance [m]
        """
        if not self.initialized:
            return

        # Skip if tilted too much
        # 傾きすぎの場合はスキップ
        euler = self.state.euler
        tilt = np.sqrt(euler[0] ** 2 + euler[1] ** 2)
        if tilt > self.config.tof_tilt_threshold:
            return

        # Convert slant range to vertical height
        # 斜距離から鉛直高度に変換
        cos_roll = np.cos(euler[0])
        cos_pitch = np.cos(euler[1])
        height = distance * cos_roll * cos_pitch

        # Innovation: y = z - h = -height - pos_z
        y = -height - self.state.position[2]

        R_val = self.config.tof_noise ** 2
        S = self.P[2, 2] + R_val
        if S < 1e-10:
            return

        # Chi-squared gating
        # χ²ゲーティング
        if self.config.tof_chi2_gate > 0:
            d2 = (y ** 2) / S
            if d2 > self.config.tof_chi2_gate:
                return  # Outlier rejection

        # Kalman gain
        K = self.P[:, 2] / S
        dx = K * y
        self._inject_error_state(dx)

        # Covariance update
        IKH = np.eye(15)
        IKH[:, 2] -= K
        self.P = IKH @ self.P @ IKH.T + np.outer(K, K) * R_val

    def update_flow_raw(self, flow_dx: int, flow_dy: int, distance: float,
                        dt: float, gyro_x: float, gyro_y: float) -> None:
        """Optical flow update with raw sensor data
        生データ入力のオプティカルフロー更新

        Args:
            flow_dx: X pixel displacement [counts]
            flow_dy: Y pixel displacement [counts]
            distance: ToF distance [m]
            dt: Sample interval [s]
            gyro_x: X angular rate [rad/s]
            gyro_y: Y angular rate [rad/s]
        """
        if not self.initialized or distance < self.config.flow_min_height or dt <= 0:
            return

        cfg = self.config

        # 1. Offset correction -> pixel angular rate [rad/s]
        flow_dx_c = float(flow_dx) - cfg.flow_offset[0]
        flow_dy_c = float(flow_dy) - cfg.flow_offset[1]

        flow_x_cam = flow_dx_c * cfg.flow_rad_per_pixel / dt
        flow_y_cam = flow_dy_c * cfg.flow_rad_per_pixel / dt

        # 2. Gyro compensation (rotation removal)
        gyro_x_c = gyro_x - self.state.gyro_bias[0]
        gyro_y_c = gyro_y - self.state.gyro_bias[1]

        gyro_scale = cfg.flow_gyro_scale
        flow_rot_x_cam = gyro_scale * gyro_y_c   # Pitch affects flow X
        flow_rot_y_cam = -gyro_scale * gyro_x_c  # Roll affects flow Y

        flow_trans_x_cam = flow_x_cam - flow_rot_x_cam
        flow_trans_y_cam = flow_y_cam - flow_rot_y_cam

        # 3. Camera to body frame transformation
        flow_trans_x = cfg.flow_cam_to_body[0, 0] * flow_trans_x_cam + cfg.flow_cam_to_body[0, 1] * flow_trans_y_cam
        flow_trans_y = cfg.flow_cam_to_body[1, 0] * flow_trans_x_cam + cfg.flow_cam_to_body[1, 1] * flow_trans_y_cam

        # 4. Translation velocity [m/s]
        vx_body = flow_trans_x * distance
        vy_body = flow_trans_y * distance

        # 5. Body to NED frame
        yaw = self.state.yaw
        cos_yaw, sin_yaw = np.cos(yaw), np.sin(yaw)
        vx_ned = cos_yaw * vx_body - sin_yaw * vy_body
        vy_ned = sin_yaw * vx_body + cos_yaw * vy_body

        # 6. Measurement update
        y = np.array([
            vx_ned - self.state.velocity[0],
            vy_ned - self.state.velocity[1]
        ])

        R_val = cfg.flow_noise ** 2

        # H matrix: H[0, 3] = 1, H[1, 4] = 1
        P33, P34, P44 = self.P[3, 3], self.P[3, 4], self.P[4, 4]

        S = np.array([
            [P33 + R_val, P34],
            [P34, P44 + R_val]
        ])

        det = S[0, 0] * S[1, 1] - S[0, 1] ** 2
        if abs(det) < 1e-10:
            return

        Si = np.array([
            [S[1, 1], -S[0, 1]],
            [-S[0, 1], S[0, 0]]
        ]) / det

        # PHT = P[:, 3:5]
        PHT = self.P[:, 3:5]

        # K = PHT @ Si
        K = PHT @ Si

        # dx = K @ y
        dx = K @ y
        self._inject_error_state(dx)

        # Covariance update: Joseph form
        KH = np.zeros((15, 15))
        KH[:, 3] = K[:, 0]
        KH[:, 4] = K[:, 1]
        IKH = np.eye(15) - KH
        KRK = K @ (np.eye(2) * R_val) @ K.T
        self.P = IKH @ self.P @ IKH.T + KRK

    def update_accel_attitude(self, accel: np.ndarray) -> None:
        """Accelerometer attitude correction (Roll/Pitch)
        加速度計による姿勢補正（ロール/ピッチ）

        Args:
            accel: Acceleration [m/s^2] (body frame)
        """
        if not self.initialized:
            return

        cfg = self.config
        accel_corrected = accel - self.state.accel_bias

        # Check for excessive motion
        # 動きが大きい場合はスキップ
        accel_norm = np.linalg.norm(accel_corrected)
        if abs(accel_norm - cfg.gravity) > cfg.accel_motion_threshold:
            return

        # Expected gravity in body frame: g_body = R^T @ [0, 0, g]
        # 期待される重力（ボディ座標系）
        R = self._quat_to_rotation_matrix(self.state.quat)
        g_expected = R.T @ np.array([0, 0, cfg.gravity])

        # Innovation: y = accel_measured - g_expected
        y = accel_corrected - g_expected

        R_val = cfg.accel_att_noise ** 2

        # H = skew(g_expected) for attitude error
        # H行列：姿勢誤差に対する重力のスキュー行列
        gx, gy, gz = g_expected
        H = np.zeros((3, 15))
        H[0, 6:9] = [0, gz, -gy]
        H[1, 6:9] = [-gz, 0, gx]
        H[2, 6:9] = [gy, -gx, 0]

        # S = H @ P @ H^T + R*I
        PHT = self.P @ H.T
        S = H @ PHT + np.eye(3) * R_val

        # Matrix inverse
        try:
            Si = np.linalg.inv(S)
        except np.linalg.LinAlgError:
            return

        # Kalman gain
        K = PHT @ Si

        # State update
        dx = K @ y
        self._inject_error_state(dx)

        # Covariance update
        IKH = np.eye(15) - K @ H
        self.P = IKH @ self.P @ IKH.T + K @ (np.eye(3) * R_val) @ K.T

    def _inject_error_state(self, dx: np.ndarray) -> None:
        """Inject error state into nominal state
        エラー状態を名目状態に注入
        """
        cfg = self.config

        # Position
        self.state.position += dx[0:3]

        # Velocity
        self.state.velocity += dx[3:6]

        # Attitude: q = q * exp(dtheta)
        dtheta = dx[6:9]
        dq = self._rotation_vector_to_quat(dtheta)
        self.state.quat = self._quat_multiply(self.state.quat, dq)
        self.state.quat = self.state.quat / np.linalg.norm(self.state.quat)

        # Fix yaw if disabled
        if not cfg.yaw_estimation_enabled:
            euler = self.state.euler
            self.state.quat = self._euler_to_quat(euler[0], euler[1], 0.0)

        # Gyro bias (conditional)
        if cfg.estimate_gyro_bias_xy:
            self.state.gyro_bias[0] += dx[9]
            self.state.gyro_bias[1] += dx[10]
        if cfg.mag_enabled:
            self.state.gyro_bias[2] += dx[11]

        # Accel bias (conditional)
        if not self.freeze_accel_bias:
            if cfg.estimate_accel_bias_xy:
                self.state.accel_bias[0] += dx[12]
                self.state.accel_bias[1] += dx[13]
            if cfg.estimate_accel_bias_z:
                self.state.accel_bias[2] += dx[14]

    def get_state(self) -> ESKFState:
        """Get current state"""
        return self.state.copy()

    def set_gyro_bias(self, bias: np.ndarray) -> None:
        """Set gyro bias"""
        self.state.gyro_bias = bias.copy()

    def set_accel_bias(self, bias: np.ndarray) -> None:
        """Set accel bias"""
        self.state.accel_bias = bias.copy()

    def reset_position_velocity(self) -> None:
        """Reset position and velocity only"""
        self.state.position = np.zeros(3)
        self.state.velocity = np.zeros(3)

        # Reset covariance for position/velocity
        cfg = self.config
        pos_var = cfg.init_pos_std ** 2
        vel_var = cfg.init_vel_std ** 2

        self.P[0:6, :] = 0
        self.P[:, 0:6] = 0
        self.P[0, 0] = self.P[1, 1] = self.P[2, 2] = pos_var
        self.P[3, 3] = self.P[4, 4] = self.P[5, 5] = vel_var

    # ========================================================================
    # Quaternion / Rotation utilities
    # クォータニオン・回転ユーティリティ
    # ========================================================================

    @staticmethod
    def _quat_to_rotation_matrix(q: np.ndarray) -> np.ndarray:
        """Convert quaternion [w, x, y, z] to rotation matrix (body -> NED)"""
        w, x, y, z = q
        return np.array([
            [1 - 2*(y*y + z*z), 2*(x*y - w*z), 2*(x*z + w*y)],
            [2*(x*y + w*z), 1 - 2*(x*x + z*z), 2*(y*z - w*x)],
            [2*(x*z - w*y), 2*(y*z + w*x), 1 - 2*(x*x + y*y)]
        ])

    @staticmethod
    def _rotation_vector_to_quat(v: np.ndarray) -> np.ndarray:
        """Convert rotation vector to quaternion"""
        angle = np.linalg.norm(v)
        if angle < 1e-10:
            return np.array([1.0, 0.0, 0.0, 0.0])
        axis = v / angle
        half_angle = angle / 2
        return np.array([
            np.cos(half_angle),
            axis[0] * np.sin(half_angle),
            axis[1] * np.sin(half_angle),
            axis[2] * np.sin(half_angle)
        ])

    @staticmethod
    def _quat_multiply(q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        """Multiply two quaternions"""
        w1, x1, y1, z1 = q1
        w2, x2, y2, z2 = q2
        return np.array([
            w1*w2 - x1*x2 - y1*y2 - z1*z2,
            w1*x2 + x1*w2 + y1*z2 - z1*y2,
            w1*y2 - x1*z2 + y1*w2 + z1*x2,
            w1*z2 + x1*y2 - y1*x2 + z1*w2
        ])

    @staticmethod
    def _euler_to_quat(roll: float, pitch: float, yaw: float) -> np.ndarray:
        """Convert Euler angles to quaternion [w, x, y, z]"""
        cr, sr = np.cos(roll / 2), np.sin(roll / 2)
        cp, sp = np.cos(pitch / 2), np.sin(pitch / 2)
        cy, sy = np.cos(yaw / 2), np.sin(yaw / 2)

        return np.array([
            cr * cp * cy + sr * sp * sy,  # w
            sr * cp * cy - cr * sp * sy,  # x
            cr * sp * cy + sr * cp * sy,  # y
            cr * cp * sy - sr * sp * cy   # z
        ])
