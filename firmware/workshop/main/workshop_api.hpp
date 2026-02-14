/**
 * @file workshop_api.hpp
 * @brief Workshop Simplified API for Students
 *        学生向けワークショップ簡易API
 *
 * This header provides a simple, Arduino-like interface to the
 * StampFly drone hardware. Students only need to implement:
 *   void setup();           // Called once at startup
 *   void loop_400Hz(float dt); // Called at 400Hz (every 2.5ms)
 *
 * All hardware complexity (FreeRTOS, SPI/I2C, sensor fusion) is
 * hidden behind the ws:: namespace functions.
 */

#pragma once

#include <cstdint>

// =============================================================================
// Student-implemented Functions
// 学生が実装する関数
// =============================================================================

/**
 * @brief Called once at startup (after all sensors are initialized)
 *        起動時に一度呼ばれる（全センサー初期化後）
 */
void setup();

/**
 * @brief Called at 400Hz (every 2.5ms)
 *        400Hzで呼ばれるメインループ
 * @param dt Time step in seconds (0.0025)
 */
void loop_400Hz(float dt);

// =============================================================================
// Workshop API Namespace
// ワークショップAPI名前空間
// =============================================================================

namespace ws {

// -----------------------------------------------------------------------------
// Motor Control (Lesson 1)
// モーター制御
// -----------------------------------------------------------------------------

/**
 * @brief Set individual motor duty cycle
 *        個別モーターのデューティ比を設定
 * @param id Motor ID (1-4): 1=FR, 2=RR, 3=RL, 4=FL
 * @param duty Duty cycle (0.0 to 1.0)
 */
void motor_set_duty(int id, float duty);

/**
 * @brief Set all motors to the same duty cycle
 *        全モーターを同じデューティに設定
 * @param duty Duty cycle (0.0 to 1.0)
 */
void motor_set_all(float duty);

/**
 * @brief Stop all motors immediately
 *        全モーターを即座に停止
 */
void motor_stop_all();

/**
 * @brief Apply motor mixer (thrust + roll/pitch/yaw control)
 *        モーターミキサー適用（推力 + 姿勢制御）
 * @param thrust Thrust command (0.0 to 1.0)
 * @param roll   Roll torque (-1.0 to 1.0, positive = right wing down)
 * @param pitch  Pitch torque (-1.0 to 1.0, positive = nose up)
 * @param yaw    Yaw torque (-1.0 to 1.0, positive = clockwise from above)
 */
void motor_mixer(float thrust, float roll, float pitch, float yaw);

// -----------------------------------------------------------------------------
// Controller Input (Lesson 2)
// コントローラ入力
// -----------------------------------------------------------------------------

/**
 * @brief Get throttle stick value (0.0 to 1.0)
 *        スロットルスティック値を取得
 */
float rc_throttle();

/**
 * @brief Get roll stick value (-1.0 to 1.0)
 *        ロールスティック値を取得
 */
float rc_roll();

/**
 * @brief Get pitch stick value (-1.0 to 1.0)
 *        ピッチスティック値を取得
 */
float rc_pitch();

/**
 * @brief Get yaw stick value (-1.0 to 1.0)
 *        ヨースティック値を取得
 */
float rc_yaw();

/**
 * @brief Check if motors are armed
 *        モーターがARMされているか確認
 */
bool is_armed();

// -----------------------------------------------------------------------------
// LED Control (Lesson 3)
// LED制御
// -----------------------------------------------------------------------------

/**
 * @brief Set LED color (RGB)
 *        LEDカラーを設定
 * @param r Red (0-255)
 * @param g Green (0-255)
 * @param b Blue (0-255)
 */
void led_color(uint8_t r, uint8_t g, uint8_t b);

// -----------------------------------------------------------------------------
// IMU Sensor (Lesson 4)
// IMUセンサー
// -----------------------------------------------------------------------------

/** @brief Get gyroscope X (roll rate) [rad/s] */
float gyro_x();

/** @brief Get gyroscope Y (pitch rate) [rad/s] */
float gyro_y();

/** @brief Get gyroscope Z (yaw rate) [rad/s] */
float gyro_z();

/** @brief Get accelerometer X (forward) [m/s^2] */
float accel_x();

/** @brief Get accelerometer Y (right) [m/s^2] */
float accel_y();

/** @brief Get accelerometer Z (down, NED) [m/s^2] */
float accel_z();

// -----------------------------------------------------------------------------
// Telemetry (Lesson 7)
// テレメトリ
// -----------------------------------------------------------------------------

/**
 * @brief Send a named float value via WiFi telemetry
 *        名前付きfloat値をWiFiテレメトリで送信
 * @param name Variable name (shown in sf log wifi)
 * @param value Float value to send
 */
void telemetry_send(const char* name, float value);

// -----------------------------------------------------------------------------
// Estimation (Lesson 9)
// 姿勢推定
// -----------------------------------------------------------------------------

/** @brief Get estimated roll angle [rad] */
float estimated_roll();

/** @brief Get estimated pitch angle [rad] */
float estimated_pitch();

/** @brief Get estimated yaw angle [rad] */
float estimated_yaw();

/** @brief Get estimated altitude [m] (positive = up) */
float estimated_altitude();

// -----------------------------------------------------------------------------
// Utility
// ユーティリティ
// -----------------------------------------------------------------------------

/** @brief Get elapsed time since boot [ms] */
uint32_t millis();

/** @brief Get battery voltage [V] */
float battery_voltage();

/** @brief Print formatted debug message to serial console */
void print(const char* fmt, ...) __attribute__((format(printf, 1, 2)));

} // namespace ws
