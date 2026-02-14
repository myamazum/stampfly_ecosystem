"""
Educational plotting utilities for StampFly
StampFly 教育用プロットユーティリティ

Provides quick visualization functions for flight logs
and control system analysis.
"""

from typing import Optional, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams["figure.dpi"] = 100
matplotlib.rcParams["figure.figsize"] = (10, 6)


def plot_trajectory(
    log: pd.DataFrame,
    x_col: str = "x",
    y_col: str = "y",
    title: str = "Flight Trajectory / 飛行軌跡",
    ax: Optional[plt.Axes] = None,
    show_start_end: bool = True,
) -> plt.Axes:
    """Plot XY flight trajectory from a log DataFrame.

    ログ DataFrame から XY 飛行軌跡をプロットする。

    Args:
        log: DataFrame with position columns / 位置列を持つ DataFrame
        x_col: X position column name / X 位置列名
        y_col: Y position column name / Y 位置列名
        title: Plot title / プロットタイトル
        ax: Matplotlib axes (creates new if None) / Matplotlib Axes
        show_start_end: Mark start/end points / 開始・終了点をマーク

    Returns:
        Matplotlib Axes object

    Usage:
        >>> import pandas as pd
        >>> log = pd.DataFrame({"x": [0, 1, 2], "y": [0, 1, 0]})
        >>> ax = plot_trajectory(log)
        >>> ax.get_title()
        'Flight Trajectory / 飛行軌跡'
        >>> plt.close()
    """
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(8, 8))

    ax.plot(log[x_col], log[y_col], "b-", linewidth=1.5, label="Trajectory / 軌跡")

    if show_start_end and len(log) > 0:
        ax.plot(log[x_col].iloc[0], log[y_col].iloc[0],
                "go", markersize=12, label="Start / 開始")
        ax.plot(log[x_col].iloc[-1], log[y_col].iloc[-1],
                "rs", markersize=12, label="End / 終了")

    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.3)
    ax.legend()

    return ax


def compare_logs(
    log1: pd.DataFrame,
    log2: pd.DataFrame,
    columns: Optional[list] = None,
    labels: tuple = ("Log 1", "Log 2"),
    title: str = "Log Comparison / ログ比較",
    time_col: str = "time",
) -> plt.Figure:
    """Compare two flight logs by overlaying time-series plots.

    2 つのフライトログを時系列プロットで重ね合わせて比較する。

    Args:
        log1: First log DataFrame / 最初のログ DataFrame
        log2: Second log DataFrame / 2 番目のログ DataFrame
        columns: Column names to compare (auto-detect if None)
                 比較する列名（None で自動検出）
        labels: Labels for each log / 各ログのラベル
        title: Figure title / 図タイトル
        time_col: Time column name / 時間列名

    Returns:
        Matplotlib Figure object

    Usage:
        >>> import pandas as pd
        >>> log1 = pd.DataFrame({"time": [0, 1, 2], "z": [0, 0.5, 0.5]})
        >>> log2 = pd.DataFrame({"time": [0, 1, 2], "z": [0, 0.3, 0.5]})
        >>> fig = compare_logs(log1, log2, columns=["z"])
        >>> len(fig.axes)
        1
        >>> plt.close()
    """
    if columns is None:
        # Auto-detect common numeric columns (excluding time)
        # 共通する数値列を自動検出（時間を除く）
        common = set(log1.columns) & set(log2.columns)
        numeric1 = set(log1.select_dtypes(include=[np.number]).columns)
        numeric2 = set(log2.select_dtypes(include=[np.number]).columns)
        columns = sorted(common & numeric1 & numeric2 - {time_col})

    if not columns:
        raise ValueError("No common numeric columns found for comparison")

    n = len(columns)
    fig, axes = plt.subplots(n, 1, figsize=(10, 3 * n), sharex=True)
    if n == 1:
        axes = [axes]

    for ax, col in zip(axes, columns):
        if time_col in log1.columns:
            ax.plot(log1[time_col], log1[col], "b-", label=labels[0], alpha=0.8)
        else:
            ax.plot(log1[col].values, "b-", label=labels[0], alpha=0.8)

        if time_col in log2.columns:
            ax.plot(log2[time_col], log2[col], "r--", label=labels[1], alpha=0.8)
        else:
            ax.plot(log2[col].values, "r--", label=labels[1], alpha=0.8)

        ax.set_ylabel(col)
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right")

    axes[-1].set_xlabel("Time (s)" if time_col in log1.columns else "Sample")
    fig.suptitle(title, fontsize=14)
    fig.tight_layout()

    return fig


def plot_step_response(
    log: pd.DataFrame,
    output_col: str = "z",
    setpoint_col: Optional[str] = None,
    setpoint_value: Optional[float] = None,
    time_col: str = "time",
    title: str = "Step Response / ステップ応答",
    ax: Optional[plt.Axes] = None,
) -> plt.Axes:
    """Plot step response with performance metrics.

    性能指標付きステップ応答をプロットする。

    Args:
        log: DataFrame with response data / 応答データの DataFrame
        output_col: Output column name / 出力列名
        setpoint_col: Setpoint column name / 目標値列名
        setpoint_value: Constant setpoint value / 一定目標値
        time_col: Time column name / 時間列名
        title: Plot title / プロットタイトル
        ax: Matplotlib axes / Matplotlib Axes

    Returns:
        Matplotlib Axes object

    Usage:
        >>> import pandas as pd
        >>> log = pd.DataFrame({"time": [0, 1, 2, 3], "z": [0, 0.6, 0.95, 1.0]})
        >>> ax = plot_step_response(log, setpoint_value=1.0)
        >>> ax.get_title()
        'Step Response / ステップ応答'
        >>> plt.close()
    """
    if ax is None:
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))

    t = log[time_col].values
    y = log[output_col].values

    # Plot response
    # 応答をプロット
    ax.plot(t, y, "b-", linewidth=1.5, label=f"Response ({output_col})")

    # Plot setpoint
    # 目標値をプロット
    if setpoint_col is not None and setpoint_col in log.columns:
        sp = log[setpoint_col].values
        ax.plot(t, sp, "r--", linewidth=1.0, label="Setpoint / 目標値")
        setpoint_value = sp[-1]
    elif setpoint_value is not None:
        ax.axhline(y=setpoint_value, color="r", linestyle="--",
                    linewidth=1.0, label=f"Setpoint = {setpoint_value}")

    # Calculate and annotate metrics if setpoint is known
    # 目標値がわかっている場合は指標を計算・注記
    if setpoint_value is not None and setpoint_value != 0:
        metrics = _compute_step_metrics(t, y, setpoint_value)
        info_text = (
            f"Rise time / 立ち上がり時間: {metrics['rise_time']:.3f} s\n"
            f"Settling time / 整定時間: {metrics['settling_time']:.3f} s\n"
            f"Overshoot / オーバーシュート: {metrics['overshoot']:.1f} %\n"
            f"Steady-state error / 定常偏差: {metrics['ss_error']:.4f}"
        )
        ax.text(0.98, 0.02, info_text, transform=ax.transAxes,
                fontsize=9, verticalalignment="bottom", horizontalalignment="right",
                bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8),
                family="monospace")

    ax.set_xlabel("Time (s) / 時間")
    ax.set_ylabel(output_col)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    ax.legend()

    return ax


def _compute_step_metrics(
    t: np.ndarray,
    y: np.ndarray,
    setpoint: float,
    tolerance: float = 0.02,
) -> dict:
    """Compute step response performance metrics.

    ステップ応答の性能指標を計算する。

    Args:
        t: Time array / 時間配列
        y: Output array / 出力配列
        setpoint: Target value / 目標値
        tolerance: Settling tolerance (fraction) / 整定許容誤差（割合）

    Returns:
        Dict with rise_time, settling_time, overshoot, ss_error
    """
    y0 = y[0]
    step = setpoint - y0

    if abs(step) < 1e-10:
        return {
            "rise_time": 0.0,
            "settling_time": 0.0,
            "overshoot": 0.0,
            "ss_error": 0.0,
        }

    normalized = (y - y0) / step

    # Rise time: time from 10% to 90%
    # 立ち上がり時間: 10% から 90% までの時間
    t10_idx = np.argmax(normalized >= 0.1)
    t90_idx = np.argmax(normalized >= 0.9)
    rise_time = t[t90_idx] - t[t10_idx] if t90_idx > t10_idx else 0.0

    # Overshoot
    # オーバーシュート
    peak = np.max(normalized)
    overshoot = max(0, (peak - 1.0)) * 100.0

    # Settling time: last time outside tolerance band
    # 整定時間: 許容誤差帯の外にある最後の時刻
    within_band = np.abs(normalized - 1.0) <= tolerance
    if np.all(within_band):
        settling_time = 0.0
    elif np.any(within_band):
        # Find last index outside band
        # 許容帯外の最後のインデックスを検索
        outside_indices = np.where(~within_band)[0]
        if len(outside_indices) > 0:
            last_outside = outside_indices[-1]
            settling_time = t[min(last_outside + 1, len(t) - 1)] - t[0]
        else:
            settling_time = 0.0
    else:
        settling_time = t[-1] - t[0]

    # Steady-state error (last 10% of data)
    # 定常偏差（データの最後 10%）
    n_ss = max(1, len(y) // 10)
    ss_value = np.mean(y[-n_ss:])
    ss_error = abs(setpoint - ss_value)

    return {
        "rise_time": rise_time,
        "settling_time": settling_time,
        "overshoot": overshoot,
        "ss_error": ss_error,
    }
