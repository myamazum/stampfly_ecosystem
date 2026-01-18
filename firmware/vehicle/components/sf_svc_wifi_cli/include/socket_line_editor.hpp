/**
 * @file socket_line_editor.hpp
 * @brief Socket-based line editor with history and completion
 *
 * Provides linenoise-like line editing over TCP sockets:
 * - Command history (up/down arrows)
 * - Cursor movement (left/right arrows)
 * - Tab completion
 *
 * ソケットベースの行エディタ（履歴・補完機能付き）
 * - コマンド履歴（上下矢印）
 * - カーソル移動（左右矢印）
 * - Tab補完
 */

#pragma once

#include <cstddef>
#include <cstdint>

namespace stampfly {

/**
 * @brief Completions structure for tab completion
 */
struct SocketCompletions {
    static constexpr int MAX_COMPLETIONS = 16;
    char* cvec[MAX_COMPLETIONS];
    size_t len = 0;

    void add(const char* str);
    void clear();
};

/**
 * @brief Callback type for tab completion
 */
using SocketCompletionCallback = void (*)(const char* buf, SocketCompletions* lc);

/**
 * @brief Socket-based line editor with history and completion
 *
 * Provides readline-like functionality over TCP sockets
 */
class SocketLineEditor {
public:
    /**
     * @brief Constructor
     * @param fd Socket file descriptor
     */
    explicit SocketLineEditor(int fd);

    /**
     * @brief Destructor - frees history
     */
    ~SocketLineEditor();

    // Non-copyable
    // コピー禁止
    SocketLineEditor(const SocketLineEditor&) = delete;
    SocketLineEditor& operator=(const SocketLineEditor&) = delete;

    /**
     * @brief Get a line of input (blocking)
     * @param prompt Prompt to display
     * @return Line buffer (caller must free with freeLine()) or nullptr on error/disconnect
     *
     * 1行の入力を取得（ブロッキング）
     */
    char* getLine(const char* prompt);

    /**
     * @brief Free a line returned by getLine()
     * @param line Line to free
     */
    void freeLine(char* line);

    /**
     * @brief Add a line to history
     * @param line Line to add
     */
    void addHistory(const char* line);

    /**
     * @brief Set maximum history length
     * @param len Maximum number of history entries (default: 10)
     */
    void setHistoryMaxLen(int len);

    /**
     * @brief Set completion callback
     * @param callback Callback function for tab completion
     */
    void setCompletionCallback(SocketCompletionCallback callback);

private:
    int fd_;

    // Line buffer
    // 行バッファ
    static constexpr size_t BUFFER_SIZE = 256;
    char buffer_[BUFFER_SIZE];
    size_t pos_ = 0;  // Cursor position / カーソル位置
    size_t len_ = 0;  // Line length / 行の長さ

    // History
    // 履歴
    static constexpr int MAX_HISTORY = 10;
    char* history_[MAX_HISTORY] = {};
    int history_len_ = 0;
    int history_max_ = MAX_HISTORY;
    int history_index_ = -1;

    // Completion callback
    // 補完コールバック
    SocketCompletionCallback completion_callback_ = nullptr;

    // Escape sequence state machine
    // エスケープシーケンス状態マシン
    enum class EscState { NONE, ESC, CSI };
    EscState esc_state_ = EscState::NONE;
    char esc_buf_[8];
    int esc_pos_ = 0;

    // Internal methods
    // 内部メソッド
    void writeStr(const char* str);
    void writeChar(char c);
    void refreshLine(const char* prompt);

    bool processChar(char c, const char* prompt);
    void processEscape(char c, const char* prompt);
    void processCSI(char c, const char* prompt);

    void handleArrowUp(const char* prompt);
    void handleArrowDown(const char* prompt);
    void handleArrowLeft(const char* prompt);
    void handleArrowRight(const char* prompt);
    void handleBackspace(const char* prompt);
    void handleDelete(const char* prompt);
    void handleTab(const char* prompt);
    void handleHome(const char* prompt);
    void handleEnd(const char* prompt);

    void insertChar(char c, const char* prompt);
    void deleteCharAt(size_t pos, const char* prompt);

    void clearHistory();
};

}  // namespace stampfly
