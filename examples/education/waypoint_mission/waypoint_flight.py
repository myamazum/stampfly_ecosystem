"""
Waypoint Mission Flight
ウェイポイントミッション飛行

Session 12: ウェイポイント飛行
"""

from stampfly_edu import connect_or_simulate, plot_trajectory

drone = connect_or_simulate()
drone.takeoff()

# Define waypoints as (forward_cm, left_cm) movements
# ウェイポイントを (前進cm, 左移動cm) で定義
waypoints = [
    (100, 0),    # Forward 1m
    (0, 100),    # Left 1m
    (-100, 0),   # Back 1m
    (0, -100),   # Right 1m (return)
]

for i, (fwd, left) in enumerate(waypoints):
    print(f"Waypoint {i+1}/{len(waypoints)}")
    if fwd > 0:
        drone.move_forward(fwd)
    elif fwd < 0:
        drone.move_back(-fwd)
    if left > 0:
        drone.move_left(left)
    elif left < 0:
        drone.move_right(-left)

drone.land()
drone.end()
print("Mission complete! / ミッション完了！")
