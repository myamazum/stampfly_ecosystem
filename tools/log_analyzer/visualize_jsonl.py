#!/usr/bin/env python3
"""
visualize_jsonl.py - Quick overview dashboard for JSONL telemetry

JSONLines テレメトリデータの一覧ダッシュボード。
全センサデータを1画面のグリッドで素早く確認できる。

Usage:
    python visualize_jsonl.py <jsonl_file> [options]
    sf log viz <jsonl_file>

Options:
    --save PNG     Save to file instead of displaying
    --time-range START END  Plot only specified time range
"""

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

try:
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
except ImportError:
    print("Error: matplotlib required. Install: pip install matplotlib")
    sys.exit(1)


def load_jsonl(filepath: str, hide_invalid: bool = True) -> dict:
    """Load JSONL and return per-sensor numpy arrays with time axes.
    JSONL を読み込みセンサごとの numpy 配列と時間軸を返す。

    Args:
        hide_invalid: If True, replace invalid sensor values with NaN
                      (Flow quality=0, ToF status!=0). Default True.
                      無効センサ値を NaN に置換するか。デフォルト True。
    """
    sensor_data = {}  # {sensor_id: [(ts, {fields}), ...]}

    with open(filepath) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            sid = obj.get('id', '')
            ts = obj.get('ts', 0)
            if sid not in sensor_data:
                sensor_data[sid] = []
            sensor_data[sid].append((ts, obj))

    # Find t0 from IMU
    t0 = 0
    if 'imu' in sensor_data and sensor_data['imu']:
        t0 = sensor_data['imu'][0][0]

    result = {}

    # IMU
    if 'imu' in sensor_data:
        d = sensor_data['imu']
        result['imu_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['gyro'] = np.array([o['gyro'] for _, o in d])
        result['accel'] = np.array([o['accel'] for _, o in d])
        result['gyro_raw'] = np.array([o['gyro_raw'] for _, o in d])
        result['accel_raw'] = np.array([o['accel_raw'] for _, o in d])
        result['quat'] = np.array([o['quat'] for _, o in d])
        result['gyro_bias'] = np.array([o['gyro_bias'] for _, o in d])
        result['accel_bias'] = np.array([o['accel_bias'] for _, o in d])

        # Compute corrected = raw_lpf - bias
        result['gyro_corr'] = result['gyro'] - result['gyro_bias']
        result['accel_corr'] = result['accel'] - result['accel_bias']

        # Compute Euler from quaternion
        q = result['quat']
        roll, pitch, yaw = [], [], []
        for i in range(len(q)):
            w, x, y, z = q[i]
            roll.append(math.degrees(math.atan2(2*(w*x+y*z), 1-2*(x*x+y*y))))
            pitch.append(math.degrees(math.asin(max(-1, min(1, 2*(w*y-z*x))))))
            yaw.append(math.degrees(math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))))
        result['euler'] = np.array([roll, pitch, yaw]).T

    # PosVel
    if 'posvel' in sensor_data:
        d = sensor_data['posvel']
        result['posvel_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['pos'] = np.array([o['pos'] for _, o in d])
        result['vel'] = np.array([o['vel'] for _, o in d])

    # Control
    if 'ctrl' in sensor_data:
        d = sensor_data['ctrl']
        result['ctrl_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['ctrl'] = np.array([[o['throttle'], o['roll'], o['pitch'], o['yaw']] for _, o in d])

    # Flow
    if 'flow' in sensor_data:
        d = sensor_data['flow']
        result['flow_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['flow'] = np.array([[o['dx'], o['dy']] for _, o in d], dtype=float)
        result['flow_q'] = np.array([o['quality'] for _, o in d])

        # Mask invalid flow data (quality=0) with NaN
        # 無効フローデータ（quality=0）を NaN でマスク
        if hide_invalid:
            invalid = result['flow_q'] == 0
            result['flow'][invalid] = np.nan

    # ToF Bottom
    if 'tof_b' in sensor_data:
        d = sensor_data['tof_b']
        result['tof_b_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['tof_bottom'] = np.array([o['distance'] for _, o in d], dtype=float)
        result['tof_bottom_status'] = np.array([o['status'] for _, o in d])
        if hide_invalid:
            invalid = result['tof_bottom_status'] != 0
            result['tof_bottom'][invalid] = np.nan

    # ToF Front
    if 'tof_f' in sensor_data:
        d = sensor_data['tof_f']
        result['tof_f_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['tof_front'] = np.array([o['distance'] for _, o in d], dtype=float)
        result['tof_front_status'] = np.array([o['status'] for _, o in d])
        if hide_invalid:
            invalid = result['tof_front_status'] != 0
            result['tof_front'][invalid] = np.nan

    # Baro
    if 'baro' in sensor_data:
        d = sensor_data['baro']
        result['baro_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['baro_alt'] = np.array([o['altitude'] for _, o in d])
        result['baro_press'] = np.array([o['pressure'] for _, o in d])

    # Mag
    if 'mag' in sensor_data:
        d = sensor_data['mag']
        result['mag_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['mag'] = np.array([[o['x'], o['y'], o['z']] for _, o in d])

    # Control loop references (angle_ref: 50Hz, rate_ref: 400Hz)
    if 'ctrl_ref' in sensor_data:
        d = sensor_data['ctrl_ref']
        result['ctrl_ref_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['angle_ref'] = np.array([o['angle_ref'] for _, o in d])   # [roll, pitch] rad
        result['flight_mode'] = np.array([o['mode'] for _, o in d])

    if 'rate_ref' in sensor_data:
        d = sensor_data['rate_ref']
        result['rate_ref_t'] = np.array([(ts - t0) / 1e6 for ts, _ in d])
        result['rate_ref'] = np.array([o['rate_ref'] for _, o in d])     # [roll, pitch, yaw] rad/s

    return result


def plot_overview(data: dict, title: str = '', save: str = None,
                  time_range: tuple = None):
    """Plot all sensor data in a grid overview.
    全センサデータをグリッドで一覧表示。
    """
    fig = plt.figure(figsize=(18, 17))
    fig.suptitle(title or 'StampFly Telemetry Overview', fontsize=14, fontweight='bold')

    # 4 columns × 5 rows = 20 panels max
    gs = GridSpec(5, 4, figure=fig, hspace=0.4, wspace=0.3)

    def make_ax(row, col, colspan=1, rowspan=1):
        ax = fig.add_subplot(gs[row:row+rowspan, col:col+colspan])
        if time_range:
            ax.set_xlim(time_range)
        return ax

    def plot_xyz(ax, t, d, labels, title, unit=''):
        colors = ['#e6194b', '#3cb44b', '#4363d8']
        for i, (lbl, c) in enumerate(zip(labels, colors)):
            ax.plot(t, d[:, i], c, linewidth=0.5, label=lbl)
        ax.set_title(title, fontsize=9, fontweight='bold')
        if unit:
            ax.set_ylabel(unit, fontsize=8)
        ax.legend(fontsize=7, loc='upper right', ncol=3)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)

    # Row 0: Attitude, Position, Velocity, Control
    if 'euler' in data:
        ax = make_ax(0, 0)
        plot_xyz(ax, data['imu_t'], data['euler'],
                 ['Roll', 'Pitch', 'Yaw'], 'Attitude (ESKF)', 'deg')

    if 'pos' in data:
        ax = make_ax(0, 1)
        plot_xyz(ax, data['posvel_t'], data['pos'],
                 ['North', 'East', 'Down'], 'Position (ESKF)', 'm')

    if 'vel' in data:
        ax = make_ax(0, 2)
        plot_xyz(ax, data['posvel_t'], data['vel'],
                 ['Vn', 'Ve', 'Vd'], 'Velocity (ESKF)', 'm/s')

    if 'ctrl' in data:
        ax = make_ax(0, 3)
        t = data['ctrl_t']
        ax.plot(t, data['ctrl'][:, 0], '#e6194b', linewidth=0.5, label='Throttle')
        ax.plot(t, data['ctrl'][:, 1], '#3cb44b', linewidth=0.5, label='Roll')
        ax.plot(t, data['ctrl'][:, 2], '#4363d8', linewidth=0.5, label='Pitch')
        ax.plot(t, data['ctrl'][:, 3], '#f58231', linewidth=0.5, label='Yaw')
        ax.set_title('Control Input', fontsize=9, fontweight='bold')
        ax.legend(fontsize=7, loc='upper right', ncol=2)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)

    # Row 1: Gyro corrected, Accel corrected, Gyro bias, Accel bias
    if 'gyro_corr' in data:
        ax = make_ax(1, 0)
        plot_xyz(ax, data['imu_t'], data['gyro_corr'],
                 ['X', 'Y', 'Z'], 'Gyro Corrected', 'rad/s')

    if 'accel_corr' in data:
        ax = make_ax(1, 1)
        plot_xyz(ax, data['imu_t'], data['accel_corr'],
                 ['X', 'Y', 'Z'], 'Accel Corrected', 'm/s²')

    if 'gyro_bias' in data:
        ax = make_ax(1, 2)
        plot_xyz(ax, data['imu_t'], data['gyro_bias'],
                 ['X', 'Y', 'Z'], 'Gyro Bias', 'rad/s')

    if 'accel_bias' in data:
        ax = make_ax(1, 3)
        plot_xyz(ax, data['imu_t'], data['accel_bias'],
                 ['X', 'Y', 'Z'], 'Accel Bias', 'm/s²')

    # Row 2: Gyro raw, Accel raw, ToF + Baro, Mag
    if 'gyro' in data:
        ax = make_ax(2, 0)
        plot_xyz(ax, data['imu_t'], data['gyro'],
                 ['X', 'Y', 'Z'], 'Gyro (LPF)', 'rad/s')

    if 'accel' in data:
        ax = make_ax(2, 1)
        plot_xyz(ax, data['imu_t'], data['accel'],
                 ['X', 'Y', 'Z'], 'Accel (LPF)', 'm/s²')

    # ToF + Baro combined
    ax = make_ax(2, 2)
    if 'tof_bottom' in data:
        ax.plot(data['tof_b_t'], data['tof_bottom'], '#e6194b', linewidth=0.5, label='ToF Bot')
    if 'tof_front' in data:
        ax.plot(data['tof_f_t'], data['tof_front'], '#f58231', linewidth=0.5, label='ToF Frt')
    if 'baro_alt' in data:
        ax.plot(data['baro_t'], data['baro_alt'], '#4363d8', linewidth=0.5, label='Baro')
    ax.set_title('Height', fontsize=9, fontweight='bold')
    ax.set_ylabel('m', fontsize=8)
    ax.legend(fontsize=7)
    ax.tick_params(labelsize=7)
    ax.grid(True, alpha=0.3)
    if time_range:
        ax.set_xlim(time_range)

    if 'mag' in data:
        ax = make_ax(2, 3)
        plot_xyz(ax, data['mag_t'], data['mag'],
                 ['X', 'Y', 'Z'], 'Magnetometer', 'μT')

    # Row 3: Flow, Flow quality, Gyro raw (pre-LPF), Accel raw (pre-LPF)
    if 'flow' in data:
        ax = make_ax(3, 0)
        t = data['flow_t']
        ax.plot(t, data['flow'][:, 0], '#e6194b', linewidth=0.5, label='dx')
        ax.plot(t, data['flow'][:, 1], '#3cb44b', linewidth=0.5, label='dy')
        ax.set_title('Optical Flow', fontsize=9, fontweight='bold')
        ax.legend(fontsize=7)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
        if time_range:
            ax.set_xlim(time_range)

    if 'flow_q' in data:
        ax = make_ax(3, 1)
        ax.plot(data['flow_t'], data['flow_q'], '#911eb4', linewidth=0.5)
        ax.set_title('Flow Quality', fontsize=9, fontweight='bold')
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
        if time_range:
            ax.set_xlim(time_range)

    if 'gyro_raw' in data:
        ax = make_ax(3, 2)
        plot_xyz(ax, data['imu_t'], data['gyro_raw'],
                 ['X', 'Y', 'Z'], 'Gyro (Raw)', 'rad/s')

    if 'accel_raw' in data:
        ax = make_ax(3, 3)
        plot_xyz(ax, data['imu_t'], data['accel_raw'],
                 ['X', 'Y', 'Z'], 'Accel (Raw)', 'm/s²')

    # Row 4: Control loop references (Target vs Actual)
    if 'angle_ref' in data:
        # (4,0) Attitude: Target vs Actual
        ax = make_ax(4, 0)
        t_ref = data['ctrl_ref_t']
        angle_ref_deg = np.degrees(data['angle_ref'])  # rad -> deg
        ax.plot(t_ref, angle_ref_deg[:, 0], '#e6194b', linewidth=1.0,
                linestyle='--', label='Roll ref')
        ax.plot(t_ref, angle_ref_deg[:, 1], '#4363d8', linewidth=1.0,
                linestyle='--', label='Pitch ref')
        if 'euler' in data:
            ax.plot(data['imu_t'], data['euler'][:, 0], '#e6194b',
                    linewidth=0.5, alpha=0.6, label='Roll act')
            ax.plot(data['imu_t'], data['euler'][:, 1], '#4363d8',
                    linewidth=0.5, alpha=0.6, label='Pitch act')
        ax.set_title('Attitude: Target vs Actual', fontsize=9, fontweight='bold')
        ax.set_ylabel('deg', fontsize=8)
        ax.legend(fontsize=7, loc='upper right', ncol=2)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)

    if 'rate_ref' in data:
        # (4,1) Rate: Target vs Actual (both at 400Hz)
        ax = make_ax(4, 1)
        t_ref = data['rate_ref_t']
        ax.plot(t_ref, data['rate_ref'][:, 0], '#e6194b', linewidth=0.8,
                linestyle='--', label='Roll ref')
        ax.plot(t_ref, data['rate_ref'][:, 1], '#4363d8', linewidth=0.8,
                linestyle='--', label='Pitch ref')
        ax.plot(t_ref, data['rate_ref'][:, 2], '#f58231', linewidth=0.8,
                linestyle='--', label='Yaw ref')
        if 'gyro_corr' in data:
            ax.plot(data['imu_t'], data['gyro_corr'][:, 0], '#e6194b',
                    linewidth=0.5, alpha=0.5, label='Roll act')
            ax.plot(data['imu_t'], data['gyro_corr'][:, 1], '#4363d8',
                    linewidth=0.5, alpha=0.5, label='Pitch act')
            ax.plot(data['imu_t'], data['gyro_corr'][:, 2], '#f58231',
                    linewidth=0.5, alpha=0.5, label='Yaw act')
        ax.set_title('Rate: Target vs Actual (400Hz)', fontsize=9, fontweight='bold')
        ax.set_ylabel('rad/s', fontsize=8)
        ax.legend(fontsize=7, loc='upper right', ncol=2)
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)

    if 'flight_mode' in data:
        # (4,2) Flight Mode
        ax = make_ax(4, 2)
        t_ref = data['ctrl_ref_t']
        mode_names = {0: 'ACRO', 1: 'STAB', 2: 'ALT', 3: 'POS'}
        ax.step(t_ref, data['flight_mode'], '#911eb4', linewidth=1.0, where='post')
        ax.set_yticks([0, 1, 2, 3])
        ax.set_yticklabels([mode_names.get(i, str(i)) for i in range(4)])
        ax.set_title('Flight Mode', fontsize=9, fontweight='bold')
        ax.tick_params(labelsize=7)
        ax.grid(True, alpha=0.3)
        ax.set_ylim(-0.5, 3.5)

    # Add time label to bottom row
    for ax in fig.get_axes():
        ax.set_xlabel('Time [s]', fontsize=7)

    if save:
        plt.savefig(save, dpi=150, bbox_inches='tight')
        print(f"Saved: {save}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="JSONL telemetry overview")
    parser.add_argument('file', help="JSONL telemetry file")
    parser.add_argument('--save', help="Save to PNG file")
    parser.add_argument('--time-range', nargs=2, type=float, metavar=('START', 'END'))
    parser.add_argument('--show-invalid', action='store_true',
                        help="Show invalid sensor data (default: hidden as gaps)")
    args = parser.parse_args()

    print(f"Loading: {args.file}")
    data = load_jsonl(args.file, hide_invalid=not args.show_invalid)

    n_imu = len(data.get('imu_t', []))
    dur = data['imu_t'][-1] if n_imu > 0 else 0
    print(f"IMU: {n_imu} samples, {dur:.1f}s")

    tr = tuple(args.time_range) if args.time_range else None
    plot_overview(data, title=Path(args.file).name, save=args.save, time_range=tr)


if __name__ == '__main__':
    main()
