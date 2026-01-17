/**
 * @file wifi_cli.cpp
 * @brief WiFi CLI Server Implementation
 *
 * Telnet-like TCP server for CLI access over WiFi.
 *
 * WiFi CLI サーバー実装
 * WiFi経由でのCLIアクセスを提供するTelnet風TCPサーバー
 */

#include "wifi_cli.hpp"

#include <cstdio>
#include <cstring>
#include <cstdarg>

#include "esp_log.h"
#include "esp_system.h"

#include "lwip/sockets.h"
#include "lwip/netdb.h"

static const char* TAG = "WiFiCLI";

namespace stampfly {

// =============================================================================
// Singleton Instance
// =============================================================================

WiFiCLI& WiFiCLI::getInstance()
{
    static WiFiCLI instance;
    return instance;
}

// =============================================================================
// Initialization
// =============================================================================

esp_err_t WiFiCLI::init(const Config& config)
{
    if (initialized_) {
        ESP_LOGW(TAG, "Already initialized");
        return ESP_OK;
    }

    config_ = config;

    // Create client mutex
    // クライアントミューテックスを作成
    client_mutex_ = xSemaphoreCreateMutex();
    if (client_mutex_ == nullptr) {
        ESP_LOGE(TAG, "Failed to create mutex");
        return ESP_ERR_NO_MEM;
    }

    initialized_ = true;
    ESP_LOGI(TAG, "Initialized (port %d, max_clients %d)",
             config_.port, config_.max_clients);

    return ESP_OK;
}

// =============================================================================
// Start / Stop
// =============================================================================

esp_err_t WiFiCLI::start()
{
    if (!initialized_) {
        ESP_LOGE(TAG, "Not initialized");
        return ESP_ERR_INVALID_STATE;
    }

    if (running_) {
        ESP_LOGW(TAG, "Already running");
        return ESP_OK;
    }

    // Create server socket
    // サーバーソケットを作成
    server_fd_ = socket(AF_INET, SOCK_STREAM, IPPROTO_TCP);
    if (server_fd_ < 0) {
        ESP_LOGE(TAG, "Failed to create socket: errno %d", errno);
        return ESP_FAIL;
    }

    // Set socket options
    // ソケットオプションを設定
    int opt = 1;
    setsockopt(server_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    // Bind to port
    // ポートにバインド
    struct sockaddr_in server_addr = {};
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(config_.port);

    if (bind(server_fd_, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        ESP_LOGE(TAG, "Failed to bind: errno %d", errno);
        close(server_fd_);
        server_fd_ = -1;
        return ESP_FAIL;
    }

    // Listen for connections
    // 接続をリッスン
    if (listen(server_fd_, config_.max_clients) < 0) {
        ESP_LOGE(TAG, "Failed to listen: errno %d", errno);
        close(server_fd_);
        server_fd_ = -1;
        return ESP_FAIL;
    }

    running_ = true;

    // Create accept task
    // 接続受付タスクを作成
    BaseType_t ret = xTaskCreate(
        acceptTask,
        "wifi_cli_accept",
        4096,
        this,
        5,  // Priority
        &accept_task_handle_
    );

    if (ret != pdPASS) {
        ESP_LOGE(TAG, "Failed to create accept task");
        close(server_fd_);
        server_fd_ = -1;
        running_ = false;
        return ESP_ERR_NO_MEM;
    }

    ESP_LOGI(TAG, "Started on port %d", config_.port);
    return ESP_OK;
}

esp_err_t WiFiCLI::stop()
{
    if (!running_) {
        return ESP_OK;
    }

    running_ = false;

    // Disconnect all clients
    // 全クライアントを切断
    disconnectAll();

    // Close server socket (this will cause accept() to fail)
    // サーバーソケットを閉じる（accept()が失敗する）
    if (server_fd_ >= 0) {
        close(server_fd_);
        server_fd_ = -1;
    }

    // Wait for accept task to finish
    // 接続受付タスクの終了を待つ
    if (accept_task_handle_ != nullptr) {
        vTaskDelay(pdMS_TO_TICKS(100));
        accept_task_handle_ = nullptr;
    }

    ESP_LOGI(TAG, "Stopped");
    return ESP_OK;
}

// =============================================================================
// Accept Task
// =============================================================================

void WiFiCLI::acceptTask(void* arg)
{
    WiFiCLI* self = static_cast<WiFiCLI*>(arg);

    ESP_LOGI(TAG, "Accept task started");

    while (self->running_) {
        struct sockaddr_in client_addr = {};
        socklen_t addr_len = sizeof(client_addr);

        // Accept new connection (blocks until connection or error)
        // 新規接続を受け入れる（接続またはエラーまでブロック）
        int client_fd = accept(self->server_fd_,
                               (struct sockaddr*)&client_addr, &addr_len);

        if (client_fd < 0) {
            if (self->running_) {
                ESP_LOGE(TAG, "Accept failed: errno %d", errno);
            }
            continue;
        }

        // Check client limit
        // クライアント数制限をチェック
        if (self->client_count_ >= MAX_CLIENTS) {
            ESP_LOGW(TAG, "Max clients reached, rejecting connection");
            const char* msg = "Server busy, try again later.\r\n";
            send(client_fd, msg, strlen(msg), 0);
            close(client_fd);
            continue;
        }

        ESP_LOGI(TAG, "New connection from %s",
                 inet_ntoa(client_addr.sin_addr));

        // Create client context
        // クライアントコンテキストを作成
        ClientContext* ctx = new ClientContext();
        ctx->server = self;
        ctx->client_fd = client_fd;
        ctx->client_ip = client_addr.sin_addr.s_addr;
        ctx->rx_pos = 0;
        ctx->last_activity_ms = xTaskGetTickCount() * portTICK_PERIOD_MS;
        ctx->active = true;

        // Add to client list
        // クライアントリストに追加
        xSemaphoreTake(self->client_mutex_, portMAX_DELAY);
        for (int i = 0; i < MAX_CLIENTS; i++) {
            if (self->clients_[i] == nullptr) {
                self->clients_[i] = ctx;
                self->client_count_++;
                break;
            }
        }
        xSemaphoreGive(self->client_mutex_);

        // Create client handler task
        // クライアントハンドラタスクを作成
        char task_name[24];
        snprintf(task_name, sizeof(task_name), "wcli_%d", client_fd);

        BaseType_t ret = xTaskCreate(
            clientTask,
            task_name,
            4096,
            ctx,
            5,  // Priority
            nullptr
        );

        if (ret != pdPASS) {
            ESP_LOGE(TAG, "Failed to create client task");
            close(client_fd);

            xSemaphoreTake(self->client_mutex_, portMAX_DELAY);
            for (int i = 0; i < MAX_CLIENTS; i++) {
                if (self->clients_[i] == ctx) {
                    self->clients_[i] = nullptr;
                    self->client_count_--;
                    break;
                }
            }
            xSemaphoreGive(self->client_mutex_);

            delete ctx;
        }
    }

    ESP_LOGI(TAG, "Accept task ended");
    vTaskDelete(nullptr);
}

// =============================================================================
// Client Task
// =============================================================================

void WiFiCLI::clientTask(void* arg)
{
    ClientContext* ctx = static_cast<ClientContext*>(arg);
    WiFiCLI* self = ctx->server;

    self->handleClient(ctx);

    // Remove from client list
    // クライアントリストから削除
    xSemaphoreTake(self->client_mutex_, portMAX_DELAY);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (self->clients_[i] == ctx) {
            self->clients_[i] = nullptr;
            self->client_count_--;
            break;
        }
    }
    xSemaphoreGive(self->client_mutex_);

    // Close socket and free context
    // ソケットを閉じてコンテキストを解放
    close(ctx->client_fd);
    delete ctx;

    vTaskDelete(nullptr);
}

// =============================================================================
// Client Handler
// =============================================================================

void WiFiCLI::handleClient(ClientContext* ctx)
{
    ESP_LOGI(TAG, "Handling client on fd %d", ctx->client_fd);

    // Send welcome message
    // ウェルカムメッセージを送信
    sendWelcome(ctx->client_fd);
    sendPrompt(ctx->client_fd);

    // Set socket timeout for recv
    // recvのソケットタイムアウトを設定
    struct timeval tv;
    tv.tv_sec = 1;
    tv.tv_usec = 0;
    setsockopt(ctx->client_fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

    while (ctx->active && running_) {
        // Check idle timeout
        // アイドルタイムアウトをチェック
        uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
        if (now - ctx->last_activity_ms > config_.idle_timeout_ms) {
            ESP_LOGI(TAG, "Client idle timeout");
            const char* msg = "\r\nIdle timeout, disconnecting.\r\n";
            send(ctx->client_fd, msg, strlen(msg), 0);
            break;
        }

        // Receive data
        // データを受信
        char buf[64];
        int len = recv(ctx->client_fd, buf, sizeof(buf) - 1, 0);

        if (len < 0) {
            if (errno == EAGAIN || errno == EWOULDBLOCK) {
                // Timeout, continue
                continue;
            }
            ESP_LOGE(TAG, "Recv error: errno %d", errno);
            break;
        }

        if (len == 0) {
            // Connection closed
            // 接続が閉じられた
            ESP_LOGI(TAG, "Client disconnected");
            break;
        }

        ctx->last_activity_ms = now;

        // Process received data
        // 受信データを処理
        for (int i = 0; i < len; i++) {
            char c = buf[i];

            // Handle special characters
            // 特殊文字を処理
            if (c == '\r' || c == '\n') {
                if (ctx->rx_pos > 0) {
                    ctx->rx_buffer[ctx->rx_pos] = '\0';
                    processLine(ctx, ctx->rx_buffer);
                    ctx->rx_pos = 0;
                    sendPrompt(ctx->client_fd);
                }
            } else if (c == 0x7F || c == '\b') {
                // Backspace
                if (ctx->rx_pos > 0) {
                    ctx->rx_pos--;
                    // Echo backspace
                    const char* bs = "\b \b";
                    send(ctx->client_fd, bs, 3, 0);
                }
            } else if (c == 0x03) {
                // Ctrl+C - cancel current line
                // Ctrl+C - 現在の行をキャンセル
                ctx->rx_pos = 0;
                const char* msg = "^C\r\n";
                send(ctx->client_fd, msg, strlen(msg), 0);
                sendPrompt(ctx->client_fd);
            } else if (c == 0x04) {
                // Ctrl+D - disconnect
                // Ctrl+D - 切断
                ESP_LOGI(TAG, "Client sent Ctrl+D");
                const char* msg = "\r\nGoodbye.\r\n";
                send(ctx->client_fd, msg, strlen(msg), 0);
                ctx->active = false;
                break;
            } else if (c >= 0x20 && c < 0x7F) {
                // Printable character
                // 印字可能文字
                if (ctx->rx_pos < sizeof(ctx->rx_buffer) - 1) {
                    ctx->rx_buffer[ctx->rx_pos++] = c;
                    // Echo character
                    send(ctx->client_fd, &c, 1, 0);
                }
            }
            // Ignore other control characters
            // 他の制御文字は無視
        }
    }

    ESP_LOGI(TAG, "Client handler ended for fd %d", ctx->client_fd);
}

// =============================================================================
// Command Processing
// =============================================================================

void WiFiCLI::processLine(ClientContext* ctx, const char* line)
{
    ESP_LOGD(TAG, "Processing: %s", line);

    // Skip empty lines
    // 空行をスキップ
    if (line[0] == '\0') {
        return;
    }

    // Handle built-in commands
    // 組み込みコマンドを処理
    if (strcmp(line, "exit") == 0 || strcmp(line, "quit") == 0) {
        const char* msg = "\r\nGoodbye.\r\n";
        send(ctx->client_fd, msg, strlen(msg), 0);
        ctx->active = false;
        return;
    }

    // Forward to CLI for command processing
    // コマンド処理のためにCLIに転送
    if (cli_ == nullptr) {
        const char* msg = "CLI not available\r\n";
        send(ctx->client_fd, msg, strlen(msg), 0);
        return;
    }

    // Parse command line into argc/argv
    // コマンドラインをargc/argvにパース
    static constexpr int MAX_ARGS = 8;
    char* argv[MAX_ARGS];
    int argc = 0;

    // Make a copy of the line for tokenization
    // トークン化のために行のコピーを作成
    char line_copy[256];
    strncpy(line_copy, line, sizeof(line_copy) - 1);
    line_copy[sizeof(line_copy) - 1] = '\0';

    // Tokenize
    // トークン化
    char* token = strtok(line_copy, " \t");
    while (token != nullptr && argc < MAX_ARGS) {
        argv[argc++] = token;
        token = strtok(nullptr, " \t");
    }

    if (argc == 0) {
        return;
    }

    // Send newline after command
    // コマンド後に改行を送信
    send(ctx->client_fd, "\r\n", 2, 0);

    // Look up and execute command
    // コマンドを検索して実行
    // Note: This requires the CLI to have a way to redirect output.
    // For now, we'll implement a simple response system.
    // 注意: CLIに出力リダイレクト機能が必要
    // 今のところ、シンプルなレスポンスシステムを実装

    // For help command
    if (strcmp(argv[0], "help") == 0 || strcmp(argv[0], "?") == 0) {
        const char* help_msg =
            "Available commands:\r\n"
            "  help    - Show this help\r\n"
            "  exit    - Disconnect\r\n"
            "  status  - Show system status\r\n"
            "  sensor  - Sensor commands\r\n"
            "  comm    - Communication settings\r\n"
            "  motor   - Motor commands\r\n"
            "  (More commands available via USB CLI)\r\n";
        send(ctx->client_fd, help_msg, strlen(help_msg), 0);
        return;
    }

    // For status command - basic implementation
    if (strcmp(argv[0], "status") == 0) {
        char buf[256];
        int len = snprintf(buf, sizeof(buf),
            "WiFi CLI Status:\r\n"
            "  Connected clients: %d\r\n"
            "  Server port: %d\r\n"
            "  Uptime: %lu ms\r\n",
            client_count_,
            config_.port,
            (unsigned long)(xTaskGetTickCount() * portTICK_PERIOD_MS)
        );
        send(ctx->client_fd, buf, len, 0);
        return;
    }

    // Unknown command
    const char* msg = "Command not available via WiFi CLI.\r\n"
                      "Type 'help' for available commands.\r\n";
    send(ctx->client_fd, msg, strlen(msg), 0);
}

// =============================================================================
// Helper Functions
// =============================================================================

void WiFiCLI::sendToClient(int fd, const char* data, size_t len)
{
    if (fd >= 0 && data != nullptr && len > 0) {
        send(fd, data, len, 0);
    }
}

void WiFiCLI::sendPrompt(int fd)
{
    const char* prompt = "stampfly> ";
    send(fd, prompt, strlen(prompt), 0);
}

void WiFiCLI::sendWelcome(int fd)
{
    const char* welcome =
        "\r\n"
        "========================================\r\n"
        "  StampFly WiFi CLI\r\n"
        "========================================\r\n"
        "Type 'help' for available commands.\r\n"
        "Type 'exit' to disconnect.\r\n"
        "\r\n";
    send(fd, welcome, strlen(welcome), 0);
}

void WiFiCLI::broadcast(const char* message)
{
    if (message == nullptr) return;

    size_t len = strlen(message);
    if (len == 0) return;

    xSemaphoreTake(client_mutex_, portMAX_DELAY);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients_[i] != nullptr && clients_[i]->active) {
            send(clients_[i]->client_fd, message, len, 0);
        }
    }
    xSemaphoreGive(client_mutex_);
}

void WiFiCLI::disconnectAll()
{
    xSemaphoreTake(client_mutex_, portMAX_DELAY);
    for (int i = 0; i < MAX_CLIENTS; i++) {
        if (clients_[i] != nullptr) {
            clients_[i]->active = false;
            // Close socket to force recv() to fail
            // recv()を失敗させるためにソケットを閉じる
            shutdown(clients_[i]->client_fd, SHUT_RDWR);
        }
    }
    xSemaphoreGive(client_mutex_);
}

}  // namespace stampfly
