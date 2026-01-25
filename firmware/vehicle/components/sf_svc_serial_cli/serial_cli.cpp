/**
 * @file serial_cli.cpp
 * @brief Serial CLI implementation using LineEditor
 *
 * Provides cursor-visible Serial CLI over USB CDC using custom LineEditor
 * instead of ESP-IDF standard linenoise.
 */

#include "serial_cli.hpp"
#include "line_editor.hpp"
#include "console.hpp"

#include "esp_log.h"
#include "esp_console.h"
#include "esp_vfs_dev.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include <cstdio>
#include <cstring>

static const char* TAG = "SerialCLI";

namespace stampfly {

// =============================================================================
// USB CDC I/O Callbacks for LineEditor
// =============================================================================

/**
 * @brief Read a single byte from stdin
 * @param ctx User context (unused for stdio)
 * @return Byte read, or -1 on error/disconnect
 *
 * stdinから1バイト読み取り
 */
static int stdio_read_byte(void* ctx)
{
    (void)ctx;  // Unused

    int c = getchar();
    if (c == EOF) {
        // USB CDC may temporarily disconnect
        // USB CDCが一時的に切断される可能性がある
        vTaskDelay(pdMS_TO_TICKS(10));
        return -1;
    }
    return c;
}

/**
 * @brief Write data to stdout
 * @param ctx User context (unused for stdio)
 * @param data Data to write
 * @param len Length of data
 * @return Number of bytes written
 *
 * stdoutにデータを書き込む
 */
static int stdio_write_data(void* ctx, const void* data, size_t len)
{
    (void)ctx;  // Unused

    if (data == nullptr || len == 0) {
        return 0;
    }

    size_t written = fwrite(data, 1, len, stdout);
    fflush(stdout);
    return static_cast<int>(written);
}

// =============================================================================
// Completion Callback for Serial CLI
// =============================================================================

/**
 * @brief Tab completion callback for Serial CLI
 * @param buf Current input buffer
 * @param lc Completions structure to populate
 *
 * Serial CLI用のTab補完コールバック
 */
static void serialCompletionCallback(const char* buf, LineCompletions* lc)
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
        "wifi",
        nullptr
    };

    for (int i = 0; commands[i] != nullptr; i++) {
        if (strncmp(buf, commands[i], buf_len) == 0) {
            lc->add(commands[i]);
        }
    }
}

// =============================================================================
// SerialCLI Implementation
// =============================================================================

SerialCLI& SerialCLI::getInstance()
{
    static SerialCLI instance;
    return instance;
}

int SerialCLI::init()
{
    if (initialized_) {
        ESP_LOGW(TAG, "SerialCLI already initialized");
        return ESP_OK;
    }

    ESP_LOGI(TAG, "Initializing Serial CLI");

    // Disable buffering on stdin/stdout for immediate character reception
    // stdin/stdoutのバッファリングを無効化（文字を即座に受信）
    setvbuf(stdin, nullptr, _IONBF, 0);
    setvbuf(stdout, nullptr, _IONBF, 0);

    // Initialize ESP-IDF console (for command registration)
    // ESP-IDFコンソールを初期化（コマンド登録用）
    esp_console_config_t console_config = ESP_CONSOLE_CONFIG_DEFAULT();
    console_config.max_cmdline_length = 256;
    console_config.max_cmdline_args = 32;

    esp_err_t ret = esp_console_init(&console_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to initialize console: %s", esp_err_to_name(ret));
        return ret;
    }

    // Register all commands via Console
    // Console経由で全コマンドを登録
    auto& console = Console::getInstance();
    console.registerAllCommands();

    initialized_ = true;
    ESP_LOGI(TAG, "Serial CLI initialized");

    return ESP_OK;
}

void SerialCLI::run()
{
    if (!initialized_) {
        ESP_LOGE(TAG, "SerialCLI not initialized, call init() first");
        return;
    }

    ESP_LOGI(TAG, "Starting Serial CLI");

    // Create LineEditor with stdio I/O callbacks
    // stdioI/Oコールバックを使用してLineEditorを作成
    LineEditorIO io = {
        .read_byte = stdio_read_byte,
        .write_data = stdio_write_data,
        .ctx = nullptr,
    };

    LineEditorConfig config = {
        .enable_telnet_negotiation = false,  // USB CDC doesn't use Telnet
        .history_max_len = 10,
    };

    LineEditor editor(io, config);
    editor.setCompletionCallback(serialCompletionCallback);

    // Get console reference
    // コンソール参照を取得
    auto& console = Console::getInstance();

    // Print welcome message
    // ウェルカムメッセージを表示
    printf("\n");
    printf("========================================\n");
    printf("  StampFly Vehicle Firmware\n");
    printf("========================================\n");
    printf("Type 'help' for available commands\n");
    printf("\n");

    // REPL loop
    // REPLループ
    while (true) {
        // Get line using LineEditor (handles history, editing, completion)
        // LineEditorを使って行を取得（履歴、編集、補完を処理）
        char* line = editor.getLine("stampfly> ");

        if (line == nullptr) {
            // Error or disconnect
            // エラーまたは切断
            vTaskDelay(pdMS_TO_TICKS(10));
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
        // Console経由でコマンドを実行
        if (!console.isInitialized()) {
            printf("Console not available\n");
        } else {
            int ret = console.run(line);
            if (ret != 0 && ret != -1) {
                // ret == -1 means command not found, already handled by console
                // ret == -1はコマンド未発見、コンソールで既に処理済み
                printf("Error: %d\n", ret);
            }
        }

        editor.freeLine(line);
    }
}

}  // namespace stampfly
