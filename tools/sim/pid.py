"""
PID Controller — Python port of firmware sf_algo_pid
PIDコントローラ — ファームウェアの忠実なポート

Matches: firmware/vehicle/components/sf_algo_pid/pid.cpp
"""

import numpy as np


class PID:
    """PID controller with anti-windup and derivative filtering.
    アンチワインドアップと微分フィルタ付き PID コントローラ。
    """

    def __init__(self, Kp: float, Ti: float, Td: float,
                 output_min: float = -1e6, output_max: float = 1e6,
                 eta: float = 0.125, derivative_on_measurement: bool = True):
        self.Kp = Kp
        self.Ti = Ti
        self.Td = Td
        self.output_min = output_min
        self.output_max = output_max
        self.eta = eta
        self.derivative_on_measurement = derivative_on_measurement

        self.integral = 0.0
        self.d_filtered = 0.0
        self.prev_measurement = None
        self.prev_error = None

    def update(self, setpoint: float, measurement: float, dt: float) -> float:
        """Compute PID output.
        PID 出力を計算。

        Args:
            setpoint: Target value
            measurement: Current value
            dt: Time step [s]

        Returns:
            Control output (clamped)
        """
        error = setpoint - measurement

        # Proportional
        p_term = self.Kp * error

        # Integral
        if self.Ti > 0 and dt > 0:
            self.integral += (self.Kp / self.Ti) * error * dt
            self.integral = np.clip(self.integral, self.output_min, self.output_max)
        i_term = self.integral

        # Derivative (on measurement to avoid derivative kick)
        d_term = 0.0
        if self.Td > 0 and dt > 0:
            if self.derivative_on_measurement:
                if self.prev_measurement is not None:
                    d_raw = -(measurement - self.prev_measurement) / dt
                    alpha = self.eta * self.Td / (self.eta * self.Td + dt)
                    self.d_filtered = alpha * self.d_filtered + (1 - alpha) * d_raw
                    d_term = self.Kp * self.Td * self.d_filtered
                self.prev_measurement = measurement
            else:
                if self.prev_error is not None:
                    d_raw = (error - self.prev_error) / dt
                    alpha = self.eta * self.Td / (self.eta * self.Td + dt)
                    self.d_filtered = alpha * self.d_filtered + (1 - alpha) * d_raw
                    d_term = self.Kp * self.Td * self.d_filtered
                self.prev_error = error

        output = p_term + i_term + d_term
        return float(np.clip(output, self.output_min, self.output_max))

    def reset(self):
        """Reset internal state."""
        self.integral = 0.0
        self.d_filtered = 0.0
        self.prev_measurement = None
        self.prev_error = None
