#include "workshop_api.hpp"

// =========================================================================
// Lesson 11: Hover Time Competition - Reference Solution
// レッスン 11: ホバリングタイム競技 - リファレンス解答
// =========================================================================
//
// This is the same as student.cpp - the competition is about YOUR tuning!
// There is no single "correct" solution.
// student.cpp と同じ内容 - 競技は自分のチューニングが勝負！
// 唯一の「正解」はない。

// PID gains (same defaults as student.cpp)
// PIDゲイン（student.cpp と同じデフォルト値）
static float Kp = 0.5f;
static float Ki = 0.3f;
static float Kd = 0.005f;

static float Kp_yaw = 2.0f;
static float Ki_yaw = 0.5f;
static float Kd_yaw = 0.01f;

// Limits / リミット
static const float integral_limit = 0.5f;
static const float rate_max_rp  = 1.0f;
static const float rate_max_yaw = 5.0f;

// State variables / 状態変数
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
    ws::print("Lesson 11: Hover Time Competition - Reference");
}

void loop_400Hz(float dt)
{
    tick++;

    if (!ws::is_armed()) {
        ws::motor_stop_all();
        roll_integral = 0.0f;  roll_prev_error = 0.0f;
        pitch_integral = 0.0f; pitch_prev_error = 0.0f;
        yaw_integral = 0.0f;   yaw_prev_error = 0.0f;
        ws::led_color(0, 0, 50);
        return;
    }

    ws::led_color(0, 50, 0);
    float throttle = ws::rc_throttle();

    // Roll PID / ロール軸PID
    float roll_target = ws::rc_roll() * rate_max_rp;
    float roll_error  = roll_target - ws::gyro_x();
    float roll_P = Kp * roll_error;
    roll_integral += roll_error * dt;
    roll_integral = clamp(roll_integral, integral_limit);
    float roll_I = Ki * roll_integral;
    float roll_D = Kd * (roll_error - roll_prev_error) / dt;
    roll_prev_error = roll_error;
    float roll_output = clamp(roll_P + roll_I + roll_D, 1.0f);

    // Pitch PID / ピッチ軸PID
    float pitch_target = ws::rc_pitch() * rate_max_rp;
    float pitch_error  = pitch_target - ws::gyro_y();
    float pitch_P = Kp * pitch_error;
    pitch_integral += pitch_error * dt;
    pitch_integral = clamp(pitch_integral, integral_limit);
    float pitch_I = Ki * pitch_integral;
    float pitch_D = Kd * (pitch_error - pitch_prev_error) / dt;
    pitch_prev_error = pitch_error;
    float pitch_output = clamp(pitch_P + pitch_I + pitch_D, 1.0f);

    // Yaw PID / ヨー軸PID
    float yaw_target = ws::rc_yaw() * rate_max_yaw;
    float yaw_error  = yaw_target - ws::gyro_z();
    float yaw_P = Kp_yaw * yaw_error;
    yaw_integral += yaw_error * dt;
    yaw_integral = clamp(yaw_integral, integral_limit);
    float yaw_I = Ki_yaw * yaw_integral;
    float yaw_D = Kd_yaw * (yaw_error - yaw_prev_error) / dt;
    yaw_prev_error = yaw_error;
    float yaw_output = clamp(yaw_P + yaw_I + yaw_D, 1.0f);

    // Apply / モーターに適用
    ws::motor_mixer(throttle, roll_output, pitch_output, yaw_output);

    // Telemetry (10Hz) / テレメトリ送信 (10Hz)
    if (tick % 40 == 0) {
        ws::telemetry_send("roll_err", roll_error);
        ws::telemetry_send("pitch_err", pitch_error);
        ws::telemetry_send("roll_out", roll_output);
        ws::telemetry_send("pitch_out", pitch_output);
        ws::telemetry_send("throttle", throttle);
    }
}
