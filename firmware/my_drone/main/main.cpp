/**
 * my_drone - Custom StampFly Firmware
 * my_drone - カスタムStampFlyファームウェア
 *
 * Native ESP-IDF firmware based on the vehicle firmware architecture.
 * Full access to all sensors, estimators, and actuators via globals and
 * StampFlyState.
 *
 * vehicle ファームウェア構成に基づくネイティブ ESP-IDF ファームウェア。
 * globals および StampFlyState 経由で全センサ・推定器・アクチュエータにアクセス可能。
 *
 * Build: sf build my_drone
 * Flash: sf flash my_drone -m
 */

#include <cstdio>
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

// Sensor drivers
// センサドライバ
#include "bmi270_wrapper.hpp"
#include "bmm150.hpp"
#include "mag_calibration.hpp"
#include "bmp280.hpp"
#include "vl53l3cx_wrapper.hpp"
#include "pmw3901_wrapper.hpp"
#include "power_monitor.hpp"

// Actuators and peripherals
// アクチュエータ・周辺機器
#include "motor_driver.hpp"
#include "led.hpp"
#include "buzzer.hpp"
#include "button.hpp"

// State management and estimation
// 状態管理・推定
#include "stampfly_state.hpp"
#include "system_state.hpp"
#include "system_manager.hpp"
#include "sensor_fusion.hpp"
#include "filter.hpp"

// Communication
// 通信
#include "controller_comm.hpp"
#include "control_arbiter.hpp"

// Logger and Telemetry
// ロガー・テレメトリ
#include "logger.hpp"
#include "telemetry.hpp"

// Vehicle configuration, globals, init, task declarations
// vehicle の設定・グローバル変数・初期化・タスク宣言
#include "config.hpp"
#include "globals.hpp"
#include "init.hpp"
#include "tasks/tasks.hpp"

static const char* TAG = "my_drone";

using namespace config;
using namespace globals;

// =============================================================================
// Required extern symbols (referenced by vehicle tasks and init.cpp)
// 必須 extern シンボル（vehicle タスクおよび init.cpp から参照される）
// =============================================================================

// Yaw alert counter (led_task checks this)
// ヨーアラートカウンタ（led_task が参照）
volatile int g_yaw_alert_counter = 0;

// Rate controller pointer stub (cmd_control.cpp references this for CLI tuning)
// レートコントローラポインタスタブ（CLI チューニング用に cmd_control.cpp が参照）
struct RateController;
RateController* g_rate_controller_ptr = nullptr;

// =============================================================================
// Attitude initialization from sensor buffers
// センサバッファからの姿勢初期化
// =============================================================================

/**
 * @brief Initialize attitude from accelerometer and magnetometer buffers
 *        加速度計・磁気計バッファから姿勢を初期化
 *
 * Called on ARM, ESKF divergence recovery, and binlog start.
 * ARM時、ESKF発散リカバリ時、binlog開始時に呼ばれる。
 */
void initializeAttitudeFromBuffers()
{
    if (g_accel_buffer_count == 0 || g_mag_buffer_count == 0) {
        ESP_LOGW(TAG, "Cannot initialize attitude: insufficient buffer data");
        return;
    }

    // Compute accelerometer average
    // 加速度計バッファの平均を計算
    stampfly::math::Vector3 accel_sum = stampfly::math::Vector3::zero();
    int accel_n = std::min(g_accel_buffer_count, REF_BUFFER_SIZE);
    for (int i = 0; i < accel_n; i++) {
        accel_sum += g_accel_buffer[i];
    }
    stampfly::math::Vector3 accel_avg = accel_sum * (1.0f / accel_n);

    // Compute magnetometer average
    // 磁気計バッファの平均を計算
    stampfly::math::Vector3 mag_sum = stampfly::math::Vector3::zero();
    int mag_n = std::min(g_mag_buffer_count, REF_BUFFER_SIZE);
    for (int i = 0; i < mag_n; i++) {
        mag_sum += g_mag_buffer[i];
    }
    stampfly::math::Vector3 mag_avg = mag_sum * (1.0f / mag_n);

    // Initialize sensor fusion attitude
    // センサフュージョンの姿勢を初期化
    if (g_fusion.isInitialized()) {
        g_fusion.initializeAttitude(accel_avg, mag_avg);
        g_mag_ref_set = true;
        ESP_LOGI(TAG, "Attitude initialized: accel=%d, mag=%d samples",
                 accel_n, mag_n);
    }
}

/**
 * @brief Set magnetometer reference from buffer (legacy, deprecated)
 *        磁気計リファレンスをバッファから設定（レガシー、非推奨）
 */
void setMagReferenceFromBuffer()
{
    if (g_mag_buffer_count == 0) return;

    stampfly::math::Vector3 sum = stampfly::math::Vector3::zero();
    int n = std::min(g_mag_buffer_count, REF_BUFFER_SIZE);
    for (int i = 0; i < n; i++) {
        sum += g_mag_buffer[i];
    }
    stampfly::math::Vector3 avg = sum * (1.0f / n);

    if (g_fusion.isInitialized()) {
        g_fusion.setMagReference(avg);
        g_mag_ref_set = true;
    }
}

// =============================================================================
// Callback: binlog start (called by Logger)
// コールバック: binlog 開始（Logger から呼ばれる）
// =============================================================================

void onBinlogStart()
{
    if (g_fusion.isInitialized()) {
        g_fusion.reset();
        g_fusion.setGyroBias(g_initial_gyro_bias);
    }
    initializeAttitudeFromBuffers();
}

// =============================================================================
// Callback: button event (called by ButtonTask)
// コールバック: ボタンイベント（ButtonTask から呼ばれる）
// =============================================================================

void onButtonEvent(stampfly::Button::Event event)
{
    auto& state = stampfly::StampFlyState::getInstance();

    switch (event) {
    case stampfly::Button::Event::CLICK:
        if (state.getFlightState() == stampfly::FlightState::IDLE) {
            if (g_landing_handler.canArm() && state.requestArm()) {
                initializeAttitudeFromBuffers();
                g_motor.arm();
                g_buzzer.armTone();
                ESP_LOGI(TAG, "ARMED");
            }
        } else if (state.getFlightState() == stampfly::FlightState::ARMED) {
            if (state.requestDisarm()) {
                g_motor.disarm();
                g_buzzer.disarmTone();
                ESP_LOGI(TAG, "DISARMED");
            }
        }
        break;

    case stampfly::Button::Event::LONG_PRESS_3S:
        // Enter pairing mode (same as vehicle firmware)
        // ペアリングモードに入る（vehicle ファームウェアと同じ）
        ESP_LOGI(TAG, "Button: LONG_PRESS (3s) - Entering pairing mode");
        g_comm.enterPairingMode();
        state.setPairingState(stampfly::PairingState::PAIRING);
        stampfly::LEDManager::getInstance().requestChannel(
            stampfly::LEDChannel::SYSTEM, stampfly::LEDPriority::PAIRING,
            stampfly::LEDPattern::BLINK_FAST, 0x0000FF);
        g_buzzer.beep();
        break;

    case stampfly::Button::Event::LONG_PRESS_5S:
        // System reset
        // システムリセット
        ESP_LOGI(TAG, "Button: LONG_PRESS (5s) - System reset");
        g_buzzer.beep();
        vTaskDelay(pdMS_TO_TICKS(600));
        esp_restart();
        break;

    default:
        break;
    }
}

// =============================================================================
// Callback: control input (called by CommTask and CLI)
// コールバック: 制御入力（CommTask および CLI から呼ばれる）
// =============================================================================

// Edge detection for arm/disarm toggle
// ARM/DISARM トグルのエッジ検出
static bool s_prev_arm_flag = false;

void handleControlInput(uint16_t throttle, uint16_t roll, uint16_t pitch,
                        uint16_t yaw, uint8_t flags)
{
    auto& state = stampfly::StampFlyState::getInstance();
    state.updateControlInput(throttle, roll, pitch, yaw);
    state.updateControlFlags(flags);

    // Handle arm/disarm from controller (rising edge)
    // コントローラからの ARM/DISARM 処理（立ち上がりエッジ）
    bool arm_flag = (flags & stampfly::CTRL_FLAG_ARM) != 0;
    if (arm_flag && !s_prev_arm_flag) {
        auto fs = state.getFlightState();
        if (fs == stampfly::FlightState::IDLE || fs == stampfly::FlightState::ERROR) {
            if (g_landing_handler.canArm() && state.requestArm()) {
                g_motor.arm();
                initializeAttitudeFromBuffers();
                g_buzzer.armTone();
                ESP_LOGI(TAG, "ARMED (controller)");
            }
        } else if (fs == stampfly::FlightState::ARMED ||
                   fs == stampfly::FlightState::FLYING) {
            if (state.requestDisarm()) {
                g_motor.disarm();
                g_buzzer.disarmTone();
                ESP_LOGI(TAG, "DISARMED (controller)");
            }
        }
    }
    s_prev_arm_flag = arm_flag;
}

// =============================================================================
// Callback: ESP-NOW control packet (called by ControllerComm via init.cpp)
// コールバック: ESP-NOW 制御パケット（init.cpp 経由で ControllerComm から呼ばれる）
// =============================================================================

void onControlPacket(const stampfly::ControlPacket& packet)
{
    auto& arbiter = stampfly::ControlArbiter::getInstance();
    if (arbiter.getCommMode() != stampfly::CommMode::ESPNOW) {
        return;
    }

    arbiter.updateFromESPNOW(packet.throttle, packet.roll, packet.pitch,
                             packet.yaw, packet.flags);
    handleControlInput(packet.throttle, packet.roll, packet.pitch,
                       packet.yaw, packet.flags);
}

// =============================================================================
// ControlTask - 400Hz P-control angular rate loop
// ControlTask - 400Hz 比例制御 角速度制御ループ
// =============================================================================

// P-gain for angular rate control [V / (rad/s)]
// 角速度制御の比例ゲイン [V / (rad/s)]
static constexpr float KP_ROLL  = 1.362f;
static constexpr float KP_PITCH = 1.984f;
static constexpr float KP_YAW   = 7.310f;

// Maximum angular rate command from stick [rad/s]
// スティック最大角速度指令 [rad/s]
static constexpr float MAX_RATE_ROLL  = 4.0f;   // ~230 deg/s
static constexpr float MAX_RATE_PITCH = 4.0f;   // ~230 deg/s
static constexpr float MAX_RATE_YAW   = 3.0f;   // ~170 deg/s

void ControlTask(void* pvParameters)
{
    ESP_LOGI(TAG, "ControlTask started (400Hz, P rate control)");
    vTaskDelay(pdMS_TO_TICKS(500));

    while (true) {
        if (xSemaphoreTake(g_control_semaphore, portMAX_DELAY) != pdTRUE)
            continue;

        auto& state = stampfly::StampFlyState::getInstance();

        // --- IMU (400Hz) ---
        stampfly::Vec3 accel, gyro;
        state.getIMUData(accel, gyro);

        // --- Controller input (normalized) ---
        // --- コントローラ入力（正規化値） ---
        float throttle, ctrl_roll, ctrl_pitch, ctrl_yaw;
        state.getControlInput(throttle, ctrl_roll, ctrl_pitch, ctrl_yaw);

        // --- Attitude (for telemetry) ---
        // --- 姿勢（テレメトリ用） ---
        float att_roll, att_pitch, att_yaw;
        state.getAttitudeEuler(att_roll, att_pitch, att_yaw);

        // --- Power monitor ---
        float voltage, current;
        state.getPowerData(voltage, current);

        // =================================================================
        // P-control angular rate loop
        // 比例制御 角速度ループ
        //
        //   rate_cmd = stick * MAX_RATE    [rad/s]
        //   error    = rate_cmd - gyro     [rad/s]
        //   output   = Kp * error          [V]
        //   -> setMixerOutput(thrust, roll_out, pitch_out, yaw_out)
        // =================================================================

        if (state.getFlightState() == stampfly::FlightState::ARMED) {
            // Convert stick input (-1..+1) to angular rate command [rad/s]
            // スティック入力（-1..+1）を角速度指令 [rad/s] に変換
            float rate_cmd_roll  = ctrl_roll  * MAX_RATE_ROLL;
            float rate_cmd_pitch = ctrl_pitch * MAX_RATE_PITCH;
            float rate_cmd_yaw   = ctrl_yaw   * MAX_RATE_YAW;

            // P-control: error = command - measured gyro
            // P制御: 偏差 = 指令値 - ジャイロ計測値
            float err_roll  = rate_cmd_roll  - gyro.x;
            float err_pitch = rate_cmd_pitch - gyro.y;
            float err_yaw   = rate_cmd_yaw   - gyro.z;

            // Control output [V] (fed to X-quad mixer)
            // 制御出力 [V]（X-quadミキサーに入力）
            float out_roll  = KP_ROLL  * err_roll;
            float out_pitch = KP_PITCH * err_pitch;
            float out_yaw   = KP_YAW   * err_yaw;

            // Apply to motors via built-in X-quad mixer
            // 内蔵 X-quad ミキサー経由でモーターに出力
            g_motor.setMixerOutput(throttle, out_roll, out_pitch, out_yaw);
        }

        // --- Teleplot output at 50Hz (400Hz / 8) ---
        // --- Teleplot 出力 50Hz（400Hz / 8） ---
        static uint32_t tick = 0;
        tick++;
        if (tick % 8 == 0) {
            printf(">gyro_x:%.2f\n", gyro.x);
            printf(">gyro_y:%.2f\n", gyro.y);
            printf(">gyro_z:%.2f\n", gyro.z);
            printf(">roll_deg:%.1f\n", att_roll * 57.3f);
            printf(">pitch_deg:%.1f\n", att_pitch * 57.3f);
            printf(">throttle:%.2f\n", throttle);
            printf(">vbat:%.2f\n", voltage);
        }
    }
}

// =============================================================================
// Timer callback and task startup
// タイマーコールバックとタスク起動
// =============================================================================

static void imu_timer_callback(void* arg)
{
    xSemaphoreGive(g_imu_semaphore);
}

static void startTasks()
{
    ESP_LOGI(TAG, "Starting tasks...");

    // Peripheral tasks (Core 0)
    // 周辺機器タスク（Core 0）
    xTaskCreatePinnedToCore(LEDTask, "LEDTask", STACK_SIZE_LED, nullptr,
                            PRIORITY_LED_TASK, &g_led_task_handle, 0);
    xTaskCreatePinnedToCore(ButtonTask, "ButtonTask", STACK_SIZE_BUTTON, nullptr,
                            PRIORITY_BUTTON_TASK, &g_button_task_handle, 0);
    xTaskCreatePinnedToCore(PowerTask, "PowerTask", STACK_SIZE_POWER, nullptr,
                            PRIORITY_POWER_TASK, &g_power_task_handle, 0);

    // Semaphores
    // セマフォ
    g_imu_semaphore = xSemaphoreCreateBinary();
    g_control_semaphore = xSemaphoreCreateBinary();
    g_telemetry_imu_semaphore = xSemaphoreCreateCounting(16, 0);

    // IMU timer (400Hz = 2500us)
    esp_timer_create_args_t imu_timer_args = {
        .callback = imu_timer_callback,
        .arg = nullptr,
        .dispatch_method = ESP_TIMER_TASK,
        .name = "imu_timer",
        .skip_unhandled_events = true,
    };
    esp_timer_create(&imu_timer_args, &g_imu_timer);
    esp_timer_start_periodic(g_imu_timer, 2500);

    // Sensor tasks (Core 1: IMU, Control, OptFlow / Core 0: others)
    // センサタスク（Core 1: IMU, Control, OptFlow / Core 0: その他）
    xTaskCreatePinnedToCore(IMUTask, "IMUTask", STACK_SIZE_IMU, nullptr,
                            PRIORITY_IMU_TASK, &g_imu_task_handle, 1);
    xTaskCreatePinnedToCore(ControlTask, "ControlTask", STACK_SIZE_CONTROL, nullptr,
                            PRIORITY_CONTROL_TASK, &g_control_task_handle, 1);
    xTaskCreatePinnedToCore(MagTask, "MagTask", STACK_SIZE_MAG, nullptr,
                            PRIORITY_MAG_TASK, &g_mag_task_handle, 0);
    xTaskCreatePinnedToCore(BaroTask, "BaroTask", STACK_SIZE_BARO, nullptr,
                            PRIORITY_BARO_TASK, &g_baro_task_handle, 0);
    xTaskCreatePinnedToCore(ToFTask, "ToFTask", STACK_SIZE_TOF, nullptr,
                            PRIORITY_TOF_TASK, &g_tof_task_handle, 0);
    xTaskCreatePinnedToCore(OptFlowTask, "OptFlowTask", STACK_SIZE_OPTFLOW, nullptr,
                            PRIORITY_OPTFLOW_TASK, &g_optflow_task_handle, 1);

    // Communication tasks (Core 0)
    // 通信タスク（Core 0）
    xTaskCreatePinnedToCore(CommTask, "CommTask", STACK_SIZE_COMM, nullptr,
                            PRIORITY_COMM_TASK, &g_comm_task_handle, 0);
    xTaskCreatePinnedToCore(CLITask, "CLITask", STACK_SIZE_CLI, nullptr,
                            PRIORITY_CLI_TASK, &g_cli_task_handle, 0);
    xTaskCreatePinnedToCore(TelemetryTask, "TelemetryTask", STACK_SIZE_TELEMETRY, nullptr,
                            PRIORITY_TELEMETRY_TASK, &g_telemetry_task_handle, 0);

    ESP_LOGI(TAG, "All tasks started");
}

// =============================================================================
// Main entry point
// メインエントリポイント
// =============================================================================

extern "C" void app_main(void)
{
    // Wait for USB debug connection
    // USB デバッグ接続を待つ
    vTaskDelay(pdMS_TO_TICKS(3000));
    printf("\n\n*** my_drone Boot ***\n\n");

    ESP_LOGI(TAG, "========================================");
    ESP_LOGI(TAG, "  my_drone");
    ESP_LOGI(TAG, "  ESP-IDF %s", esp_get_idf_version());
    ESP_LOGI(TAG, "========================================");

    // NVS initialization
    // NVS 初期化
    esp_err_t ret = nvs_flash_init();
    if (ret == ESP_ERR_NVS_NO_FREE_PAGES || ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ret = nvs_flash_init();
    }
    ESP_ERROR_CHECK(ret);

    // Network interface (required for ESP-NOW / WiFi)
    // ネットワークインタフェース（ESP-NOW / WiFi に必要）
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());

    // State managers
    // 状態マネージャ
    auto& state = stampfly::StampFlyState::getInstance();
    ESP_ERROR_CHECK(state.init());

    auto& sys_mgr = stampfly::SystemManager::getInstance();
    stampfly::SystemManager::Config sys_cfg;
    sys_cfg.init_timeout_ms = 5000;
    sys_cfg.calib_timeout_ms = 10000;
    ESP_ERROR_CHECK(sys_mgr.init(sys_cfg));

    // Hardware initialization (same sequence as vehicle firmware)
    // ハードウェア初期化（vehicle ファームウェアと同じ順序）
    init::i2c();
    stampfly::SystemStateManager::getInstance().init();
    init::actuators();
    init::sensors();
    init::estimators();
    init::communication();
    init::console();
    init::logger();
    init::telemetry();
    init::wifi_cli();

    // Start all FreeRTOS tasks
    // 全 FreeRTOS タスクを起動
    startTasks();

    // Wait for sensors to populate StampFlyState
    // センサが StampFlyState にデータを書き込むまで待機
    vTaskDelay(pdMS_TO_TICKS(3000));

    // Initialize ESKF with stable sensor data
    // 安定したセンサデータで ESKF を初期化
    if (g_fusion.isInitialized()) {
        g_fusion.reset();
        g_fusion.setGyroBias(g_initial_gyro_bias);
        initializeAttitudeFromBuffers();
        g_eskf_ready = true;
        ESP_LOGI(TAG, "ESKF initialized");
    }

    // Auto-enter pairing mode if no controller is paired
    // 未ペアリング時は自動的にペアリングモードに入る
    if (!g_comm.isPaired()) {
        ESP_LOGI(TAG, "No controller paired - entering pairing mode automatically");
        ESP_LOGI(TAG, "  Long press button (3s) to re-enter pairing mode later");
        g_comm.enterPairingMode();
        state.setPairingState(stampfly::PairingState::PAIRING);
        stampfly::LEDManager::getInstance().requestChannel(
            stampfly::LEDChannel::SYSTEM, stampfly::LEDPriority::PAIRING,
            stampfly::LEDPattern::BLINK_FAST, 0x0000FF);
        g_buzzer.beep();
    } else {
        ESP_LOGI(TAG, "Controller paired: ready for control input");
    }

    // Ready
    state.setFlightState(stampfly::FlightState::IDLE);
    ESP_LOGI(TAG, "Ready! Free heap: %lu bytes", esp_get_free_heap_size());

    // app_main must not return
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
}
