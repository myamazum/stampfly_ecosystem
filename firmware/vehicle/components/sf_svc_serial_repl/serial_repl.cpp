/**
 * @file serial_repl.cpp
 * @brief Serial REPL implementation using ESP-IDF Console REPL
 *
 * ESP-IDF の esp_console REPL API を使用した Serial REPL の実装
 * USB CDC 経由で linenoise による履歴・補完・行編集機能を提供
 */

#include "serial_repl.hpp"
#include "console.hpp"

#include <cstdio>
#include <cstring>

#include "esp_log.h"
#include "esp_console.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char* TAG = "SerialREPL";

namespace stampfly {

// =============================================================================
// Singleton Instance
// =============================================================================

SerialREPL& SerialREPL::getInstance()
{
    static SerialREPL instance;
    return instance;
}

// =============================================================================
// Initialization
// =============================================================================

esp_err_t SerialREPL::init()
{
    if (initialized_) {
        ESP_LOGW(TAG, "SerialREPL already initialized");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing SerialREPL with esp_console REPL");

    // =========================================================================
    // Configure esp_console REPL for USB CDC
    // USB CDC 用に esp_console REPL を設定
    // =========================================================================
    esp_console_repl_config_t repl_config = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    repl_config.prompt = "stampfly>";
    repl_config.max_cmdline_length = 256;
    repl_config.history_save_path = NULL;  // Don't save history to file
    repl_config.task_stack_size = 4096;
    repl_config.task_priority = 5;

    // USB CDC device configuration
    // USB CDC デバイス設定
    esp_console_dev_usb_cdc_config_t cdc_config = ESP_CONSOLE_DEV_CDC_CONFIG_DEFAULT();

    // Initialize the REPL
    // REPL を初期化
    esp_err_t ret = esp_console_new_repl_usb_cdc(&cdc_config, &repl_config, &repl_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to create USB CDC REPL: %s", esp_err_to_name(ret));
        return ret;
    }

    initialized_ = true;
    ESP_LOGI(TAG, "SerialREPL initialized successfully");
    return ESP_OK;
}

// =============================================================================
// Start REPL
// =============================================================================

esp_err_t SerialREPL::start()
{
    if (!initialized_) {
        ESP_LOGE(TAG, "SerialREPL not initialized");
        return ESP_ERR_INVALID_STATE;
    }

    if (running_) {
        ESP_LOGW(TAG, "SerialREPL already running");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Starting SerialREPL");

    // Start the REPL task
    // REPL タスクを開始
    esp_err_t ret = esp_console_start_repl(repl_);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start REPL: %s", esp_err_to_name(ret));
        return ret;
    }

    running_ = true;
    ESP_LOGI(TAG, "SerialREPL started");
    return ESP_OK;
}

// =============================================================================
// Run (blocking - for compatibility, but not used with esp_console REPL)
// =============================================================================

void SerialREPL::run()
{
    // With esp_console REPL, the REPL runs in its own task
    // esp_console REPL では、REPL は独自のタスクで実行される
    // This function is kept for API compatibility but should not be called
    // この関数は API 互換性のために残すが、呼び出すべきではない

    ESP_LOGW(TAG, "SerialREPL::run() called but esp_console REPL manages its own task");
    ESP_LOGW(TAG, "Use SerialREPL::start() instead");

    // Block forever to prevent the calling task from exiting
    // 呼び出し元タスクが終了しないように永久にブロック
    while (true) {
        vTaskDelay(pdMS_TO_TICKS(10000));
    }
}

// =============================================================================
// Configuration
// =============================================================================

void SerialREPL::setHistoryMaxLen(int len)
{
    history_max_len_ = len;
    // Note: With esp_console REPL, history is managed internally
    // esp_console REPL では履歴は内部で管理される
}

}  // namespace stampfly
