"""
ESKF State Visualizer
ESKF状態可視化

Matplotlib-based visualization for ESKF states with optional overlay.
"""

from pathlib import Path
from typing import Optional, List
import sys

import numpy as np

try:
    import matplotlib.pyplot as plt
    from matplotlib.gridspec import GridSpec
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def quat_to_euler_deg(qw, qx, qy, qz):
    """Convert quaternion to Euler angles in degrees

    Args:
        qw, qx, qy, qz: Quaternion components (can be scalars or arrays)

    Returns:
        Tuple of (roll, pitch, yaw) in degrees
    """
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (qw * qx + qy * qz)
    cosr_cosp = 1 - 2 * (qx * qx + qy * qy)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # Pitch (y-axis rotation)
    sinp = 2 * (qw * qy - qz * qx)
    pitch = np.where(np.abs(sinp) >= 1, np.sign(sinp) * np.pi / 2, np.arcsin(sinp))

    # Yaw (z-axis rotation)
    siny_cosp = 2 * (qw * qz + qx * qy)
    cosy_cosp = 1 - 2 * (qy * qy + qz * qz)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return np.rad2deg(roll), np.rad2deg(pitch), np.rad2deg(yaw)


def plot_states(
    data,
    overlay=None,
    output_file: Optional[str] = None,
    mode: str = 'all',
    time_range: Optional[tuple] = None,
) -> None:
    """Plot ESKF states from LogData

    Args:
        data: LogData object (primary data)
        overlay: Optional LogData object (reference/overlay)
        output_file: Optional file path to save plot
        mode: Display mode ('all', 'position', 'velocity', 'attitude')
        time_range: Optional (start, end) time range in seconds
    """
    if not HAS_MATPLOTLIB:
        print("Error: matplotlib required for visualization", file=sys.stderr)
        print("Install with: pip install matplotlib", file=sys.stderr)
        return

    # Extract time axis
    t_us = np.array([s.timestamp_us for s in data.samples])
    t = (t_us - t_us[0]) / 1e6  # seconds from start

    # Apply time range filter
    if time_range:
        mask = (t >= time_range[0]) & (t <= time_range[1])
        t = t[mask]
        # Filter samples (we'll need to re-extract data)
        samples = [s for s, m in zip(data.samples, mask) if m]
    else:
        samples = data.samples

    n_samples = len(samples)
    duration = t[-1] - t[0] if len(t) > 1 else 0
    sample_rate = n_samples / duration if duration > 0 else 0

    # Prepare overlay data if provided
    overlay_t = None
    overlay_samples = None
    if overlay:
        overlay_t_us = np.array([s.timestamp_us for s in overlay.samples])
        overlay_t = (overlay_t_us - overlay_t_us[0]) / 1e6
        if time_range:
            mask = (overlay_t >= time_range[0]) & (overlay_t <= time_range[1])
            overlay_t = overlay_t[mask]
            overlay_samples = [s for s, m in zip(overlay.samples, mask) if m]
        else:
            overlay_samples = overlay.samples

    # Determine layout
    if mode == 'position':
        n_rows = 1
        plot_position = True
        plot_velocity = False
        plot_attitude = False
    elif mode == 'velocity':
        n_rows = 1
        plot_position = False
        plot_velocity = True
        plot_attitude = False
    elif mode == 'attitude':
        n_rows = 1
        plot_position = False
        plot_velocity = False
        plot_attitude = True
    else:  # all
        n_rows = 3
        plot_position = True
        plot_velocity = True
        plot_attitude = True

    # Check if we have ESKF data
    has_eskf = samples[0].eskf_position is not None if samples else False

    if not has_eskf:
        print("Note: No ESKF state data found, showing raw sensor data", file=sys.stderr)
        _plot_raw_sensors(data, output_file, time_range)
        return

    # Create figure
    row_height = 2.5
    fig, axes = plt.subplots(n_rows, 1, figsize=(14, row_height * n_rows),
                              sharex=True, squeeze=False)
    axes = axes.flatten()

    # Common style
    legend_style = dict(
        fontsize=8,
        framealpha=0.9,
        loc='upper right',
        ncol=3,
    )

    ax_idx = 0

    # Position plot
    if plot_position:
        ax = axes[ax_idx]

        pos_x = np.array([s.eskf_position[0] for s in samples])
        pos_y = np.array([s.eskf_position[1] for s in samples])
        pos_z = np.array([s.eskf_position[2] for s in samples])

        ax.plot(t, pos_x, 'r-', label='X', linewidth=0.8)
        ax.plot(t, pos_y, 'g-', label='Y', linewidth=0.8)
        ax.plot(t, pos_z, 'b-', label='Z', linewidth=0.8)

        if overlay_samples and overlay_samples[0].eskf_position is not None:
            ov_x = np.array([s.eskf_position[0] for s in overlay_samples])
            ov_y = np.array([s.eskf_position[1] for s in overlay_samples])
            ov_z = np.array([s.eskf_position[2] for s in overlay_samples])
            ax.plot(overlay_t, ov_x, 'r--', label='X (ref)', linewidth=0.5, alpha=0.7)
            ax.plot(overlay_t, ov_y, 'g--', label='Y (ref)', linewidth=0.5, alpha=0.7)
            ax.plot(overlay_t, ov_z, 'b--', label='Z (ref)', linewidth=0.5, alpha=0.7)

        ax.set_ylabel('Position [m]', fontsize=9)
        ax.legend(**legend_style)
        ax.grid(True, alpha=0.3)
        ax_idx += 1

    # Velocity plot
    if plot_velocity:
        ax = axes[ax_idx]

        vel_x = np.array([s.eskf_velocity[0] for s in samples])
        vel_y = np.array([s.eskf_velocity[1] for s in samples])
        vel_z = np.array([s.eskf_velocity[2] for s in samples])

        ax.plot(t, vel_x, 'r-', label='Vx', linewidth=0.8)
        ax.plot(t, vel_y, 'g-', label='Vy', linewidth=0.8)
        ax.plot(t, vel_z, 'b-', label='Vz', linewidth=0.8)

        if overlay_samples and overlay_samples[0].eskf_velocity is not None:
            ov_x = np.array([s.eskf_velocity[0] for s in overlay_samples])
            ov_y = np.array([s.eskf_velocity[1] for s in overlay_samples])
            ov_z = np.array([s.eskf_velocity[2] for s in overlay_samples])
            ax.plot(overlay_t, ov_x, 'r--', label='Vx (ref)', linewidth=0.5, alpha=0.7)
            ax.plot(overlay_t, ov_y, 'g--', label='Vy (ref)', linewidth=0.5, alpha=0.7)
            ax.plot(overlay_t, ov_z, 'b--', label='Vz (ref)', linewidth=0.5, alpha=0.7)

        ax.set_ylabel('Velocity [m/s]', fontsize=9)
        ax.legend(**legend_style)
        ax.grid(True, alpha=0.3)
        ax_idx += 1

    # Attitude plot
    if plot_attitude:
        ax = axes[ax_idx]

        # Convert quaternion to Euler
        qw = np.array([s.eskf_quat[0] for s in samples])
        qx = np.array([s.eskf_quat[1] for s in samples])
        qy = np.array([s.eskf_quat[2] for s in samples])
        qz = np.array([s.eskf_quat[3] for s in samples])
        roll, pitch, yaw = quat_to_euler_deg(qw, qx, qy, qz)

        ax.plot(t, roll, 'r-', label='Roll', linewidth=0.8)
        ax.plot(t, pitch, 'g-', label='Pitch', linewidth=0.8)
        ax.plot(t, yaw, 'b-', label='Yaw', linewidth=0.8)

        if overlay_samples and overlay_samples[0].eskf_quat is not None:
            ov_qw = np.array([s.eskf_quat[0] for s in overlay_samples])
            ov_qx = np.array([s.eskf_quat[1] for s in overlay_samples])
            ov_qy = np.array([s.eskf_quat[2] for s in overlay_samples])
            ov_qz = np.array([s.eskf_quat[3] for s in overlay_samples])
            ov_roll, ov_pitch, ov_yaw = quat_to_euler_deg(ov_qw, ov_qx, ov_qy, ov_qz)
            ax.plot(overlay_t, ov_roll, 'r--', label='Roll (ref)', linewidth=0.5, alpha=0.7)
            ax.plot(overlay_t, ov_pitch, 'g--', label='Pitch (ref)', linewidth=0.5, alpha=0.7)
            ax.plot(overlay_t, ov_yaw, 'b--', label='Yaw (ref)', linewidth=0.5, alpha=0.7)

        ax.set_ylabel('Attitude [deg]', fontsize=9)
        ax.legend(**legend_style)
        ax.grid(True, alpha=0.3)
        ax_idx += 1

    # X-axis label on bottom plot
    axes[-1].set_xlabel('Time [s]', fontsize=9)

    # Title
    title = f'ESKF States ({n_samples} samples @ {sample_rate:.0f}Hz, {duration:.1f}s)'
    if overlay:
        title += ' [with overlay]'
    fig.suptitle(title, fontsize=11, fontweight='bold')

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved plot to: {output_file}", file=sys.stderr)
    else:
        plt.show()


def _plot_raw_sensors(
    data,
    output_file: Optional[str] = None,
    time_range: Optional[tuple] = None,
) -> None:
    """Plot raw sensor data (when no ESKF state available)"""
    t_us = np.array([s.timestamp_us for s in data.samples])
    t = (t_us - t_us[0]) / 1e6

    if time_range:
        mask = (t >= time_range[0]) & (t <= time_range[1])
        t = t[mask]
        samples = [s for s, m in zip(data.samples, mask) if m]
    else:
        samples = data.samples

    # Extract sensor data
    gyro = np.array([s.gyro for s in samples])
    accel = np.array([s.accel for s in samples])

    n_samples = len(samples)
    duration = t[-1] - t[0] if len(t) > 1 else 0
    sample_rate = n_samples / duration if duration > 0 else 0

    fig, axes = plt.subplots(2, 1, figsize=(14, 6), sharex=True)

    # Gyro
    axes[0].plot(t, np.rad2deg(gyro[:, 0]), 'r-', label='X', linewidth=0.5)
    axes[0].plot(t, np.rad2deg(gyro[:, 1]), 'g-', label='Y', linewidth=0.5)
    axes[0].plot(t, np.rad2deg(gyro[:, 2]), 'b-', label='Z', linewidth=0.5)
    axes[0].set_ylabel('Gyro [deg/s]', fontsize=9)
    axes[0].legend(loc='upper right', ncol=3, fontsize=8)
    axes[0].grid(True, alpha=0.3)

    # Accel
    axes[1].plot(t, accel[:, 0], 'r-', label='X', linewidth=0.5)
    axes[1].plot(t, accel[:, 1], 'g-', label='Y', linewidth=0.5)
    axes[1].plot(t, accel[:, 2], 'b-', label='Z', linewidth=0.5)
    axes[1].set_ylabel('Accel [m/s²]', fontsize=9)
    axes[1].set_xlabel('Time [s]', fontsize=9)
    axes[1].legend(loc='upper right', ncol=3, fontsize=8)
    axes[1].grid(True, alpha=0.3)

    fig.suptitle(f'Raw Sensor Data ({n_samples} samples @ {sample_rate:.0f}Hz)',
                 fontsize=11, fontweight='bold')

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved plot to: {output_file}", file=sys.stderr)
    else:
        plt.show()


def plot_comparison(
    estimated_data,
    reference_data,
    output_file: Optional[str] = None,
    time_range: Optional[tuple] = None,
) -> None:
    """Plot estimated vs reference comparison with error subplots

    Args:
        estimated_data: LogData with estimated states
        reference_data: LogData with reference states
        output_file: Optional file path to save plot
        time_range: Optional (start, end) time range in seconds
    """
    if not HAS_MATPLOTLIB:
        print("Error: matplotlib required for visualization", file=sys.stderr)
        return

    # This is a more detailed comparison view
    plot_states(
        estimated_data,
        overlay=reference_data,
        output_file=output_file,
        mode='all',
        time_range=time_range,
    )


def plot_error_timeseries(
    time_series_error,
    output_file: Optional[str] = None,
) -> None:
    """Plot error time series

    Args:
        time_series_error: TimeSeriesError object from metrics
        output_file: Optional file path to save plot
    """
    if not HAS_MATPLOTLIB:
        print("Error: matplotlib required for visualization", file=sys.stderr)
        return

    t = time_series_error.timestamps_us / 1e6

    fig, axes = plt.subplots(3, 1, figsize=(14, 8), sharex=True)

    # Position error
    axes[0].plot(t, time_series_error.position_error[:, 0], 'r-', label='X', linewidth=0.5)
    axes[0].plot(t, time_series_error.position_error[:, 1], 'g-', label='Y', linewidth=0.5)
    axes[0].plot(t, time_series_error.position_error[:, 2], 'b-', label='Z', linewidth=0.5)
    axes[0].set_ylabel('Position Error [m]', fontsize=9)
    axes[0].legend(loc='upper right', ncol=3, fontsize=8)
    axes[0].grid(True, alpha=0.3)

    # Velocity error
    axes[1].plot(t, time_series_error.velocity_error[:, 0], 'r-', label='Vx', linewidth=0.5)
    axes[1].plot(t, time_series_error.velocity_error[:, 1], 'g-', label='Vy', linewidth=0.5)
    axes[1].plot(t, time_series_error.velocity_error[:, 2], 'b-', label='Vz', linewidth=0.5)
    axes[1].set_ylabel('Velocity Error [m/s]', fontsize=9)
    axes[1].legend(loc='upper right', ncol=3, fontsize=8)
    axes[1].grid(True, alpha=0.3)

    # Attitude error
    axes[2].plot(t, time_series_error.attitude_error_deg[:, 0], 'r-', label='Roll', linewidth=0.5)
    axes[2].plot(t, time_series_error.attitude_error_deg[:, 1], 'g-', label='Pitch', linewidth=0.5)
    axes[2].plot(t, time_series_error.attitude_error_deg[:, 2], 'b-', label='Yaw', linewidth=0.5)
    axes[2].set_ylabel('Attitude Error [deg]', fontsize=9)
    axes[2].set_xlabel('Time [s]', fontsize=9)
    axes[2].legend(loc='upper right', ncol=3, fontsize=8)
    axes[2].grid(True, alpha=0.3)

    fig.suptitle('ESKF Error Time Series', fontsize=11, fontweight='bold')

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        print(f"Saved plot to: {output_file}", file=sys.stderr)
    else:
        plt.show()
