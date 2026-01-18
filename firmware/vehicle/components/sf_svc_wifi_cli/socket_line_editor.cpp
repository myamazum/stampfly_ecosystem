/**
 * @file socket_line_editor.cpp
 * @brief Socket-based line editor implementation
 *
 * ソケットベース行エディタの実装
 */

#include "socket_line_editor.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include "lwip/sockets.h"

namespace stampfly {

// =============================================================================
// SocketCompletions
// =============================================================================

void SocketCompletions::add(const char* str)
{
    if (len >= MAX_COMPLETIONS || str == nullptr) {
        return;
    }
    cvec[len] = strdup(str);
    if (cvec[len] != nullptr) {
        len++;
    }
}

void SocketCompletions::clear()
{
    for (size_t i = 0; i < len; i++) {
        free(cvec[i]);
        cvec[i] = nullptr;
    }
    len = 0;
}

// =============================================================================
// Constructor / Destructor
// =============================================================================

SocketLineEditor::SocketLineEditor(int fd)
    : fd_(fd)
{
    memset(buffer_, 0, sizeof(buffer_));
    memset(history_, 0, sizeof(history_));
    memset(esc_buf_, 0, sizeof(esc_buf_));
}

SocketLineEditor::~SocketLineEditor()
{
    clearHistory();
}

void SocketLineEditor::clearHistory()
{
    for (int i = 0; i < history_len_; i++) {
        free(history_[i]);
        history_[i] = nullptr;
    }
    history_len_ = 0;
}

// =============================================================================
// Public Methods
// =============================================================================

char* SocketLineEditor::getLine(const char* prompt)
{
    // Reset line state
    // 行状態をリセット
    memset(buffer_, 0, sizeof(buffer_));
    pos_ = 0;
    len_ = 0;
    history_index_ = -1;
    esc_state_ = EscState::NONE;
    esc_pos_ = 0;

    // Send prompt
    // プロンプトを送信
    if (prompt != nullptr) {
        writeStr(prompt);
    }

    // Read characters
    // 文字を読み取る
    while (true) {
        char c;
        int ret = recv(fd_, &c, 1, 0);

        if (ret <= 0) {
            // Error or disconnect
            // エラーまたは切断
            return nullptr;
        }

        // Process character
        // 文字を処理
        if (processChar(c, prompt)) {
            // Line complete
            // 行完了
            buffer_[len_] = '\0';
            writeStr("\r\n");
            return strdup(buffer_);
        }
    }
}

void SocketLineEditor::freeLine(char* line)
{
    free(line);
}

void SocketLineEditor::addHistory(const char* line)
{
    if (line == nullptr || line[0] == '\0') {
        return;
    }

    // Don't add duplicate of most recent entry
    // 直近のエントリと重複する場合は追加しない
    if (history_len_ > 0 && strcmp(history_[history_len_ - 1], line) == 0) {
        return;
    }

    // If at max, remove oldest entry
    // 最大に達していたら最古のエントリを削除
    if (history_len_ >= history_max_) {
        free(history_[0]);
        memmove(history_, history_ + 1, (history_max_ - 1) * sizeof(char*));
        history_len_--;
    }

    // Add new entry
    // 新しいエントリを追加
    history_[history_len_] = strdup(line);
    if (history_[history_len_] != nullptr) {
        history_len_++;
    }
}

void SocketLineEditor::setHistoryMaxLen(int len)
{
    if (len < 1) len = 1;
    if (len > MAX_HISTORY) len = MAX_HISTORY;
    history_max_ = len;

    // Trim existing history if needed
    // 必要に応じて既存の履歴を削減
    while (history_len_ > history_max_) {
        free(history_[0]);
        memmove(history_, history_ + 1, (history_len_ - 1) * sizeof(char*));
        history_len_--;
    }
}

void SocketLineEditor::setCompletionCallback(SocketCompletionCallback callback)
{
    completion_callback_ = callback;
}

// =============================================================================
// Character Processing
// =============================================================================

bool SocketLineEditor::processChar(char c, const char* prompt)
{
    // Handle escape sequences
    // エスケープシーケンスを処理
    if (esc_state_ == EscState::ESC) {
        processEscape(c, prompt);
        return false;
    }
    if (esc_state_ == EscState::CSI) {
        processCSI(c, prompt);
        return false;
    }

    // Regular character processing
    // 通常の文字処理
    switch (c) {
        case '\r':
        case '\n':
            // Enter - line complete
            // Enter - 行完了
            return true;

        case 0x1B:  // ESC
            esc_state_ = EscState::ESC;
            esc_pos_ = 0;
            return false;

        case 0x7F:  // DEL
        case '\b':  // Backspace (Ctrl+H)
            handleBackspace(prompt);
            return false;

        case 0x01:  // Ctrl+A - Home
            handleHome(prompt);
            return false;

        case 0x02:  // Ctrl+B - Left
            handleArrowLeft(prompt);
            return false;

        case 0x03:  // Ctrl+C - Cancel
            writeStr("^C\r\n");
            if (prompt) writeStr(prompt);
            len_ = 0;
            pos_ = 0;
            buffer_[0] = '\0';
            return false;

        case 0x04:  // Ctrl+D - EOF (if empty) or delete
            if (len_ == 0) {
                return true;  // Treat as disconnect
            }
            handleDelete(prompt);
            return false;

        case 0x05:  // Ctrl+E - End
            handleEnd(prompt);
            return false;

        case 0x06:  // Ctrl+F - Right
            handleArrowRight(prompt);
            return false;

        case '\t':  // Tab - completion
            handleTab(prompt);
            return false;

        case 0x0B:  // Ctrl+K - Kill to end of line
            // Delete from cursor to end
            // カーソルから末尾まで削除
            if (pos_ < len_) {
                len_ = pos_;
                buffer_[len_] = '\0';
                refreshLine(prompt);
            }
            return false;

        case 0x0C:  // Ctrl+L - Clear screen
            writeStr("\x1B[2J\x1B[H");  // Clear and home
            refreshLine(prompt);
            return false;

        case 0x0E:  // Ctrl+N - Down (next history)
            handleArrowDown(prompt);
            return false;

        case 0x10:  // Ctrl+P - Up (previous history)
            handleArrowUp(prompt);
            return false;

        case 0x15:  // Ctrl+U - Kill line
            len_ = 0;
            pos_ = 0;
            buffer_[0] = '\0';
            refreshLine(prompt);
            return false;

        case 0x17:  // Ctrl+W - Kill word
            // Delete previous word
            // 前の単語を削除
            while (pos_ > 0 && buffer_[pos_ - 1] == ' ') {
                deleteCharAt(pos_ - 1, prompt);
            }
            while (pos_ > 0 && buffer_[pos_ - 1] != ' ') {
                deleteCharAt(pos_ - 1, prompt);
            }
            return false;

        default:
            // Printable character
            // 印字可能文字
            if (c >= 0x20 && c < 0x7F) {
                insertChar(c, prompt);
            }
            return false;
    }
}

void SocketLineEditor::processEscape(char c, const char* prompt)
{
    if (c == '[') {
        esc_state_ = EscState::CSI;
        return;
    }
    if (c == 'O') {
        // SS3 sequence (some terminals use this)
        // SS3シーケンス（一部のターミナルで使用）
        esc_state_ = EscState::CSI;
        return;
    }
    // Unknown escape, reset
    // 不明なエスケープ、リセット
    esc_state_ = EscState::NONE;
}

void SocketLineEditor::processCSI(char c, const char* prompt)
{
    // CSI sequences: ESC [ <params> <final_byte>
    // Final byte is in range 0x40-0x7E
    // CSIシーケンス: ESC [ <パラメータ> <最終バイト>

    if (c >= '0' && c <= '9') {
        // Parameter byte
        // パラメータバイト
        if (esc_pos_ < (int)sizeof(esc_buf_) - 1) {
            esc_buf_[esc_pos_++] = c;
        }
        return;
    }
    if (c == ';') {
        // Parameter separator
        // パラメータセパレータ
        if (esc_pos_ < (int)sizeof(esc_buf_) - 1) {
            esc_buf_[esc_pos_++] = c;
        }
        return;
    }

    // Final byte
    // 最終バイト
    esc_state_ = EscState::NONE;
    esc_buf_[esc_pos_] = '\0';

    switch (c) {
        case 'A':  // Up arrow
            handleArrowUp(prompt);
            break;
        case 'B':  // Down arrow
            handleArrowDown(prompt);
            break;
        case 'C':  // Right arrow
            handleArrowRight(prompt);
            break;
        case 'D':  // Left arrow
            handleArrowLeft(prompt);
            break;
        case 'H':  // Home
            handleHome(prompt);
            break;
        case 'F':  // End
            handleEnd(prompt);
            break;
        case '~':
            // Extended codes: 1~ Home, 3~ Delete, 4~ End, etc.
            // 拡張コード: 1~ Home, 3~ Delete, 4~ End など
            if (esc_pos_ > 0) {
                int code = atoi(esc_buf_);
                switch (code) {
                    case 1:  // Home
                        handleHome(prompt);
                        break;
                    case 3:  // Delete
                        handleDelete(prompt);
                        break;
                    case 4:  // End
                        handleEnd(prompt);
                        break;
                }
            }
            break;
    }

    esc_pos_ = 0;
}

// =============================================================================
// Arrow Key Handlers
// =============================================================================

void SocketLineEditor::handleArrowUp(const char* prompt)
{
    if (history_len_ == 0) {
        return;
    }

    // First up press: start from most recent
    // 最初の上押下: 最新から開始
    if (history_index_ < 0) {
        history_index_ = history_len_ - 1;
    } else if (history_index_ > 0) {
        history_index_--;
    } else {
        return;  // Already at oldest
    }

    // Copy history entry to buffer
    // 履歴エントリをバッファにコピー
    strncpy(buffer_, history_[history_index_], BUFFER_SIZE - 1);
    buffer_[BUFFER_SIZE - 1] = '\0';
    len_ = strlen(buffer_);
    pos_ = len_;

    refreshLine(prompt);
}

void SocketLineEditor::handleArrowDown(const char* prompt)
{
    if (history_index_ < 0) {
        return;
    }

    if (history_index_ < history_len_ - 1) {
        history_index_++;
        strncpy(buffer_, history_[history_index_], BUFFER_SIZE - 1);
        buffer_[BUFFER_SIZE - 1] = '\0';
    } else {
        // Past most recent - clear line
        // 最新を過ぎた - 行をクリア
        history_index_ = -1;
        buffer_[0] = '\0';
    }
    len_ = strlen(buffer_);
    pos_ = len_;

    refreshLine(prompt);
}

void SocketLineEditor::handleArrowLeft(const char* prompt)
{
    (void)prompt;
    if (pos_ > 0) {
        pos_--;
        writeStr("\x1B[D");  // Move cursor left
    }
}

void SocketLineEditor::handleArrowRight(const char* prompt)
{
    (void)prompt;
    if (pos_ < len_) {
        pos_++;
        writeStr("\x1B[C");  // Move cursor right
    }
}

void SocketLineEditor::handleHome(const char* prompt)
{
    (void)prompt;
    if (pos_ > 0) {
        char buf[16];
        snprintf(buf, sizeof(buf), "\x1B[%dD", (int)pos_);
        writeStr(buf);
        pos_ = 0;
    }
}

void SocketLineEditor::handleEnd(const char* prompt)
{
    (void)prompt;
    if (pos_ < len_) {
        char buf[16];
        snprintf(buf, sizeof(buf), "\x1B[%dC", (int)(len_ - pos_));
        writeStr(buf);
        pos_ = len_;
    }
}

// =============================================================================
// Edit Operations
// =============================================================================

void SocketLineEditor::handleBackspace(const char* prompt)
{
    if (pos_ > 0) {
        deleteCharAt(pos_ - 1, prompt);
    }
}

void SocketLineEditor::handleDelete(const char* prompt)
{
    if (pos_ < len_) {
        // Delete character at cursor
        // カーソル位置の文字を削除
        memmove(buffer_ + pos_, buffer_ + pos_ + 1, len_ - pos_);
        len_--;
        refreshLine(prompt);
    }
}

void SocketLineEditor::handleTab(const char* prompt)
{
    if (completion_callback_ == nullptr) {
        return;
    }

    // Get completions
    // 補完候補を取得
    SocketCompletions completions;
    buffer_[len_] = '\0';
    completion_callback_(buffer_, &completions);

    if (completions.len == 0) {
        // No completions - beep
        // 補完なし - ビープ
        writeStr("\x07");
    } else if (completions.len == 1) {
        // Single completion - insert it
        // 単一の補完 - 挿入
        strncpy(buffer_, completions.cvec[0], BUFFER_SIZE - 1);
        buffer_[BUFFER_SIZE - 1] = '\0';
        len_ = strlen(buffer_);
        pos_ = len_;
        refreshLine(prompt);
    } else {
        // Multiple completions - show them
        // 複数の補完 - 表示
        writeStr("\r\n");
        for (size_t i = 0; i < completions.len; i++) {
            writeStr(completions.cvec[i]);
            writeStr("  ");
        }
        writeStr("\r\n");
        refreshLine(prompt);
    }

    completions.clear();
}

void SocketLineEditor::insertChar(char c, const char* prompt)
{
    if (len_ >= BUFFER_SIZE - 1) {
        return;
    }

    if (pos_ == len_) {
        // Insert at end - simple append
        // 末尾に挿入 - 単純な追加
        buffer_[pos_] = c;
        pos_++;
        len_++;
        buffer_[len_] = '\0';
        writeChar(c);
    } else {
        // Insert in middle - need to shift
        // 中間に挿入 - シフトが必要
        memmove(buffer_ + pos_ + 1, buffer_ + pos_, len_ - pos_);
        buffer_[pos_] = c;
        pos_++;
        len_++;
        buffer_[len_] = '\0';
        refreshLine(prompt);
    }
}

void SocketLineEditor::deleteCharAt(size_t del_pos, const char* prompt)
{
    if (del_pos >= len_) {
        return;
    }

    memmove(buffer_ + del_pos, buffer_ + del_pos + 1, len_ - del_pos);
    len_--;
    if (pos_ > del_pos) {
        pos_--;
    }
    refreshLine(prompt);
}

// =============================================================================
// Output Helpers
// =============================================================================

void SocketLineEditor::writeStr(const char* str)
{
    if (str == nullptr || fd_ < 0) return;
    size_t len = strlen(str);
    if (len > 0) {
        send(fd_, str, len, 0);
    }
}

void SocketLineEditor::writeChar(char c)
{
    if (fd_ >= 0) {
        send(fd_, &c, 1, 0);
    }
}

void SocketLineEditor::refreshLine(const char* prompt)
{
    // Clear current line and rewrite
    // 現在の行をクリアして書き直す
    // \r - return to start
    // \x1B[K - clear to end of line
    // <prompt><buffer>
    // Move cursor to correct position

    writeStr("\r\x1B[K");  // Carriage return + clear line

    if (prompt) {
        writeStr(prompt);
    }
    writeStr(buffer_);

    // Move cursor to correct position
    // カーソルを正しい位置に移動
    if (pos_ < len_) {
        char buf[16];
        snprintf(buf, sizeof(buf), "\x1B[%dD", (int)(len_ - pos_));
        writeStr(buf);
    }
}

}  // namespace stampfly
