#include "workshop_api.hpp"

// =========================================================================
// Lesson 8: System Modeling - Model-Based Gain Design - Solution
// レッスン 8: システムモデリング - モデルベースゲイン設計 - 解答
// =========================================================================

// Physical parameters from system identification
// システム同定による物理パラメータ
static const float tau_m = 0.02f;    // Motor time constant [s] / モータ時定数
static const float K_roll  = 102.0f; // Effective plant gain (roll) / 実効プラントゲイン
static const float K_pitch =  70.0f; // Effective plant gain (pitch)
static const float K_yaw   =  19.0f; // Effective plant gain (yaw)

// Rate limits / レート制限
static const float rate_max_rp  = 1.0f;   // [rad/s]
static const float rate_max_yaw = 5.0f;   // [rad/s]

static uint32_t tick = 0;

static float clamp(float val, float lim)
{
    if (val >  lim) return  lim;
    if (val < -lim) return -lim;
    return val;
}

void setup()
{
    ws::print("Lesson 8: System Modeling - Solution");

    // Set WiFi channel (use 1, 6, or 11 to avoid interference)
    // WiFiチャンネルを設定（混信を避けるため1, 6, 11のいずれかを使用）
    ws::set_channel(1);
}

void loop_400Hz(float dt)
{
    tick++;

    if (!ws::is_armed()) {
        ws::motor_stop_all();
        ws::led_color(0, 0, 50);
        return;
    }

    ws::led_color(0, 50, 0);
    float throttle = ws::rc_throttle();

    // =====================================================================
    // Model-based Kp design
    // モデルベース Kp 設計
    // =====================================================================
    //
    // Plant:      G_p(s) = K / (s * (tau_m * s + 1))
    // Closed-loop: G_cl(s) = Kp*K / (tau_m*s^2 + s + Kp*K)
    //
    // Design formula: Kp = 1 / (4 * zeta^2 * K * tau_m)
    //
    // zeta = 0.7 gives fast response with small overshoot (~5%)

    float zeta = 0.7f;

    // Per-axis Kp from design formula
    // 軸ごとの Kp を設計式から計算
    float Kp_roll  = 1.0f / (4.0f * zeta * zeta * K_roll  * tau_m);
    float Kp_pitch = 1.0f / (4.0f * zeta * zeta * K_pitch * tau_m);
    float Kp_yaw   = 1.0f / (4.0f * zeta * zeta * K_yaw   * tau_m);

    // Expected values for zeta = 0.7:
    // 期待値 (zeta = 0.7):
    //   Kp_roll  = 1/(4*0.49*102*0.02) = 0.25
    //   Kp_pitch = 1/(4*0.49*70*0.02)  = 0.36
    //   Kp_yaw   = 1/(4*0.49*19*0.02)  = 1.34

    // P control with per-axis gains
    // 軸ごとのゲインで P 制御
    float roll_target  = ws::rc_roll()  * rate_max_rp;
    float pitch_target = ws::rc_pitch() * rate_max_rp;
    float yaw_target   = ws::rc_yaw()   * rate_max_yaw;

    float roll_cmd  = Kp_roll  * (roll_target  - ws::gyro_x());
    float pitch_cmd = Kp_pitch * (pitch_target - ws::gyro_y());
    float yaw_cmd   = Kp_yaw   * (yaw_target   - ws::gyro_z());

    // Apply through mixer
    // ミキサー経由で適用
    ws::motor_mixer(throttle,
                    clamp(roll_cmd,  1.0f),
                    clamp(pitch_cmd, 1.0f),
                    clamp(yaw_cmd,   1.0f));

    // Debug print (2Hz) / デバッグ出力 (2Hz)
    if (tick % 200 == 0) {
        ws::print("zeta=%.2f Kp_r=%.3f Kp_p=%.3f Kp_y=%.3f",
                  zeta, Kp_roll, Kp_pitch, Kp_yaw);
    }
}
