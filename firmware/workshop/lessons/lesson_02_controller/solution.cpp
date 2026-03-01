#include "workshop_api.hpp"

// =========================================================================
// Lesson 2: Open-Loop Control (Manual Mixing) - Solution
// レッスン 2: オープンループ制御（手動ミキシング） - 解答
// =========================================================================

static uint32_t tick = 0;

void setup()
{
    ws::print("L2: Open-Loop Control - Solution");
}

void loop_400Hz(float dt)
{
    tick++;

    // Read stick values into variables
    // スティック値を変数に読み取る
    float t = ws::rc_throttle();
    float r = ws::rc_roll()  * 0.3f;
    float p = ws::rc_pitch() * 0.3f;
    float y = ws::rc_yaw()   * 0.3f;

    // Compute each motor's Duty using manual mixing
    // 手動ミキシングで各モータの Duty を計算
    ws::motor_set_duty(1, t + r - p - y);  // FR
    ws::motor_set_duty(2, t + r + p + y);  // RR
    ws::motor_set_duty(3, t - r + p - y);  // RL
    ws::motor_set_duty(4, t - r - p + y);  // FL

    // Print values every 200ms
    // 200ms毎に値を表示
    if (tick % 80 == 0) {
        ws::print("T=%.2f R=%.2f P=%.2f Y=%.2f", t, r, p, y);
    }
}
