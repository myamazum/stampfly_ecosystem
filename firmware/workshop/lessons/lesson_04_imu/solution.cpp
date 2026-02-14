#include "workshop_api.hpp"

// =========================================================================
// Lesson 4: IMU Sensor - Solution
// レッスン 4: IMUセンサ - 解答
// =========================================================================

static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 4: IMU Sensor - Solution");
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

    // Send via WiFi telemetry (viewable with sf log wifi)
    // WiFiテレメトリで送信（sf log wifi で確認可能）
    ws::telemetry_send("gyro_x", gx);
    ws::telemetry_send("gyro_y", gy);
    ws::telemetry_send("gyro_z", gz);
    ws::telemetry_send("accel_z", az);

    // Print every 100ms
    // 100ms毎に表示
    if (tick % 40 == 0) {
        ws::print("G=(%.3f,%.3f,%.3f) A=(%.2f,%.2f,%.2f)",
                  gx, gy, gz, ax, ay, az);
    }
}
