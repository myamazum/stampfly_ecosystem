"""
PID Control of a First-Order System (no drone required)
1次系の PID 制御（ドローン不要）

Session 3-4: フィードバック制御入門 / PID 理論
"""

import matplotlib.pyplot as plt
from stampfly_edu.sim import FirstOrderPlant, simulate_pid, compare_controllers

# Create a first-order plant: G(s) = 1 / (s + 1)
# 1次系プラント: G(s) = 1 / (s + 1)
plant = FirstOrderPlant(K=1.0, tau=1.0)

# Compare P, PI, PID controllers
# P, PI, PID コントローラを比較
configs = [
    {"Kp": 2.0, "Ti": 0.0, "Td": 0.0},   # P only
    {"Kp": 2.0, "Ti": 1.0, "Td": 0.0},   # PI
    {"Kp": 2.0, "Ti": 1.0, "Td": 0.1},   # PID
]
labels = ["P only (Kp=2)", "PI (Ti=1.0)", "PID (Td=0.1)"]

fig = compare_controllers(
    plant, configs, labels=labels,
    title="PID Control of First-Order System / 1次系の PID 制御",
    duration=10.0,
)
plt.savefig("pid_comparison.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: pid_comparison.png")
