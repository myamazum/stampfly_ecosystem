#include "workshop_api.hpp"

// =========================================================================
// Lesson 8: Modeling - Custom Motor Mixer - Solution
// レッスン 8: モデリング - カスタムモーターミキサー - 解答
// =========================================================================

// Physical parameters / 物理パラメータ
static const float L = 0.023f;      // Arm length [m] / アーム長
static const float kq = 0.01f;      // Torque-to-thrust ratio / トルク対推力比

// PID gains / PIDゲイン
static const float Kp_roll = 0.5f, Ki_roll = 0.3f, Kd_roll = 0.005f;
static const float Kp_pitch = 0.5f, Ki_pitch = 0.3f, Kd_pitch = 0.005f;
static const float Kp_yaw = 2.0f, Ki_yaw = 0.5f, Kd_yaw = 0.01f;
static const float integral_limit = 0.5f;
static const float rate_max_rp = 1.0f, rate_max_yaw = 5.0f;

// PID state / PID状態変数
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

// Clamp motor duty to valid range [0.0, 1.0]
// モーターデューティを有効範囲 [0.0, 1.0] にクランプ
static float clamp_duty(float duty)
{
    if (duty < 0.0f) return 0.0f;
    if (duty > 1.0f) return 1.0f;
    return duty;
}

void setup()
{
    ws::print("Lesson 8: Modeling - Custom Mixer - Solution");
    ws::print("L=%.3f m, kq=%.3f", L, kq);
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

    // =====================================================================
    // PID control (same as Lesson 6)
    // PID制御（レッスン6と同じ）
    // =====================================================================

    // Roll PID / ロール軸PID
    float roll_target = ws::rc_roll() * rate_max_rp;
    float roll_error = roll_target - ws::gyro_x();
    float roll_P = Kp_roll * roll_error;
    roll_integral += roll_error * dt;
    roll_integral = clamp(roll_integral, integral_limit);
    float roll_I = Ki_roll * roll_integral;
    float roll_D = Kd_roll * (roll_error - roll_prev_error) / dt;
    roll_prev_error = roll_error;
    float roll_cmd = clamp(roll_P + roll_I + roll_D, 1.0f);

    // Pitch PID / ピッチ軸PID
    float pitch_target = ws::rc_pitch() * rate_max_rp;
    float pitch_error = pitch_target - ws::gyro_y();
    float pitch_P = Kp_pitch * pitch_error;
    pitch_integral += pitch_error * dt;
    pitch_integral = clamp(pitch_integral, integral_limit);
    float pitch_I = Ki_pitch * pitch_integral;
    float pitch_D = Kd_pitch * (pitch_error - pitch_prev_error) / dt;
    pitch_prev_error = pitch_error;
    float pitch_cmd = clamp(pitch_P + pitch_I + pitch_D, 1.0f);

    // Yaw PID / ヨー軸PID
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
    // Custom motor mixer from first principles
    // 第一原理からのカスタムモーターミキサー
    // =====================================================================
    //
    // X-quad motor mixer derivation:
    // X配置クアッドミキサーの導出:
    //
    //   Total thrust:  T = F1 + F2 + F3 + F4
    //   Roll torque:   tau_roll  = (F1 + F2 - F3 - F4) * L
    //   Pitch torque:  tau_pitch = (-F1 + F2 + F3 - F4) * L
    //   Yaw torque:    tau_yaw   = (-F1 + F2 - F3 + F4) * kq
    //
    // Solving for individual motor forces:
    //   F1 = T/4 + tau_roll/(4*L) - tau_pitch/(4*L) - tau_yaw/(4*kq)
    //   F2 = T/4 + tau_roll/(4*L) + tau_pitch/(4*L) + tau_yaw/(4*kq)
    //   F3 = T/4 - tau_roll/(4*L) + tau_pitch/(4*L) - tau_yaw/(4*kq)
    //   F4 = T/4 - tau_roll/(4*L) - tau_pitch/(4*L) + tau_yaw/(4*kq)

    float T = throttle;        // Total thrust command / 推力指令
    float tau_r = roll_cmd;    // Roll torque command / ロールトルク指令
    float tau_p = pitch_cmd;   // Pitch torque command / ピッチトルク指令
    float tau_y = yaw_cmd;     // Yaw torque command / ヨートルク指令

    // Pre-compute divisors / 除算の事前計算
    float inv_4L  = 1.0f / (4.0f * L);   // = 1/(4*0.023) ~ 10.87
    float inv_4kq = 1.0f / (4.0f * kq);  // = 1/(4*0.01)  = 25.0

    // Motor 1 (FR): +roll, -pitch, -yaw (CW)
    float m1 = T / 4.0f + tau_r * inv_4L - tau_p * inv_4L - tau_y * inv_4kq;

    // Motor 2 (RR): +roll, +pitch, +yaw (CCW)
    float m2 = T / 4.0f + tau_r * inv_4L + tau_p * inv_4L + tau_y * inv_4kq;

    // Motor 3 (RL): -roll, +pitch, -yaw (CW)
    float m3 = T / 4.0f - tau_r * inv_4L + tau_p * inv_4L - tau_y * inv_4kq;

    // Motor 4 (FL): -roll, -pitch, +yaw (CCW)
    float m4 = T / 4.0f - tau_r * inv_4L - tau_p * inv_4L + tau_y * inv_4kq;

    // Clamp to valid duty range
    // デューティ有効範囲にクランプ
    m1 = clamp_duty(m1);
    m2 = clamp_duty(m2);
    m3 = clamp_duty(m3);
    m4 = clamp_duty(m4);

    // Apply directly to individual motors
    // 個別モーターに直接適用
    ws::motor_set_duty(1, m1);
    ws::motor_set_duty(2, m2);
    ws::motor_set_duty(3, m3);
    ws::motor_set_duty(4, m4);

    // =====================================================================
    // Telemetry (10Hz) / テレメトリ送信 (10Hz)
    // =====================================================================
    if (tick % 40 == 0) {
        ws::telemetry_send("m1_duty", m1);
        ws::telemetry_send("m2_duty", m2);
        ws::telemetry_send("m3_duty", m3);
        ws::telemetry_send("m4_duty", m4);
        ws::telemetry_send("roll_cmd", roll_cmd);
        ws::telemetry_send("pitch_cmd", pitch_cmd);
        ws::telemetry_send("yaw_cmd", yaw_cmd);
        ws::telemetry_send("throttle", throttle);
    }

    // Debug print (2Hz) / デバッグ出力 (2Hz)
    if (tick % 200 == 0) {
        ws::print("M1:%.2f M2:%.2f M3:%.2f M4:%.2f  T:%.2f R:%.2f P:%.2f Y:%.2f",
                  m1, m2, m3, m4, throttle, roll_cmd, pitch_cmd, yaw_cmd);
    }
}
