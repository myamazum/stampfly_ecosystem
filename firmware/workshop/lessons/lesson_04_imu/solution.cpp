#include "workshop_api.hpp"

// =========================================================================
// Lesson 4: IMU Sensor - Solution
// レッスン 4: IMUセンサ - 解答
// =========================================================================

static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 4: IMU Sensor - Solution");

    // Set WiFi channel (use 1, 6, or 11 to avoid interference)
    // WiFiチャンネルを設定（混信を避けるため1, 6, 11のいずれかを使用）
    ws::set_channel(1);
}

void loop_400Hz(float dt)
{
    tick++;

    // Read gyroscope and accelerometer
    // ジャイロと加速度センサを読み取る
    float gx = ws::gyro_x();
    float gy = ws::gyro_y();
    float gz = ws::gyro_z();
    float ax = ws::accel_x();
    float ay = ws::accel_y();
    float az = ws::accel_z();

    // Print every 100ms
    // 100ms毎に表示
    if (tick % 40 == 0) {
        ws::print("G=(%.3f,%.3f,%.3f) A=(%.2f,%.2f,%.2f)",
                  gx, gy, gz, ax, ay, az);
    }
}
