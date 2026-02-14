#include "workshop_api.hpp"

// =========================================================================
// Lesson 7: Telemetry + Step Response
// レッスン 7: テレメトリ + ステップ応答
// =========================================================================
//
// Goal: Use WiFi telemetry to capture and analyze the step response
//       of your PID controller.
// 目標: WiFiテレメトリを使ってPIDコントローラのステップ応答を
//       キャプチャし分析する
//
// Experiment: Apply a known step input to roll rate, measure gyro
//             response, and log everything via telemetry.
// 実験: ロールレートに既知のステップ入力を加え、ジャイロ応答を
//       計測し、テレメトリで全てを記録する

// PID gains from Lesson 6
// レッスン6のPIDゲイン
static const float Kp_roll = 0.5f, Ki_roll = 0.3f, Kd_roll = 0.005f;
static const float Kp_pitch = 0.5f, Ki_pitch = 0.3f, Kd_pitch = 0.005f;
static const float Kp_yaw = 2.0f, Ki_yaw = 0.5f, Kd_yaw = 0.01f;

static const float integral_limit = 0.5f;
static const float output_limit = 1.0f;
static const float rate_max_rp = 1.0f;
static const float rate_max_yaw = 5.0f;

// PID state
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
static const float step_rate      = 0.5f;  // Step amplitude [rad/s]
static const uint32_t step_delay  = 800;   // Wait 2s (800 ticks) before step
static const uint32_t step_duration = 400; // Step for 1s (400 ticks)
static const uint32_t total_duration = 1600; // Total experiment 4s

void setup()
{
    ws::print("Lesson 7: Telemetry + Step Response");
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
        ws::led_color(0, 0, 50);
        return;
    }

    float throttle = ws::rc_throttle();

    // =====================================================================
    // Step response experiment
    // ステップ応答実験
    // =====================================================================
    // The experiment starts when throttle > 0.3
    // 実験はスロットル > 0.3 で開始

    if (!step_active && throttle > 0.3f) {
        step_active = true;
        step_start_tick = tick;
        ws::print("Step response experiment started!");
    }

    uint32_t elapsed = step_active ? (tick - step_start_tick) : 0;

    // TODO: Determine the roll step target based on experiment phase
    // ステップ目標をフェーズに応じて決定
    //
    // Phase 1: elapsed < step_delay      --> roll_step = 0 (baseline)
    // Phase 2: step_delay <= elapsed < step_delay + step_duration
    //                                    --> roll_step = step_rate (step!)
    // Phase 3: elapsed >= step_delay + step_duration
    //                                    --> roll_step = 0 (recovery)

    float roll_step = 0.0f;  // TODO: set based on phase

    // Override roll target with step input (ignore stick during experiment)
    // ステップ入力でロール目標を上書き（実験中はスティック無視）
    float roll_target = roll_step;
    float pitch_target = 0.0f;  // Hold pitch at zero
    float yaw_target = 0.0f;    // Hold yaw at zero

    // --- PID (same as Lesson 6) ---
    float roll_actual = ws::gyro_x();
    float roll_error  = roll_target - roll_actual;
    float roll_P = Kp_roll * roll_error;
    roll_integral += roll_error * dt;
    roll_integral = clamp(roll_integral, integral_limit);
    float roll_I = Ki_roll * roll_integral;
    float roll_D = Kd_roll * (roll_error - roll_prev_error) / dt;
    roll_prev_error = roll_error;
    float roll_output = clamp(roll_P + roll_I + roll_D, output_limit);

    float pitch_actual = ws::gyro_y();
    float pitch_error  = pitch_target - pitch_actual;
    float pitch_P = Kp_pitch * pitch_error;
    pitch_integral += pitch_error * dt;
    pitch_integral = clamp(pitch_integral, integral_limit);
    float pitch_I = Ki_pitch * pitch_integral;
    float pitch_D = Kd_pitch * (pitch_error - pitch_prev_error) / dt;
    pitch_prev_error = pitch_error;
    float pitch_output = clamp(pitch_P + pitch_I + pitch_D, output_limit);

    float yaw_actual = ws::gyro_z();
    float yaw_error  = yaw_target - yaw_actual;
    float yaw_P = Kp_yaw * yaw_error;
    yaw_integral += yaw_error * dt;
    yaw_integral = clamp(yaw_integral, integral_limit);
    float yaw_I = Ki_yaw * yaw_integral;
    float yaw_D = Kd_yaw * (yaw_error - yaw_prev_error) / dt;
    yaw_prev_error = yaw_error;
    float yaw_output = clamp(yaw_P + yaw_I + yaw_D, output_limit);

    ws::motor_mixer(throttle, roll_output, pitch_output, yaw_output);

    // =====================================================================
    // TODO: Send telemetry data
    // テレメトリデータを送信
    // =====================================================================
    // Send at 400Hz during the experiment for high-resolution data
    // 実験中は400Hzで送信し、高解像度データを取得

    if (step_active && elapsed < total_duration) {
        // TODO: Send the following via ws::telemetry_send():
        //   "step_target" - the step input (roll_step)
        //   "step_actual" - gyro roll rate (roll_actual)
        //   "step_error"  - tracking error (roll_error)
        //   "step_output" - PID output (roll_output)
        //   "step_P"      - P term (roll_P)
        //   "step_I"      - I term (roll_I)
        //   "step_D"      - D term (roll_D)

        // LED: red during step, green otherwise
        // LED: ステップ中は赤、それ以外は緑
        if (elapsed >= step_delay && elapsed < step_delay + step_duration) {
            ws::led_color(50, 0, 0);
        } else {
            ws::led_color(0, 50, 0);
        }
    }

    // End experiment
    // 実験終了
    if (step_active && elapsed >= total_duration) {
        ws::print("Step response experiment complete!");
        step_active = false;
    }
}
