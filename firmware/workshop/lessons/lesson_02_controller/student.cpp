#include "workshop_api.hpp"

// =========================================================================
// Lesson 2: Controller Input
// レッスン 2: コントローラ入力
// =========================================================================
//
// Goal: Read controller stick values and map them to motors.
// 目標: コントローラスティックの値を読み取り、モータにマッピングする
//
// Stick ranges:
// スティック範囲:
//   Throttle: 0.0 to 1.0   (スロットル: 0.0〜1.0)
//   Roll:    -1.0 to 1.0   (ロール: -1.0〜1.0)
//   Pitch:   -1.0 to 1.0   (ピッチ: -1.0〜1.0)
//   Yaw:     -1.0 to 1.0   (ヨー: -1.0〜1.0)

void setup()
{
    ws::print("Lesson 2: Controller Input");
}

void loop_400Hz(float dt)
{
    // TODO: Read controller input
    // TODO: コントローラ入力を読み取る
    // float throttle = ws::rc_throttle();  // 0.0 to 1.0
    // float roll = ws::rc_roll();          // -1.0 to 1.0
    // float pitch = ws::rc_pitch();        // -1.0 to 1.0
    // float yaw = ws::rc_yaw();            // -1.0 to 1.0

    // TODO: Map throttle directly to all motors (open-loop control)
    // TODO: スロットルを全モータに直接マッピング（開ループ制御）
    // ヒント: ws::motor_set_all(throttle);

    // TODO: Print values every 200ms (80 ticks at 400Hz)
    // TODO: 200ms毎に値を表示（400Hzで80ティック）
}
