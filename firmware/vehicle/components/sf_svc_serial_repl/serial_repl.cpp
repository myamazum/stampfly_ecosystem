/**
 * @file serial_repl.cpp
 * @brief Serial REPL implementation with linenoise
 *
 * USB Serial を使用した REPL の実装
 * linenoise による履歴・補完・行編集機能を提供
 *
 * Note: VFS configuration for stdin/stdout is handled by ESP-IDF based on
 * sdkconfig (CONFIG_ESP_CONSOLE_USB_CDC or CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG)
 */

#include "serial_repl.hpp"
#include "console.hpp"

#include <cstdio>
#include <cstring>

#include "esp_log.h"
#include "linenoise/linenoise.h"
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

    ESP_LOGI(TAG, "Initializing SerialREPL with linenoise");

    // =========================================================================
    // Configure linenoise
    // linenoise の設定
    //
    // Note: VFS (stdin/stdout routing) is already configured by ESP-IDF
    // based on sdkconfig (CONFIG_ESP_CONSOLE_USB_CDC)
    // =========================================================================
    linenoiseSetMultiLine(1);  // Enable multiline mode / マルチライン有効化
    linenoiseHistorySetMaxLen(history_max_len_);

    // Set completion callback for tab completion
    // Tab補完用コールバックを設定
    linenoiseSetCompletionCallback(
        reinterpret_cast<linenoiseCompletionCallback*>(completionCallback));

    // Set hints callback (optional)
    // ヒントコールバックを設定（オプション）
    linenoiseSetHintsCallback(
        reinterpret_cast<linenoiseHintsCallback*>(hintsCallback));

    // Disable buffering for stdin
    // stdinのバッファリングを無効化
    setvbuf(stdin, NULL, _IONBF, 0);

    initialized_ = true;
    ESP_LOGI(TAG, "SerialREPL initialized successfully");
    return ESP_OK;
}

// =============================================================================
// Main REPL Loop
// =============================================================================

void SerialREPL::run()
{
    if (!initialized_) {
        ESP_LOGE(TAG, "SerialREPL not initialized");
        return;
    }

    auto& console = Console::getInstance();

    // Set output to stdout for Serial REPL
    // Serial REPL用にstdout出力を設定
    console.setOutput([](const char* str, void*) {
        printf("%s", str);
        fflush(stdout);
    }, nullptr);

    // Welcome message
    // ウェルカムメッセージ
    printf("\r\n");
    printf("=== StampFly CLI ===\r\n");
    printf("Type 'help' for available commands.\r\n");
    printf("\r\n");

    while (true) {
        // linenoise handles:
        // - History (up/down arrows)
        // - Line editing (left/right arrows, backspace, delete)
        // - Tab completion
        // - Ctrl+C (returns nullptr)
        // - Ctrl+D (returns nullptr at empty line)
        //
        // linenoiseが処理する機能:
        // - 履歴（上下矢印）
        // - 行編集（左右矢印、バックスペース、削除）
        // - Tab補完
        // - Ctrl+C（nullptrを返す）
        // - Ctrl+D（空行でnullptrを返す）
        char* line = linenoise("stampfly> ");

        if (line == nullptr) {
            // EOF, Ctrl+C, or error - small delay and continue
            // EOF、Ctrl+C、またはエラー - 少し待って継続
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        // Skip empty lines
        // 空行はスキップ
        if (strlen(line) == 0) {
            linenoiseFree(line);
            continue;
        }

        // Add to history
        // 履歴に追加
        linenoiseHistoryAdd(line);

        // Execute command
        // コマンドを実行
        int ret = console.run(line);
        if (ret != 0) {
            printf("Error: command returned %d\r\n", ret);
        }

        linenoiseFree(line);
    }
}

// =============================================================================
// Configuration
// =============================================================================

void SerialREPL::setHistoryMaxLen(int len)
{
    history_max_len_ = len;
    if (initialized_) {
        linenoiseHistorySetMaxLen(len);
    }
}

// =============================================================================
// Completion Callback
// =============================================================================

void SerialREPL::completionCallback(const char* buf, void* lc)
{
    if (buf == nullptr || lc == nullptr) {
        return;
    }

    linenoiseCompletions* completions = static_cast<linenoiseCompletions*>(lc);
    size_t buf_len = strlen(buf);

    // Get registered commands from esp_console
    // esp_consoleから登録済みコマンドを取得

    // List of known commands for completion
    // 補完用の既知コマンドリスト
    static const char* commands[] = {
        "help",
        "status",
        "reboot",
        "version",
        "sensor",
        "loglevel",
        "binlog",
        "motor",
        "trim",
        "gain",
        "comm",
        "pair",
        "unpair",
        "calib",
        "magcal",
        "led",
        "sound",
        "pos",
        "debug",
        "ctrl",
        "attitude",
        nullptr
    };

    for (int i = 0; commands[i] != nullptr; i++) {
        // Check if command starts with the current input
        // コマンドが現在の入力で始まるかチェック
        if (strncmp(buf, commands[i], buf_len) == 0) {
            linenoiseAddCompletion(completions, commands[i]);
        }
    }
}

// =============================================================================
// Hints Callback
// =============================================================================

char* SerialREPL::hintsCallback(const char* buf, int* color, int* bold)
{
    if (buf == nullptr) {
        return nullptr;
    }

    // Provide hints for common commands
    // よく使うコマンドのヒントを提供
    if (strcmp(buf, "motor") == 0) {
        *color = 35;  // Magenta
        *bold = 0;
        return const_cast<char*>(" <motor_num> <duty>");
    }
    if (strcmp(buf, "gain") == 0) {
        *color = 35;
        *bold = 0;
        return const_cast<char*>(" [pitch|roll|yaw] [p|i|d] <value>");
    }
    if (strcmp(buf, "trim") == 0) {
        *color = 35;
        *bold = 0;
        return const_cast<char*>(" <roll> <pitch>");
    }
    if (strcmp(buf, "led") == 0) {
        *color = 35;
        *bold = 0;
        return const_cast<char*>(" <r> <g> <b>");
    }
    if (strcmp(buf, "loglevel") == 0) {
        *color = 35;
        *bold = 0;
        return const_cast<char*>(" [none|error|warn|info|debug|verbose]");
    }
    if (strcmp(buf, "binlog") == 0) {
        *color = 35;
        *bold = 0;
        return const_cast<char*>(" [start|stop|status]");
    }
    if (strcmp(buf, "calib") == 0) {
        *color = 35;
        *bold = 0;
        return const_cast<char*>(" [gyro|acc] - Calibrate sensors");
    }
    if (strcmp(buf, "magcal") == 0) {
        *color = 35;
        *bold = 0;
        return const_cast<char*>(" [start|stop|status] - Magnetometer calibration");
    }

    return nullptr;
}

}  // namespace stampfly
