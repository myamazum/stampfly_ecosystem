"""
ESKF Log Data Loader
ESKFログデータローダー

Loads and parses CSV log files from StampFly telemetry.
Supports multiple formats: extended (400Hz), normal, FFT batch.
"""

import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Iterator, Any

import numpy as np


@dataclass
class SensorSample:
    """Single sensor sample from log
    ログの単一センササンプル
    """
    timestamp_us: int           # Timestamp [us]

    # IMU data (required)
    gyro: np.ndarray            # [rad/s] body frame
    accel: np.ndarray           # [m/s^2] body frame

    # Gyro corrected (optional, for comparison)
    gyro_corrected: Optional[np.ndarray] = None

    # ESKF state from log (optional, for comparison)
    eskf_quat: Optional[np.ndarray] = None      # [w, x, y, z]
    eskf_position: Optional[np.ndarray] = None  # [m] NED
    eskf_velocity: Optional[np.ndarray] = None  # [m/s]
    eskf_gyro_bias: Optional[np.ndarray] = None # [rad/s]
    eskf_accel_bias: Optional[np.ndarray] = None # [m/s^2]

    # Altitude sensors (optional)
    baro_altitude: Optional[float] = None       # [m]
    tof_distance: Optional[float] = None        # [m] bottom ToF

    # Optical flow (optional)
    flow_dx: Optional[int] = None               # [counts]
    flow_dy: Optional[int] = None               # [counts]
    flow_quality: Optional[int] = None

    # Controller inputs (optional)
    ctrl_throttle: Optional[float] = None
    ctrl_roll: Optional[float] = None
    ctrl_pitch: Optional[float] = None
    ctrl_yaw: Optional[float] = None


@dataclass
class LogData:
    """Complete log data
    ログデータ全体
    """
    samples: List[SensorSample]
    format: str                 # 'extended', 'normal', 'fft_batch', 'unknown'
    columns: List[str]          # Original CSV columns
    sample_rate_hz: float       # Estimated sample rate
    duration_s: float           # Total duration

    def __len__(self) -> int:
        return len(self.samples)

    def __iter__(self) -> Iterator[SensorSample]:
        return iter(self.samples)

    @property
    def timestamps(self) -> np.ndarray:
        """Get all timestamps as numpy array [s]"""
        return np.array([s.timestamp_us for s in self.samples]) / 1e6

    @property
    def gyro(self) -> np.ndarray:
        """Get all gyro readings as Nx3 array [rad/s]"""
        return np.array([s.gyro for s in self.samples])

    @property
    def accel(self) -> np.ndarray:
        """Get all accel readings as Nx3 array [m/s^2]"""
        return np.array([s.accel for s in self.samples])

    def has_eskf(self) -> bool:
        """Check if ESKF state data is available"""
        return self.samples and self.samples[0].eskf_quat is not None

    def has_altitude_sensors(self) -> bool:
        """Check if altitude sensor data is available"""
        return self.samples and (
            self.samples[0].baro_altitude is not None or
            self.samples[0].tof_distance is not None
        )

    def has_flow(self) -> bool:
        """Check if optical flow data is available"""
        return self.samples and self.samples[0].flow_dx is not None


def detect_csv_format(columns: List[str]) -> str:
    """Detect CSV format from column names
    カラム名からCSVフォーマットを検出

    Returns:
        'extended': 400Hz telemetry with ESKF state
        'fft_batch': FFT batch telemetry
        'normal': Normal WiFi telemetry
        'unknown': Unknown format
    """
    if 'timestamp_us' in columns and 'quat_w' in columns:
        return 'extended'
    elif 'timestamp_ms' in columns and 'gyro_corrected_x' in columns:
        return 'fft_batch'
    elif 'timestamp_ms' in columns and 'roll_deg' in columns:
        return 'normal'
    return 'unknown'


def load_csv(filepath: str | Path) -> LogData:
    """Load CSV log file
    CSVログファイルを読み込み

    Args:
        filepath: Path to CSV file

    Returns:
        LogData object with parsed samples
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Log file not found: {filepath}")

    samples = []

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        fmt = detect_csv_format(columns)

        for row in reader:
            sample = _parse_row(row, fmt)
            if sample is not None:
                samples.append(sample)

    if not samples:
        raise ValueError(f"No valid samples in file: {filepath}")

    # Calculate metadata
    duration = (samples[-1].timestamp_us - samples[0].timestamp_us) / 1e6
    sample_rate = len(samples) / duration if duration > 0 else 0

    return LogData(
        samples=samples,
        format=fmt,
        columns=columns,
        sample_rate_hz=sample_rate,
        duration_s=duration,
    )


def _parse_row(row: Dict[str, str], fmt: str) -> Optional[SensorSample]:
    """Parse a single CSV row to SensorSample"""
    try:
        if fmt == 'extended':
            return _parse_extended_row(row)
        elif fmt == 'fft_batch':
            return _parse_fft_batch_row(row)
        elif fmt == 'normal':
            return _parse_normal_row(row)
        else:
            return _parse_generic_row(row)
    except (ValueError, KeyError) as e:
        return None


def _parse_extended_row(row: Dict[str, str]) -> SensorSample:
    """Parse extended format row (400Hz with ESKF)"""
    sample = SensorSample(
        timestamp_us=int(row['timestamp_us']),
        gyro=np.array([
            float(row['gyro_x']),
            float(row['gyro_y']),
            float(row['gyro_z']),
        ]),
        accel=np.array([
            float(row['accel_x']),
            float(row['accel_y']),
            float(row['accel_z']),
        ]),
    )

    # Gyro corrected
    if 'gyro_corrected_x' in row:
        sample.gyro_corrected = np.array([
            float(row['gyro_corrected_x']),
            float(row['gyro_corrected_y']),
            float(row['gyro_corrected_z']),
        ])

    # ESKF state
    if 'quat_w' in row:
        sample.eskf_quat = np.array([
            float(row['quat_w']),
            float(row['quat_x']),
            float(row['quat_y']),
            float(row['quat_z']),
        ])

    if 'pos_x' in row:
        sample.eskf_position = np.array([
            float(row['pos_x']),
            float(row['pos_y']),
            float(row['pos_z']),
        ])

    if 'vel_x' in row:
        sample.eskf_velocity = np.array([
            float(row['vel_x']),
            float(row['vel_y']),
            float(row['vel_z']),
        ])

    if 'gyro_bias_x' in row:
        sample.eskf_gyro_bias = np.array([
            float(row['gyro_bias_x']),
            float(row['gyro_bias_y']),
            float(row['gyro_bias_z']),
        ])

    if 'accel_bias_x' in row:
        sample.eskf_accel_bias = np.array([
            float(row['accel_bias_x']),
            float(row['accel_bias_y']),
            float(row['accel_bias_z']),
        ])

    # Altitude sensors
    if 'baro_altitude' in row:
        sample.baro_altitude = float(row['baro_altitude'])

    if 'tof_bottom' in row:
        sample.tof_distance = float(row['tof_bottom'])

    # Flow
    if 'flow_x' in row:
        sample.flow_dx = int(float(row['flow_x']))
    if 'flow_y' in row:
        sample.flow_dy = int(float(row['flow_y']))
    if 'flow_quality' in row:
        sample.flow_quality = int(float(row['flow_quality']))

    # Controller
    if 'ctrl_throttle' in row:
        sample.ctrl_throttle = float(row['ctrl_throttle'])
        sample.ctrl_roll = float(row['ctrl_roll'])
        sample.ctrl_pitch = float(row['ctrl_pitch'])
        sample.ctrl_yaw = float(row['ctrl_yaw'])

    return sample


def _parse_fft_batch_row(row: Dict[str, str]) -> SensorSample:
    """Parse FFT batch format row"""
    return SensorSample(
        timestamp_us=int(float(row['timestamp_ms']) * 1000),
        gyro=np.array([
            float(row['gyro_x']),
            float(row['gyro_y']),
            float(row['gyro_z']),
        ]),
        accel=np.array([
            float(row['accel_x']),
            float(row['accel_y']),
            float(row['accel_z']),
        ]),
        gyro_corrected=np.array([
            float(row.get('gyro_corrected_x', row['gyro_x'])),
            float(row.get('gyro_corrected_y', row['gyro_y'])),
            float(row.get('gyro_corrected_z', row['gyro_z'])),
        ]) if 'gyro_corrected_x' in row else None,
    )


def _parse_normal_row(row: Dict[str, str]) -> SensorSample:
    """Parse normal WiFi telemetry row"""
    return SensorSample(
        timestamp_us=int(float(row['timestamp_ms']) * 1000),
        gyro=np.array([
            float(row.get('gyro_x', 0)),
            float(row.get('gyro_y', 0)),
            float(row.get('gyro_z', 0)),
        ]),
        accel=np.array([
            float(row.get('accel_x', 0)),
            float(row.get('accel_y', 0)),
            float(row.get('accel_z', 0)),
        ]),
    )


def _parse_generic_row(row: Dict[str, str]) -> Optional[SensorSample]:
    """Try to parse generic row with common column patterns"""
    # Try to find timestamp
    timestamp_us = 0
    for key in ['timestamp_us', 'timestamp_ms', 'time_us', 'time_ms', 't']:
        if key in row:
            val = float(row[key])
            if 'ms' in key:
                val *= 1000
            timestamp_us = int(val)
            break

    if timestamp_us == 0:
        return None

    # Try to find gyro
    gyro = np.zeros(3)
    for i, suffix in enumerate(['x', 'y', 'z']):
        for prefix in ['gyro_', 'gyr_', 'w']:
            key = f'{prefix}{suffix}'
            if key in row:
                gyro[i] = float(row[key])
                break

    # Try to find accel
    accel = np.zeros(3)
    for i, suffix in enumerate(['x', 'y', 'z']):
        for prefix in ['accel_', 'acc_', 'a']:
            key = f'{prefix}{suffix}'
            if key in row:
                accel[i] = float(row[key])
                break

    return SensorSample(
        timestamp_us=timestamp_us,
        gyro=gyro,
        accel=accel,
    )


def load_jsonl(filepath: str | Path) -> Iterator[Dict[str, Any]]:
    """Load JSON Lines format file
    JSONLフォーマットファイルを読み込み

    Yields:
        Dictionary for each line
    """
    filepath = Path(filepath)
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def write_csv_header(file, columns: List[str]) -> None:
    """Write CSV header"""
    file.write(','.join(columns) + '\n')


def write_csv_row(file, values: Dict[str, Any], columns: List[str]) -> None:
    """Write CSV row"""
    row = [str(values.get(col, '')) for col in columns]
    file.write(','.join(row) + '\n')


# State output columns for ESKF replay
STATE_OUTPUT_COLUMNS = [
    'timestamp_us',
    'pos_x', 'pos_y', 'pos_z',
    'vel_x', 'vel_y', 'vel_z',
    'quat_w', 'quat_x', 'quat_y', 'quat_z',
    'roll_deg', 'pitch_deg', 'yaw_deg',
    'gyro_bias_x', 'gyro_bias_y', 'gyro_bias_z',
    'accel_bias_x', 'accel_bias_y', 'accel_bias_z',
]


def state_to_row(timestamp_us: int, state) -> Dict[str, Any]:
    """Convert ESKF state to CSV row dictionary

    Args:
        timestamp_us: Timestamp in microseconds
        state: ESKFState object

    Returns:
        Dictionary with column values
    """
    euler = state.euler
    return {
        'timestamp_us': timestamp_us,
        'pos_x': state.position[0],
        'pos_y': state.position[1],
        'pos_z': state.position[2],
        'vel_x': state.velocity[0],
        'vel_y': state.velocity[1],
        'vel_z': state.velocity[2],
        'quat_w': state.quat[0],
        'quat_x': state.quat[1],
        'quat_y': state.quat[2],
        'quat_z': state.quat[3],
        'roll_deg': np.rad2deg(euler[0]),
        'pitch_deg': np.rad2deg(euler[1]),
        'yaw_deg': np.rad2deg(euler[2]),
        'gyro_bias_x': state.gyro_bias[0],
        'gyro_bias_y': state.gyro_bias[1],
        'gyro_bias_z': state.gyro_bias[2],
        'accel_bias_x': state.accel_bias[0],
        'accel_bias_y': state.accel_bias[1],
        'accel_bias_z': state.accel_bias[2],
    }
