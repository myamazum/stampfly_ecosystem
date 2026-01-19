/**
 * @file cli_task.cpp
 * @brief CLI Task - Serial CLI using custom LineEditor
 *
 * CLIタスク - 独自 LineEditor を使用した Serial CLI
 *
 * Features:
 * - Command history (up/down arrows)
 * - Tab completion for registered commands
 * - Line editing (cursor movement, backspace, delete)
 *
 * Note: Binary logging moved to stampfly_logger component (400Hz via ESP Timer)
 */

#include "tasks_common.hpp"
#include "serial_cli.hpp"
#include "console.hpp"

static const char* TAG = "CLITask";

using namespace config;
using namespace globals;

void CLITask(void* pvParameters)
{
    ESP_LOGI(TAG, "CLITask started");

    // Get SerialCLI instance
    // SerialCLI インスタンスを取得
    auto& cli = stampfly::SerialCLI::getInstance();

    // Initialize SerialCLI (initializes esp_console for command registration)
    // SerialCLI を初期化（コマンド登録用に esp_console を初期化）
    esp_err_t ret = cli.init();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize SerialCLI: %s", esp_err_to_name(ret));
        // Fall back to simple loop if initialization fails
        // 初期化に失敗した場合はシンプルなループにフォールバック
        while (true) {
            vTaskDelay(pdMS_TO_TICKS(1000));
        }
    }

    // Now that esp_console is initialized, register all commands
    // esp_console が初期化されたので、全コマンドを登録
    auto& console = stampfly::Console::getInstance();
    console.registerAllCommands();

    // Run the CLI loop (blocking)
    // CLI ループを実行（ブロッキング）
    ESP_LOGI(TAG, "Starting SerialCLI");
    cli.run();

    // Should not reach here unless CLI is stopped
    // CLI が停止されない限りここには到達しない
    ESP_LOGI(TAG, "CLITask ending");
    vTaskDelete(NULL);
}
