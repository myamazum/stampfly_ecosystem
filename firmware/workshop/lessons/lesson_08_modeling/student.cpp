#include "workshop_api.hpp"

// =========================================================================
// Lesson 8: Modeling - Custom Motor Mixer
// レッスン 8: モデリング - カスタムモーターミキサー
// =========================================================================
//
// Goal: Implement the motor mixer from first principles using
//       quadrotor dynamics equations.
// 目標: クアッドロータの力学方程式から、モーターミキサーを
//       自分で実装する
//
// Instead of ws::motor_mixer(), you will compute each motor's duty
// from thrust and torque commands using the physical model.
// ws::motor_mixer() の代わりに、物理モデルを使って推力と
// トルク指令から各モーターのデューティを計算する
//
// Motor layout (X configuration):
// モーター配置（X配置）:
//
//            Front
//       FL (M4)   FR (M1)
//          \   ^   /
//           \  |  /
//            \ | /
//             \|/
//              X      <- Center
//             /|\
//            / | \
//           /  |  \
//       RL (M3)  RR (M2)
//            Rear
//
// Arm length L = 0.023 m (center to motor)
// アーム長 L = 0.023 m（中心からモーターまで）

// Physical parameters
// 物理パラメータ
static const float L = 0.023f;      // Arm length [m] / アーム長 [m]
static const float kq = 0.01f;      // Torque-to-thrust ratio / トルク対推力比

// PID (reuse from Lesson 6)
static const float Kp_roll = 0.5f, Ki_roll = 0.3f, Kd_roll = 0.005f;
static const float Kp_pitch = 0.5f, Ki_pitch = 0.3f, Kd_pitch = 0.005f;
static const float Kp_yaw = 2.0f, Ki_yaw = 0.5f, Kd_yaw = 0.01f;
static const float integral_limit = 0.5f;
static const float rate_max_rp = 1.0f, rate_max_yaw = 5.0f;

static float roll_integral = 0.0f, roll_prev_error = 0.0f;
static float pitch_integral = 0.0f, pitch_prev_error = 0.0f;
static float yaw_integral = 0.0f, yaw_prev_error = 0.0f;
static uint32_t tick = 0;

static float clamp(float val, float lim)
{
    if (val >  lim) return  lim;
    if (val < -lim) return -lim;
    return val;
}

void setup()
{
    ws::print("Lesson 8: Modeling - Custom Mixer");
}

void loop_400Hz(float dt)
{
    tick++;

    if (!ws::is_armed()) {
        ws::motor_stop_all();
        roll_integral = 0.0f; roll_prev_error = 0.0f;
        pitch_integral = 0.0f; pitch_prev_error = 0.0f;
        yaw_integral = 0.0f; yaw_prev_error = 0.0f;
        ws::led_color(0, 0, 50);
        return;
    }

    ws::led_color(0, 50, 0);
    float throttle = ws::rc_throttle();

    // --- PID (same as Lesson 6) ---
    // Roll
    float roll_target = ws::rc_roll() * rate_max_rp;
    float roll_error = roll_target - ws::gyro_x();
    float roll_P = Kp_roll * roll_error;
    roll_integral += roll_error * dt;
    roll_integral = clamp(roll_integral, integral_limit);
    float roll_I = Ki_roll * roll_integral;
    float roll_D = Kd_roll * (roll_error - roll_prev_error) / dt;
    roll_prev_error = roll_error;
    float roll_cmd = clamp(roll_P + roll_I + roll_D, 1.0f);

    // Pitch
    float pitch_target = ws::rc_pitch() * rate_max_rp;
    float pitch_error = pitch_target - ws::gyro_y();
    float pitch_P = Kp_pitch * pitch_error;
    pitch_integral += pitch_error * dt;
    pitch_integral = clamp(pitch_integral, integral_limit);
    float pitch_I = Ki_pitch * pitch_integral;
    float pitch_D = Kd_pitch * (pitch_error - pitch_prev_error) / dt;
    pitch_prev_error = pitch_error;
    float pitch_cmd = clamp(pitch_P + pitch_I + pitch_D, 1.0f);

    // Yaw
    float yaw_target = ws::rc_yaw() * rate_max_yaw;
    float yaw_error = yaw_target - ws::gyro_z();
    float yaw_P = Kp_yaw * yaw_error;
    yaw_integral += yaw_error * dt;
    yaw_integral = clamp(yaw_integral, integral_limit);
    float yaw_I = Ki_yaw * yaw_integral;
    float yaw_D = Kd_yaw * (yaw_error - yaw_prev_error) / dt;
    yaw_prev_error = yaw_error;
    float yaw_cmd = clamp(yaw_P + yaw_I + yaw_D, 1.0f);

    // =====================================================================
    // TODO: Custom motor mixer from first principles
    // カスタムモーターミキサーを第一原理から実装
    // =====================================================================
    //
    // The standard X-quad mixer computes each motor's contribution
    // from total thrust (T), roll torque, pitch torque, and yaw torque.
    //
    // Equations:
    //   M1 (FR) = T/4 + roll/(4*L) - pitch/(4*L) - yaw/(4*kq)
    //   M2 (RR) = T/4 + roll/(4*L) + pitch/(4*L) + yaw/(4*kq)
    //   M3 (RL) = T/4 - roll/(4*L) + pitch/(4*L) - yaw/(4*kq)
    //   M4 (FL) = T/4 - roll/(4*L) - pitch/(4*L) + yaw/(4*kq)
    //
    // Where:
    //   T     = throttle (total thrust command, 0.0 to 1.0)
    //   roll  = roll_cmd (roll torque command)
    //   pitch = pitch_cmd (pitch torque command)
    //   yaw   = yaw_cmd (yaw torque command)
    //   L     = arm length (0.023 m)
    //   kq    = torque coefficient (0.01)
    //
    // After computing, clamp each motor to [0.0, 1.0]

    float m1 = 0.0f;  // TODO: FR motor
    float m2 = 0.0f;  // TODO: RR motor
    float m3 = 0.0f;  // TODO: RL motor
    float m4 = 0.0f;  // TODO: FL motor

    // TODO: Clamp motor values to [0.0, 1.0]
    // ヒント: if (m1 < 0.0f) m1 = 0.0f; if (m1 > 1.0f) m1 = 1.0f;

    // Apply to individual motors (NOT motor_mixer!)
    // 個別モーターに適用（motor_mixer は使わない！）
    ws::motor_set_duty(1, m1);
    ws::motor_set_duty(2, m2);
    ws::motor_set_duty(3, m3);
    ws::motor_set_duty(4, m4);

    // Debug print (2Hz)
    if (tick % 200 == 0) {
        ws::print("M1:%.2f M2:%.2f M3:%.2f M4:%.2f", m1, m2, m3, m4);
    }
}
