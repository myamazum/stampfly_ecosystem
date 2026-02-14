#include "workshop_api.hpp"

// =========================================================================
// Lesson 7: Telemetry + Step Response - Solution
// レッスン 7: テレメトリ + ステップ応答 - 解答
// =========================================================================

// PID gains from Lesson 6
// Lesson 6 の PID ゲイン
static const float Kp_roll = 0.5f, Ki_roll = 0.3f, Kd_roll = 0.005f;
static const float Kp_pitch = 0.5f, Ki_pitch = 0.3f, Kd_pitch = 0.005f;
static const float Kp_yaw = 2.0f, Ki_yaw = 0.5f, Kd_yaw = 0.01f;

static const float integral_limit = 0.5f;
static const float output_limit = 1.0f;
static const float rate_max_rp = 1.0f;
static const float rate_max_yaw = 5.0f;

// PID state
// PID状態変数
static float roll_integral = 0.0f, roll_prev_error = 0.0f;
static float pitch_integral = 0.0f, pitch_prev_error = 0.0f;
static float yaw_integral = 0.0f, yaw_prev_error = 0.0f;

static float clamp(float val, float lim)
{
    if (val >  lim) return  lim;
    if (val < -lim) return -lim;
    return val;
}

// --- Step response experiment ---
// ステップ応答実験
static uint32_t tick = 0;
static bool step_active = false;
static uint32_t step_start_tick = 0;

// Step parameters
// ステップパラメータ
static const float step_rate      = 0.5f;   // Step amplitude [rad/s] / ステップ振幅
static const uint32_t step_delay  = 800;    // Wait 2s before step / ステップ前の待機2秒
static const uint32_t step_duration = 400;  // Step for 1s / ステップ1秒間
static const uint32_t total_duration = 1600; // Total 4s / 合計4秒

void setup()
{
    ws::print("Lesson 7: Telemetry + Step Response - Solution");
    ws::print("ARM and raise throttle > 30%% to start experiment");
}

void loop_400Hz(float dt)
{
    tick++;

    if (!ws::is_armed()) {
        ws::motor_stop_all();
        roll_integral = 0.0f; roll_prev_error = 0.0f;
        pitch_integral = 0.0f; pitch_prev_error = 0.0f;
        yaw_integral = 0.0f; yaw_prev_error = 0.0f;
        step_active = false;
        step_start_tick = 0;
        ws::led_color(0, 0, 50);  // Blue = disarmed / 青 = 非ARM
        return;
    }

    float throttle = ws::rc_throttle();

    // =====================================================================
    // Step response experiment
    // =====================================================================

    // Start experiment when throttle > 30%
    // スロットル30%超で実験開始
    if (!step_active && throttle > 0.3f) {
        step_active = true;
        step_start_tick = tick;
        ws::print(">>> Step experiment started! Hold drone steady.");
    }

    uint32_t elapsed = step_active ? (tick - step_start_tick) : 0;

    // Determine step target based on phase
    // フェーズに応じたステップ目標の決定
    float roll_step = 0.0f;
    if (step_active) {
        if (elapsed >= step_delay && elapsed < step_delay + step_duration) {
            roll_step = step_rate;  // Apply step / ステップ入力
        }
        // else: 0 (baseline or recovery) / ベースラインまたは回復
    }

    // Override roll target with step input during experiment
    // 実験中はステップ入力でロール目標を上書き
    float roll_target = step_active ? roll_step : ws::rc_roll() * rate_max_rp;
    float pitch_target = step_active ? 0.0f : ws::rc_pitch() * rate_max_rp;
    float yaw_target = step_active ? 0.0f : ws::rc_yaw() * rate_max_yaw;

    // =====================================================================
    // Roll PID / ロール軸 PID
    // =====================================================================
    float roll_actual = ws::gyro_x();
    float roll_error  = roll_target - roll_actual;

    float roll_P = Kp_roll * roll_error;

    roll_integral += roll_error * dt;
    roll_integral = clamp(roll_integral, integral_limit);
    float roll_I = Ki_roll * roll_integral;

    float roll_D = Kd_roll * (roll_error - roll_prev_error) / dt;
    roll_prev_error = roll_error;

    float roll_output = clamp(roll_P + roll_I + roll_D, output_limit);

    // =====================================================================
    // Pitch PID / ピッチ軸 PID
    // =====================================================================
    float pitch_actual = ws::gyro_y();
    float pitch_error  = pitch_target - pitch_actual;

    float pitch_P = Kp_pitch * pitch_error;

    pitch_integral += pitch_error * dt;
    pitch_integral = clamp(pitch_integral, integral_limit);
    float pitch_I = Ki_pitch * pitch_integral;

    float pitch_D = Kd_pitch * (pitch_error - pitch_prev_error) / dt;
    pitch_prev_error = pitch_error;

    float pitch_output = clamp(pitch_P + pitch_I + pitch_D, output_limit);

    // =====================================================================
    // Yaw PID / ヨー軸 PID
    // =====================================================================
    float yaw_actual = ws::gyro_z();
    float yaw_error  = yaw_target - yaw_actual;

    float yaw_P = Kp_yaw * yaw_error;

    yaw_integral += yaw_error * dt;
    yaw_integral = clamp(yaw_integral, integral_limit);
    float yaw_I = Ki_yaw * yaw_integral;

    float yaw_D = Kd_yaw * (yaw_error - yaw_prev_error) / dt;
    yaw_prev_error = yaw_error;

    float yaw_output = clamp(yaw_P + yaw_I + yaw_D, output_limit);

    // =====================================================================
    // Apply to motors / モータに適用
    // =====================================================================
    ws::motor_mixer(throttle, roll_output, pitch_output, yaw_output);

    // =====================================================================
    // Telemetry: send at 400Hz during experiment
    // テレメトリ: 実験中は400Hzで送信
    // =====================================================================
    if (step_active && elapsed < total_duration) {
        ws::telemetry_send("step_target", roll_step);
        ws::telemetry_send("step_actual", roll_actual);
        ws::telemetry_send("step_error",  roll_error);
        ws::telemetry_send("step_output", roll_output);
        ws::telemetry_send("step_P",      roll_P);
        ws::telemetry_send("step_I",      roll_I);
        ws::telemetry_send("step_D",      roll_D);
        ws::telemetry_send("throttle",    throttle);

        // LED feedback / LED表示
        if (elapsed < step_delay) {
            ws::led_color(50, 50, 0);    // Yellow = waiting / 黄 = 待機中
        } else if (elapsed < step_delay + step_duration) {
            ws::led_color(50, 0, 0);     // Red = step active / 赤 = ステップ中
        } else {
            ws::led_color(0, 50, 0);     // Green = recovery / 緑 = 回復中
        }

        // Phase progress print (2Hz)
        // フェーズ進捗表示 (2Hz)
        if (tick % 200 == 0) {
            if (elapsed < step_delay) {
                ws::print("Phase: BASELINE  t=%.1fs", elapsed / 400.0f);
            } else if (elapsed < step_delay + step_duration) {
                ws::print("Phase: STEP      t=%.1fs  actual=%.3f",
                          elapsed / 400.0f, roll_actual);
            } else {
                ws::print("Phase: RECOVERY  t=%.1fs  actual=%.3f",
                          elapsed / 400.0f, roll_actual);
            }
        }
    }

    // End experiment / 実験終了
    if (step_active && elapsed >= total_duration) {
        ws::print(">>> Step experiment complete! Use 'sf log wifi' to analyze.");
        step_active = false;
        ws::led_color(0, 0, 50);  // Blue = done / 青 = 完了
    }

    // Normal telemetry when not in experiment (10Hz)
    // 実験外では通常テレメトリ (10Hz)
    if (!step_active && tick % 40 == 0) {
        ws::telemetry_send("roll_rate", roll_actual);
        ws::telemetry_send("pitch_rate", pitch_actual);
        ws::telemetry_send("yaw_rate", yaw_actual);
        ws::telemetry_send("throttle", throttle);
    }
}
