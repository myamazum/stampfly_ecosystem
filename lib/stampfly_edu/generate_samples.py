"""
Generate synthetic sample datasets for education
教育用の合成サンプルデータセットを生成

Generates realistic-looking flight data based on StampFly physical parameters
so that notebooks work without a real drone.

Usage:
    python -m stampfly_edu.generate_samples
"""

from pathlib import Path

import numpy as np
import pandas as pd


# Output directory
# 出力ディレクトリ
OUTPUT_DIR = Path(__file__).parent.parent.parent / "analysis" / "datasets" / "education"

# StampFly parameters (from tools/sysid/defaults.py)
# StampFly パラメータ
GYRO_NOISE = 1.22e-4      # rad/s/√Hz
ACCEL_NOISE = 1.18e-3      # m/s²/√Hz
BARO_NOISE = 0.11          # m
TOF_NOISE = 0.01           # m
SAMPLE_RATE = 400           # Hz (telemetry rate)
DT = 1.0 / SAMPLE_RATE


def generate_static_noise(duration: float = 60.0) -> pd.DataFrame:
    """Generate 60s of stationary sensor noise data.

    60 秒間の静止センサノイズデータを生成する。
    """
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) * DT

    # Gyroscope noise + slow bias drift
    # ジャイロノイズ + 低速バイアスドリフト
    gyro_sigma = GYRO_NOISE * np.sqrt(SAMPLE_RATE)
    bias_drift = 1.75e-3  # rad/s bias instability

    rng = np.random.default_rng(42)
    gx = rng.normal(0, gyro_sigma, n) + bias_drift * np.sin(2 * np.pi * 0.01 * t)
    gy = rng.normal(0, gyro_sigma, n) + bias_drift * np.cos(2 * np.pi * 0.008 * t)
    gz = rng.normal(0, gyro_sigma, n) + bias_drift * np.sin(2 * np.pi * 0.012 * t)

    # Accelerometer noise (gravity on z-axis)
    # 加速度計ノイズ（z 軸に重力）
    accel_sigma = ACCEL_NOISE * np.sqrt(SAMPLE_RATE)
    ax = rng.normal(0, accel_sigma, n)
    ay = rng.normal(0, accel_sigma, n)
    az = rng.normal(-9.80665, accel_sigma, n)

    # Barometer and ToF
    # 気圧計と ToF
    baro = rng.normal(0, BARO_NOISE, n)
    tof = rng.normal(0, TOF_NOISE, n)

    return pd.DataFrame({
        "time": t,
        "gyro_x": gx,
        "gyro_y": gy,
        "gyro_z": gz,
        "accel_x": ax,
        "accel_y": ay,
        "accel_z": az,
        "baro_alt": baro,
        "tof_range": tof,
    })


def generate_rate_step_response() -> pd.DataFrame:
    """Generate a rate PID step response (roll axis).

    レート PID ステップ応答を生成する（ロール軸）。
    """
    # Simulate 1st-order system with PID
    # PID 付き 1 次系をシミュレート
    duration = 3.0
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) * DT

    # Step input: 0 for first 0.5s, then 1.0 rad/s
    # ステップ入力: 最初 0.5 秒は 0、その後 1.0 rad/s
    setpoint = np.zeros(n)
    setpoint[int(0.5 * SAMPLE_RATE):] = 1.0

    # Simulate second-order response (typical PID tuned system)
    # 2 次応答をシミュレート（典型的な PID 調整済みシステム）
    wn = 25.0   # Natural frequency (rad/s)
    zeta = 0.7  # Damping ratio
    response = np.zeros(n)

    for i in range(1, n):
        if setpoint[i] > 0:
            t_step = (i - int(0.5 * SAMPLE_RATE)) * DT
            if t_step >= 0:
                wd = wn * np.sqrt(1 - zeta**2)
                envelope = np.exp(-zeta * wn * t_step)
                phi = np.arctan2(np.sqrt(1 - zeta**2), zeta)
                response[i] = setpoint[i] * (
                    1 - envelope * np.sin(wd * t_step + phi) / np.sqrt(1 - zeta**2)
                )

    rng = np.random.default_rng(123)
    noise = rng.normal(0, GYRO_NOISE * np.sqrt(SAMPLE_RATE), n)
    measured = response + noise

    return pd.DataFrame({
        "time": t,
        "setpoint": setpoint,
        "roll_rate": measured,
        "roll_rate_clean": response,
        "motor_1": 0.5 + 0.1 * response,
        "motor_2": 0.5 - 0.1 * response,
        "motor_3": 0.5 - 0.1 * response,
        "motor_4": 0.5 + 0.1 * response,
    })


def generate_hover(duration: float = 30.0) -> pd.DataFrame:
    """Generate 30s hover flight data.

    30 秒ホバリングデータを生成する。
    """
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) * DT

    rng = np.random.default_rng(456)

    # Position with small drift
    # 小さなドリフト付きの位置
    x = np.cumsum(rng.normal(0, 0.0001, n))
    y = np.cumsum(rng.normal(0, 0.0001, n))
    z = 0.5 + rng.normal(0, 0.005, n)  # Hover at 0.5m

    # Attitude oscillation (small)
    # 小さな姿勢振動
    roll = rng.normal(0, 0.5, n)   # degrees
    pitch = rng.normal(0, 0.5, n)
    yaw = np.cumsum(rng.normal(0, 0.01, n))

    # Angular rates
    # 角速度
    p = rng.normal(0, 0.02, n)  # rad/s
    q = rng.normal(0, 0.02, n)
    r = rng.normal(0, 0.01, n)

    # Motors near hover thrust
    # ホバー推力付近のモーター
    hover_duty = 0.55
    m1 = hover_duty + rng.normal(0, 0.02, n)
    m2 = hover_duty + rng.normal(0, 0.02, n)
    m3 = hover_duty + rng.normal(0, 0.02, n)
    m4 = hover_duty + rng.normal(0, 0.02, n)

    return pd.DataFrame({
        "time": t,
        "x": x, "y": y, "z": z,
        "roll": roll, "pitch": pitch, "yaw": yaw,
        "p": p, "q": q, "r": r,
        "motor_1": m1, "motor_2": m2, "motor_3": m3, "motor_4": m4,
        "battery_voltage": 3.7 - 0.3 * t / duration,
    })


def generate_altitude_step() -> pd.DataFrame:
    """Generate altitude step response (0.3m -> 0.6m).

    高度ステップ応答を生成する（0.3m → 0.6m）。
    """
    duration = 10.0
    n = int(duration * SAMPLE_RATE)
    t = np.arange(n) * DT

    setpoint = np.full(n, 0.3)
    setpoint[int(2.0 * SAMPLE_RATE):] = 0.6

    # Simulate altitude response (overdamped with FF)
    # 高度応答をシミュレート（FF 付き過減衰）
    z = np.zeros(n)
    z[0] = 0.3
    wn = 5.0
    zeta = 0.9

    for i in range(1, n):
        t_step = (i - int(2.0 * SAMPLE_RATE)) * DT
        if i < int(2.0 * SAMPLE_RATE):
            z[i] = 0.3
        elif t_step >= 0:
            step_size = 0.3
            wd = wn * np.sqrt(max(1 - zeta**2, 0.01))
            envelope = np.exp(-zeta * wn * t_step)
            if zeta < 1.0:
                phi = np.arctan2(np.sqrt(1 - zeta**2), zeta)
                z[i] = 0.3 + step_size * (
                    1 - envelope * np.sin(wd * t_step + phi) / np.sqrt(1 - zeta**2)
                )
            else:
                z[i] = 0.3 + step_size * (1 - envelope * (1 + wn * t_step))

    rng = np.random.default_rng(789)
    noise = rng.normal(0, 0.005, n)

    return pd.DataFrame({
        "time": t,
        "setpoint": setpoint,
        "z": z + noise,
        "z_clean": z,
        "vz": np.gradient(z, DT),
        "tof_range": z + rng.normal(0, TOF_NOISE, n),
        "baro_alt": z + rng.normal(0, BARO_NOISE, n),
    })


def generate_square_path() -> pd.DataFrame:
    """Generate square path flight data (1m x 1m).

    矩形パス飛行データを生成する（1m x 1m）。
    """
    # Build waypoints: takeoff -> square -> land
    # ウェイポイント構築: 離陸 → 矩形 → 着陸
    speed = 0.3  # m/s
    side = 1.0   # m

    segments = [
        # (dx, dy, dz, description)
        (0, 0, 0.5, "takeoff"),       # Hover at 0.5m
        (side, 0, 0, "forward"),      # Forward 1m
        (0, side, 0, "left"),         # Left 1m
        (-side, 0, 0, "backward"),    # Backward 1m
        (0, -side, 0, "right"),       # Right 1m
        (0, 0, -0.5, "land"),         # Land
    ]

    all_t, all_x, all_y, all_z = [], [], [], []
    cx, cy, cz = 0.0, 0.0, 0.0
    ct = 0.0

    rng = np.random.default_rng(101)

    for dx, dy, dz, desc in segments:
        dist = np.sqrt(dx**2 + dy**2 + dz**2)
        seg_time = dist / speed if dist > 0 else 1.0
        n_pts = int(seg_time * SAMPLE_RATE)
        if n_pts < 10:
            n_pts = 10

        t_seg = np.linspace(0, seg_time, n_pts, endpoint=False)
        frac = t_seg / seg_time

        # Smooth trajectory (S-curve)
        # 滑らかな軌跡（S カーブ）
        smooth_frac = 3 * frac**2 - 2 * frac**3

        x_seg = cx + dx * smooth_frac + rng.normal(0, 0.005, n_pts)
        y_seg = cy + dy * smooth_frac + rng.normal(0, 0.005, n_pts)
        z_seg = cz + dz * smooth_frac + rng.normal(0, 0.003, n_pts)

        all_t.extend((ct + t_seg).tolist())
        all_x.extend(x_seg.tolist())
        all_y.extend(y_seg.tolist())
        all_z.extend(z_seg.tolist())

        cx += dx
        cy += dy
        cz += dz
        ct += seg_time

    # Downsample to 50 Hz for position data (typical GPS-like rate)
    # 位置データを 50Hz にダウンサンプリング
    ds_factor = SAMPLE_RATE // 50
    indices = list(range(0, len(all_t), ds_factor))

    return pd.DataFrame({
        "time": [all_t[i] for i in indices],
        "x": [all_x[i] for i in indices],
        "y": [all_y[i] for i in indices],
        "z": [all_z[i] for i in indices],
    })


def main():
    """Generate all sample datasets.

    全サンプルデータセットを生成する。
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {
        "static_noise_60s.csv": generate_static_noise,
        "rate_step_response.csv": generate_rate_step_response,
        "hover_30s.csv": generate_hover,
        "altitude_step.csv": generate_altitude_step,
        "square_path.csv": generate_square_path,
    }

    for filename, generator in datasets.items():
        path = OUTPUT_DIR / filename
        df = generator()
        df.to_csv(path, index=False, float_format="%.6f")
        print(f"Generated {path} ({len(df)} rows, {len(df.columns)} columns)")

    print(f"\nAll datasets saved to {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
