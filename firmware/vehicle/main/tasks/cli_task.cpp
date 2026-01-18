/**
 * @file cli_task.cpp
 * @brief CLI Task - Serial REPL using ESP-IDF Console REPL API
 *
 * CLIタスク - ESP-IDF Console REPL API を使用した Serial REPL
 *
 * Features:
 * - Command history (up/down arrows)
 * - Tab completion for registered commands
 * - Line editing (cursor movement, backspace, delete)
 *
 * Note: Binary logging moved to stampfly_logger component (400Hz via ESP Timer)
 */

#include "tasks_common.hpp"
#include "serial_repl.hpp"

static const char* TAG = "CLITask";

using namespace config;
using namespace globals;

void CLITask(void* pvParameters)
{
    ESP_LOGI(TAG, "CLITask started");

    // Get SerialREPL instance
    // SerialREPLインスタンスを取得
    auto& repl = stampfly::SerialREPL::getInstance();

    // Initialize SerialREPL (creates USB CDC REPL)
    // SerialREPLを初期化（USB CDC REPL を作成）
    esp_err_t ret = repl.init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize SerialREPL: %s", esp_err_to_name(ret));
        // Fall back to simple loop if initialization fails
        // 初期化に失敗した場合はシンプルなループにフォールバック
        while (true) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }

    // Start the REPL (non-blocking, starts internal task)
    // REPLを開始（非ブロッキング、内部タスクを開始）
    ret = repl.start();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start SerialREPL: %s", esp_err_to_name(ret));
        while (true) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }

    // The REPL runs in its own task managed by esp_console
    // REPL は esp_console が管理する独自のタスクで実行される
    // This task can now be deleted or used for other purposes
    // このタスクは削除するか、他の目的に使用できる
    ESP_LOGI(TAG, "SerialREPL started, CLITask exiting");

    // Delete this task since REPL has its own task
    // REPL は独自のタスクを持つため、このタスクを削除
    vTaskDelete(NULL);
}
