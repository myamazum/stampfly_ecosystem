"""
Unit tests for ESKF implementation
ESKF実装の単体テスト
"""

import unittest
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
from eskf_sim.eskf import ESKF, ESKFConfig, ESKFState


class TestESKFConfig(unittest.TestCase):
    """Test ESKFConfig dataclass"""

    def test_default_config(self):
        """Test default configuration values"""
        config = ESKFConfig()

        # Check process noise defaults
        self.assertGreater(config.gyro_noise, 0)
        self.assertGreater(config.accel_noise, 0)
        self.assertGreater(config.gyro_bias_noise, 0)
        self.assertGreater(config.accel_bias_noise, 0)

        # Check measurement noise defaults
        self.assertGreater(config.tof_noise, 0)
        self.assertGreater(config.flow_noise, 0)
        self.assertGreater(config.accel_att_noise, 0)

    def test_to_dict(self):
        """Test conversion to dictionary"""
        config = ESKFConfig()
        d = config.to_dict()

        # to_dict returns nested structure
        self.assertIn('process_noise', d)
        self.assertIn('measurement_noise', d)
        self.assertEqual(d['process_noise']['gyro_noise'], config.gyro_noise)

    def test_from_dict(self):
        """Test creation from dictionary (nested format)"""
        d = {
            'process_noise': {'gyro_noise': 0.05, 'accel_noise': 0.1},
        }
        config = ESKFConfig.from_dict(d)

        self.assertEqual(config.gyro_noise, 0.05)
        self.assertEqual(config.accel_noise, 0.1)

    def test_from_dict_with_nested(self):
        """Test creation from nested dictionary"""
        d = {
            'process_noise': {
                'gyro_noise': 0.05,
                'accel_noise': 0.1,
            },
            'measurement_noise': {
                'tof_noise': 0.01,
            },
        }
        config = ESKFConfig.from_dict(d)

        self.assertEqual(config.gyro_noise, 0.05)
        self.assertEqual(config.accel_noise, 0.1)
        self.assertEqual(config.tof_noise, 0.01)


class TestESKFState(unittest.TestCase):
    """Test ESKFState dataclass"""

    def test_default_state(self):
        """Test default state values"""
        state = ESKFState()

        # Check default values
        np.testing.assert_array_equal(state.position, [0, 0, 0])
        np.testing.assert_array_equal(state.velocity, [0, 0, 0])
        np.testing.assert_array_equal(state.quat, [1, 0, 0, 0])
        np.testing.assert_array_equal(state.gyro_bias, [0, 0, 0])
        np.testing.assert_array_equal(state.accel_bias, [0, 0, 0])

    def test_euler_property(self):
        """Test euler angle computation from quaternion"""
        # Identity quaternion should give zero euler angles
        state = ESKFState()
        euler = state.euler
        np.testing.assert_array_almost_equal(euler, [0, 0, 0])

    def test_euler_with_rotation(self):
        """Test euler angles with rotated quaternion"""
        state = ESKFState()
        # 90 degree rotation around z-axis (w, x, y, z)
        state.quat = np.array([np.cos(np.pi/4), 0, 0, np.sin(np.pi/4)])
        euler = state.euler
        # Yaw should be ~90 degrees
        self.assertAlmostEqual(euler[2], np.pi/2, places=5)


class TestESKFInit(unittest.TestCase):
    """Test ESKF initialization"""

    def test_init_default_config(self):
        """Test initialization with default config"""
        eskf = ESKF()
        self.assertIsNotNone(eskf)

    def test_init_custom_config(self):
        """Test initialization with custom config"""
        config = ESKFConfig()
        config.gyro_noise = 0.05
        eskf = ESKF(config)
        self.assertEqual(eskf.config.gyro_noise, 0.05)

    def test_init_resets_state(self):
        """Test that init() resets state"""
        eskf = ESKF()
        eskf.init()

        state = eskf.get_state()
        np.testing.assert_array_equal(state.position, [0, 0, 0])
        np.testing.assert_array_equal(state.velocity, [0, 0, 0])


class TestESKFPredict(unittest.TestCase):
    """Test ESKF prediction step"""

    def setUp(self):
        self.eskf = ESKF()
        self.eskf.init()

    def test_predict_with_zero_input(self):
        """Test prediction with zero IMU input"""
        accel = np.array([0.0, 0.0, -9.81])
        gyro = np.array([0.0, 0.0, 0.0])
        dt = 0.0025

        self.eskf.predict(accel, gyro, dt)
        state = self.eskf.get_state()

        # Position should remain near zero with zero acceleration (gravity cancels)
        np.testing.assert_array_almost_equal(state.position, [0, 0, 0], decimal=3)

    def test_predict_with_acceleration(self):
        """Test prediction with acceleration"""
        accel = np.array([1.0, 0.0, -9.81])  # 1 m/s^2 in x
        gyro = np.array([0.0, 0.0, 0.0])
        dt = 0.01

        self.eskf.predict(accel, gyro, dt)
        state = self.eskf.get_state()

        # Velocity should increase in x direction
        self.assertGreater(state.velocity[0], 0)

    def test_predict_with_rotation(self):
        """Test prediction with angular velocity"""
        accel = np.array([0.0, 0.0, -9.81])
        gyro = np.array([0.0, 0.0, 0.1])  # 0.1 rad/s around z
        dt = 0.01

        initial_quat = self.eskf.get_state().quat.copy()
        self.eskf.predict(accel, gyro, dt)
        new_quat = self.eskf.get_state().quat

        # Quaternion should change
        self.assertFalse(np.allclose(initial_quat, new_quat))

    def test_predict_maintains_quaternion_norm(self):
        """Test that quaternion remains normalized after prediction"""
        accel = np.array([0.1, 0.2, -9.81])
        gyro = np.array([0.1, 0.2, 0.3])
        dt = 0.01

        for _ in range(100):
            self.eskf.predict(accel, gyro, dt)

        quat = self.eskf.get_state().quat
        norm = np.linalg.norm(quat)
        self.assertAlmostEqual(norm, 1.0, places=5)


class TestESKFMeasurementUpdates(unittest.TestCase):
    """Test ESKF measurement updates"""

    def setUp(self):
        self.eskf = ESKF()
        self.eskf.init()

    def test_update_tof_basic(self):
        """Test ToF update"""
        self.eskf.update_tof(0.5)
        state = self.eskf.get_state()

        # Position z should be influenced toward 0.5
        # (exact value depends on Kalman gain)
        self.assertIsNotNone(state.position[2])

    def test_update_tof_multiple(self):
        """Test multiple ToF updates converge"""
        tof_distance = 0.5
        for _ in range(50):
            self.eskf.update_tof(tof_distance)

        state = self.eskf.get_state()
        # NED coordinate: height 0.5m above ground -> position[2] = -0.5
        # NED座標系: 地面から0.5m上 -> position[2] = -0.5
        self.assertAlmostEqual(state.position[2], -tof_distance, places=1)

    def test_update_baro(self):
        """Test barometer update"""
        self.eskf.update_baro(10.0)
        # Should not crash
        state = self.eskf.get_state()
        self.assertIsNotNone(state)

    def test_update_flow_raw(self):
        """Test optical flow update"""
        tof_distance = 0.5
        flow_dx = 0.1
        flow_dy = 0.0
        dt = 0.01
        gyro_x = 0.0
        gyro_y = 0.0

        self.eskf.update_flow_raw(flow_dx, flow_dy, tof_distance, dt, gyro_x, gyro_y)
        state = self.eskf.get_state()
        self.assertIsNotNone(state)

    def test_update_accel_attitude(self):
        """Test accelerometer attitude correction"""
        accel = np.array([0.0, 0.0, -9.81])
        self.eskf.update_accel_attitude(accel)

        state = self.eskf.get_state()
        # Quaternion w should be close to 1 for level (identity quaternion)
        # Allow some tolerance since single update won't fully converge
        self.assertGreater(abs(state.quat[0]), 0.9)


class TestESKFIntegration(unittest.TestCase):
    """Integration tests for ESKF"""

    def test_hover_simulation(self):
        """Test simulating hover condition"""
        eskf = ESKF()
        eskf.init()

        # Simulate 1 second of hover
        dt = 0.0025  # 400Hz
        accel = np.array([0.0, 0.0, -9.81])
        gyro = np.array([0.0, 0.0, 0.0])
        tof = 0.5

        for _ in range(400):
            eskf.predict(accel, gyro, dt)
            eskf.update_tof(tof)
            eskf.update_accel_attitude(accel)

        state = eskf.get_state()

        # Position should be stable near tof measurement
        # NED coordinate: height 0.5m above ground -> position[2] = -0.5
        self.assertAlmostEqual(state.position[2], -tof, places=1)
        # Velocity should be near zero
        np.testing.assert_array_almost_equal(state.velocity, [0, 0, 0], decimal=1)

    def test_covariance_bounded(self):
        """Test that covariance doesn't explode"""
        eskf = ESKF()
        eskf.init()

        dt = 0.0025
        accel = np.array([0.1, 0.1, -9.81])
        gyro = np.array([0.01, 0.01, 0.01])

        for _ in range(1000):
            eskf.predict(accel, gyro, dt)

        # Covariance should be bounded
        P_diag = np.diag(eskf.P)
        self.assertTrue(np.all(P_diag < 1e6))
        self.assertTrue(np.all(P_diag > 0))


if __name__ == '__main__':
    unittest.main()
