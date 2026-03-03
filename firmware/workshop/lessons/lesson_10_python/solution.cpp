#include "workshop_api.hpp"
#include <cmath>

// PID state (rate control)
// PID状態変数（角速度制御）
static float roll_int = 0, pitch_int = 0, yaw_int = 0;
static float roll_prev = 0, pitch_prev = 0, yaw_prev = 0;

void setup()
{
    ws::print("Lesson 10: Python SDK - Stable flight mode (Solution)");

    // Set WiFi channel (use 1, 6, or 11 to avoid interference)
    // WiFiチャンネルを設定（混信を避けるため1, 6, 11のいずれかを使用）
    ws::set_channel(1);
}

void loop_400Hz(float dt)
{
    // Standard PID control (same as Lesson 8 solution)
    // This provides stable flight for Python SDK control
    // 標準PID制御（Lesson 8の解答と同じ）
    // Python SDKからの操作のために安定した飛行を提供する

    constexpr float Kp = 0.5f, Ki = 0.3f, Kd = 0.005f;
    constexpr float Kp_yaw = 2.0f, Ki_yaw = 0.5f, Kd_yaw = 0.01f;
    constexpr float rate_max = 1.0f, yaw_rate_max = 5.0f;
    constexpr float int_limit = 0.5f;

    // RC input -> rate target
    // RC入力 -> 角速度目標
    float roll_target  = ws::rc_roll()  * rate_max;
    float pitch_target = ws::rc_pitch() * rate_max;
    float yaw_target   = ws::rc_yaw()   * yaw_rate_max;

    // Error
    float roll_error  = roll_target  - ws::gyro_x();
    float pitch_error = pitch_target - ws::gyro_y();
    float yaw_error   = yaw_target   - ws::gyro_z();

    // Integral with anti-windup
    // 積分（アンチワインドアップ付き）
    roll_int  += roll_error  * dt;
    pitch_int += pitch_error * dt;
    yaw_int   += yaw_error   * dt;

    if (roll_int  >  int_limit) roll_int  =  int_limit;
    if (roll_int  < -int_limit) roll_int  = -int_limit;
    if (pitch_int >  int_limit) pitch_int =  int_limit;
    if (pitch_int < -int_limit) pitch_int = -int_limit;
    if (yaw_int   >  int_limit) yaw_int   =  int_limit;
    if (yaw_int   < -int_limit) yaw_int   = -int_limit;

    // Derivative
    // 微分
    float roll_d  = (roll_error  - roll_prev)  / dt;
    float pitch_d = (pitch_error - pitch_prev) / dt;
    float yaw_d   = (yaw_error   - yaw_prev)   / dt;
    roll_prev  = roll_error;
    pitch_prev = pitch_error;
    yaw_prev   = yaw_error;

    // PID output
    // PID出力
    float roll_out  = Kp     * roll_error  + Ki     * roll_int  + Kd     * roll_d;
    float pitch_out = Kp     * pitch_error + Ki     * pitch_int + Kd     * pitch_d;
    float yaw_out   = Kp_yaw * yaw_error   + Ki_yaw * yaw_int   + Kd_yaw * yaw_d;

    ws::motor_mixer(ws::rc_throttle(), roll_out, pitch_out, yaw_out);
}
