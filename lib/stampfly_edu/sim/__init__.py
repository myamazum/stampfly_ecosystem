"""
PID Simulation Module for Education
教育用 PID シミュレーションモジュール

Provides plant models and simulation utilities for control system education.
制御システム教育のためのプラントモデルとシミュレーションユーティリティを提供。

Reuses the PID controller from simulator/vpython/control/pid.py.
simulator/vpython/control/pid.py の PID コントローラを再利用。
"""

from .plants import FirstOrderPlant, SecondOrderPlant, DronePlant
from .simulate import simulate_pid, compare_controllers, StepResponseMetrics

__all__ = [
    "FirstOrderPlant",
    "SecondOrderPlant",
    "DronePlant",
    "simulate_pid",
    "compare_controllers",
    "StepResponseMetrics",
]
