#include "workshop_api.hpp"

// =========================================================================
// Lesson 7: System Identification
// レッスン 7: システム同定
// =========================================================================
//
// Goal: Fly with two Kp configurations and compare responses with
//       the L6 model predictions. Verify model parameters from data.
// 目標: 2種類のKp設定で飛行し、L6のモデル予測と応答を比較する。
//       データからモデルパラメータを検証する。
//
// Mode 0: L5 uniform Kp (Kp=0.5 all axes)
// Mode 1: L6 model-based Kp (per-axis, zeta=0.7)

static uint32_t tick = 0;

// --- Kp mode ---
// 0 = L5 uniform, 1 = L6 model-based
static int kp_mode = 0;

// Physical parameters from L6
// L6 の物理パラメータ
static const float tau_m = 0.02f;
static const float K_roll  = 102.0f;
static const float K_pitch =  70.0f;
static const float K_yaw   =  19.0f;

// Rate limits
// レート制限
static const float rate_max_rp  = 1.0f;
static const float rate_max_yaw = 5.0f;

static float clamp(float val, float lim)
{
    if (val >  lim) return  lim;
    if (val < -lim) return -lim;
    return val;
}

void setup()
{
    ws::print("Lesson 7: System Identification");

    // TODO: Set your WiFi channel (1, 6, or 11)
    // TODO: 自分のWiFiチャンネルを設定する（1, 6, 11のいずれか）
    // ws::set_channel(1);
}

void loop_400Hz(float dt)
{
    tick++;

    if (!ws::is_armed()) {
        ws::motor_stop_all();
        ws::led_color(0, 0, 50);
        return;
    }

    float throttle = ws::rc_throttle();

    // =====================================================================
    // Kp mode selection
    // Kp モード選択
    // =====================================================================
    // TODO: Switch kp_mode between 0 and 1
    //       (e.g., change the value here and re-flash, or
    //        implement a stick-based toggle)
    // ヒント: kp_mode の値をここで変えて再書き込みする

    float Kp_roll_val, Kp_pitch_val, Kp_yaw_val;

    if (kp_mode == 0) {
        // Mode 0: L5 uniform Kp
        // モード 0: L5 の一律 Kp
        Kp_roll_val  = 0.5f;
        Kp_pitch_val = 0.5f;
        Kp_yaw_val   = 2.0f;
        ws::led_color(0, 50, 0);   // Green = Mode 0
    } else {
        // Mode 1: L6 model-based Kp (zeta = 0.7)
        // モード 1: L6 のモデルベース Kp (zeta = 0.7)
        // TODO: Calculate Kp from the design formula
        //   Kp = 1 / (4 * zeta^2 * K * tau_m)
        float zeta = 0.7f;
        Kp_roll_val  = 0.0f;  // TODO: compute from K_roll
        Kp_pitch_val = 0.0f;  // TODO: compute from K_pitch
        Kp_yaw_val   = 0.0f;  // TODO: compute from K_yaw
        ws::led_color(0, 0, 50);   // Blue = Mode 1
    }

    // =====================================================================
    // P control (same structure as L5/L6)
    // P 制御（L5/L6 と同じ構造）
    // =====================================================================
    float roll_target  = ws::rc_roll()  * rate_max_rp;
    float pitch_target = ws::rc_pitch() * rate_max_rp;
    float yaw_target   = ws::rc_yaw()   * rate_max_yaw;

    float roll_cmd  = Kp_roll_val  * (roll_target  - ws::gyro_x());
    float pitch_cmd = Kp_pitch_val * (pitch_target - ws::gyro_y());
    float yaw_cmd   = Kp_yaw_val   * (yaw_target   - ws::gyro_z());

    ws::motor_mixer(throttle,
                    clamp(roll_cmd,  1.0f),
                    clamp(pitch_cmd, 1.0f),
                    clamp(yaw_cmd,   1.0f));

    // =====================================================================
    // Debug print (2Hz)
    // デバッグ出力 (2Hz)
    // =====================================================================
    if (tick % 200 == 0) {
        ws::print("Mode=%d Kp_r=%.3f Kp_p=%.3f Kp_y=%.3f",
                  kp_mode, Kp_roll_val, Kp_pitch_val, Kp_yaw_val);
    }
}
