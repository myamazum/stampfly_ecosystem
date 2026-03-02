/**
 * @file workshop_globals.cpp
 * @brief Global variable definitions for workshop firmware
 *        ワークショップファームウェア用グローバル変数定義
 *
 * Provides definitions for all symbols declared in vehicle/main/globals.hpp.
 * This allows vehicle sensor tasks to link against workshop-provided globals.
 * Nearly identical to vehicle/main/globals.cpp.
 */

#include "workshop_globals.hpp"

namespace globals {

// =============================================================================
// Sensors
// =============================================================================

stampfly::BMI270Wrapper g_imu;
stampfly::BMM150 g_mag;
stampfly::MagCalibrator g_mag_cal;
stampfly::BMP280 g_baro;
stampfly::VL53L3CXWrapper g_tof_bottom;
stampfly::VL53L3CXWrapper g_tof_front;
stampfly::PMW3901* g_optflow = nullptr;
stampfly::PowerMonitor g_power;

// =============================================================================
// Actuators
// =============================================================================

stampfly::MotorDriver g_motor;
stampfly::Buzzer g_buzzer;
stampfly::Button g_button;

// =============================================================================
// Estimators
// =============================================================================

sf::SensorFusion g_fusion;
stampfly::AttitudeEstimator g_attitude_est;
stampfly::AltitudeEstimator g_altitude_est;
stampfly::LandingHandler g_landing_handler;

// =============================================================================
// Filters
// =============================================================================

stampfly::LowPassFilter g_accel_lpf[3];
stampfly::LowPassFilter g_gyro_lpf[3];

// =============================================================================
// Communication
// =============================================================================

stampfly::ControllerComm g_comm;
stampfly::Logger g_logger;

// =============================================================================
// Barometer Reference
// =============================================================================

float g_baro_reference_altitude = 0.0f;
bool g_baro_reference_set = false;

// =============================================================================
// Sensor Reference Buffers
// =============================================================================

stampfly::math::Vector3 g_accel_buffer[REF_BUFFER_SIZE];
int g_accel_buffer_index = 0;
int g_accel_buffer_count = 0;

stampfly::math::Vector3 g_gyro_buffer[REF_BUFFER_SIZE];
int g_gyro_buffer_index = 0;
int g_gyro_buffer_count = 0;

stampfly::math::Vector3 g_mag_buffer[REF_BUFFER_SIZE];
int g_mag_buffer_index = 0;
int g_mag_buffer_count = 0;
bool g_mag_ref_set = false;

float g_baro_buffer[REF_BUFFER_SIZE];
int g_baro_buffer_index = 0;
int g_baro_buffer_count = 0;

float g_tof_bottom_buffer[REF_BUFFER_SIZE];
int g_tof_bottom_buffer_index = 0;
int g_tof_bottom_buffer_count = 0;

float g_tof_front_buffer[REF_BUFFER_SIZE];
int g_tof_front_buffer_index = 0;
int g_tof_front_buffer_count = 0;

OptFlowData g_optflow_buffer[REF_BUFFER_SIZE];
int g_optflow_buffer_index = 0;
int g_optflow_buffer_count = 0;

// =============================================================================
// Calibration Data
// =============================================================================

stampfly::math::Vector3 g_initial_gyro_bias = stampfly::math::Vector3::zero();

// =============================================================================
// State Flags
// =============================================================================

volatile bool g_eskf_ready = false;
volatile bool g_boot_complete = false;   // Set by app_main after init is done
volatile bool g_setup_complete = false;  // Set by ControlTask after setup()

volatile bool g_imu_task_healthy = false;
volatile bool g_tof_task_healthy = false;
volatile bool g_mag_task_healthy = false;
volatile bool g_optflow_task_healthy = false;
volatile bool g_baro_task_healthy = false;

sf::HealthMonitor g_health;

volatile bool g_mag_data_ready = false;
volatile bool g_baro_data_ready = false;
volatile bool g_tof_bottom_data_ready = false;
volatile bool g_tof_front_data_ready = false;
volatile bool g_optflow_data_ready = false;

// =============================================================================
// Task Handles
// =============================================================================

TaskHandle_t g_imu_task_handle = nullptr;
TaskHandle_t g_control_task_handle = nullptr;  // Used by WorkshopTask
TaskHandle_t g_optflow_task_handle = nullptr;
TaskHandle_t g_mag_task_handle = nullptr;
TaskHandle_t g_baro_task_handle = nullptr;
TaskHandle_t g_tof_task_handle = nullptr;
TaskHandle_t g_power_task_handle = nullptr;
TaskHandle_t g_led_task_handle = nullptr;
TaskHandle_t g_button_task_handle = nullptr;
TaskHandle_t g_comm_task_handle = nullptr;
TaskHandle_t g_cli_task_handle = nullptr;
TaskHandle_t g_telemetry_task_handle = nullptr;

// =============================================================================
// Timer and Synchronization
// =============================================================================

esp_timer_handle_t g_imu_timer = nullptr;
SemaphoreHandle_t g_imu_semaphore = nullptr;
SemaphoreHandle_t g_control_semaphore = nullptr;  // Used by WorkshopTask
SemaphoreHandle_t g_telemetry_imu_semaphore = nullptr;

} // namespace globals

// =============================================================================
// CLI-accessible Pointers
// =============================================================================

stampfly::MagCalibrator* g_mag_calibrator = nullptr;
stampfly::Logger* g_logger_ptr = nullptr;
stampfly::ControllerComm* g_comm_ptr = nullptr;
stampfly::MotorDriver* g_motor_ptr = nullptr;
stampfly::Buzzer* g_buzzer_ptr = nullptr;
sf::SensorFusion* g_fusion_ptr = nullptr;

// =============================================================================
// Stubs for vehicle symbols not used in workshop
// workshopで使用しないvehicleシンボルのスタブ
// =============================================================================

// cmd_control.cpp references this (for CLI gain tuning)
// Forward-declare to avoid pulling in rate_controller.hpp
struct RateController;
RateController* g_rate_controller_ptr = nullptr;

// =============================================================================
// Debug Checkpoints
// =============================================================================

extern "C" {
    volatile uint8_t g_imu_checkpoint = 0;
    volatile uint32_t g_imu_last_loop = 0;
    volatile uint8_t g_optflow_checkpoint = 0;
    volatile uint32_t g_optflow_last_loop = 0;
}

