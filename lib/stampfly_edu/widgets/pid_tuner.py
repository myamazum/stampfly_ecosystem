"""
Interactive PID Tuning Widget
インタラクティブ PID チューニングウィジェット

Provides ipywidgets sliders for Kp, Ti, Td with real-time step response
update in Jupyter notebooks.

Usage:
    from stampfly_edu.widgets import pid_tuner_widget
    from stampfly_edu.sim import FirstOrderPlant

    plant = FirstOrderPlant(K=1.0, tau=1.0)
    pid_tuner_widget(plant)
"""

import numpy as np
import matplotlib.pyplot as plt

try:
    import ipywidgets as widgets
    from IPython.display import display
    _HAS_WIDGETS = True
except ImportError:
    _HAS_WIDGETS = False


def pid_tuner_widget(
    plant,
    Kp_range: tuple = (0.0, 10.0, 0.1),
    Ti_range: tuple = (0.0, 5.0, 0.05),
    Td_range: tuple = (0.0, 1.0, 0.01),
    setpoint: float = 1.0,
    duration: float = 5.0,
    dt: float = 0.001,
):
    """Create an interactive PID tuning widget.

    インタラクティブ PID チューニングウィジェットを作成する。

    Args:
        plant: Plant model with .step() and .reset() methods
        Kp_range: (min, max, step) for Kp slider
        Ti_range: (min, max, step) for Ti slider
        Td_range: (min, max, step) for Td slider
        setpoint: Step setpoint value / 目標値
        duration: Simulation duration (s) / シミュレーション時間
        dt: Time step (s) / タイムステップ
    """
    if not _HAS_WIDGETS:
        print("ipywidgets is not installed. Install with: pip install ipywidgets")
        print("ipywidgets がインストールされていません: pip install ipywidgets")
        return

    # Import here to avoid circular dependency
    # 循環依存を避けるためここでインポート
    from stampfly_edu.sim.simulate import simulate_pid, compute_metrics

    # Create sliders
    # スライダーを作成
    kp_slider = widgets.FloatSlider(
        value=1.0, min=Kp_range[0], max=Kp_range[1], step=Kp_range[2],
        description="Kp:", continuous_update=False,
        style={"description_width": "40px"},
        layout=widgets.Layout(width="400px"),
    )
    ti_slider = widgets.FloatSlider(
        value=0.0, min=Ti_range[0], max=Ti_range[1], step=Ti_range[2],
        description="Ti:", continuous_update=False,
        style={"description_width": "40px"},
        layout=widgets.Layout(width="400px"),
    )
    td_slider = widgets.FloatSlider(
        value=0.0, min=Td_range[0], max=Td_range[1], step=Td_range[2],
        description="Td:", continuous_update=False,
        style={"description_width": "40px"},
        layout=widgets.Layout(width="400px"),
    )

    output_widget = widgets.Output()

    def update(change=None):
        Kp = kp_slider.value
        Ti = ti_slider.value
        Td = td_slider.value

        result = simulate_pid(
            plant, Kp=Kp, Ti=Ti, Td=Td,
            setpoint=setpoint, duration=duration, dt=dt,
        )
        metrics = compute_metrics(result)

        with output_widget:
            output_widget.clear_output(wait=True)

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)

            # Step response
            # ステップ応答
            ax1.plot(result["time"], result["output"], "b-", linewidth=1.5,
                     label="Response / 応答")
            ax1.axhline(y=setpoint, color="r", linestyle="--", linewidth=0.8,
                       label="Setpoint / 目標値")

            # Tolerance band
            # 許容誤差帯
            ax1.axhline(y=setpoint * 1.02, color="gray", linestyle=":",
                       linewidth=0.5, alpha=0.5)
            ax1.axhline(y=setpoint * 0.98, color="gray", linestyle=":",
                       linewidth=0.5, alpha=0.5)

            ax1.set_ylabel("Output / 出力")
            ax1.set_title(
                f"PID Step Response (Kp={Kp:.2f}, Ti={Ti:.2f}, Td={Td:.2f})\n"
                f"Rise: {metrics.rise_time:.3f}s | "
                f"Settling: {metrics.settling_time:.3f}s | "
                f"Overshoot: {metrics.overshoot:.1f}%"
            )
            ax1.legend(loc="lower right")
            ax1.grid(True, alpha=0.3)

            # Control signal
            # 制御信号
            ax2.plot(result["time"], result["control"], "g-", linewidth=1.0)
            ax2.set_ylabel("Control / 制御入力")
            ax2.set_xlabel("Time (s) / 時間")
            ax2.grid(True, alpha=0.3)

            fig.tight_layout()
            plt.show()

    # Connect callbacks
    # コールバックを接続
    kp_slider.observe(update, names="value")
    ti_slider.observe(update, names="value")
    td_slider.observe(update, names="value")

    # Initial plot
    # 初期プロット
    update()

    # Layout
    # レイアウト
    sliders_box = widgets.VBox([
        widgets.HTML("<h3>PID Tuner / PIDチューナー</h3>"),
        kp_slider,
        ti_slider,
        td_slider,
    ])

    display(widgets.VBox([sliders_box, output_widget]))
