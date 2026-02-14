"""
Flight log loading and processing utilities
フライトログの読み込みと処理ユーティリティ

Provides standardized CSV loading with column name normalization
for educational use.
"""

from pathlib import Path
from typing import Optional, Union

import numpy as np
import pandas as pd


# Standard column name mapping for education use
# 教育用の標準列名マッピング
_COLUMN_ALIASES = {
    # Time / 時間
    "timestamp": "time",
    "time_ms": "time",
    "t": "time",
    # Position / 位置
    "pos_x": "x",
    "pos_y": "y",
    "pos_z": "z",
    "position_x": "x",
    "position_y": "y",
    "position_z": "z",
    # Velocity / 速度
    "vel_x": "vx",
    "vel_y": "vy",
    "vel_z": "vz",
    "velocity_x": "vx",
    "velocity_y": "vy",
    "velocity_z": "vz",
    # Attitude / 姿勢
    "roll_deg": "roll",
    "pitch_deg": "pitch",
    "yaw_deg": "yaw",
    # Angular rate / 角速度
    "gyro_x": "p",
    "gyro_y": "q",
    "gyro_z": "r",
    "roll_rate": "p",
    "pitch_rate": "q",
    "yaw_rate": "r",
    # Acceleration / 加速度
    "acc_x": "ax",
    "acc_y": "ay",
    "acc_z": "az",
    "accel_x": "ax",
    "accel_y": "ay",
    "accel_z": "az",
    # Altitude sensors / 高度センサ
    "altitude": "alt",
    "baro_alt": "baro",
    "tof_range": "tof",
    # Motor / モーター
    "motor_1": "m1",
    "motor_2": "m2",
    "motor_3": "m3",
    "motor_4": "m4",
    # Battery / バッテリー
    "battery_voltage": "vbat",
    "bat_v": "vbat",
}

# Education sample dataset directory
# 教育用サンプルデータセットのディレクトリ
_DATASETS_DIR = Path(__file__).parent.parent.parent / "analysis" / "datasets" / "education"


def load_flight_log(
    path: Union[str, Path],
    normalize_columns: bool = True,
    time_zero: bool = True,
) -> pd.DataFrame:
    """Load a CSV flight log as a pandas DataFrame.

    CSV フライトログを pandas DataFrame として読み込む。

    Args:
        path: Path to CSV file / CSV ファイルのパス
        normalize_columns: Apply column name aliases / 列名エイリアスを適用
        time_zero: Shift time column to start from 0 / 時間列を 0 開始にシフト

    Returns:
        DataFrame with normalized column names

    Usage:
        >>> import tempfile, os
        >>> f = tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False)
        >>> _ = f.write("time,pos_x,pos_y\\n0.0,1.0,2.0\\n0.1,1.1,2.1\\n")
        >>> f.close()
        >>> df = load_flight_log(f.name)
        >>> list(df.columns)
        ['time', 'x', 'y']
        >>> os.unlink(f.name)
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Log file not found: {path}")

    df = pd.read_csv(path)

    if normalize_columns:
        # Apply column aliases (lowercase first)
        # 列エイリアスを適用（まず小文字化）
        df.columns = [c.strip().lower() for c in df.columns]
        df.rename(columns=_COLUMN_ALIASES, inplace=True)

    if time_zero and "time" in df.columns:
        df["time"] = df["time"] - df["time"].iloc[0]

    return df


def load_sample_data(name: str) -> pd.DataFrame:
    """Load a bundled education sample dataset.

    バンドルされた教育用サンプルデータセットを読み込む。

    Available datasets / 利用可能なデータセット:
        - "static_noise": 60s stationary sensor noise / 静止センサノイズ
        - "rate_step": Rate PID step response / レート PID ステップ応答
        - "hover": 30s hover flight / 30 秒ホバリング
        - "altitude_step": Altitude step response / 高度ステップ応答
        - "square_path": Square path flight / 矩形パス飛行

    Args:
        name: Dataset name (without extension) / データセット名（拡張子なし）

    Returns:
        DataFrame with normalized column names

    Usage:
        >>> df = load_sample_data("hover")
        >>> "time" in df.columns
        True
    """
    # Map short names to filenames
    # 短縮名をファイル名にマッピング
    name_map = {
        "static_noise": "static_noise_60s.csv",
        "rate_step": "rate_step_response.csv",
        "hover": "hover_30s.csv",
        "altitude_step": "altitude_step.csv",
        "square_path": "square_path.csv",
    }

    filename = name_map.get(name)
    if filename is None:
        available = ", ".join(sorted(name_map.keys()))
        raise ValueError(
            f"Unknown dataset '{name}'. Available: {available}"
        )

    path = _DATASETS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(
            f"Sample data not found: {path}\n"
            f"Run 'python -m stampfly_edu.generate_samples' to create sample data."
        )

    return load_flight_log(path)
