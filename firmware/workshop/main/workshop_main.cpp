/**
 * @file workshop_main.cpp
 * @brief StampFly Workshop - Main Entry Point
 *        StampFly ワークショップ メインエントリポイント
 *
 * Simplified version of vehicle/main/main.cpp for workshop use.
 * Starts the same sensor/peripheral tasks but the ControlTask
 * is replaced by a workshop version that calls setup()/loop_400Hz().
 */

#include <stdio.h>
#include <cmath>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include "esp_log.h"
#include "esp_system.h"
#include "esp_timer.h"
#include "nvs_flash.h"
#include "esp_netif.h"
#include "esp_event.h"

#include "workshop_globals.hpp"
#include "config.hpp"
#include "init.hpp"
#include "tasks/tasks.hpp"

static const char* TAG = "workshop";

using namespace config;
using namespace globals;

// Button event handler (simplified from vehicle)
void onButtonEvent(stampfly::Button::Event event)
{
    auto& state = stampfly::StampFlyState::getInstance();

    switch (event) {
        case stampfly::Button::Event::CLICK:
            if (state.getFlightState() == stampfly::FlightState::IDLE) {
                if (g_landing_handler.canArm() && state.requestArm()) {
                    g_motor.arm();
                    g_motor.resetStats();
                    g_buzzer.armTone();
                    ESP_LOGI(TAG, "Motors ARMED");
                }
            } else if (state.getFlightState() == stampfly::FlightState::ARMED) {
                if (state.requestDisarm()) {
                    g_motor.saveStatsToNVS();
                    g_motor.disarm();
                    g_buzzer.disarmTone();
                    ESP_LOGI(TAG, "Motors DISARMED");
                }
            }
            break;

        case stampfly::Button::Event::LONG_PRESS_3S:
            g_comm.enterPairingMode();
            state.setPairingState(stampfly::PairingState::PAIRING);
            stampfly::LEDManager::getInstance().requestChannel(
                stampfly::LEDChannel::SYSTEM, stampfly::LEDPriority::PAIRING,
                stampfly::LEDPattern::BLINK_FAST, 0x0000FF);
            g_buzzer.beep();
            break;

        case stampfly::Button::Event::LONG_PRESS_5S:
            g_buzzer.beep();
            vTaskDelay(pdMS_TO_TICKS(600));
            esp_restart();
            break;

        default:
            break;
    }
}

// ESP-NOW control packet handler
void onControlPacket(const stampfly::ControlPacket& packet)
{
    auto& arbiter = stampfly::ControlArbiter::getInstance();
    if (arbiter.getCommMode() != stampfly::CommMode::ESPNOW) {
        return;
    }
    handleControlInput(packet.throttle, packet.roll, packet.pitch,
                       packet.yaw, packet.flags);
}

// Attitude initialization helpers (used during boot and ARM)
void initializeAttitudeFromBuffers()
{
    if (g_accel_buffer_count == 0 || g_mag_buffer_count == 0) return;

    stampfly::math::Vector3 accel_sum = stampfly::math::Vector3::zero();
    int ac = std::min(g_accel_buffer_count, REF_BUFFER_SIZE);
    for (int i = 0; i < ac; i++) accel_sum += g_accel_buffer[i];
    stampfly::math::Vector3 accel_avg = accel_sum * (1.0f / ac);

    stampfly::math::Vector3 mag_sum = stampfly::math::Vector3::zero();
    int mc = std::min(g_mag_buffer_count, REF_BUFFER_SIZE);
    for (int i = 0; i < mc; i++) mag_sum += g_mag_buffer[i];
    stampfly::math::Vector3 mag_avg = mag_sum * (1.0f / mc);

    if (g_fusion.isInitialized()) {
        g_fusion.initializeAttitude(accel_avg, mag_avg);
        g_mag_ref_set = true;
    }
}

// Legacy stub (referenced by tasks_common.hpp)
void setMagReferenceFromBuffer()
{
    initializeAttitudeFromBuffers();
}

// Binlog start callback stub (referenced by logger component)
void onBinlogStart()
{
    if (g_fusion.isInitialized()) {
        g_fusion.reset();
        g_fusion.setGyroBias(g_initial_gyro_bias);
    }
    initializeAttitudeFromBuffers();
}

// Timer callback for 400Hz IMU timing
static void imu_timer_callback(void* arg)
{
    xSemaphoreGive(g_imu_semaphore);
}

static void startTasks()
{
    ESP_LOGI(TAG, "Starting FreeRTOS tasks...");

    // Peripheral tasks (Core 0)
    xTaskCreatePinnedToCore(LEDTask, "LEDTask", STACK_SIZE_LED, nullptr,
                            PRIORITY_LED_TASK, &g_led_task_handle, 0);
    xTaskCreatePinnedToCore(ButtonTask, "ButtonTask", STACK_SIZE_BUTTON, nullptr,
                            PRIORITY_BUTTON_TASK, &g_button_task_handle, 0);
    xTaskCreatePinnedToCore(PowerTask, "PowerTask", STACK_SIZE_POWER, nullptr,
                            PRIORITY_POWER_TASK, &g_power_task_handle, 0);

    // Semaphores
    g_imu_semaphore = xSemaphoreCreateBinary();
    g_control_semaphore = xSemaphoreCreateBinary();
    g_telemetry_imu_semaphore = xSemaphoreCreateCounting(16, 0);

    // IMU timer (400Hz)
    esp_timer_create_args_t imu_timer_args = {
        .callback = imu_timer_callback,
        .arg = nullptr,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "imu_timer",
        .skip_unhandled_events = true,
    };
    esp_timer_create(&imu_timer_args, &g_imu_timer);
    esp_timer_start_periodic(g_imu_timer, 2500);
    ESP_LOGI(TAG, "IMU timer started: 400Hz");

    // Sensor tasks (Core 1)
    xTaskCreatePinnedToCore(IMUTask, "IMUTask", STACK_SIZE_IMU, nullptr,
                            PRIORITY_IMU_TASK, &g_imu_task_handle, 1);

    // Workshop ControlTask (Core 1) - calls setup()/loop_400Hz()
    xTaskCreatePinnedToCore(ControlTask, "ControlTask", STACK_SIZE_CONTROL, nullptr,
                            PRIORITY_CONTROL_TASK, &g_control_task_handle, 1);

    // I2C sensor tasks (Core 0)
    xTaskCreatePinnedToCore(MagTask, "MagTask", STACK_SIZE_MAG, nullptr,
                            PRIORITY_MAG_TASK, &g_mag_task_handle, 0);
    xTaskCreatePinnedToCore(BaroTask, "BaroTask", STACK_SIZE_BARO, nullptr,
                            PRIORITY_BARO_TASK, &g_baro_task_handle, 0);
    xTaskCreatePinnedToCore(ToFTask, "ToFTask", STACK_SIZE_TOF, nullptr,
                            PRIORITY_TOF_TASK, &g_tof_task_handle, 0);
    xTaskCreatePinnedToCore(OptFlowTask, "OptFlowTask", STACK_SIZE_OPTFLOW, nullptr,
                            PRIORITY_OPTFLOW_TASK, &g_optflow_task_handle, 1);

    // Communication task (Core 0)
    xTaskCreatePinnedToCore(CommTask, "CommTask", STACK_SIZE_COMM, nullptr,
                            PRIORITY_COMM_TASK, &g_comm_task_handle, 0);

    // CLI task (Core 0)
    xTaskCreatePinnedToCore(CLITask, "CLITask", STACK_SIZE_CLI, nullptr,
                            PRIORITY_CLI_TASK, &g_cli_task_handle, 0);

    // Telemetry task (Core 0)
    xTaskCreatePinnedToCore(TelemetryTask, "TelemetryTask", STACK_SIZE_TELEMETRY, nullptr,
                            PRIORITY_TELEMETRY_TASK, &g_telemetry_task_handle, 0);

    ESP_LOGI(TAG, "All tasks started");
}

extern "C" void app_main(void)
{
    vTaskDelay(pdMS_TO_TICKS(3000));

    printf("\n\n*** StampFly Workshop Boot ***\n\n");
    fflush(stdout);

    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  StampFly Workshop Skeleton");
    ESP_LOGI(TAG, "  ESP-IDF version: %s", esp_get_idf_version());
    ESP_LOGI(TAG, "========================================");

    // Initialize NVS
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Initialize network interface
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // Initialize state and system manager
    auto& state = stampfly::StampFlyState::getInstance();
    ESP_ERROR_CHECK(state.init());

    auto& sys_mgr = stampfly::SystemManager::getInstance();
    stampfly::SystemManager::Config sys_cfg;
    sys_cfg.init_timeout_ms = 5000;
    sys_cfg.calib_timeout_ms = 10000;
    ESP_ERROR_CHECK(sys_mgr.init(sys_cfg));

    // I2C bus
    init::i2c();

    // SystemStateManager
    {
        auto& sys_state = stampfly::SystemStateManager::getInstance();
        sys_state.init();
    }

    // Actuators
    init::actuators();

    auto& led_mgr = stampfly::LEDManager::getInstance();

    // Phase 1: Place on ground (3 seconds)
    ESP_LOGI(TAG, "Place aircraft on ground...");
    g_buzzer.startTone();
    led_mgr.requestChannel(stampfly::LEDChannel::SYSTEM, stampfly::LEDPriority::BOOT,
                           stampfly::LEDPattern::BREATHE, 0xFFFFFF);
    for (int i = 3; i > 0; i--) {
        ESP_LOGI(TAG, "  %d...", i);
        for (int j = 0; j < 30; j++) {
            led_mgr.update();
            vTaskDelay(pdMS_TO_TICKS(33));
        }
    }

    // Phase 2: Sensor initialization
    ESP_LOGI(TAG, "Initializing sensors...");
    led_mgr.requestChannel(stampfly::LEDChannel::SYSTEM, stampfly::LEDPriority::BOOT,
                           stampfly::LEDPattern::BREATHE, 0x0000FF);

    auto updateLed = [&]() {
        for (int i = 0; i < 10; i++) {
            led_mgr.update();
            vTaskDelay(pdMS_TO_TICKS(20));
        }
    };

    updateLed(); init::sensors();
    updateLed(); init::estimators();
    updateLed(); init::communication();
    updateLed(); init::console();
    updateLed(); init::logger();
    updateLed(); init::telemetry();
    updateLed(); init::wifi_cli();
    updateLed();

    // Start tasks
    startTasks();

    // Wait for sensor buffers
    ESP_LOGI(TAG, "Waiting for sensors...");
    {
        int wait_ms = 0;
        while (wait_ms < 2000) {
            if (g_accel_buffer_count > 0 && g_gyro_buffer_count > 0 &&
                g_mag_buffer_count > 0 && g_baro_buffer_count > 0 &&
                g_tof_bottom_buffer_count > 0 && g_optflow_buffer_count > 0) {
                break;
            }
            vTaskDelay(pdMS_TO_TICKS(10));
            wait_ms += 10;
        }
    }

    // Phase 3: Sensor stabilization (simplified wait)
    ESP_LOGI(TAG, "Stabilizing sensors...");
    led_mgr.requestChannel(stampfly::LEDChannel::SYSTEM, stampfly::LEDPriority::BOOT,
                           stampfly::LEDPattern::BLINK_SLOW, 0xFF00FF);
    vTaskDelay(pdMS_TO_TICKS(3000));

    // Initialize sensor fusion
    if (g_fusion.isInitialized()) {
        g_fusion.reset();
        g_fusion.setGyroBias(g_initial_gyro_bias);
        initializeAttitudeFromBuffers();
        g_eskf_ready = true;
    }

    // Phase 4: Ready!
    g_buzzer.beep(); vTaskDelay(pdMS_TO_TICKS(150));
    g_buzzer.beep(); vTaskDelay(pdMS_TO_TICKS(150));
    g_buzzer.beep();

    state.setFlightState(stampfly::FlightState::IDLE);
    led_mgr.releaseChannel(stampfly::LEDChannel::SYSTEM, stampfly::LEDPriority::BOOT);

    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "Workshop ready! Pair controller and ARM.");
    ESP_LOGI(TAG, "Free heap: %lu bytes", esp_get_free_heap_size());
    ESP_LOGI(TAG, "========================================");

    while (true) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
