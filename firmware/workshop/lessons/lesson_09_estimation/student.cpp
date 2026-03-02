#include "workshop_api.hpp"
#include <cmath>

// Complementary filter state
// 相補フィルタの状態変数
static float cf_roll = 0.0f;
static float cf_pitch = 0.0f;
static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 9: Attitude Estimation");

    // TODO: Set your WiFi channel (1, 6, or 11)
    // TODO: 自分のWiFiチャンネルを設定する（1, 6, 11のいずれか）
    // ws::set_channel(1);
}

void loop_400Hz(float dt)
{
    tick++;

    // Read sensors / センサ値を読み取る
    float gx = ws::gyro_x();
    float gy = ws::gyro_y();
    float ax = ws::accel_x();
    float ay = ws::accel_y();
    float az = ws::accel_z();

    // TODO: Compute accelerometer-based angles
    // 加速度センサからの角度を計算する
    // Hint: accel_roll  = atan2f(ay, az)
    //       accel_pitch = atan2f(-ax, az)
    // float accel_roll  = ???;
    // float accel_pitch = ???;

    // TODO: Implement complementary filter
    // 相補フィルタを実装する
    // Formula: angle = alpha * (angle + gyro * dt) + (1 - alpha) * accel_angle
    // alpha = 0.98 (trust gyroscope 98%, accelerometer 2%)
    // cf_roll  = ???;
    // cf_pitch = ???;

    // TODO: Get ESKF reference values for comparison
    // 比較用にESKFの推定値を取得する
    // float eskf_roll  = ws::estimated_roll();
    // float eskf_pitch = ws::estimated_pitch();

    // TODO: Print values every 200ms (80 ticks)
    // 200ms毎に値を表示する（CF vs ESKF を比較）
    // 200ms毎に値を表示する
}
