/*
 * M5Stack Atom JoyStick ドライバ - ESP-IDF I2C Master Driver版
 * ESP-IDF I2C master driver with proper timeout (replaces lgfx I2C)
 *
 * MIT License
 * Copyright (c) 2024 Kouhei Ito
 */
#include "atoms3joy.h"
#include <M5Unified.h>
#include <driver/i2c_master.h>
#include <esp_log.h>
#include <string.h>

static const char* TAG = "JOY";

// I2Cバスとデバイスハンドル
// I2C bus and device handles
static i2c_master_bus_handle_t joy_i2c_bus = NULL;
static i2c_master_dev_handle_t joy_i2c_dev = NULL;

// ジョイスティックデータ
static joy_data_t joy_data;
static int16_t button_counter[4] = {0};
static uint8_t button_old_state[4] = {0};
static bool joy_initialized = false;

// I2Cタイムアウト (ms)
// I2C timeout per transaction
#define JOY_I2C_TIMEOUT_MS 50

// I2C連続エラーカウント
// Consecutive I2C error counter for bus recovery
static uint32_t i2c_error_count = 0;
static const uint32_t I2C_RECOVERY_THRESHOLD = 10;

// I2Cバス復旧
// I2C bus recovery: reset and reinitialize
static esp_err_t i2c_bus_recovery(void)
{
    ESP_LOGW(TAG, "I2Cバス復旧中...");

    // デバイスを削除して再追加
    // Remove and re-add device
    if (joy_i2c_dev) {
        i2c_master_bus_rm_device(joy_i2c_dev);
        joy_i2c_dev = NULL;
    }

    // バスリセット
    // Reset bus
    if (joy_i2c_bus) {
        i2c_master_bus_reset(joy_i2c_bus);
    }

    // デバイス再登録
    // Re-add device
    i2c_device_config_t dev_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = JOY_I2C_ADDRESS,
        .scl_speed_hz = JOY_I2C_FREQ_HZ,
    };

    esp_err_t ret = i2c_master_bus_add_device(joy_i2c_bus, &dev_config, &joy_i2c_dev);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2Cデバイス再登録失敗: %s", esp_err_to_name(ret));
    } else {
        ESP_LOGI(TAG, "I2Cバス復旧完了");
    }

    i2c_error_count = 0;
    return ret;
}

// I2Cから2バイト読み取り (リトルエンディアン)
// Read 2 bytes from I2C (little-endian) with timeout
static bool read_2byte_data(uint8_t reg_addr, uint16_t *data)
{
    uint8_t buf[2];

    esp_err_t ret = i2c_master_transmit_receive(
        joy_i2c_dev,
        &reg_addr, 1,
        buf, 2,
        JOY_I2C_TIMEOUT_MS
    );

    if (ret != ESP_OK) {
        i2c_error_count++;
        if (i2c_error_count >= I2C_RECOVERY_THRESHOLD) {
            i2c_bus_recovery();
        }
        return false;
    }

    i2c_error_count = 0;
    *data = (uint16_t)(buf[1] << 8) | buf[0];
    return true;
}

// I2Cから1バイト読み取り
// Read 1 byte from I2C with timeout
static bool read_byte_data(uint8_t reg_addr, uint8_t *data)
{
    esp_err_t ret = i2c_master_transmit_receive(
        joy_i2c_dev,
        &reg_addr, 1,
        data, 1,
        JOY_I2C_TIMEOUT_MS
    );

    if (ret != ESP_OK) {
        i2c_error_count++;
        if (i2c_error_count >= I2C_RECOVERY_THRESHOLD) {
            i2c_bus_recovery();
        }
        return false;
    }

    i2c_error_count = 0;
    return true;
}

extern "C" esp_err_t joy_init(void)
{
    if (joy_initialized) {
        return ESP_OK;
    }

    // lgfxのEx_I2Cを解放してESP-IDF I2Cドライバに切り替え
    // Release lgfx Ex_I2C and switch to ESP-IDF I2C master driver
    // (lgfx I2Cにはタイムアウトがなく、バス異常時に永久ブロックする問題がある)
    // (lgfx I2C lacks proper timeout, causing infinite block on bus error)
    ESP_LOGI(TAG, "Ex_I2Cを解放してESP-IDF I2Cドライバに切替");
    m5::Ex_I2C.release();

    // ESP-IDF I2Cマスターバス作成
    // Create ESP-IDF I2C master bus with timeout support
    i2c_master_bus_config_t bus_config = {
        .i2c_port = I2C_NUM_1,
        .sda_io_num = (gpio_num_t)JOY_I2C_SDA_PIN,
        .scl_io_num = (gpio_num_t)JOY_I2C_SCL_PIN,
        .clk_source = I2C_CLK_SRC_DEFAULT,
        .glitch_ignore_cnt = 7,
        .flags = {
            .enable_internal_pullup = true,
        },
    };

    esp_err_t ret = i2c_new_master_bus(&bus_config, &joy_i2c_bus);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2Cバス作成失敗: %s", esp_err_to_name(ret));
        return ret;
    }

    // ジョイスティックデバイス登録
    // Add joystick device to I2C bus
    i2c_device_config_t dev_config = {
        .dev_addr_length = I2C_ADDR_BIT_LEN_7,
        .device_address = JOY_I2C_ADDRESS,
        .scl_speed_hz = JOY_I2C_FREQ_HZ,
    };

    ret = i2c_master_bus_add_device(joy_i2c_bus, &dev_config, &joy_i2c_dev);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "I2Cデバイス登録失敗: %s", esp_err_to_name(ret));
        return ret;
    }

    // データ初期化
    memset(&joy_data, 0, sizeof(joy_data));
    memset(button_counter, 0, sizeof(button_counter));
    memset(button_old_state, 0, sizeof(button_old_state));

    // 接続確認 (デバイスからの読み取りテスト)
    // Connection test (read from device)
    uint16_t test_data;
    if (!read_2byte_data(LEFT_STICK_X_ADDRESS, &test_data)) {
        ESP_LOGE(TAG, "ジョイスティック応答なし (addr: 0x%02X)", JOY_I2C_ADDRESS);
        return ESP_ERR_NOT_FOUND;
    }

    joy_initialized = true;
    ESP_LOGI(TAG, "ジョイスティック初期化完了 (I2C addr: 0x%02X, ESP-IDF I2Cドライバ)", JOY_I2C_ADDRESS);

    return ESP_OK;
}

extern "C" esp_err_t joy_update(void)
{
    if (!joy_initialized) {
        return ESP_ERR_INVALID_STATE;
    }

    // スティック値読み取り
    if (!read_2byte_data(LEFT_STICK_X_ADDRESS, &joy_data.stick[STICK_LEFTX])) return ESP_FAIL;
    if (!read_2byte_data(LEFT_STICK_Y_ADDRESS, &joy_data.stick[STICK_LEFTY])) return ESP_FAIL;
    if (!read_2byte_data(RIGHT_STICK_X_ADDRESS, &joy_data.stick[STICK_RIGHTX])) return ESP_FAIL;
    if (!read_2byte_data(RIGHT_STICK_Y_ADDRESS, &joy_data.stick[STICK_RIGHTY])) return ESP_FAIL;

    // ボタン読み取り + デバウンス処理
    for (int i = 0; i < 4; i++) {
        uint8_t raw_button;
        if (!read_byte_data(LEFT_STICK_BUTTON_ADDRESS + i, &raw_button)) return ESP_FAIL;

        // ボタンは負論理 (押すと0)
        joy_data.button[i] = (~raw_button) & 0x01;

        // デバウンス処理
        button_old_state[i] = joy_data.button_state[i];

        if (joy_data.button[i] == 1) {
            if (button_counter[i] < 0) button_counter[i] = 0;
            button_counter[i]++;
            if (button_counter[i] > 1) {
                button_counter[i] = 1;
                joy_data.button_state[i] = 1;  // 押し確定
            }
        } else {
            if (button_counter[i] > 0) button_counter[i] = 0;
            button_counter[i]--;
            if (button_counter[i] < -1) {
                button_counter[i] = -1;
                joy_data.button_state[i] = 0;  // 放し確定
            }
        }
    }

    // バッテリー電圧読み取り
    uint16_t voltage_raw;
    if (read_2byte_data(BATTERY_VOLTAGE1_ADDRESS, &voltage_raw)) {
        joy_data.battery_voltage[0] = (float)voltage_raw / 1000.0f;
    }

    if (read_2byte_data(BATTERY_VOLTAGE2_ADDRESS, &voltage_raw)) {
        joy_data.battery_voltage[1] = (float)voltage_raw / 1000.0f;
    }

    return ESP_OK;
}

extern "C" const joy_data_t* joy_get_data(void)
{
    return &joy_data;
}

// スティック値取得
extern "C" uint16_t joy_get_stick_left_x(void)  { return joy_data.stick[STICK_LEFTX]; }
extern "C" uint16_t joy_get_stick_left_y(void)  { return joy_data.stick[STICK_LEFTY]; }
extern "C" uint16_t joy_get_stick_right_x(void) { return joy_data.stick[STICK_RIGHTX]; }
extern "C" uint16_t joy_get_stick_right_y(void) { return joy_data.stick[STICK_RIGHTY]; }

// ボタン状態取得 (デバウンス済み)
extern "C" uint8_t joy_get_button_left_stick(void)  { return joy_data.button_state[BTN_LEFT_STICK]; }
extern "C" uint8_t joy_get_button_right_stick(void) { return joy_data.button_state[BTN_RIGHT_STICK]; }
extern "C" uint8_t joy_get_button_left(void)        { return joy_data.button_state[BTN_LEFT]; }
extern "C" uint8_t joy_get_button_right(void)       { return joy_data.button_state[BTN_RIGHT]; }

// ボタン生値取得 (デバウンスなし, 起動時判定用)
extern "C" uint8_t joy_get_button_left_raw(void)  { return joy_data.button[BTN_LEFT]; }
extern "C" uint8_t joy_get_button_right_raw(void) { return joy_data.button[BTN_RIGHT]; }

// バッテリー電圧取得
extern "C" float joy_get_battery_voltage1(void) { return joy_data.battery_voltage[0]; }
extern "C" float joy_get_battery_voltage2(void) { return joy_data.battery_voltage[1]; }

// スティックモード (デフォルト: Mode 2)
static uint8_t stick_mode = STICK_MODE_2;

extern "C" void joy_set_stick_mode(uint8_t mode)
{
    if (mode == STICK_MODE_2 || mode == STICK_MODE_3) {
        stick_mode = mode;
        ESP_LOGI(TAG, "スティックモード設定: %d", mode);
    }
}

extern "C" uint8_t joy_get_stick_mode(void)
{
    return stick_mode;
}

// ドローン操作用関数 (モードに応じて自動切替)
extern "C" uint16_t joy_get_throttle(void)
{
    // Mode 2: 左Y, Mode 3: 右Y
    return (stick_mode == STICK_MODE_2) ? joy_data.stick[STICK_LEFTY] : joy_data.stick[STICK_RIGHTY];
}

extern "C" uint16_t joy_get_aileron(void)
{
    // Mode 2: 右X, Mode 3: 左X
    return (stick_mode == STICK_MODE_2) ? joy_data.stick[STICK_RIGHTX] : joy_data.stick[STICK_LEFTX];
}

extern "C" uint16_t joy_get_elevator(void)
{
    // Mode 2: 右Y, Mode 3: 左Y
    return (stick_mode == STICK_MODE_2) ? joy_data.stick[STICK_RIGHTY] : joy_data.stick[STICK_LEFTY];
}

extern "C" uint16_t joy_get_rudder(void)
{
    // Mode 2: 左X, Mode 3: 右X
    return (stick_mode == STICK_MODE_2) ? joy_data.stick[STICK_LEFTX] : joy_data.stick[STICK_RIGHTX];
}

extern "C" uint8_t joy_get_arm_button(void)
{
    // Mode 2: 左スティック押し込み, Mode 3: 右スティック押し込み
    return (stick_mode == STICK_MODE_2) ? joy_data.button_state[BTN_LEFT_STICK] : joy_data.button_state[BTN_RIGHT_STICK];
}

extern "C" uint8_t joy_get_flip_button(void)
{
    // Mode 2: 右スティック押し込み, Mode 3: 左スティック押し込み
    return (stick_mode == STICK_MODE_2) ? joy_data.button_state[BTN_RIGHT_STICK] : joy_data.button_state[BTN_LEFT_STICK];
}
