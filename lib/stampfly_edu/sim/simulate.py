"""
PID simulation and comparison utilities
PID シミュレーションと比較ユーティリティ

Runs closed-loop simulations with plant models and PID controllers,
computing step response metrics automatically.
"""

import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Reuse PID from simulator
# シミュレータの PID を再利用
_vpython_dir = Path(__file__).parent.parent.parent.parent / "simulator" / "vpython" / "control"
if str(_vpython_dir) not in sys.path:
    sys.path.insert(0, str(_vpython_dir))

from pid import PID


@dataclass
class StepResponseMetrics:
    """Step response performance metrics.

    ステップ応答の性能指標。

    Attributes:
        rise_time: Time from 10% to 90% of final value (s)
                   最終値の 10% から 90% までの時間（秒）
        settling_time: Time to stay within 2% of final value (s)
                       最終値の 2% 以内に留まるまでの時間（秒）
        overshoot: Peak overshoot (%) / ピークオーバーシュート (%)
        steady_state_error: Absolute SS error / 定常偏差の絶対値
    """
    rise_time: float
    settling_time: float
    overshoot: float
    steady_state_error: float

    def __repr__(self):
        return (
            f"StepResponseMetrics(\n"
            f"  rise_time={self.rise_time:.4f} s,\n"
            f"  settling_time={self.settling_time:.4f} s,\n"
            f"  overshoot={self.overshoot:.2f} %,\n"
            f"  steady_state_error={self.steady_state_error:.6f}\n"
            f")"
        )


def simulate_pid(
    plant,
    Kp: float = 1.0,
    Ti: float = 0.0,
    Td: float = 0.0,
    eta: float = 0.125,
    setpoint: float = 1.0,
    duration: float = 5.0,
    dt: float = 0.001,
    step_time: float = 0.0,
    disturbance_time: Optional[float] = None,
    disturbance_value: float = 0.0,
    output_min: float = -float("inf"),
    output_max: float = float("inf"),
) -> pd.DataFrame:
    """Run a closed-loop PID simulation.

    閉ループ PID シミュレーションを実行する。

    Args:
        plant: Plant model (must have .step(u, dt) and .reset() methods)
               プラントモデル（.step(u, dt) と .reset() メソッドが必要）
        Kp: Proportional gain / 比例ゲイン
        Ti: Integral time (s), 0=disabled / 積分時間、0=無効
        Td: Derivative time (s), 0=disabled / 微分時間、0=無効
        eta: Derivative filter coefficient / 微分フィルタ係数
        setpoint: Step setpoint value / ステップ目標値
        duration: Simulation duration (s) / シミュレーション時間（秒）
        dt: Time step (s) / 時間ステップ（秒）
        step_time: Time when step is applied (s) / ステップ適用時間（秒）
        disturbance_time: Time for disturbance (s) / 外乱適用時間（秒）
        disturbance_value: Disturbance magnitude / 外乱の大きさ
        output_min: Controller output lower limit / コントローラ出力下限
        output_max: Controller output upper limit / コントローラ出力上限

    Returns:
        DataFrame with columns: time, setpoint, output, error, control

    Usage:
        >>> from stampfly_edu.sim.plants import FirstOrderPlant
        >>> plant = FirstOrderPlant(K=1.0, tau=1.0)
        >>> result = simulate_pid(plant, Kp=2.0, Ti=1.0, duration=5.0)
        >>> result.columns.tolist()
        ['time', 'setpoint', 'output', 'error', 'control']
        >>> abs(result['output'].iloc[-1] - 1.0) < 0.05
        True
    """
    plant.reset()
    controller = PID(
        Kp=Kp, Ti=Ti, Td=Td, eta=eta,
        output_min=output_min, output_max=output_max,
    )

    n_steps = int(duration / dt)
    time_array = np.zeros(n_steps)
    sp_array = np.zeros(n_steps)
    output_array = np.zeros(n_steps)
    error_array = np.zeros(n_steps)
    control_array = np.zeros(n_steps)

    for i in range(n_steps):
        t = i * dt
        time_array[i] = t

        # Step setpoint
        # ステップ目標値
        sp = setpoint if t >= step_time else 0.0
        sp_array[i] = sp

        # Current output
        y = plant.y if hasattr(plant, "y") else (plant.omega if hasattr(plant, "omega") else 0.0)
        output_array[i] = y
        error_array[i] = sp - y

        # PID control
        u = controller.update(sp, y, dt)

        # Apply disturbance
        # 外乱を適用
        if disturbance_time is not None and t >= disturbance_time:
            u += disturbance_value

        control_array[i] = u

        # Advance plant
        plant.step(u, dt)

    return pd.DataFrame({
        "time": time_array,
        "setpoint": sp_array,
        "output": output_array,
        "error": error_array,
        "control": control_array,
    })


def compute_metrics(result: pd.DataFrame, tolerance: float = 0.02) -> StepResponseMetrics:
    """Compute step response metrics from simulation result.

    シミュレーション結果からステップ応答指標を計算する。

    Args:
        result: DataFrame from simulate_pid() / simulate_pid() の結果
        tolerance: Settling tolerance (fraction) / 整定許容誤差

    Returns:
        StepResponseMetrics
    """
    t = result["time"].values
    y = result["output"].values
    sp = result["setpoint"].values

    # Find step start
    # ステップ開始を見つける
    step_idx = np.argmax(sp > 0)
    if step_idx == 0 and sp[0] == 0:
        step_idx = 0
    step_value = sp[-1]

    if abs(step_value) < 1e-10:
        return StepResponseMetrics(0, 0, 0, 0)

    y_after = y[step_idx:]
    t_after = t[step_idx:] - t[step_idx]

    normalized = y_after / step_value

    # Rise time: 10% to 90%
    idx_10 = np.argmax(normalized >= 0.1)
    idx_90 = np.argmax(normalized >= 0.9)
    rise_time = t_after[idx_90] - t_after[idx_10] if idx_90 > idx_10 else 0.0

    # Overshoot
    peak = np.max(normalized)
    overshoot = max(0, (peak - 1.0)) * 100.0

    # Settling time
    within_band = np.abs(normalized - 1.0) <= tolerance
    if np.all(within_band):
        settling_time = 0.0
    else:
        outside_indices = np.where(~within_band)[0]
        if len(outside_indices) > 0:
            last_outside = outside_indices[-1]
            settling_time = t_after[min(last_outside + 1, len(t_after) - 1)]
        else:
            settling_time = 0.0

    # Steady-state error
    n_ss = max(1, len(y_after) // 10)
    ss_error = abs(step_value - np.mean(y_after[-n_ss:]))

    return StepResponseMetrics(
        rise_time=rise_time,
        settling_time=settling_time,
        overshoot=overshoot,
        steady_state_error=ss_error,
    )


def compare_controllers(
    plant,
    params_list: list,
    labels: Optional[list] = None,
    setpoint: float = 1.0,
    duration: float = 5.0,
    dt: float = 0.001,
    title: str = "Controller Comparison / コントローラ比較",
) -> plt.Figure:
    """Compare multiple PID configurations on the same plant.

    同一プラントで複数の PID 設定を比較する。

    Args:
        plant: Plant model / プラントモデル
        params_list: List of dicts with PID parameters (Kp, Ti, Td)
                     PID パラメータの辞書リスト
        labels: Labels for each configuration / 各設定のラベル
        setpoint: Step setpoint / ステップ目標値
        duration: Simulation duration (s) / シミュレーション時間
        dt: Time step (s) / タイムステップ
        title: Plot title / プロットタイトル

    Returns:
        Matplotlib Figure

    Usage:
        >>> from stampfly_edu.sim.plants import FirstOrderPlant
        >>> plant = FirstOrderPlant(K=1.0, tau=1.0)
        >>> params = [{"Kp": 1.0}, {"Kp": 2.0}, {"Kp": 5.0}]
        >>> fig = compare_controllers(plant, params, labels=["Kp=1", "Kp=2", "Kp=5"])
        >>> len(fig.axes)
        3
        >>> plt.close()
    """
    if labels is None:
        labels = [f"Config {i+1}" for i in range(len(params_list))]

    fig, axes = plt.subplots(3, 1, figsize=(10, 9), sharex=True)
    colors = plt.cm.tab10(np.linspace(0, 1, len(params_list)))

    results = []
    metrics_list = []

    for i, (params, label) in enumerate(zip(params_list, labels)):
        result = simulate_pid(
            plant,
            Kp=params.get("Kp", 1.0),
            Ti=params.get("Ti", 0.0),
            Td=params.get("Td", 0.0),
            eta=params.get("eta", 0.125),
            setpoint=setpoint,
            duration=duration,
            dt=dt,
        )
        metrics = compute_metrics(result)
        results.append(result)
        metrics_list.append(metrics)

        # Plot output
        axes[0].plot(result["time"], result["output"],
                     color=colors[i], label=f"{label}", linewidth=1.5)

        # Plot error
        axes[1].plot(result["time"], result["error"],
                     color=colors[i], label=f"{label}", linewidth=1.0)

        # Plot control signal
        axes[2].plot(result["time"], result["control"],
                     color=colors[i], label=f"{label}", linewidth=1.0)

    # Setpoint on output plot
    axes[0].axhline(y=setpoint, color="k", linestyle="--",
                    linewidth=0.8, label="Setpoint / 目標値")

    axes[0].set_ylabel("Output / 出力")
    axes[0].set_title(title)
    axes[0].legend(loc="lower right", fontsize=8)
    axes[0].grid(True, alpha=0.3)

    axes[1].set_ylabel("Error / 偏差")
    axes[1].grid(True, alpha=0.3)

    axes[2].set_ylabel("Control / 制御入力")
    axes[2].set_xlabel("Time (s) / 時間")
    axes[2].grid(True, alpha=0.3)

    # Add metrics table
    # 指標テーブルを追加
    metrics_text = "Metrics / 性能指標:\n"
    for label, m in zip(labels, metrics_list):
        metrics_text += (
            f"  {label}: tr={m.rise_time:.3f}s, "
            f"ts={m.settling_time:.3f}s, "
            f"OS={m.overshoot:.1f}%\n"
        )
    fig.text(0.02, 0.01, metrics_text, fontsize=8, family="monospace",
             verticalalignment="bottom",
             bbox=dict(boxstyle="round", facecolor="lightyellow", alpha=0.8))

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.12)

    return fig
