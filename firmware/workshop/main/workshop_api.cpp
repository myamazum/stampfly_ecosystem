/**
 * @file workshop_api.cpp
 * @brief Workshop API implementation - bridges ws:: calls to hardware globals
 *        ワークショップAPI実装 - ws:: 呼び出しをハードウェアグローバルにブリッジ
 */

#include "workshop_api.hpp"
#include "workshop_globals.hpp"

#include "stampfly_state.hpp"
#include "led_manager.hpp"
#include "esp_log.h"
#include "esp_timer.h"

#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <algorithm>

using namespace globals;
using namespace ws_internal;

// =============================================================================
// Motor Control
// =============================================================================

void ws::motor_set_duty(int id, float duty)
{
    duty = std::clamp(duty, 0.0f, 1.0f);
    switch (id) {
        case 1: g_motor.setMotor(stampfly::MotorDriver::MOTOR_FR, duty); break;
        case 2: g_motor.setMotor(stampfly::MotorDriver::MOTOR_RR, duty); break;
        case 3: g_motor.setMotor(stampfly::MotorDriver::MOTOR_RL, duty); break;
        case 4: g_motor.setMotor(stampfly::MotorDriver::MOTOR_FL, duty); break;
        default: break;
    }
}

void ws::motor_set_all(float duty)
{
    duty = std::clamp(duty, 0.0f, 1.0f);
    g_motor.setMotor(stampfly::MotorDriver::MOTOR_FR, duty);
    g_motor.setMotor(stampfly::MotorDriver::MOTOR_RR, duty);
    g_motor.setMotor(stampfly::MotorDriver::MOTOR_RL, duty);
    g_motor.setMotor(stampfly::MotorDriver::MOTOR_FL, duty);
}

void ws::motor_stop_all()
{
    g_motor.setMotor(stampfly::MotorDriver::MOTOR_FR, 0);
    g_motor.setMotor(stampfly::MotorDriver::MOTOR_RR, 0);
    g_motor.setMotor(stampfly::MotorDriver::MOTOR_RL, 0);
    g_motor.setMotor(stampfly::MotorDriver::MOTOR_FL, 0);
}

void ws::motor_mixer(float thrust, float roll, float pitch, float yaw)
{
    g_motor.setMixerOutput(thrust, roll, pitch, yaw);
}

// =============================================================================
// Controller Input
// =============================================================================

float ws::rc_throttle()
{
    auto& state = stampfly::StampFlyState::getInstance();
    float t, r, p, y;
    state.getNormalizedControlInput(t, r, p, y);
    return t;
}

float ws::rc_roll()
{
    auto& state = stampfly::StampFlyState::getInstance();
    float t, r, p, y;
    state.getNormalizedControlInput(t, r, p, y);
    return r;
}

float ws::rc_pitch()
{
    auto& state = stampfly::StampFlyState::getInstance();
    float t, r, p, y;
    state.getNormalizedControlInput(t, r, p, y);
    return p;
}

float ws::rc_yaw()
{
    auto& state = stampfly::StampFlyState::getInstance();
    float t, r, p, y;
    state.getNormalizedControlInput(t, r, p, y);
    return y;
}

bool ws::is_armed()
{
    auto& state = stampfly::StampFlyState::getInstance();
    auto fs = state.getFlightState();
    return (fs == stampfly::FlightState::ARMED ||
            fs == stampfly::FlightState::FLYING);
}

// =============================================================================
// LED Control
// =============================================================================

void ws::led_color(uint8_t r, uint8_t g, uint8_t b)
{
    uint32_t color = (static_cast<uint32_t>(r) << 16) |
                     (static_cast<uint32_t>(g) << 8) |
                     static_cast<uint32_t>(b);
    stampfly::LEDManager::getInstance().requestChannel(
        stampfly::LEDChannel::STATUS,
        stampfly::LEDPriority::USER,
        stampfly::LEDPattern::SOLID,
        color);
}

// =============================================================================
// IMU Sensor
// =============================================================================

float ws::gyro_x()
{
    stampfly::Vec3 a, g;
    stampfly::StampFlyState::getInstance().getIMUCorrected(a, g);
    return g.x;
}

float ws::gyro_y()
{
    stampfly::Vec3 a, g;
    stampfly::StampFlyState::getInstance().getIMUCorrected(a, g);
    return g.y;
}

float ws::gyro_z()
{
    stampfly::Vec3 a, g;
    stampfly::StampFlyState::getInstance().getIMUCorrected(a, g);
    return g.z;
}

float ws::accel_x()
{
    stampfly::Vec3 a, g;
    stampfly::StampFlyState::getInstance().getIMUCorrected(a, g);
    return a.x;
}

float ws::accel_y()
{
    stampfly::Vec3 a, g;
    stampfly::StampFlyState::getInstance().getIMUCorrected(a, g);
    return a.y;
}

float ws::accel_z()
{
    stampfly::Vec3 a, g;
    stampfly::StampFlyState::getInstance().getIMUCorrected(a, g);
    return a.z;
}

// =============================================================================
// Telemetry
// =============================================================================

void ws::telemetry_send(const char* name, float value)
{
    // Update existing entry
    for (int i = 0; i < MAX_USER_TELEM; i++) {
        if (g_user_telemetry[i].active &&
            strncmp(g_user_telemetry[i].name, name, sizeof(g_user_telemetry[i].name) - 1) == 0) {
            g_user_telemetry[i].value = value;
            return;
        }
    }
    // Find empty slot
    for (int i = 0; i < MAX_USER_TELEM; i++) {
        if (!g_user_telemetry[i].active) {
            strncpy(g_user_telemetry[i].name, name, sizeof(g_user_telemetry[i].name) - 1);
            g_user_telemetry[i].name[sizeof(g_user_telemetry[i].name) - 1] = '\0';
            g_user_telemetry[i].value = value;
            g_user_telemetry[i].active = true;
            return;
        }
    }
}

// =============================================================================
// Estimation
// =============================================================================

float ws::estimated_roll()
{
    float r, p, y;
    stampfly::StampFlyState::getInstance().getAttitudeEuler(r, p, y);
    return r;
}

float ws::estimated_pitch()
{
    float r, p, y;
    stampfly::StampFlyState::getInstance().getAttitudeEuler(r, p, y);
    return p;
}

float ws::estimated_yaw()
{
    float r, p, y;
    stampfly::StampFlyState::getInstance().getAttitudeEuler(r, p, y);
    return y;
}

float ws::estimated_altitude()
{
    auto fused = g_fusion.getState();
    return -fused.position.z;  // NED -> altitude (positive up)
}

// =============================================================================
// Utility
// =============================================================================

uint32_t ws::millis()
{
    return static_cast<uint32_t>(esp_timer_get_time() / 1000);
}

float ws::battery_voltage()
{
    return stampfly::StampFlyState::getInstance().getVoltage();
}

void ws::print(const char* fmt, ...)
{
    va_list args;
    va_start(args, fmt);
    vprintf(fmt, args);
    va_end(args);
    printf("\n");
}
