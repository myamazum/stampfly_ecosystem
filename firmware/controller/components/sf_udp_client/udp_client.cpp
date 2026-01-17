/**
 * @file udp_client.cpp
 * @brief UDP client implementation
 *        UDPクライアント実装
 */

#include "udp_client.hpp"
#include "esp_log.h"
#include "esp_netif.h"
#include "lwip/sockets.h"
#include "lwip/netdb.h"
#include <cstring>

static const char* TAG = "UDPClient";

namespace stampfly {

UDPClient& UDPClient::getInstance() {
    static UDPClient instance;
    return instance;
}

esp_err_t UDPClient::init(const Config& config) {
    if (initialized_) {
        ESP_LOGW(TAG, "Already initialized");
        return ESP_OK;
    }

    config_ = config;

    // Create mutex
    // ミューテックスを作成
    mutex_ = xSemaphoreCreateMutex();
    if (mutex_ == nullptr) {
        ESP_LOGE(TAG, "Failed to create mutex");
        return ESP_ERR_NO_MEM;
    }

    // Initialize TCP/IP stack
    // TCP/IPスタックを初期化
    esp_err_t ret = esp_netif_init();
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "Failed to init netif: %s", esp_err_to_name(ret));
        return ret;
    }

    // Create default event loop (if not already created)
    // デフォルトイベントループを作成（未作成の場合）
    ret = esp_event_loop_create_default();
    if (ret != ESP_OK && ret != ESP_ERR_INVALID_STATE) {
        ESP_LOGE(TAG, "Failed to create event loop: %s", esp_err_to_name(ret));
        return ret;
    }

    // Create default WiFi STA
    // デフォルトWiFi STAを作成
    esp_netif_create_default_wifi_sta();

    // Initialize WiFi with default config
    // デフォルト設定でWiFiを初期化
    wifi_init_config_t wifi_init_config = WIFI_INIT_CONFIG_DEFAULT();
    ret = esp_wifi_init(&wifi_init_config);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to init WiFi: %s", esp_err_to_name(ret));
        return ret;
    }

    // Register event handlers
    // イベントハンドラを登録
    ret = esp_event_handler_instance_register(
        WIFI_EVENT,
        ESP_EVENT_ANY_ID,
        &wifiEventHandler,
        this,
        &wifi_event_handler_
    );
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register WiFi event handler: %s", esp_err_to_name(ret));
        return ret;
    }

    ret = esp_event_handler_instance_register(
        IP_EVENT,
        IP_EVENT_STA_GOT_IP,
        &wifiEventHandler,
        this,
        &ip_event_handler_
    );
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to register IP event handler: %s", esp_err_to_name(ret));
        return ret;
    }

    // Set WiFi mode to STA
    // WiFiモードをSTAに設定
    ret = esp_wifi_set_mode(WIFI_MODE_STA);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to set WiFi mode: %s", esp_err_to_name(ret));
        return ret;
    }

    initialized_ = true;
    ESP_LOGI(TAG, "Initialized");

    return ESP_OK;
}

esp_err_t UDPClient::start() {
    if (!initialized_) {
        ESP_LOGE(TAG, "Not initialized");
        return ESP_ERR_INVALID_STATE;
    }

    if (running_) {
        ESP_LOGW(TAG, "Already running");
        return ESP_OK;
    }

    // Start WiFi
    // WiFiを開始
    esp_err_t ret = esp_wifi_start();
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Failed to start WiFi: %s", esp_err_to_name(ret));
        return ret;
    }

    running_ = true;
    ESP_LOGI(TAG, "Started");

    return ESP_OK;
}

esp_err_t UDPClient::stop() {
    if (!running_) {
        return ESP_OK;
    }

    running_ = false;

    // Stop RX task
    // 受信タスクを停止
    if (rx_task_handle_ != nullptr) {
        vTaskDelay(pdMS_TO_TICKS(200));
        rx_task_handle_ = nullptr;
    }

    // Close socket
    // ソケットを閉じる
    if (sock_fd_ >= 0) {
        close(sock_fd_);
        sock_fd_ = -1;
    }

    // Disconnect WiFi
    // WiFiを切断
    esp_wifi_disconnect();
    wifi_connected_ = false;

    ESP_LOGI(TAG, "Stopped");
    return ESP_OK;
}

void UDPClient::wifiEventHandler(void* arg, esp_event_base_t event_base,
                                  int32_t event_id, void* event_data) {
    UDPClient* client = static_cast<UDPClient*>(arg);

    if (event_base == WIFI_EVENT) {
        switch (event_id) {
            case WIFI_EVENT_STA_START:
                ESP_LOGI(TAG, "WiFi STA started");
                break;

            case WIFI_EVENT_STA_CONNECTED:
                ESP_LOGI(TAG, "WiFi connected to AP");
                break;

            case WIFI_EVENT_STA_DISCONNECTED:
                ESP_LOGW(TAG, "WiFi disconnected");
                client->wifi_connected_ = false;
                if (client->sock_fd_ >= 0) {
                    close(client->sock_fd_);
                    client->sock_fd_ = -1;
                }
                // Auto reconnect if running
                // 動作中なら自動再接続
                if (client->running_) {
                    esp_wifi_connect();
                }
                break;

            default:
                break;
        }
    } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t* event = static_cast<ip_event_got_ip_t*>(event_data);
        ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
        client->wifi_connected_ = true;

        // Create UDP socket
        // UDPソケットを作成
        client->sock_fd_ = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP);
        if (client->sock_fd_ < 0) {
            ESP_LOGE(TAG, "Failed to create socket");
            return;
        }

        // Set receive timeout
        // 受信タイムアウトを設定
        struct timeval tv;
        tv.tv_sec = 0;
        tv.tv_usec = 100000;  // 100ms
        setsockopt(client->sock_fd_, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

        // Setup vehicle address
        // Vehicle アドレスを設定
        memset(&client->vehicle_addr_, 0, sizeof(client->vehicle_addr_));
        client->vehicle_addr_.sin_family = AF_INET;
        client->vehicle_addr_.sin_port = htons(client->config_.control_port);
        inet_aton(client->config_.vehicle_ip, &client->vehicle_addr_.sin_addr);

        // Bind to telemetry port for receiving
        // テレメトリ受信用にポートにバインド
        SockAddrIn local_addr = {};
        local_addr.sin_family = AF_INET;
        local_addr.sin_addr.s_addr = htonl(INADDR_ANY);
        local_addr.sin_port = htons(client->config_.telemetry_port);

        if (bind(client->sock_fd_, (struct sockaddr*)&local_addr, sizeof(local_addr)) < 0) {
            ESP_LOGW(TAG, "Failed to bind to telemetry port: %d", errno);
            // Continue anyway - we can still send
            // 続行 - 送信は可能
        }

        // Start RX task
        // 受信タスクを開始
        if (client->rx_task_handle_ == nullptr) {
            xTaskCreatePinnedToCore(
                rxTask,
                "udp_rx",
                RX_TASK_STACK_SIZE,
                client,
                RX_TASK_PRIORITY,
                &client->rx_task_handle_,
                1  // Core 1
            );
        }

        ESP_LOGI(TAG, "UDP client ready");
    }
}

esp_err_t UDPClient::scanForVehicle(char* ssid_out, size_t ssid_len) {
    if (!initialized_) {
        return ESP_ERR_INVALID_STATE;
    }

    // Configure scan
    // スキャン設定
    wifi_scan_config_t scan_config = {};
    scan_config.show_hidden = false;
    scan_config.scan_type = WIFI_SCAN_TYPE_ACTIVE;
    scan_config.scan_time.active.min = 100;
    scan_config.scan_time.active.max = 300;

    // Start scan
    // スキャン開始
    esp_err_t ret = esp_wifi_scan_start(&scan_config, true);
    if (ret != ESP_OK) {
        ESP_LOGE(TAG, "Scan failed: %s", esp_err_to_name(ret));
        return ret;
    }

    // Get scan results
    // スキャン結果を取得
    uint16_t ap_count = 0;
    esp_wifi_scan_get_ap_num(&ap_count);

    if (ap_count == 0) {
        ESP_LOGI(TAG, "No APs found");
        return ESP_ERR_NOT_FOUND;
    }

    wifi_ap_record_t* ap_list = new wifi_ap_record_t[ap_count];
    esp_wifi_scan_get_ap_records(&ap_count, ap_list);

    // Find Vehicle AP
    // Vehicle APを検索
    bool found = false;
    for (uint16_t i = 0; i < ap_count; i++) {
        const char* ssid = reinterpret_cast<const char*>(ap_list[i].ssid);
        if (strncmp(ssid, config_.vehicle_ssid_prefix, strlen(config_.vehicle_ssid_prefix)) == 0) {
            strncpy(ssid_out, ssid, ssid_len - 1);
            ssid_out[ssid_len - 1] = '\0';
            ESP_LOGI(TAG, "Found Vehicle AP: %s (RSSI: %d)", ssid, ap_list[i].rssi);
            found = true;
            break;
        }
    }

    delete[] ap_list;

    return found ? ESP_OK : ESP_ERR_NOT_FOUND;
}

esp_err_t UDPClient::connectToAP(const char* ssid, const char* password) {
    if (!initialized_) {
        return ESP_ERR_INVALID_STATE;
    }

    wifi_config_t wifi_config = {};
    strncpy(reinterpret_cast<char*>(wifi_config.sta.ssid), ssid, sizeof(wifi_config.sta.ssid) - 1);
    if (password && strlen(password) > 0) {
        strncpy(reinterpret_cast<char*>(wifi_config.sta.password), password, sizeof(wifi_config.sta.password) - 1);
    }

    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
    ESP_LOGI(TAG, "Connecting to %s...", ssid);

    return esp_wifi_connect();
}

esp_err_t UDPClient::sendControl(uint16_t throttle, uint16_t roll,
                                  uint16_t pitch, uint16_t yaw, uint8_t flags) {
    if (!isConnected()) {
        return ESP_ERR_INVALID_STATE;
    }

    // Build control packet
    // 制御パケットを構築
    udp::ControlPacket pkt = udp::buildControlPacket(
        sequence_++,
        udp::DEVICE_ID_CONTROLLER,
        throttle,
        roll,
        pitch,
        yaw,
        flags
    );

    // Send packet
    // パケットを送信
    ssize_t sent = sendto(
        sock_fd_,
        &pkt,
        sizeof(pkt),
        0,
        (struct sockaddr*)&vehicle_addr_,
        sizeof(vehicle_addr_)
    );

    if (sent < 0) {
        ESP_LOGW(TAG, "Send failed: errno %d", errno);
        error_count_++;
        return ESP_FAIL;
    }

    tx_count_++;
    return ESP_OK;
}

bool UDPClient::hasTelemetry() const {
    uint32_t now = xTaskGetTickCount() * portTICK_PERIOD_MS;
    return (now - last_telemetry_time_ms_) < TELEMETRY_TIMEOUT_MS;
}

bool UDPClient::getLastTelemetry(udp::TelemetryPacket& pkt) const {
    if (!hasTelemetry()) {
        return false;
    }

    if (xSemaphoreTake(mutex_, pdMS_TO_TICKS(10)) == pdTRUE) {
        pkt = last_telemetry_;
        xSemaphoreGive(mutex_);
        return true;
    }

    return false;
}

void UDPClient::resetStats() {
    tx_count_ = 0;
    rx_count_ = 0;
    error_count_ = 0;
}

void UDPClient::rxTask(void* arg) {
    UDPClient* client = static_cast<UDPClient*>(arg);
    uint8_t buffer[RX_BUFFER_SIZE];

    ESP_LOGI(TAG, "RX task started");

    while (client->running_) {
        if (client->sock_fd_ < 0) {
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        // Receive packet
        // パケットを受信
        ssize_t len = recv(client->sock_fd_, buffer, sizeof(buffer), 0);

        if (len > 0) {
            // Check for telemetry packet
            // テレメトリパケットをチェック
            if (len == sizeof(udp::TelemetryPacket) &&
                buffer[0] == udp::PACKET_HEADER &&
                buffer[1] == udp::PKT_TYPE_TELEMETRY) {

                const udp::TelemetryPacket* pkt =
                    reinterpret_cast<const udp::TelemetryPacket*>(buffer);

                if (udp::validateTelemetryPacket(*pkt)) {
                    client->processTelemetry(*pkt);
                } else {
                    ESP_LOGW(TAG, "Telemetry checksum error");
                    client->error_count_++;
                }
            }
        } else if (len < 0 && errno != EAGAIN && errno != EWOULDBLOCK) {
            ESP_LOGW(TAG, "recv error: errno %d", errno);
            client->error_count_++;
        }
    }

    ESP_LOGI(TAG, "RX task stopped");
    vTaskDelete(nullptr);
}

void UDPClient::processTelemetry(const udp::TelemetryPacket& pkt) {
    if (xSemaphoreTake(mutex_, pdMS_TO_TICKS(10)) == pdTRUE) {
        last_telemetry_ = pkt;
        last_telemetry_time_ms_ = xTaskGetTickCount() * portTICK_PERIOD_MS;
        xSemaphoreGive(mutex_);
    }

    rx_count_++;

    // Invoke callback
    // コールバックを呼び出し
    if (telemetry_callback_) {
        telemetry_callback_(pkt);
    }
}

}  // namespace stampfly
