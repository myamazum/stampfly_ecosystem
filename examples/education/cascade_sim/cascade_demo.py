"""
Cascade vs Single-Loop Attitude Control Demo
カスケード vs 単ループ姿勢制御デモ

Session 9: 姿勢制御 — カスケードの概念
"""

import matplotlib.pyplot as plt
from stampfly_edu.sim.cascade import compare_cascade_vs_single

# Compare cascade vs single-loop
# カスケード vs 単ループを比較
fig = compare_cascade_vs_single(setpoint_deg=10.0, duration=1.5)
plt.savefig("cascade_comparison.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: cascade_comparison.png")
