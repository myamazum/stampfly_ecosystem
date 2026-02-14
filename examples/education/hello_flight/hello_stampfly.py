"""
Hello StampFly — Your first flight in 3 lines!
はじめての StampFly — 3 行で初飛行！

This is the simplest possible StampFly program.
これは最もシンプルな StampFly プログラムです。

Session 1: StampFly とドローン制御の世界
"""

from stampfly_edu import connect_or_simulate

# Connect to drone (falls back to simulator if no drone)
# ドローンに接続（ドローンがなければシミュレータにフォールバック）
drone = connect_or_simulate()

# Fly!
# 飛ばそう！
drone.takeoff()
drone.land()
drone.end()
