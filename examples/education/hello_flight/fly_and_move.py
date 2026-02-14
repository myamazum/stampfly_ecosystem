"""
Fly and Move — Takeoff, fly forward, and land
飛んで移動 — 離陸、前進、着陸

Session 1: StampFly とドローン制御の世界
"""

import time
from stampfly_edu import connect_or_simulate

drone = connect_or_simulate()

# Takeoff / 離陸
drone.takeoff()

# Move forward 50cm / 50cm 前進
drone.move_forward(50)

# Wait and check telemetry / テレメトリを確認
print(f"Height: {drone.get_height()} cm")
print(f"Battery: {drone.get_battery()} %")
print(f"Attitude: {drone.get_attitude()}")

# Land / 着陸
drone.land()
drone.end()
