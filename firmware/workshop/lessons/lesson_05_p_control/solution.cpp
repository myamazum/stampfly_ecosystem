#include "workshop_api.hpp"

// =========================================================================
// Lesson 5: Rate P-Control + First Flight - Solution
// レッスン 5: レートP制御 + 初フライト - 解答
// =========================================================================

static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 5: Rate P-Control - Solution");
}

void loop_400Hz(float dt)
{
    tick++;

    // Safety: only run control when armed
    // 安全: ARM状態のときだけ制御を実行
    if (!ws::is_armed()) {
        ws::motor_stop_all();
        ws::led_color(0, 0, 50);  // Blue = disarmed / 青 = ディスアーム
        return;
    }

    ws::led_color(0, 50, 0);  // Green = armed / 緑 = アーム

    float throttle = ws::rc_throttle();

    // --- P gains ---
    // P ゲイン
    float Kp_roll  = 0.5f;
    float Kp_pitch = 0.5f;
    float Kp_yaw   = 2.0f;

    // --- Maximum angular rate [rad/s] ---
    // 最大角速度 [rad/s]
    float rate_max_rp  = 1.0f;   // roll/pitch
    float rate_max_yaw = 5.0f;   // yaw

    // --- Roll axis ---
    // ロール軸
    float roll_target = ws::rc_roll() * rate_max_rp;
    float roll_actual = ws::gyro_x();
    float roll_error  = roll_target - roll_actual;
    float roll_output = Kp_roll * roll_error;

    // --- Pitch axis ---
    // ピッチ軸
    float pitch_target = ws::rc_pitch() * rate_max_rp;
    float pitch_actual = ws::gyro_y();
    float pitch_error  = pitch_target - pitch_actual;
    float pitch_output = Kp_pitch * pitch_error;

    // --- Yaw axis ---
    // ヨー軸
    float yaw_target = ws::rc_yaw() * rate_max_yaw;
    float yaw_actual = ws::gyro_z();
    float yaw_error  = yaw_target - yaw_actual;
    float yaw_output = Kp_yaw * yaw_error;

    // --- Apply to motors ---
    // モーターに適用
    ws::motor_mixer(throttle, roll_output, pitch_output, yaw_output);

    // --- Telemetry (10Hz) ---
    // テレメトリ (10Hz)
    if (tick % 40 == 0) {
        ws::telemetry_send("roll_target", roll_target);
        ws::telemetry_send("roll_actual", roll_actual);
        ws::telemetry_send("roll_error",  roll_error);
        ws::telemetry_send("pitch_target", pitch_target);
        ws::telemetry_send("pitch_actual", pitch_actual);
        ws::telemetry_send("yaw_target", yaw_target);
        ws::telemetry_send("yaw_actual", yaw_actual);
        ws::telemetry_send("throttle", throttle);
    }

    // --- Debug print (2Hz) ---
    // デバッグ出力 (2Hz)
    if (tick % 200 == 0) {
        ws::print("R:%.2f/%.2f P:%.2f/%.2f Y:%.2f/%.2f T:%.2f",
                  roll_actual, roll_target,
                  pitch_actual, pitch_target,
                  yaw_actual, yaw_target,
                  throttle);
    }
}
