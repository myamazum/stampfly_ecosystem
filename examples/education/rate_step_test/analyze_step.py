"""
Analyze Rate Step Response Data
レートステップ応答データの分析

Session 5: 実機で PID を感じる
"""

import matplotlib.pyplot as plt
from stampfly_edu import load_sample_data, plot_step_response

# Load sample rate step response data
# サンプルレートステップ応答データを読み込む
log = load_sample_data("rate_step")

print(f"Data: {len(log)} samples, {log['time'].iloc[-1]:.2f}s duration")
print(f"Columns: {list(log.columns)}")

# Plot step response with metrics
# 性能指標付きステップ応答をプロット
ax = plot_step_response(
    log,
    output_col="p",
    setpoint_col="setpoint",
    title="Rate Step Response (Roll) / レートステップ応答 (ロール)",
)
plt.savefig("rate_step_response.png", dpi=150, bbox_inches="tight")
plt.show()
print("Saved: rate_step_response.png")
