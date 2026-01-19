/**
 * @file serial_cli.hpp
 * @brief Serial CLI using custom LineEditor
 *
 * Provides command-line interface over USB CDC with:
 * - Command history (up/down arrows)
 * - Tab completion for registered commands
 * - Line editing (cursor movement, backspace, delete)
 *
 * シリアルCLI（独自LineEditor使用）
 * - コマンド履歴（上下矢印）
 * - Tab補完
 * - 行編集（カーソル移動、バックスペース、削除）
 */

#pragma once

#include "esp_err.h"

namespace stampfly {

/**
 * @brief Serial CLI class using custom LineEditor
 *
 * Singleton class that manages USB CDC CLI with custom
 * line editing instead of ESP-IDF's linenoise.
 */
class SerialCLI {
public:
    /**
     * @brief Get singleton instance
     * @return Reference to SerialCLI instance
     */
    static SerialCLI& getInstance();

    /**
     * @brief Initialize Serial CLI
     *
     * Initializes esp_console for command registration.
     * Does not start the REPL loop.
     *
     * esp_console をコマンド登録用に初期化。
     * REPL ループは開始しない。
     *
     * @return ESP_OK on success
     */
    esp_err_t init();

    /**
     * @brief Run the CLI loop (blocking)
     *
     * Runs the line editing loop in the current task.
     * This function does not return until CLI is stopped.
     *
     * 現在のタスクで行編集ループを実行。
     * CLI が停止するまでこの関数は戻らない。
     */
    void run();

    /**
     * @brief Stop the CLI loop
     *
     * Signals the CLI loop to exit.
     *
     * CLI ループに終了を通知。
     */
    void stop();

    /**
     * @brief Check if CLI is initialized
     * @return true if initialized
     */
    bool isInitialized() const { return initialized_; }

    /**
     * @brief Check if CLI is running
     * @return true if running
     */
    bool isRunning() const { return running_; }

    /**
     * @brief Set history maximum length
     * @param len Maximum number of history entries (default: 20)
     */
    void setHistoryMaxLen(int len);

private:
    SerialCLI() = default;
    ~SerialCLI() = default;

    // Non-copyable
    // コピー禁止
    SerialCLI(const SerialCLI&) = delete;
    SerialCLI& operator=(const SerialCLI&) = delete;

    bool initialized_ = false;
    bool running_ = false;
    bool should_stop_ = false;
    int history_max_len_ = 20;
};

}  // namespace stampfly
