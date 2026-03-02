#include "workshop_api.hpp"

// =========================================================================
// Lesson 4: IMU Sensor
// レッスン 4: IMUセンサ
// =========================================================================
//
// Goal: Read gyroscope and accelerometer values, display via serial monitor.
// 目標: ジャイロと加速度センサの値を読み取り、シリアルモニタで確認する
//
// Coordinate system (NED):
// 座標系（NED: 北東下）:
//   X = forward / 前方
//   Y = right   / 右方
//   Z = down    / 下方

void setup()
{
    ws::print("Lesson 4: IMU Sensor");

    // TODO: Set your WiFi channel (1, 6, or 11)
    // TODO: 自分のWiFiチャンネルを設定する（1, 6, 11のいずれか）
    // ws::set_channel(1);
}

void loop_400Hz(float dt)
{
    // TODO: Read gyroscope values
    // TODO: ジャイロ値を読み取る
    // float gx = ws::gyro_x();  // Roll rate [rad/s] / ロール角速度
    // float gy = ws::gyro_y();  // Pitch rate [rad/s] / ピッチ角速度
    // float gz = ws::gyro_z();  // Yaw rate [rad/s] / ヨー角速度

    // TODO: Read accelerometer values
    // TODO: 加速度センサ値を読み取る
    // float ax = ws::accel_x();  // Forward [m/s^2] / 前方加速度
    // float ay = ws::accel_y();  // Right [m/s^2] / 右方加速度
    // float az = ws::accel_z();  // Down [m/s^2] / 下方加速度 (静止時 ≈ 9.81)

    // TODO: Print values every 100ms (40 ticks at 400Hz)
    // TODO: 100ms毎に値を表示（400Hzで40ティック）
}
