"""
Visualization for System Identification Results
システム同定結果の可視化

Provides matplotlib-based plotting for:
- Allan variance curves
- Step response fits
- Noise histograms
- Parameter comparison
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

# Matplotlib import with backend handling
try:
    import matplotlib
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


def check_matplotlib():
    """Check if matplotlib is available"""
    if not HAS_MATPLOTLIB:
        raise ImportError(
            "matplotlib is required for visualization. "
            "Install with: pip install matplotlib"
        )


def plot_allan_deviation(
    tau: np.ndarray,
    adev: np.ndarray,
    arw: Optional[float] = None,
    bias_instability: Optional[float] = None,
    bi_tau: Optional[float] = None,
    title: str = "Allan Deviation",
    unit: str = "",
    ax: Optional['plt.Axes'] = None,
    color: str = 'blue',
    label: Optional[str] = None,
) -> 'plt.Axes':
    """
    Plot Allan deviation curve with annotations

    Args:
        tau: Cluster times [s]
        adev: Allan deviation values
        arw: Angle/Velocity Random Walk value (for annotation)
        bias_instability: Bias instability value (for annotation)
        bi_tau: τ at bias instability
        title: Plot title
        unit: Unit string for y-axis
        ax: Matplotlib axes (creates new if None)
        color: Line color
        label: Line label

    Returns:
        Matplotlib axes
    """
    check_matplotlib()

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 6))

    # Plot Allan deviation
    ax.loglog(tau, adev, color=color, linewidth=1.5, alpha=0.8, label=label)

    # Reference slope lines
    if len(tau) > 1:
        # ARW slope (-0.5 on log-log)
        tau_arw = np.array([tau[0], tau[-1]])
        if arw:
            adev_arw = arw * (tau_arw / 1.0) ** (-0.5)
            ax.loglog(tau_arw, adev_arw, '--', color='gray', alpha=0.5,
                      linewidth=1, label='ARW slope (-1/2)')

    # Mark bias instability
    if bias_instability and bi_tau:
        ax.plot(bi_tau, bias_instability, 'o', color='red', markersize=8)
        ax.annotate(
            f'BI: {bias_instability:.2e} {unit}\nτ={bi_tau:.2f}s',
            xy=(bi_tau, bias_instability),
            xytext=(bi_tau * 2, bias_instability * 2),
            fontsize=9,
            arrowprops=dict(arrowstyle='->', color='red', alpha=0.7),
        )

    # Mark ARW at τ=1s
    if arw:
        tau_1s = 1.0
        if tau[0] <= tau_1s <= tau[-1]:
            ax.plot(tau_1s, arw, 's', color='green', markersize=8)
            ax.annotate(
                f'ARW: {arw:.2e} {unit}/√Hz',
                xy=(tau_1s, arw),
                xytext=(tau_1s / 3, arw * 0.5),
                fontsize=9,
                arrowprops=dict(arrowstyle='->', color='green', alpha=0.7),
            )

    ax.set_xlabel('Cluster Time τ [s]')
    ax.set_ylabel(f'Allan Deviation [{unit}]' if unit else 'Allan Deviation')
    ax.set_title(title)
    ax.grid(True, alpha=0.3, which='both')
    if label:
        ax.legend()

    return ax


def plot_noise_analysis(
    noise_estimate: 'NoiseEstimate',
    output_path: Optional[str | Path] = None,
    show: bool = True,
) -> Optional['plt.Figure']:
    """
    Generate comprehensive noise analysis plots

    Args:
        noise_estimate: NoiseEstimate from estimate_sensor_noise()
        output_path: If provided, save figure to this path
        show: If True, display plot interactively

    Returns:
        Matplotlib figure (or None if not showing)
    """
    check_matplotlib()

    fig, axes = plt.subplots(3, 2, figsize=(14, 12))

    # Gyro Allan deviation
    ax = axes[0, 0]
    colors = ['red', 'green', 'blue']
    for i, ar in enumerate(noise_estimate.gyro_allan):
        if len(ar.tau) > 0:
            ax.loglog(ar.tau, ar.adev, color=colors[i], alpha=0.7,
                      label=f"{'XYZ'[i]}")
    ax.set_xlabel('Cluster Time τ [s]')
    ax.set_ylabel('Allan Deviation [rad/s]')
    ax.set_title('Gyroscope Allan Deviation')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')

    # Accel Allan deviation
    ax = axes[0, 1]
    for i, ar in enumerate(noise_estimate.accel_allan):
        if len(ar.tau) > 0:
            ax.loglog(ar.tau, ar.adev, color=colors[i], alpha=0.7,
                      label=f"{'XYZ'[i]}")
    ax.set_xlabel('Cluster Time τ [s]')
    ax.set_ylabel('Allan Deviation [m/s²]')
    ax.set_title('Accelerometer Allan Deviation')
    ax.legend()
    ax.grid(True, alpha=0.3, which='both')

    # Gyro histogram placeholder (need raw data)
    ax = axes[1, 0]
    ax.bar(['X', 'Y', 'Z'], noise_estimate.gyro_std * 1000, color=colors, alpha=0.7)
    ax.set_ylabel('Std Dev [mrad/s]')
    ax.set_title('Gyroscope Standard Deviation')
    ax.grid(True, alpha=0.3)

    # Accel histogram placeholder
    ax = axes[1, 1]
    ax.bar(['X', 'Y', 'Z'], noise_estimate.accel_std, color=colors, alpha=0.7)
    ax.set_ylabel('Std Dev [m/s²]')
    ax.set_title('Accelerometer Standard Deviation')
    ax.grid(True, alpha=0.3)

    # Baro/ToF
    ax = axes[2, 0]
    sensors = ['Baro', 'ToF', 'Flow']
    values = [noise_estimate.baro_std, noise_estimate.tof_std, noise_estimate.flow_std]
    ax.bar(sensors, values, color=['blue', 'orange', 'purple'], alpha=0.7)
    ax.set_ylabel('Std Dev')
    ax.set_title('Altitude/Flow Sensor Noise')
    ax.grid(True, alpha=0.3)

    # Summary text
    ax = axes[2, 1]
    params = noise_estimate.to_dict()
    summary = (
        f"Process Noise (Q):\n"
        f"  gyro_noise: {params['process_noise']['gyro_noise']:.6f} rad/s/√Hz\n"
        f"  accel_noise: {params['process_noise']['accel_noise']:.6f} m/s²/√Hz\n"
        f"  gyro_bias_noise: {params['process_noise']['gyro_bias_noise']:.8f}\n"
        f"  accel_bias_noise: {params['process_noise']['accel_bias_noise']:.8f}\n\n"
        f"Measurement Noise (R):\n"
        f"  baro: {params['measurement_noise']['baro_noise']:.4f} m\n"
        f"  tof: {params['measurement_noise']['tof_noise']:.4f} m\n"
        f"  flow: {params['measurement_noise']['flow_noise']:.2f}\n\n"
        f"Analysis:\n"
        f"  samples: {params['analysis']['samples']}\n"
        f"  duration: {params['analysis']['duration_sec']:.1f} s\n"
        f"  sample_rate: {params['analysis']['sample_rate_hz']:.0f} Hz"
    )

    ax.text(0.1, 0.9, summary, transform=ax.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    ax.axis('off')
    ax.set_title('Estimated Parameters')

    fig.suptitle(f"Sensor Noise Analysis - {noise_estimate.samples} samples")
    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)

    if show:
        plt.show()
        return None

    return fig


def plot_step_response(
    time: np.ndarray,
    measured: np.ndarray,
    fitted: Optional[np.ndarray] = None,
    setpoint: Optional[np.ndarray] = None,
    title: str = "Step Response",
    ylabel: str = "Value",
    output_path: Optional[str | Path] = None,
    show: bool = True,
) -> Optional['plt.Figure']:
    """
    Plot step response with optional fitted curve

    Args:
        time: Time array [s]
        measured: Measured data
        fitted: Fitted response (optional)
        setpoint: Setpoint/reference (optional)
        title: Plot title
        ylabel: Y-axis label
        output_path: If provided, save figure
        show: If True, display interactively

    Returns:
        Matplotlib figure (or None if showing)
    """
    check_matplotlib()

    fig, ax = plt.subplots(figsize=(12, 6))

    ax.plot(time, measured, 'b-', linewidth=1, alpha=0.7, label='Measured')

    if fitted is not None:
        ax.plot(time, fitted, 'r--', linewidth=2, label='Fitted')

    if setpoint is not None:
        ax.plot(time, setpoint, 'g:', linewidth=1.5, label='Setpoint')

    ax.set_xlabel('Time [s]')
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)

    if show:
        plt.show()
        return None

    return fig


def plot_param_comparison(
    estimated: Dict[str, float],
    reference: Dict[str, float],
    title: str = "Parameter Comparison",
    output_path: Optional[str | Path] = None,
    show: bool = True,
) -> Optional['plt.Figure']:
    """
    Bar plot comparing estimated vs reference parameters

    Args:
        estimated: Estimated parameter values
        reference: Reference parameter values
        title: Plot title
        output_path: If provided, save figure
        show: If True, display interactively

    Returns:
        Matplotlib figure (or None if showing)
    """
    check_matplotlib()

    # Find common parameters
    common_keys = sorted(set(estimated.keys()) & set(reference.keys()))
    if not common_keys:
        raise ValueError("No common parameters to compare")

    fig, ax = plt.subplots(figsize=(12, 6))

    x = np.arange(len(common_keys))
    width = 0.35

    est_vals = [estimated[k] for k in common_keys]
    ref_vals = [reference[k] for k in common_keys]

    ax.bar(x - width/2, est_vals, width, label='Estimated', color='blue', alpha=0.7)
    ax.bar(x + width/2, ref_vals, width, label='Reference', color='gray', alpha=0.7)

    ax.set_ylabel('Value')
    ax.set_title(title)
    ax.set_xticks(x)
    ax.set_xticklabels(common_keys, rotation=45, ha='right')
    ax.legend()
    ax.grid(True, alpha=0.3, axis='y')

    # Add error percentages
    for i, (est, ref) in enumerate(zip(est_vals, ref_vals)):
        if ref != 0:
            error_pct = (est - ref) / ref * 100
            color = 'green' if abs(error_pct) < 20 else 'red'
            ax.annotate(
                f'{error_pct:+.1f}%',
                xy=(i, max(est, ref)),
                xytext=(0, 5),
                textcoords='offset points',
                ha='center',
                fontsize=8,
                color=color,
            )

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)

    if show:
        plt.show()
        return None

    return fig


def plot_plant_fit(
    time: np.ndarray,
    u_plant: np.ndarray,
    y_measured: np.ndarray,
    y_simulated: np.ndarray,
    residual: np.ndarray,
    axis: str = "roll",
    K: Optional[float] = None,
    tau_m: Optional[float] = None,
    r_squared: Optional[float] = None,
    output_path: Optional[str | Path] = None,
    show: bool = True,
) -> Optional['plt.Figure']:
    """
    Plot plant model fit results
    プラントモデルフィット結果をプロット

    Upper subplot: measured output and fitted output with plant input on twin axis
    Lower subplot: residual (measured - fitted)

    Args:
        time: Time array [s]
        u_plant: Reconstructed plant input (duty)
        y_measured: Measured angular velocity [rad/s]
        y_simulated: Simulated angular velocity [rad/s]
        residual: y_measured - y_simulated [rad/s]
        axis: Axis name ('roll', 'pitch', 'yaw')
        K: Identified plant gain (for annotation)
        tau_m: Identified time constant (for annotation)
        r_squared: Fit quality R^2 (for annotation)
        output_path: If provided, save figure to this path
        show: If True, display plot interactively

    Returns:
        Matplotlib figure (or None if showing)
    """
    check_matplotlib()

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                    gridspec_kw={'height_ratios': [3, 1]})

    # Upper: measured/fitted output + plant input on secondary axis
    color_meas = 'steelblue'
    color_fit = 'orangered'
    color_input = 'gray'

    ax1.plot(time, y_measured, color=color_meas, linewidth=0.8,
             alpha=0.7, label='Measured (gyro)')
    ax1.plot(time, y_simulated, color=color_fit, linewidth=1.5,
             alpha=0.9, linestyle='--', label='Fitted model')
    ax1.set_ylabel('Angular velocity [rad/s]')
    ax1.grid(True, alpha=0.3)

    # Plant input on secondary axis
    ax1_twin = ax1.twinx()
    ax1_twin.plot(time, u_plant, color=color_input, linewidth=0.5,
                  alpha=0.3, label='Plant input u(t)')
    ax1_twin.set_ylabel('Plant input [duty]', color=color_input)
    ax1_twin.tick_params(axis='y', labelcolor=color_input)

    # Annotation with fit parameters
    info_parts = [f"Axis: {axis}"]
    if K is not None:
        info_parts.append(f"K = {K:.1f}")
    if tau_m is not None:
        info_parts.append(f"tau_m = {tau_m:.4f} s")
    if r_squared is not None:
        info_parts.append(f"R2 = {r_squared:.3f}")
    info_text = "  |  ".join(info_parts)
    ax1.set_title(f"Plant Model Fit: G_p(s) = K / (s * (tau_m * s + 1))\n{info_text}")

    # Combine legends
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax1_twin.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

    # Lower: residual
    ax2.plot(time, residual, color='green', linewidth=0.5, alpha=0.7)
    ax2.axhline(y=0, color='black', linewidth=0.5, linestyle='-')
    ax2.set_xlabel('Time [s]')
    ax2.set_ylabel('Residual [rad/s]')
    ax2.grid(True, alpha=0.3)

    rmse = np.sqrt(np.mean(residual ** 2))
    ax2.set_title(f"Residual (RMSE = {rmse:.4f} rad/s)")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150)

    if show:
        plt.show()
        return None

    return fig
