#include "workshop_api.hpp"

// =========================================================================
// Lesson 2: Open-Loop Control (Manual Mixing)
// レッスン 2: オープンループ制御（手動ミキシング）
// =========================================================================
//
// Goal: Read stick values into variables and compute each motor's Duty
//       using arithmetic (addition / subtraction / scaling).
// 目標: スティック値を変数に読み取り、四則演算で各モータの Duty を計算する
//
// Motor sign convention (see motor_layout diagram):
// モータ符号規則（motor_layout 図を参照）:
//   M1 FR: T + R - P - Y
//   M2 RR: T + R + P + Y
//   M3 RL: T - R + P - Y
//   M4 FL: T - R - P + Y

static uint32_t tick = 0;

void setup()
{
    ws::print("L2: Open-Loop Control");
}

void loop_400Hz(float dt)
{
    tick++;

    // Step 1: Read stick values into variables
    // Step 1: スティック値を変数に読み取る
    //   float t = ws::rc_throttle();
    //   float r = ws::rc_roll()  * 0.3f;   // Scale for gentle response
    //   float p = ws::rc_pitch() * 0.3f;
    //   float y = ws::rc_yaw()   * 0.3f;

    // Step 2: Compute each motor's Duty and set it
    // Step 2: 各モータの Duty を計算して設定する
    //   ws::motor_set_duty(1, t + r - p - y);  // FR
    //   ws::motor_set_duty(2, t + r + p + y);  // RR
    //   ws::motor_set_duty(3, t - r + p - y);  // RL
    //   ws::motor_set_duty(4, t - r - p + y);  // FL

    // Step 3: Print values every 200ms (80 ticks at 400Hz)
    // Step 3: 200ms毎に値を表示（400Hzで80ティック）
    //   if (tick % 80 == 0)
    //       ws::print("T=%.2f R=%.2f P=%.2f Y=%.2f",
    //           t, r, p, y);
}
