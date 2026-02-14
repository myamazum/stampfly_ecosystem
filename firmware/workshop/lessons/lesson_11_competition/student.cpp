#include "workshop_api.hpp"

// =========================================================================
// Lesson 11: Hover Time Competition
// レッスン 11: ホバリングタイム競技
// =========================================================================
//
// Goal: Optimize your rate PID gains for the longest hover time.
// 目標: 角速度PIDゲインを最適化し、最長ホバリングタイムを目指す
//
// This is the same rate PID structure from Lesson 6.
// Tune the gains below to achieve the best stability!
// レッスン6と同じ角速度PID構造です。
// 下のゲインを調整して最高の安定性を目指しましょう！
//
// Block diagram / ブロック線図:
//
//   stick -->[scale]--> target -->(+)--> error -->[PID]--> motor_mixer
//                                  ^(-)
//                                  |
//                                 gyro

// =====================================================================
// PID gains - TUNE THESE FOR COMPETITION!
// PIDゲイン - 競技に向けてここを調整！
// =====================================================================

// Roll/Pitch gains / ロール・ピッチゲイン
static float Kp = 0.5f;      // TODO: Tune! / 調整せよ！
static float Ki = 0.3f;      // TODO: Tune! / 調整せよ！
static float Kd = 0.005f;    // TODO: Tune! / 調整せよ！

// Yaw gains / ヨーゲイン
static float Kp_yaw = 2.0f;  // TODO: Tune! / 調整せよ！
static float Ki_yaw = 0.5f;  // TODO: Tune! / 調整せよ！
static float Kd_yaw = 0.01f; // TODO: Tune! / 調整せよ！

// Limits / リミット
static const float integral_limit = 0.5f; // Anti-windup limit / アンチワインドアップ
static const float rate_max_rp  = 1.0f;   // Max roll/pitch rate [rad/s]
static const float rate_max_yaw = 5.0f;   // Max yaw rate [rad/s]

// State variables / 状態変数
static float roll_integral = 0.0f, roll_prev_error = 0.0f;
static float pitch_integral = 0.0f, pitch_prev_error = 0.0f;
static float yaw_integral = 0.0f, yaw_prev_error = 0.0f;
static uint32_t tick = 0;

// Clamp helper / クランプ補助関数
static float clamp(float val, float lim)
{
    if (val >  lim) return  lim;
    if (val < -lim) return -lim;
    return val;
}

void setup()
{
    ws::print("Lesson 11: Hover Time Competition");
    ws::print("Tune your PID gains and hover as long as you can!");
    // ゲインを調整して、できるだけ長くホバリングしよう！
}

void loop_400Hz(float dt)
{
    tick++;

    if (!ws::is_armed()) {
        ws::motor_stop_all();
        // Reset state when disarmed / ディスアーム時にリセット
        roll_integral = 0.0f;  roll_prev_error = 0.0f;
        pitch_integral = 0.0f; pitch_prev_error = 0.0f;
        yaw_integral = 0.0f;   yaw_prev_error = 0.0f;
        ws::led_color(0, 0, 50);  // Blue = disarmed / 青 = 非ARM
        return;
    }

    ws::led_color(0, 50, 0);  // Green = armed / 緑 = ARM

    float throttle = ws::rc_throttle();

    // =================================================================
    // Roll axis PID / ロール軸PID
    // =================================================================
    float roll_target = ws::rc_roll() * rate_max_rp;
    float roll_error  = roll_target - ws::gyro_x();

    // P term / P項
    float roll_P = Kp * roll_error;

    // I term with anti-windup / I項（アンチワインドアップ付き）
    roll_integral += roll_error * dt;
    roll_integral = clamp(roll_integral, integral_limit);
    float roll_I = Ki * roll_integral;

    // D term / D項
    float roll_D = Kd * (roll_error - roll_prev_error) / dt;
    roll_prev_error = roll_error;

    float roll_output = clamp(roll_P + roll_I + roll_D, 1.0f);

    // =================================================================
    // Pitch axis PID / ピッチ軸PID
    // =================================================================
    float pitch_target = ws::rc_pitch() * rate_max_rp;
    float pitch_error  = pitch_target - ws::gyro_y();

    float pitch_P = Kp * pitch_error;

    pitch_integral += pitch_error * dt;
    pitch_integral = clamp(pitch_integral, integral_limit);
    float pitch_I = Ki * pitch_integral;

    float pitch_D = Kd * (pitch_error - pitch_prev_error) / dt;
    pitch_prev_error = pitch_error;

    float pitch_output = clamp(pitch_P + pitch_I + pitch_D, 1.0f);

    // =================================================================
    // Yaw axis PID / ヨー軸PID
    // =================================================================
    float yaw_target = ws::rc_yaw() * rate_max_yaw;
    float yaw_error  = yaw_target - ws::gyro_z();

    float yaw_P = Kp_yaw * yaw_error;

    yaw_integral += yaw_error * dt;
    yaw_integral = clamp(yaw_integral, integral_limit);
    float yaw_I = Ki_yaw * yaw_integral;

    float yaw_D = Kd_yaw * (yaw_error - yaw_prev_error) / dt;
    yaw_prev_error = yaw_error;

    float yaw_output = clamp(yaw_P + yaw_I + yaw_D, 1.0f);

    // =================================================================
    // Apply to motors / モーターに適用
    // =================================================================
    ws::motor_mixer(throttle, roll_output, pitch_output, yaw_output);

    // =================================================================
    // Telemetry (10Hz) / テレメトリ送信 (10Hz)
    // =================================================================
    if (tick % 40 == 0) {
        ws::telemetry_send("roll_err", roll_error);
        ws::telemetry_send("pitch_err", pitch_error);
        ws::telemetry_send("roll_out", roll_output);
        ws::telemetry_send("pitch_out", pitch_output);
        ws::telemetry_send("throttle", throttle);
    }
}
