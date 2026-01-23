"""
Unit tests for ESKF Optimizer
ESKFオプティマイザの単体テスト
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import numpy as np
from eskf_sim.optimizer import (
    ESKFOptimizer,
    GridSearchResult,
    OptimizationResult,
    PARAMS,
    PARAM_NAMES,
)
from eskf_sim.eskf import ESKFConfig


class TestGridSearchResult(unittest.TestCase):
    """Test GridSearchResult dataclass"""

    def test_1d_result_creation(self):
        """Test creating 1D grid search result"""
        result = GridSearchResult(
            param_name='gyro_noise',
            values=[0.001, 0.01, 0.1],
            costs=[1.0, 0.5, 0.8],
            best_value=0.01,
            best_cost=0.5,
        )
        self.assertEqual(result.param_name, 'gyro_noise')
        self.assertEqual(len(result.values), 3)
        self.assertEqual(result.best_value, 0.01)
        self.assertEqual(result.best_cost, 0.5)
        self.assertIsNone(result.param_name2)

    def test_2d_result_creation(self):
        """Test creating 2D grid search result"""
        result = GridSearchResult(
            param_name='gyro_noise',
            values=[0.001, 0.01],
            costs=[],
            best_value=0.01,
            best_cost=0.3,
            param_name2='accel_noise',
            values2=[0.01, 0.1],
            cost_matrix=[[1.0, 0.8], [0.5, 0.3]],
            best_value2=0.1,
        )
        self.assertEqual(result.param_name2, 'accel_noise')
        self.assertEqual(result.best_value2, 0.1)
        self.assertEqual(len(result.cost_matrix), 2)

    def test_to_dict_1d(self):
        """Test to_dict for 1D result"""
        result = GridSearchResult(
            param_name='flow_noise',
            values=[0.001, 0.01, 0.1],
            costs=[1.0, 0.5, 0.8],
            best_value=0.01,
            best_cost=0.5,
        )
        d = result.to_dict()
        self.assertIn('param_name', d)
        self.assertIn('values', d)
        self.assertIn('costs', d)
        self.assertIn('best_value', d)
        self.assertIn('best_cost', d)
        self.assertNotIn('param_name2', d)

    def test_to_dict_2d(self):
        """Test to_dict for 2D result"""
        result = GridSearchResult(
            param_name='gyro_noise',
            values=[0.001, 0.01],
            costs=[],
            best_value=0.01,
            best_cost=0.3,
            param_name2='accel_noise',
            values2=[0.01, 0.1],
            cost_matrix=[[1.0, 0.8], [0.5, 0.3]],
            best_value2=0.1,
        )
        d = result.to_dict()
        self.assertIn('param_name2', d)
        self.assertIn('values2', d)
        self.assertIn('cost_matrix', d)
        self.assertIn('best_value2', d)
        self.assertNotIn('costs', d)  # costs not included in 2D


class TestParamDefinitions(unittest.TestCase):
    """Test parameter definitions"""

    def test_all_params_have_required_fields(self):
        """Test all parameters have min, max, default"""
        for name, info in PARAMS.items():
            self.assertIn('min', info, f"{name} missing 'min'")
            self.assertIn('max', info, f"{name} missing 'max'")
            self.assertIn('default', info, f"{name} missing 'default'")

    def test_param_bounds_valid(self):
        """Test parameter bounds are valid"""
        for name, info in PARAMS.items():
            self.assertLess(info['min'], info['max'], f"{name}: min >= max")
            self.assertGreaterEqual(info['default'], info['min'], f"{name}: default < min")
            self.assertLessEqual(info['default'], info['max'], f"{name}: default > max")

    def test_param_names_match(self):
        """Test PARAM_NAMES matches PARAMS keys"""
        self.assertEqual(set(PARAM_NAMES), set(PARAMS.keys()))


class TestESKFOptimizerInit(unittest.TestCase):
    """Test ESKFOptimizer initialization"""

    def setUp(self):
        """Create a test CSV file"""
        self.test_dir = tempfile.mkdtemp()
        self.test_csv = os.path.join(self.test_dir, 'test.csv')

        # Create minimal valid CSV
        with open(self.test_csv, 'w') as f:
            f.write('timestamp_us,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z\n')
            # Add some test data (400Hz for 0.1 seconds = 40 samples)
            for i in range(40):
                t = i * 2500  # 400Hz = 2500us interval
                f.write(f'{t},0.0,0.0,-9.81,0.0,0.0,0.0\n')

    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_init_with_valid_file(self):
        """Test initialization with valid file"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)
        self.assertEqual(len(optimizer.datasets), 1)
        self.assertEqual(optimizer.cost_fn_type, 'rmse')

    def test_init_with_multiple_files(self):
        """Test initialization with multiple files"""
        test_csv2 = os.path.join(self.test_dir, 'test2.csv')
        with open(test_csv2, 'w') as f:
            f.write('timestamp_us,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z\n')
            for i in range(40):
                t = i * 2500
                f.write(f'{t},0.0,0.0,-9.81,0.0,0.0,0.0\n')

        optimizer = ESKFOptimizer([self.test_csv, test_csv2], quiet=True)
        self.assertEqual(len(optimizer.datasets), 2)

    def test_init_with_cost_fn(self):
        """Test initialization with different cost functions"""
        for cost_fn in ['rmse', 'mae', 'position']:
            optimizer = ESKFOptimizer([self.test_csv], cost_fn=cost_fn, quiet=True)
            self.assertEqual(optimizer.cost_fn_type, cost_fn)

    def test_init_with_invalid_file(self):
        """Test initialization with non-existent file"""
        with self.assertRaises(ValueError):
            ESKFOptimizer(['/nonexistent/file.csv'], quiet=True)


class TestGridSearch(unittest.TestCase):
    """Test Grid Search functionality"""

    def setUp(self):
        """Create test CSV with ESKF reference data"""
        self.test_dir = tempfile.mkdtemp()
        self.test_csv = os.path.join(self.test_dir, 'test.csv')

        # Create CSV with ESKF reference columns
        with open(self.test_csv, 'w') as f:
            # Extended format with ESKF state columns
            f.write('timestamp_us,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,')
            f.write('tof_distance,baro_altitude,flow_dx,flow_dy,')
            f.write('eskf_pos_x,eskf_pos_y,eskf_pos_z,')
            f.write('eskf_vel_x,eskf_vel_y,eskf_vel_z,')
            f.write('eskf_quat_w,eskf_quat_x,eskf_quat_y,eskf_quat_z\n')

            # Generate 100 samples (0.25 seconds at 400Hz)
            for i in range(100):
                t = i * 2500
                # Simulate hovering with slight drift
                z = 0.5 + i * 0.0001
                f.write(f'{t},0.0,0.0,-9.81,0.01,0.02,0.0,')
                f.write(f'{z},10.0,0.0,0.0,')
                f.write(f'0.0,0.0,{z},')
                f.write(f'0.0,0.0,0.0001,')
                f.write(f'1.0,0.0,0.0,0.0\n')

    def tearDown(self):
        """Clean up test files"""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_grid_search_1d_valid_param(self):
        """Test 1D grid search with valid parameter"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)

        # Use small steps for faster test
        best_params, grid_result = optimizer.optimize_grid(
            param_name='gyro_noise',
            steps=3,
        )

        self.assertIsNotNone(best_params)
        self.assertIsNotNone(grid_result)
        self.assertEqual(grid_result.param_name, 'gyro_noise')
        self.assertEqual(len(grid_result.values), 3)
        self.assertEqual(len(grid_result.costs), 3)
        self.assertIn('gyro_noise', best_params)

    def test_grid_search_1d_all_params(self):
        """Test 1D grid search works for all parameters"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)

        for param_name in PARAM_NAMES:
            best_params, grid_result = optimizer.optimize_grid(
                param_name=param_name,
                steps=3,
            )
            self.assertEqual(grid_result.param_name, param_name)
            self.assertIn(param_name, best_params)

    def test_grid_search_2d(self):
        """Test 2D grid search"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)

        best_params, grid_result = optimizer.optimize_grid(
            param_name='gyro_noise',
            steps=3,
            param_name2='accel_noise',
            steps2=2,
        )

        self.assertIsNotNone(best_params)
        self.assertIsNotNone(grid_result)
        self.assertEqual(grid_result.param_name, 'gyro_noise')
        self.assertEqual(grid_result.param_name2, 'accel_noise')
        self.assertEqual(len(grid_result.values), 3)
        self.assertEqual(len(grid_result.values2), 2)
        self.assertEqual(len(grid_result.cost_matrix), 3)
        self.assertEqual(len(grid_result.cost_matrix[0]), 2)

    def test_grid_search_invalid_param(self):
        """Test grid search with invalid parameter name"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)

        with self.assertRaises(ValueError) as ctx:
            optimizer.optimize_grid(param_name='invalid_param', steps=3)

        self.assertIn('Unknown parameter', str(ctx.exception))

    def test_grid_search_invalid_param2(self):
        """Test grid search with invalid second parameter"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)

        with self.assertRaises(ValueError) as ctx:
            optimizer.optimize_grid(
                param_name='gyro_noise',
                steps=3,
                param_name2='invalid_param',
                steps2=2,
            )

        self.assertIn('Unknown parameter', str(ctx.exception))

    def test_grid_search_values_log_spaced(self):
        """Test that grid values are log-spaced"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)

        _, grid_result = optimizer.optimize_grid(
            param_name='gyro_noise',
            steps=5,
        )

        values = np.array(grid_result.values)
        # Check log spacing: ratios should be approximately equal
        ratios = values[1:] / values[:-1]
        self.assertTrue(np.allclose(ratios, ratios[0], rtol=0.01))

    def test_grid_search_best_cost_is_minimum(self):
        """Test that best_cost is actually the minimum"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)

        _, grid_result = optimizer.optimize_grid(
            param_name='tof_noise',
            steps=5,
        )

        self.assertEqual(grid_result.best_cost, min(grid_result.costs))

    def test_grid_search_2d_best_in_matrix(self):
        """Test that 2D best cost is minimum in matrix"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)

        _, grid_result = optimizer.optimize_grid(
            param_name='gyro_noise',
            steps=3,
            param_name2='accel_noise',
            steps2=3,
        )

        # Flatten matrix and check best_cost is minimum
        flat_costs = [c for row in grid_result.cost_matrix for c in row]
        self.assertEqual(grid_result.best_cost, min(flat_costs))


class TestESKFConfig(unittest.TestCase):
    """Test ESKFConfig integration with optimizer"""

    def test_params_dict_to_config(self):
        """Test converting params dict to ESKFConfig"""
        test_dir = tempfile.mkdtemp()
        test_csv = os.path.join(test_dir, 'test.csv')

        with open(test_csv, 'w') as f:
            f.write('timestamp_us,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z\n')
            for i in range(40):
                f.write(f'{i * 2500},0.0,0.0,-9.81,0.0,0.0,0.0\n')

        try:
            optimizer = ESKFOptimizer([test_csv], quiet=True)

            params_dict = {'gyro_noise': 0.05, 'accel_noise': 0.1}
            config = optimizer._params_dict_to_config(params_dict)

            self.assertEqual(config.gyro_noise, 0.05)
            self.assertEqual(config.accel_noise, 0.1)
        finally:
            import shutil
            shutil.rmtree(test_dir)


class TestCostFunction(unittest.TestCase):
    """Test cost function computation"""

    def setUp(self):
        """Create test CSV"""
        self.test_dir = tempfile.mkdtemp()
        self.test_csv = os.path.join(self.test_dir, 'test.csv')

        with open(self.test_csv, 'w') as f:
            f.write('timestamp_us,accel_x,accel_y,accel_z,gyro_x,gyro_y,gyro_z,')
            f.write('tof_distance,eskf_pos_x,eskf_pos_y,eskf_pos_z,')
            f.write('eskf_vel_x,eskf_vel_y,eskf_vel_z,')
            f.write('eskf_quat_w,eskf_quat_x,eskf_quat_y,eskf_quat_z\n')

            for i in range(50):
                t = i * 2500
                f.write(f'{t},0.0,0.0,-9.81,0.0,0.0,0.0,')
                f.write(f'0.5,0.0,0.0,0.5,')
                f.write(f'0.0,0.0,0.0,')
                f.write(f'1.0,0.0,0.0,0.0\n')

    def tearDown(self):
        import shutil
        shutil.rmtree(self.test_dir)

    def test_cost_returns_float(self):
        """Test that cost function returns a float"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)
        params = {name: info['default'] for name, info in PARAMS.items()}

        cost, results = optimizer._compute_cost(params)

        self.assertIsInstance(cost, float)
        self.assertGreater(cost, 0)

    def test_cost_function_types(self):
        """Test different cost function types"""
        for cost_fn in ['rmse', 'mae', 'position']:
            optimizer = ESKFOptimizer([self.test_csv], cost_fn=cost_fn, quiet=True)
            params = {name: info['default'] for name, info in PARAMS.items()}

            cost, _ = optimizer._compute_cost(params)
            self.assertIsInstance(cost, float)

    def test_eval_count_increments(self):
        """Test that eval_count increments"""
        optimizer = ESKFOptimizer([self.test_csv], quiet=True)
        params = {name: info['default'] for name, info in PARAMS.items()}

        initial_count = optimizer.eval_count
        optimizer._compute_cost(params)
        self.assertEqual(optimizer.eval_count, initial_count + 1)

        optimizer._compute_cost(params)
        self.assertEqual(optimizer.eval_count, initial_count + 2)


if __name__ == '__main__':
    unittest.main()
