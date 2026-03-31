#!/usr/bin/env python3
"""
visualize_interactive.py - Interactive Telemetry Visualization Tool

Browser-based interactive visualization using Plotly.
Supports zoom, pan, signal toggle, and configurable tile layout.

ブラウザベースのインタラクティブ可視化ツール（Plotly使用）。
ズーム・パン・信号トグル・タイルレイアウト設定が可能。

Usage:
    python visualize_interactive.py <csv_file> [options]

    # Default layout (auto)
    python visualize_interactive.py flight.csv

    # Custom layout: 3 rows x 2 columns
    python visualize_interactive.py flight.csv --layout 3x2

    # Select specific signal groups
    python visualize_interactive.py flight.csv --groups gyro attitude bias_gyro

    # Save to HTML file
    python visualize_interactive.py flight.csv -o dashboard.html

Available signal groups:
    gyro          Raw gyro [rad/s]
    accel         Raw accel [m/s²]
    gyro_corr     Bias-corrected gyro [rad/s]
    attitude      Roll/Pitch/Yaw [deg]
    position      Position NED [m]
    velocity      Velocity NED [m/s]
    bias_gyro     Gyro bias [rad/s]
    bias_accel    Accel bias [m/s²]
    control       Controller inputs
    height        Baro altitude / ToF [m]
    flow          Optical flow [counts]
"""

import argparse
import csv
import math
import sys
import webbrowser
import tempfile
from pathlib import Path

import numpy as np

try:
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
except ImportError:
    print("Error: plotly is required. Install with: pip install plotly")
    sys.exit(1)


# =============================================================================
# Signal group definitions
# 信号グループ定義
# =============================================================================

SIGNAL_GROUPS = {
    'gyro': {
        'title': 'Raw Gyro [rad/s]',
        'signals': [
            ('gyro_x', 'X', 'red'),
            ('gyro_y', 'Y', 'green'),
            ('gyro_z', 'Z', 'blue'),
        ],
    },
    'accel': {
        'title': 'Raw Accel [m/s²]',
        'signals': [
            ('accel_x', 'X', 'red'),
            ('accel_y', 'Y', 'green'),
            ('accel_z', 'Z', 'blue'),
        ],
    },
    'gyro_corr': {
        'title': 'Corrected Gyro [rad/s]',
        'signals': [
            ('gyro_corrected_x', 'X', 'red'),
            ('gyro_corrected_y', 'Y', 'green'),
            ('gyro_corrected_z', 'Z', 'blue'),
        ],
    },
    'attitude': {
        'title': 'Attitude [deg]',
        'signals': [],  # Computed from quaternion
        'computed': True,
    },
    'position': {
        'title': 'Position NED [m]',
        'signals': [
            ('pos_x', 'North', 'red'),
            ('pos_y', 'East', 'green'),
            ('pos_z', 'Down', 'blue'),
        ],
    },
    'velocity': {
        'title': 'Velocity NED [m/s]',
        'signals': [
            ('vel_x', 'North', 'red'),
            ('vel_y', 'East', 'green'),
            ('vel_z', 'Down', 'blue'),
        ],
    },
    'bias_gyro': {
        'title': 'Gyro Bias [rad/s]',
        'signals': [
            ('gyro_bias_x', 'X', 'red'),
            ('gyro_bias_y', 'Y', 'green'),
            ('gyro_bias_z', 'Z', 'blue'),
        ],
    },
    'bias_accel': {
        'title': 'Accel Bias [m/s²]',
        'signals': [
            ('accel_bias_x', 'X', 'red'),
            ('accel_bias_y', 'Y', 'green'),
            ('accel_bias_z', 'Z', 'blue'),
        ],
    },
    'control': {
        'title': 'Control Inputs',
        'signals': [
            ('ctrl_throttle', 'Throttle', 'orange'),
            ('ctrl_roll', 'Roll', 'red'),
            ('ctrl_pitch', 'Pitch', 'green'),
            ('ctrl_yaw', 'Yaw', 'blue'),
        ],
    },
    'height': {
        'title': 'Height [m]',
        'signals': [
            ('baro_altitude', 'Baro', 'purple'),
            ('tof_bottom', 'ToF Bottom', 'orange'),
            ('tof_front', 'ToF Front', 'cyan'),
        ],
    },
    'flow': {
        'title': 'Optical Flow',
        'signals': [
            ('flow_x', 'X [counts]', 'red'),
            ('flow_y', 'Y [counts]', 'green'),
            ('flow_quality', 'Quality', 'blue'),
        ],
    },
}

DEFAULT_GROUPS = [
    'gyro', 'accel', 'gyro_corr', 'control',
    'attitude', 'position', 'velocity',
    'bias_gyro', 'bias_accel',
    'height', 'flow',
]


def load_csv(filepath: str) -> dict:
    """Load CSV and return dict of numpy arrays"""
    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames
        rows = list(reader)

    data = {}
    for col in columns:
        try:
            data[col] = np.array([float(r[col]) for r in rows])
        except (ValueError, KeyError):
            pass

    # Compute time in seconds
    # 時間を秒で計算
    if 'timestamp_us' in data:
        data['time_s'] = (data['timestamp_us'] - data['timestamp_us'][0]) / 1e6
    elif 'timestamp_ms' in data:
        data['time_s'] = (data['timestamp_ms'] - data['timestamp_ms'][0]) / 1e3

    # Compute attitude from quaternion
    # クォータニオンから姿勢を計算
    if all(k in data for k in ['quat_w', 'quat_x', 'quat_y', 'quat_z']):
        n = len(data['quat_w'])
        data['roll_deg'] = np.zeros(n)
        data['pitch_deg'] = np.zeros(n)
        data['yaw_deg'] = np.zeros(n)
        for i in range(n):
            w, x, y, z = data['quat_w'][i], data['quat_x'][i], data['quat_y'][i], data['quat_z'][i]
            data['roll_deg'][i] = math.degrees(math.atan2(2*(w*x + y*z), 1 - 2*(x*x + y*y)))
            data['pitch_deg'][i] = math.degrees(math.asin(max(-1, min(1, 2*(w*y - z*x)))))
            data['yaw_deg'][i] = math.degrees(math.atan2(2*(w*z + x*y), 1 - 2*(y*y + z*z)))

    return data


def create_figure(data: dict, groups: list, layout: tuple = None,
                  title: str = "StampFly Telemetry") -> go.Figure:
    """Create interactive Plotly figure
    インタラクティブな Plotly 図を作成
    """
    t = data.get('time_s', np.arange(len(next(iter(data.values())))))

    # Filter to groups that have data
    # データのあるグループのみフィルタ
    valid_groups = []
    for g in groups:
        if g not in SIGNAL_GROUPS:
            print(f"Warning: Unknown group '{g}', skipping")
            continue
        gdef = SIGNAL_GROUPS[g]
        if g == 'attitude':
            if 'roll_deg' in data:
                valid_groups.append(g)
        else:
            if any(s[0] in data for s in gdef['signals']):
                valid_groups.append(g)

    n_plots = len(valid_groups)
    if n_plots == 0:
        print("Error: No valid signal groups with data")
        return None

    # Determine layout
    # レイアウト決定
    if layout:
        rows, cols = layout
    else:
        cols = 1
        rows = n_plots

    # Pad if needed
    while rows * cols < n_plots:
        rows += 1

    # Create subplots
    subplot_titles = [SIGNAL_GROUPS[g]['title'] for g in valid_groups]
    # Pad titles if layout has more cells than groups
    while len(subplot_titles) < rows * cols:
        subplot_titles.append("")

    fig = make_subplots(
        rows=rows, cols=cols,
        subplot_titles=subplot_titles,
        shared_xaxes=True,
        vertical_spacing=0.03,
    )

    for idx, group_name in enumerate(valid_groups):
        row = idx // cols + 1
        col = idx % cols + 1
        gdef = SIGNAL_GROUPS[group_name]

        if group_name == 'attitude':
            # Attitude is computed
            for name, label, color in [
                ('roll_deg', 'Roll', 'red'),
                ('pitch_deg', 'Pitch', 'green'),
                ('yaw_deg', 'Yaw', 'blue'),
            ]:
                if name in data:
                    fig.add_trace(
                        go.Scattergl(
                            x=t, y=data[name],
                            name=f'{label}',
                            legendgroup=group_name,
                            legendgrouptitle_text=gdef['title'],
                            line=dict(color=color, width=1),
                            visible=True,
                        ),
                        row=row, col=col,
                    )
        else:
            for col_name, label, color in gdef['signals']:
                if col_name in data:
                    fig.add_trace(
                        go.Scattergl(
                            x=t, y=data[col_name],
                            name=f'{label}',
                            legendgroup=group_name,
                            legendgrouptitle_text=gdef['title'],
                            line=dict(color=color, width=1),
                            visible=True,
                        ),
                        row=row, col=col,
                    )

        # Set y-axis title
        fig.update_yaxes(title_text=gdef['title'], row=row, col=col)

    # Set x-axis title on bottom row
    for c in range(1, cols + 1):
        fig.update_xaxes(title_text="Time [s]", row=rows, col=c)

    # Layout settings
    height = max(300, 250 * rows)
    fig.update_layout(
        title=title,
        height=height,
        legend=dict(
            groupclick="togglegroup",  # Click group title to toggle all signals in group
            tracegroupgap=10,
        ),
        hovermode='x unified',
        template='plotly_white',
    )

    # Enable rangeslider on bottom x-axis for easy time navigation
    # 下部の x 軸にレンジスライダーを追加（時間ナビゲーション用）
    fig.update_xaxes(rangeslider=dict(visible=True), row=rows, col=1)

    return fig


def visualize(filepath: str, groups: list = None, layout: tuple = None,
              output: str = None, title: str = None):
    """Main visualization function"""
    print(f"Loading: {filepath}")
    data = load_csv(filepath)

    n_samples = len(data.get('time_s', []))
    duration = data['time_s'][-1] - data['time_s'][0] if 'time_s' in data and n_samples > 1 else 0
    rate = n_samples / duration if duration > 0 else 0
    print(f"Samples: {n_samples}, Duration: {duration:.1f}s, Rate: {rate:.0f} Hz")

    if groups is None:
        groups = DEFAULT_GROUPS

    if title is None:
        title = f"StampFly Telemetry — {Path(filepath).name}"

    fig = create_figure(data, groups, layout, title)
    if fig is None:
        return

    if output:
        fig.write_html(output)
        print(f"Saved: {output}")
    else:
        # Save to temp file and open in browser
        # 一時ファイルに保存してブラウザで開く
        tmp = tempfile.NamedTemporaryFile(suffix='.html', delete=False, prefix='stampfly_viz_')
        fig.write_html(tmp.name)
        tmp.close()
        print(f"Opening in browser: {tmp.name}")
        webbrowser.open(f'file://{tmp.name}')


def main():
    parser = argparse.ArgumentParser(
        description="Interactive telemetry visualization (Plotly)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Signal groups:
  gyro        Raw gyro [rad/s]
  accel       Raw accel [m/s²]
  gyro_corr   Bias-corrected gyro [rad/s]
  attitude    Roll/Pitch/Yaw [deg]
  position    Position NED [m]
  velocity    Velocity NED [m/s]
  bias_gyro   Gyro bias [rad/s]
  bias_accel  Accel bias [m/s²]
  control     Controller inputs
  height      Baro/ToF altitude [m]
  flow        Optical flow

Examples:
  %(prog)s flight.csv
  %(prog)s flight.csv --layout 3x2
  %(prog)s flight.csv --groups attitude bias_gyro bias_accel
  %(prog)s flight.csv -o dashboard.html
""")
    parser.add_argument('file', help="CSV telemetry file")
    parser.add_argument('--layout', '-l', default=None,
                        help="Tile layout as ROWSxCOLS (e.g., 3x2). Default: Nx1")
    parser.add_argument('--groups', '-g', nargs='+', default=None,
                        help="Signal groups to display (default: all)")
    parser.add_argument('--output', '-o', default=None,
                        help="Save to HTML file instead of opening browser")

    args = parser.parse_args()

    layout = None
    if args.layout:
        try:
            parts = args.layout.lower().split('x')
            layout = (int(parts[0]), int(parts[1]))
        except (ValueError, IndexError):
            print(f"Error: Invalid layout '{args.layout}'. Use format ROWSxCOLS (e.g., 3x2)")
            return 1

    visualize(args.file, args.groups, layout, args.output)
    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
