"""
External PID Controller via RC Control
RC 制御による外部 PID コントローラ

Session 13: カスタムコントローラ
"""

import sys
import time
from pathlib import Path

# Import PID from simulator
# シミュレータの PID をインポート
_vpython_dir = Path(__file__).parent.parent.parent.parent / "simulator" / "vpython" / "control"
sys.path.insert(0, str(_vpython_dir))
from pid import PID

from stampfly_edu import connect_or_simulate

drone = connect_or_simulate()
drone.takeoff()

# Position PID controllers
# 位置 PID コントローラ
pid_x = PID(Kp=30.0, Ti=3.0, Td=0.5, output_min=-50, output_max=50)
pid_y = PID(Kp=30.0, Ti=3.0, Td=0.5, output_min=-50, output_max=50)

# Target position (hold at origin)
# 目標位置（原点に保持）
target_x, target_y = 0.0, 0.0

# Control loop at 20Hz
# 20Hz の制御ループ
dt = 0.05
for i in range(200):  # 10 seconds
    telem = drone.get_telemetry()
    x = telem.get("x", 0.0)
    y = telem.get("y", 0.0)

    cmd_fb = int(pid_x.update(target_x, x, dt))
    cmd_lr = int(pid_y.update(target_y, y, dt))

    drone.send_rc_control(cmd_lr, cmd_fb, 0, 0)
    time.sleep(dt)

# Stop and land
# 停止して着陸
drone.send_rc_control(0, 0, 0, 0)
drone.land()
drone.end()
print("External PID control complete! / 外部 PID 制御完了！")
