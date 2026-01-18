/**
 * @file serial_repl.hpp
 * @brief Serial REPL using ESP-IDF Console REPL API
 *
 * Provides command-line interface over USB CDC with:
 * - Command history (up/down arrows)
 * - Tab completion for registered commands
 * - Line editing (cursor movement, backspace, delete)
 *
 * シリアルREPL（ESP-IDF Console REPL API 使用）
 * - コマンド履歴（上下矢印）
 * - Tab補完
 * - 行編集（カーソル移動、バックスペース、削除）
 */

#pragma once

#include "esp_err.h"
#include "esp_console.h"

namespace stampfly {

/**
 * @brief Serial REPL class using ESP-IDF Console REPL API
 *
 * Singleton class that manages USB CDC REPL with linenoise
 * for advanced line editing capabilities.
 */
class SerialREPL {
public:
    /**
     * @brief Get singleton instance
     * @return Reference to SerialREPL instance
     */
    static SerialREPL& getInstance();

    /**
     * @brief Initialize Serial REPL
     *
     * Creates USB CDC REPL with esp_console API.
     * Configures linenoise with history and completion.
     *
     * esp_console API を使用して USB CDC REPL を作成。
     * linenoise の履歴と補完を設定。
     *
     * @return ESP_OK on success
     */
    esp_err_t init();

    /**
     * @brief Start the REPL (non-blocking)
     *
     * Starts the REPL task managed by esp_console.
     * Returns immediately after starting the task.
     *
     * esp_console が管理する REPL タスクを開始。
     * タスク開始後すぐに戻る。
     *
     * @return ESP_OK on success
     */
    esp_err_t start();

    /**
     * @brief Run the REPL loop (blocking, for compatibility)
     *
     * With esp_console REPL, the task is managed internally.
     * This function blocks forever for API compatibility.
     * Prefer using start() instead.
     *
     * esp_console REPL ではタスクは内部管理される。
     * API 互換性のためにこの関数は永久にブロックする。
     * 代わりに start() を使用することを推奨。
     */
    void run();

    /**
     * @brief Check if REPL is initialized
     * @return true if initialized
     */
    bool isInitialized() const { return initialized_; }

    /**
     * @brief Check if REPL is running
     * @return true if running
     */
    bool isRunning() const { return running_; }

    /**
     * @brief Set history maximum length
     * @param len Maximum number of history entries (default: 20)
     */
    void setHistoryMaxLen(int len);

private:
    SerialREPL() = default;
    ~SerialREPL() = default;

    // Non-copyable
    // コピー禁止
    SerialREPL(const SerialREPL&) = delete;
    SerialREPL& operator=(const SerialREPL&) = delete;

    bool initialized_ = false;
    bool running_ = false;
    int history_max_len_ = 20;
    esp_console_repl_t* repl_ = nullptr;
};

}  // namespace stampfly
