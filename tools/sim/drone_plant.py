"""
Simplified Drone Plant Model for Control Tuning
制御チューニング用の簡略化ドローンプラントモデル

Models the StampFly as a rigid body with:
- 4 motors in X configuration
- First-order motor dynamics
- Simple aerodynamic drag
- Gravity

State: [pos_x, pos_y, pos_z, vel_x, vel_y, vel_z, roll, pitch, yaw, p, q, r]
       (NED frame for position/velocity, body frame for angular rates)
"""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class DroneParams:
    """Physical parameters of the drone.
    ドローンの物理パラメータ。
    """
    mass: float = 0.037           # [kg]
    gravity: float = 9.81         # [m/s²]
    arm_length: float = 0.033     # [m] center to motor
    Ixx: float = 2.6e-6           # [kg·m²] roll inertia
    Iyy: float = 2.6e-6           # [kg·m²] pitch inertia
    Izz: float = 5.0e-6           # [kg·m²] yaw inertia
    k_thrust: float = 1.5e-3     # [N] per unit duty (0-1)
    k_torque: float = 0.01       # torque-to-thrust ratio
    motor_tau: float = 0.02       # [s] motor time constant
    drag_coeff: float = 0.01      # [N·s/m] linear drag
    # Voltage-to-torque scale: PID outputs voltage, plant expects torque [Nm]
    # Approximate: 4 motors × k_thrust × arm_length / 4 per volt
    # 電圧→トルク変換: PID出力は電圧、プラントはトルク[Nm]を期待
    torque_scale: float = 5.0e-5  # [Nm/V] = 4 * 1.5e-3 * 0.033 / 4

    @classmethod
    def from_config(cls, config: dict) -> 'DroneParams':
        """Create from parsed config.hpp."""
        p = cls()
        alt = config.get('altitude_control', {})
        if 'MASS' in alt:
            p.mass = alt['MASS']
        if 'GRAVITY' in alt:
            p.gravity = alt['GRAVITY']
        return p


class DronePlant:
    """Simplified 6-DOF drone dynamics.
    簡略化6自由度ドローンダイナミクス。

    Input: [thrust_total, torque_roll, torque_pitch, torque_yaw]
    Output: full state vector
    """

    def __init__(self, params: Optional[DroneParams] = None):
        self.params = params or DroneParams()

        # State: [x, y, z, vx, vy, vz, roll, pitch, yaw, p, q, r]
        self.state = np.zeros(12)

        # Motor duties [0-1] for 4 motors
        self.motor_duties = np.zeros(4)

    def reset(self, altitude: float = 0.0):
        """Reset to hover at given altitude."""
        self.state = np.zeros(12)
        self.state[2] = -altitude  # NED: z negative = up
        self.motor_duties = np.zeros(4)

    def step(self, control: np.ndarray, dt: float) -> np.ndarray:
        """Advance one time step.

        Args:
            control: [total_thrust_N, roll_torque_Nm, pitch_torque_Nm, yaw_torque_Nm]
            dt: Time step [s]

        Returns:
            Updated state vector [12]
        """
        p = self.params
        x, y, z = self.state[0:3]
        vx, vy, vz = self.state[3:6]
        roll, pitch, yaw = self.state[6:9]
        wx, wy, wz = self.state[9:12]

        thrust = control[0]
        tau_roll = control[1]
        tau_pitch = control[2]
        tau_yaw = control[3]

        # Rotation matrix (body to NED)
        cr, sr = np.cos(roll), np.sin(roll)
        cp, sp = np.cos(pitch), np.sin(pitch)
        cy, sy = np.cos(yaw), np.sin(yaw)

        R = np.array([
            [cp*cy, sr*sp*cy - cr*sy, cr*sp*cy + sr*sy],
            [cp*sy, sr*sp*sy + cr*cy, cr*sp*sy - sr*cy],
            [-sp,   sr*cp,            cr*cp]
        ])

        # Thrust in body frame: [0, 0, -thrust] (up in body = -z)
        thrust_body = np.array([0, 0, -thrust])
        thrust_ned = R @ thrust_body

        # Gravity in NED
        gravity_ned = np.array([0, 0, p.mass * p.gravity])

        # Drag
        vel_ned = np.array([vx, vy, vz])
        drag_ned = -p.drag_coeff * vel_ned

        # Linear acceleration
        accel = (thrust_ned + gravity_ned + drag_ned) / p.mass

        # Angular acceleration
        alpha_x = tau_roll / p.Ixx
        alpha_y = tau_pitch / p.Iyy
        alpha_z = tau_yaw / p.Izz

        # Integration (Euler)
        # Position
        self.state[0] += vx * dt + 0.5 * accel[0] * dt**2
        self.state[1] += vy * dt + 0.5 * accel[1] * dt**2
        self.state[2] += vz * dt + 0.5 * accel[2] * dt**2

        # Velocity
        self.state[3] += accel[0] * dt
        self.state[4] += accel[1] * dt
        self.state[5] += accel[2] * dt

        # Attitude (small angle approximation for angular rates -> euler rates)
        self.state[6] += wx * dt
        self.state[7] += wy * dt
        self.state[8] += wz * dt

        # Angular rates
        self.state[9] += alpha_x * dt
        self.state[10] += alpha_y * dt
        self.state[11] += alpha_z * dt

        # Wrap angles
        self.state[6] = _wrap_angle(self.state[6])
        self.state[7] = _wrap_angle(self.state[7])
        self.state[8] = _wrap_angle(self.state[8])

        return self.state.copy()

    @property
    def position(self) -> np.ndarray:
        return self.state[0:3]

    @property
    def velocity(self) -> np.ndarray:
        return self.state[3:6]

    @property
    def euler(self) -> np.ndarray:
        return self.state[6:9]

    @property
    def angular_rate(self) -> np.ndarray:
        return self.state[9:12]

    @property
    def altitude(self) -> float:
        """Altitude above ground (positive up)."""
        return -self.state[2]

    def hover_thrust(self) -> float:
        """Thrust needed for hover [N]."""
        return self.params.mass * self.params.gravity


def _wrap_angle(angle: float) -> float:
    """Wrap angle to [-pi, pi]."""
    while angle > np.pi:
        angle -= 2 * np.pi
    while angle < -np.pi:
        angle += 2 * np.pi
    return angle
