/**
 * @file serial_cli.cpp
 * @brief Serial CLI implementation using custom LineEditor
 *
 * 独自 LineEditor を使用した Serial CLI の実装
 * USB CDC 経由で履歴・補完・行編集機能を提供
 */

#include "serial_cli.hpp"
#include "console.hpp"
#include "line_editor.hpp"

#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>

#include "esp_log.h"
#include "esp_console.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char* TAG = "SerialCLI";

namespace stampfly {

// =============================================================================
// I/O Callbacks for LineEditor
// =============================================================================

/**
 * @brief Read a byte from stdin
 * @param ctx Unused context
 * @return Byte read, or -1 on error
 *
 * stdin から 1 バイト読み取る
 */
static int stdio_read_byte(void* ctx)
{
    (void)ctx;
    int c = getchar();
    if (c == EOF) {
        // EOF - wait a bit and try again (USB CDC may return EOF temporarily)
        // EOF - 少し待って再試行（USB CDC は一時的に EOF を返すことがある）
        vTaskDelay(pdMS_TO_TICKS(10));
        return -1;
    }
    return c;
}

/**
 * @brief Write data to stdout
 * @param ctx Unused context
 * @param data Data to write
 * @param len Length of data
 * @return Number of bytes written
 *
 * stdout にデータを書き込む
 */
static int stdio_write_data(void* ctx, const void* data, size_t len)
{
    (void)ctx;
    if (data == nullptr || len == 0) {
        return 0;
    }
    // Use fwrite for binary-safe output
    // バイナリセーフな出力のために fwrite を使用
    size_t written = fwrite(data, 1, len, stdout);
    fflush(stdout);
    return static_cast<int>(written);
}

// =============================================================================
// Tab Completion Callback
// =============================================================================

/**
 * @brief Tab completion callback
 * @param buf Current input buffer
 * @param lc Completions to fill
 *
 * Tab補完コールバック
 */
static void completion_callback(const char* buf, LineCompletions* lc)
{
    if (buf == nullptr || lc == nullptr) {
        return;
    }

    size_t buf_len = strlen(buf);

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
        if (strncmp(buf, commands[i], buf_len) == 0) {
            lc->add(commands[i]);
        }
    }
}

// =============================================================================
// Singleton Instance
// =============================================================================

SerialCLI& SerialCLI::getInstance()
{
    static SerialCLI instance;
    return instance;
}

// =============================================================================
// Initialization
// =============================================================================

esp_err_t SerialCLI::init()
{
    if (initialized_) {
        ESP_LOGW(TAG, "SerialCLI already initialized");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing SerialCLI");

    // =========================================================================
    // VFS Setup
    // VFS セットアップ
    // =========================================================================
    // Note: VFS is set up automatically by esp_vfs_console component based on
    // sdkconfig (CONFIG_ESP_CONSOLE_USB_SERIAL_JTAG or similar).
    // We just need to disable stdin buffering for character-at-a-time input.
    //
    // esp_vfs_console コンポーネントが sdkconfig に基づいて
    // 自動的に VFS をセットアップする。
    // ここでは1文字ずつ入力を受け取るため stdin バッファリングを無効化する。

    setvbuf(stdin, NULL, _IONBF, 0);

    // =========================================================================
    // Initialize esp_console (for command registration)
    // esp_console を初期化（コマンド登録用）
    // =========================================================================
    esp_console_config_t console_config = {
        .max_cmdline_length = 256,
        .max_cmdline_args = 8,
        .hint_color = 36,  // ANSI cyan color code
        .hint_bold = 0,
    };

    esp_err_t ret = esp_console_init(&console_config);
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        // ESP_ERR_INVALID_STATE means already initialized
        // ESP_ERR_INVALID_STATE は既に初期化済みを意味する
        ESP_LOGE(TAG, "Failed to initialize esp_console: %s", esp_err_to_name(ret));
        return ret;
    }

    initialized_ = true;
    ESP_LOGI(TAG, "SerialCLI initialized");
    return ESP_OK;
}

// =============================================================================
// CLI Loop
// =============================================================================

void SerialCLI::run()
{
    if (!initialized_) {
        ESP_LOGE(TAG, "SerialCLI not initialized");
        return;
    }

    if (running_) {
        ESP_LOGW(TAG, "SerialCLI already running");
        return;
    }

    running_ = true;
    should_stop_ = false;

    ESP_LOGI(TAG, "Starting CLI loop");

    // Create LineEditor with stdio callbacks
    // stdio コールバックで LineEditor を作成
    LineEditorIO io = {
        .read_byte = stdio_read_byte,
        .write_data = stdio_write_data,
        .ctx = nullptr,
    };

    LineEditorConfig config = {
        .enable_telnet_negotiation = false,
        .history_max_len = history_max_len_,
    };

    LineEditor editor(io, config);
    editor.setCompletionCallback(completion_callback);

    // Get console reference
    // コンソール参照を取得
    auto& console = Console::getInstance();

    // Welcome message
    // ウェルカムメッセージ
    printf("\r\n");
    printf("========================================\r\n");
    printf("  StampFly Serial CLI\r\n");
    printf("========================================\r\n");
    printf("Type 'help' for available commands.\r\n");
    printf("\r\n");
    fflush(stdout);

    // Main loop
    // メインループ
    while (!should_stop_) {
        // Get line using LineEditor (handles history, editing, completion)
        // LineEditor を使って行を取得（履歴、編集、補完を処理）
        char* line = editor.getLine("stampfly> ");

        if (line == nullptr) {
            // Error (usually USB disconnect)
            // エラー（通常は USB 切断）
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        // Skip empty lines
        // 空行をスキップ
        if (line[0] == '\0') {
            editor.freeLine(line);
            continue;
        }

        // Add to history
        // 履歴に追加
        editor.addHistory(line);

        // Execute command via Console
        // Console 経由でコマンドを実行
        if (!console.isInitialized()) {
            printf("Console not initialized\r\n");
            fflush(stdout);
        } else {
            int ret = console.run(line);
            if (ret != 0) {
                // Error already printed by console.run()
                // エラーは console.run() で既に表示済み
            }
        }

        editor.freeLine(line);
    }

    running_ = false;
    ESP_LOGI(TAG, "CLI loop ended");
}

void SerialCLI::stop()
{
    should_stop_ = true;
}

// =============================================================================
// Configuration
// =============================================================================

void SerialCLI::setHistoryMaxLen(int len)
{
    history_max_len_ = len;
}

}  // namespace stampfly
