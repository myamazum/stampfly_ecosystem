"""
ESKF Simulation and Parameter Tuning Toolkit
ESKFシミュレーション・パラメータチューニングツール群

This package provides Python implementations for:
- ESKF (Error-State Kalman Filter) replay simulation
- Parameter optimization (Q/R tuning)
- Error metrics calculation
- Visualization

Unix philosophy: Small, focused tools that work together via pipes.

CLI Usage:
    sf eskf replay flight.csv --params custom.yaml -o states.csv
    sf eskf compare estimated.csv --ref logged.csv
    sf eskf tune flight.csv -o optimized.yaml
    sf eskf plot states.csv --overlay ref.csv -o result.png
    sf eskf params show --format yaml > default.yaml
"""

from .eskf import ESKF, ESKFConfig, ESKFState
from .loader import load_csv, detect_csv_format, LogData, SensorSample
from .metrics import compute_metrics, MetricsResult, TimeSeriesError

__all__ = [
    # ESKF core
    'ESKF',
    'ESKFConfig',
    'ESKFState',
    # Loader
    'load_csv',
    'detect_csv_format',
    'LogData',
    'SensorSample',
    # Metrics
    'compute_metrics',
    'MetricsResult',
    'TimeSeriesError',
]

__version__ = '0.1.0'
