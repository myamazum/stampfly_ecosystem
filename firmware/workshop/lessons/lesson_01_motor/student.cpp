#include "workshop_api.hpp"

// =========================================================================
// Lesson 1: Motor Control
// レッスン 1: モータ制御
// =========================================================================
//
// Goal: Understand motor IDs, PWM duty cycle, and motor layout.
// 目標: モータ ID、PWM デューティ比、モータ配置を理解する
//
// Motor layout:
// モータ配置:
//        Front
//   FL(M4)  FR(M1)
//       \  ^  /
//        \ | /
//         \|/
//          X
//         /|\
//        / | \
//   RL(M3)  RR(M2)
//        Rear

void setup()
{
    ws::print("Lesson 1: Motor Control");
}

void loop_400Hz(float dt)
{
    // TODO: Spin motor 1 (FR) at 10% duty
    // TODO: モータ 1 (FR) を 10% デューティで回す
    // ヒント: ws::motor_set_duty(1, 0.1f);

    // TODO: Try spinning each motor one at a time
    // TODO: 各モータを1つずつ回してみる
    // Motor IDs: 1=FR, 2=RR, 3=RL, 4=FL
    // モータ ID: 1=右前, 2=右後, 3=左後, 4=左前
}
