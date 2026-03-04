#include "workshop_api.hpp"
#include <cmath>

// Complementary filter state
// 相補フィルタの状態変数
static float cf_roll = 0.0f;
static float cf_pitch = 0.0f;
static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 9: Attitude Estimation - Solution");

    // Set WiFi channel (use 1, 6, or 11 to avoid interference)
    // WiFiチャンネルを設定（混信を避けるため1, 6, 11のいずれかを使用）
    ws::set_channel(1);
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

    // Accelerometer-based angles
    // 加速度センサから角度を計算
    float accel_roll  = atan2f(ay, az);
    float accel_pitch = atan2f(-ax, az);

    // Complementary filter
    // 相補フィルタ: ジャイロ98% + 加速度2%
    constexpr float alpha = 0.98f;
    cf_roll  = alpha * (cf_roll  + gx * dt) + (1.0f - alpha) * accel_roll;
    cf_pitch = alpha * (cf_pitch + gy * dt) + (1.0f - alpha) * accel_pitch;

    // ESKF reference for comparison
    // 比較用のESKF推定値
    float eskf_roll  = ws::estimated_roll();
    float eskf_pitch = ws::estimated_pitch();

    // Teleplot output (real-time graph in VSCode Teleplot extension)
    // Teleplot出力（VSCode Teleplot拡張でリアルタイムグラフ化）
    // Decimation: every 4 ticks = 100Hz (to avoid serial bandwidth overload)
    // デシメーション: 4tick毎 = 100Hz（シリアル帯域の負荷軽減）
    if (tick % 4 == 0) {
        ws::print(">cf_roll:%.2f", cf_roll * 57.3f);
        ws::print(">cf_pitch:%.2f", cf_pitch * 57.3f);
        ws::print(">eskf_roll:%.2f", eskf_roll * 57.3f);
        ws::print(">eskf_pitch:%.2f", eskf_pitch * 57.3f);
    }

    // Print every 200ms (80 ticks at 400Hz) for serial monitor
    // 200ms毎にシリアルモニタ用テキスト表示
    if (tick % 80 == 0) {
        ws::print("CF: R=%.1f P=%.1f | ESKF: R=%.1f P=%.1f",
                  cf_roll * 57.3f, cf_pitch * 57.3f,
                  eskf_roll * 57.3f, eskf_pitch * 57.3f);
    }
}
