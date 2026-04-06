"""
Closed-Loop Control Simulator
閉ループ制御シミュレータ

Simulates the full control cascade:
  Position PID → Attitude PID → Rate PID → Mixer → Drone Plant

Uses config.hpp parameters via config_parser (SSOT).
"""

import sys
import os
import numpy as np
from dataclasses import dataclass, field
from typing import Optional, Dict, List

# Add tools/ to path
_tools_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

from sim.pid import PID
from sim.drone_plant import DronePlant, DroneParams
from common.config_parser import load_config


@dataclass
class SimResult:
    """Simulation results.
    シミュレーション結果。
    """
    t: List[float] = field(default_factory=list)
    pos_x: List[float] = field(default_factory=list)
    pos_y: List[float] = field(default_factory=list)
    pos_z: List[float] = field(default_factory=list)
    vel_x: List[float] = field(default_factory=list)
    vel_y: List[float] = field(default_factory=list)
    vel_z: List[float] = field(default_factory=list)
    roll: List[float] = field(default_factory=list)
    pitch: List[float] = field(default_factory=list)
    yaw: List[float] = field(default_factory=list)
    roll_rate: List[float] = field(default_factory=list)
    pitch_rate: List[float] = field(default_factory=list)
    yaw_rate: List[float] = field(default_factory=list)
    thrust: List[float] = field(default_factory=list)
    angle_ref_roll: List[float] = field(default_factory=list)
    angle_ref_pitch: List[float] = field(default_factory=list)

    def record(self, t: float, plant: DronePlant, thrust: float,
               angle_ref_r: float = 0, angle_ref_p: float = 0):
        self.t.append(t)
        s = plant.state
        self.pos_x.append(s[0]); self.pos_y.append(s[1]); self.pos_z.append(s[2])
        self.vel_x.append(s[3]); self.vel_y.append(s[4]); self.vel_z.append(s[5])
        self.roll.append(s[6]); self.pitch.append(s[7]); self.yaw.append(s[8])
        self.roll_rate.append(s[9]); self.pitch_rate.append(s[10]); self.yaw_rate.append(s[11])
        self.thrust.append(thrust)
        self.angle_ref_roll.append(angle_ref_r)
        self.angle_ref_pitch.append(angle_ref_p)

    def metrics(self) -> Dict[str, float]:
        """Compute performance metrics."""
        px = np.array(self.pos_x)
        py = np.array(self.pos_y)
        vx = np.array(self.vel_x)
        vy = np.array(self.vel_y)
        r = np.array(self.roll)
        p = np.array(self.pitch)

        # Settle time (5% band for position)
        settle = self.t[-1]
        thresh = 0.015  # 15mm
        for i in range(len(px)-1, 0, -1):
            if abs(px[i]) > thresh or abs(py[i]) > thresh:
                settle = self.t[min(i+1, len(self.t)-1)]
                break

        return {
            'pos_x_max': float(np.max(np.abs(px))),
            'pos_y_max': float(np.max(np.abs(py))),
            'pos_x_rms': float(np.sqrt(np.mean(px**2))),
            'pos_y_rms': float(np.sqrt(np.mean(py**2))),
            'vel_x_rms': float(np.sqrt(np.mean(vx**2))),
            'vel_y_rms': float(np.sqrt(np.mean(vy**2))),
            'roll_max_deg': float(np.max(np.abs(r)) * 180/np.pi),
            'pitch_max_deg': float(np.max(np.abs(p)) * 180/np.pi),
            'settle_time': settle,
        }


class ClosedLoopSim:
    """Full cascade closed-loop simulator.
    全カスケード閉ループシミュレータ。

    Control cascade (from outermost to innermost):
    1. Position PID: pos_error → vel_target
    2. Velocity PID: vel_error → angle_correction (NED)
    3. NED → Body conversion
    4. Attitude PID: angle_error → rate_target
    5. Rate PID: rate_error → torque
    6. Mixer: [thrust, torques] → motor commands
    7. Drone plant: motor commands → state update
    """

    def __init__(self, config_path: Optional[str] = None,
                 param_overrides: Optional[Dict[str, float]] = None):
        """Initialize with config.hpp parameters.

        Args:
            config_path: Path to config.hpp (auto-detected if None)
            param_overrides: Override specific parameters {namespace.PARAM: value}
        """
        config = load_config(config_path)

        # Apply overrides
        if param_overrides:
            for key, val in param_overrides.items():
                parts = key.split('.')
                if len(parts) == 2:
                    ns, name = parts
                    if ns in config:
                        config[ns][name] = val

        self._config = config

        # Plant
        self.plant = DronePlant(DroneParams.from_config(config))

        # Rate PID (innermost)
        rc = config.get('rate_control', {})
        eta = rc.get('PID_ETA', 0.125)
        self.roll_rate_pid = PID(
            rc.get('ROLL_RATE_KP', 0.65), rc.get('ROLL_RATE_TI', 0.7),
            rc.get('ROLL_RATE_TD', 0.01),
            -rc.get('ROLL_OUTPUT_LIMIT', 3.7), rc.get('ROLL_OUTPUT_LIMIT', 3.7), eta)
        self.pitch_rate_pid = PID(
            rc.get('PITCH_RATE_KP', 0.95), rc.get('PITCH_RATE_TI', 0.7),
            rc.get('PITCH_RATE_TD', 0.025),
            -rc.get('PITCH_OUTPUT_LIMIT', 3.7), rc.get('PITCH_OUTPUT_LIMIT', 3.7), eta)
        self.yaw_rate_pid = PID(
            rc.get('YAW_RATE_KP', 3.0), rc.get('YAW_RATE_TI', 0.8),
            rc.get('YAW_RATE_TD', 0.01),
            -rc.get('YAW_OUTPUT_LIMIT', 3.7), rc.get('YAW_OUTPUT_LIMIT', 3.7), eta)

        # Attitude PID
        ac = config.get('attitude_control', {})
        eta_att = ac.get('PID_ETA', 0.125)
        max_rate = ac.get('MAX_RATE_SETPOINT', 3.0)
        self.roll_angle_pid = PID(
            ac.get('ROLL_ANGLE_KP', 5.0), ac.get('ROLL_ANGLE_TI', 4.0),
            ac.get('ROLL_ANGLE_TD', 0.04), -max_rate, max_rate, eta_att)
        self.pitch_angle_pid = PID(
            ac.get('PITCH_ANGLE_KP', 5.0), ac.get('PITCH_ANGLE_TI', 4.0),
            ac.get('PITCH_ANGLE_TD', 0.04), -max_rate, max_rate, eta_att)
        self.max_roll_angle = ac.get('MAX_ROLL_ANGLE', 0.5236)
        self.max_pitch_angle = ac.get('MAX_PITCH_ANGLE', 0.5236)

        # Altitude PID
        altc = config.get('altitude_control', {})
        eta_alt = altc.get('PID_ETA', 0.125)
        self.alt_pid = PID(
            altc.get('ALT_KP', 0.6), altc.get('ALT_TI', 7.0),
            altc.get('ALT_TD', 0.0),
            -altc.get('ALT_OUTPUT_MAX', 0.5), altc.get('ALT_OUTPUT_MAX', 0.5), eta_alt)
        self.alt_vel_pid = PID(
            altc.get('VEL_KP', 0.1), altc.get('VEL_TI', 2.5),
            altc.get('VEL_TD', 0.0),
            -altc.get('VEL_OUTPUT_MAX', 0.15), altc.get('VEL_OUTPUT_MAX', 0.15), eta_alt)
        self.hover_correction = altc.get('HOVER_THRUST_CORRECTION', 1.12)
        self.mass = altc.get('MASS', 0.037)
        self.gravity = altc.get('GRAVITY', 9.81)

        # Position PID
        pc = config.get('position_control', {})
        eta_pos = pc.get('PID_ETA', 0.125)
        self.pos_x_pid = PID(
            pc.get('POS_KP', 1.0), pc.get('POS_TI', 5.0), pc.get('POS_TD', 0.1),
            -pc.get('POS_OUTPUT_MAX', 0.5), pc.get('POS_OUTPUT_MAX', 0.5), eta_pos)
        self.pos_y_pid = PID(
            pc.get('POS_KP', 1.0), pc.get('POS_TI', 5.0), pc.get('POS_TD', 0.1),
            -pc.get('POS_OUTPUT_MAX', 0.5), pc.get('POS_OUTPUT_MAX', 0.5), eta_pos)
        self.vel_x_pid = PID(
            pc.get('VEL_KP', 0.3), pc.get('VEL_TI', 2.0), pc.get('VEL_TD', 0.02),
            -pc.get('VEL_OUTPUT_MAX', 0.20), pc.get('VEL_OUTPUT_MAX', 0.20), eta_pos)
        self.vel_y_pid = PID(
            pc.get('VEL_KP', 0.3), pc.get('VEL_TI', 2.0), pc.get('VEL_TD', 0.02),
            -pc.get('VEL_OUTPUT_MAX', 0.20), pc.get('VEL_OUTPUT_MAX', 0.20), eta_pos)
        self.max_tilt = pc.get('MAX_TILT_ANGLE', 0.1745)

    def run(self, duration: float = 10.0, dt: float = 0.0025,
            disturbance_pos: Optional[np.ndarray] = None,
            altitude_setpoint: float = 0.5,
            pos_setpoint: Optional[np.ndarray] = None,
            mode: str = 'position',
            record_interval: int = 4) -> SimResult:
        """Run closed-loop simulation.

        Args:
            duration: Simulation duration [s]
            dt: Time step [s] (default: 2.5ms = 400Hz)
            disturbance_pos: Initial position offset [x, y] in [m]
            altitude_setpoint: Target altitude [m] (positive up)
            pos_setpoint: Target position [x, y] in [m] (NED)
            mode: 'position', 'altitude', 'stabilize', 'rate'
            record_interval: Record every N steps (default: 4 = 100Hz)

        Returns:
            SimResult with time series
        """
        result = SimResult()
        self.plant.reset(altitude=altitude_setpoint)

        # Apply disturbance
        if disturbance_pos is not None:
            self.plant.state[0] = disturbance_pos[0]
            self.plant.state[1] = disturbance_pos[1]

        if pos_setpoint is None:
            pos_setpoint = np.array([0.0, 0.0])

        alt_sp = altitude_setpoint
        hover_thrust = self.plant.hover_thrust() * self.hover_correction

        steps = int(duration / dt)
        for i in range(steps):
            t = i * dt
            s = self.plant.state
            roll, pitch, yaw = s[6], s[7], s[8]
            p, q, r = s[9], s[10], s[11]
            pos = s[0:3]
            vel = s[3:6]
            altitude = -pos[2]

            # === Altitude control ===
            thrust = hover_thrust
            if mode in ('altitude', 'position'):
                alt_vel_target = self.alt_pid.update(alt_sp, altitude, dt)
                alt_correction = self.alt_vel_pid.update(alt_vel_target, -vel[2], dt)
                thrust = hover_thrust + alt_correction

            # === Position control ===
            roll_angle_target = 0.0
            pitch_angle_target = 0.0

            if mode == 'position':
                # Outer: position → velocity target
                vel_target_x = self.pos_x_pid.update(pos_setpoint[0], pos[0], dt)
                vel_target_y = self.pos_y_pid.update(pos_setpoint[1], pos[1], dt)

                # Inner: velocity → angle correction (NED)
                angle_ned_x = self.vel_x_pid.update(vel_target_x, vel[0], dt)
                angle_ned_y = self.vel_y_pid.update(vel_target_y, vel[1], dt)

                # NED → Body (with pitch negation for NED convention)
                cy, sy = np.cos(yaw), np.sin(yaw)
                pitch_body = -(cy * angle_ned_x + sy * angle_ned_y)
                roll_body = -sy * angle_ned_x + cy * angle_ned_y

                roll_angle_target = np.clip(roll_body, -self.max_tilt, self.max_tilt)
                pitch_angle_target = np.clip(pitch_body, -self.max_tilt, self.max_tilt)

            # === Attitude control ===
            roll_rate_target = self.roll_angle_pid.update(
                roll_angle_target, roll, dt)
            pitch_rate_target = self.pitch_angle_pid.update(
                pitch_angle_target, pitch, dt)
            yaw_rate_target = 0.0  # No yaw control for now

            # === Rate control ===
            tau_roll = self.roll_rate_pid.update(roll_rate_target, p, dt)
            tau_pitch = self.pitch_rate_pid.update(pitch_rate_target, q, dt)
            tau_yaw = self.yaw_rate_pid.update(yaw_rate_target, r, dt)

            # === Plant update ===
            # Scale PID voltage output to torque [Nm]
            ts = self.plant.params.torque_scale
            control = np.array([thrust, tau_roll * ts, tau_pitch * ts, tau_yaw * ts])
            self.plant.step(control, dt)

            # Record
            if i % record_interval == 0:
                result.record(t, self.plant, thrust,
                            roll_angle_target, pitch_angle_target)

        return result


def run_position_step_test(config_path: Optional[str] = None,
                           param_overrides: Optional[Dict] = None,
                           disturbance: float = 0.3) -> SimResult:
    """Convenience: run position hold step response test.
    位置保持ステップ応答テスト。
    """
    sim = ClosedLoopSim(config_path, param_overrides)
    return sim.run(
        duration=10.0,
        disturbance_pos=np.array([disturbance, 0.0]),
        mode='position',
    )


if __name__ == '__main__':
    # Quick test
    result = run_position_step_test()
    m = result.metrics()
    print("=== Position Step Response (0.3m disturbance) ===")
    for k, v in m.items():
        print(f"  {k}: {v:.4f}")
    print(f"\nTrajectory (every 0.5s):")
    for i in range(0, len(result.t), max(1, len(result.t)//20)):
        print(f"  t={result.t[i]:5.2f}s  "
              f"pos=[{result.pos_x[i]:7.4f},{result.pos_y[i]:7.4f}]  "
              f"pitch={result.pitch[i]*180/np.pi:5.1f}°")
