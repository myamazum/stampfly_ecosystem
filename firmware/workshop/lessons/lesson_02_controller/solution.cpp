#include "workshop_api.hpp"

// =========================================================================
// Lesson 2: Controller Input - Solution
// レッスン 2: コントローラ入力 - 解答
// =========================================================================

static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 2: Controller Input - Solution");
}

void loop_400Hz(float dt)
{
    tick++;

    // Read controller input
    // コントローラ入力を読み取る
    float throttle = ws::rc_throttle();
    float roll = ws::rc_roll();
    float pitch = ws::rc_pitch();
    float yaw = ws::rc_yaw();

    // Direct throttle-to-motor mapping (open loop)
    // スロットルをモータに直接マッピング（開ループ）
    ws::motor_set_all(throttle);

    // Print values every 200ms
    // 200ms毎に値を表示
    if (tick % 80 == 0) {
        ws::print("T=%.2f R=%.2f P=%.2f Y=%.2f", throttle, roll, pitch, yaw);
    }
}
