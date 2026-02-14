"""
Square Path Flight — Fly a 1m x 1m square and record the trajectory
矩形パス飛行 — 1m x 1m の矩形を飛行し軌跡を記録

Session 2: プログラムで自律飛行
"""

import time
from stampfly_edu import connect_or_simulate, plot_trajectory

drone = connect_or_simulate()

# Takeoff / 離陸
drone.takeoff()

# Fly a 1m square (100cm per side)
# 1m の正方形を飛行（各辺 100cm）
sides = ["forward", "left", "back", "right"]
move_funcs = {
    "forward": drone.move_forward,
    "left": drone.move_left,
    "back": drone.move_back,
    "right": drone.move_right,
}

for side in sides:
    print(f"Moving {side} 100cm...")
    move_funcs[side](100)

# Land / 着陸
drone.land()

# Plot trajectory if using simulator
# シミュレータ使用時は軌跡をプロット
if hasattr(drone, "get_trajectory"):
    import pandas as pd
    import matplotlib.pyplot as plt

    traj = drone.get_trajectory()
    if traj:
        df = pd.DataFrame(traj, columns=["x", "y", "z", "t"])
        # Convert cm to m / cm を m に変換
        df["x"] = df["x"] / 100.0
        df["y"] = df["y"] / 100.0
        plot_trajectory(df)
        plt.savefig("square_trajectory.png", dpi=150, bbox_inches="tight")
        print("Saved trajectory plot to square_trajectory.png")
        plt.show()

drone.end()
