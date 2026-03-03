#include "workshop_api.hpp"

// =========================================================================
// Lesson 6: System Modeling - Model-Based Gain Design
// レッスン 6: システムモデリング - モデルベースゲイン設計
// =========================================================================
//
// Goal: Derive the plant transfer function and design P gains from
//       the second-order closed-loop model.
// 目標: プラント伝達関数を導出し、2次系の閉ループモデルから
//       Pゲインを設計する
//
// Plant model:  G_p(s) = K / (s * (tau_m * s + 1))
// プラントモデル: G_p(s) = K / (s * (tau_m * s + 1))
//
// Closed-loop with P control:
//   G_cl(s) = Kp*K / (tau_m*s^2 + s + Kp*K)
// P制御の閉ループ:
//   G_cl(s) = Kp*K / (tau_m*s^2 + s + Kp*K)
//
// Design formula:
//   Kp = 1 / (4 * zeta^2 * K * tau_m)
// 設計式:
//   Kp = 1 / (4 * zeta^2 * K * tau_m)

// Physical parameters from system identification
// システム同定による物理パラメータ
static const float tau_m = 0.02f;    // Motor time constant [s] / モータ時定数
static const float K_roll  = 102.0f; // Effective plant gain (roll) / 実効プラントゲイン
static const float K_pitch =  70.0f; // Effective plant gain (pitch)
static const float K_yaw   =  19.0f; // Effective plant gain (yaw)

// Rate limits
// レート制限
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
    ws::print("Lesson 6: System Modeling");

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

    ws::led_color(0, 50, 0);
    float throttle = ws::rc_throttle();

    // =====================================================================
    // TODO: Model-based Kp design
    // モデルベース Kp 設計
    // =====================================================================
    //
    // Step 1: Choose a target damping ratio zeta
    // ステップ1: 目標減衰比 zeta を選ぶ
    //
    //   zeta = 0.5 -> underdamped (oscillatory) / 不足減衰（振動的）
    //   zeta = 0.7 -> slightly underdamped (fast, small overshoot) / やや不足減衰
    //   zeta = 1.0 -> critically damped (no oscillation) / 臨界減衰
    //
    float zeta = 0.7f;  // Try changing this! / この値を変えてみよう！

    // Step 2: Compute per-axis Kp from the design formula
    // ステップ2: 設計式から軸ごとの Kp を計算
    //
    //   Kp = 1 / (4 * zeta^2 * K * tau_m)
    //
    // TODO: Calculate Kp for each axis
    float Kp_roll  = 0.0f;  // TODO: Compute from K_roll, zeta, tau_m
    float Kp_pitch = 0.0f;  // TODO: Compute from K_pitch, zeta, tau_m
    float Kp_yaw   = 0.0f;  // TODO: Compute from K_yaw, zeta, tau_m

    // Step 3: P control with per-axis gains
    // ステップ3: 軸ごとのゲインで P 制御
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

    // Debug print (2Hz)
    if (tick % 200 == 0) {
        ws::print("zeta=%.2f Kp_r=%.3f Kp_p=%.3f Kp_y=%.3f",
                  zeta, Kp_roll, Kp_pitch, Kp_yaw);
    }
}
