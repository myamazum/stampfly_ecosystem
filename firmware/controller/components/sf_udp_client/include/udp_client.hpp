/**
 * @file udp_client.hpp
 * @brief UDP client for sending control packets and receiving telemetry
 *        制御パケット送信とテレメトリ受信用UDPクライアント
 *
 * This component provides UDP-based communication as an alternative to ESP-NOW.
 * ESP-NOWの代替としてUDPベースの通信を提供するコンポーネント。
 */

#pragma once

// Include system headers before namespace
// 名前空間の前にシステムヘッダをインクルード
#include "lwip/sockets.h"

#include "udp_protocol.hpp"
#include "esp_err.h"
#include "esp_wifi.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "freertos/semphr.h"
#include <functional>

// Type alias for sockaddr_in
// sockaddr_in用型エイリアス
using SockAddrIn = struct sockaddr_in;

namespace stampfly {

/**
 * @brief UDP Client for Controller
 *        Controller用UDPクライアント
 *
 * Manages UDP communication with Vehicle over WiFi.
 * WiFi経由でVehicleとのUDP通信を管理。
 */
class UDPClient {
public:
    /// Get singleton instance / シングルトンインスタンスを取得
    static UDPClient& getInstance();

    // Delete copy/move
    UDPClient(const UDPClient&) = delete;
    UDPClient& operator=(const UDPClient&) = delete;

    /**
     * @brief Client configuration
     *        クライアント設定
     */
    struct Config {
        const char* vehicle_ssid_prefix;  ///< Vehicle AP SSID prefix / Vehicle APのSSIDプレフィックス
        const char* vehicle_password;     ///< Vehicle AP password (empty for open) / パスワード（オープンなら空）
        const char* vehicle_ip;           ///< Vehicle IP address / Vehicle IPアドレス
        uint16_t control_port;            ///< Control packet port / 制御パケットポート
        uint16_t telemetry_port;          ///< Telemetry packet port / テレメトリパケットポート
        uint32_t connection_timeout_ms;   ///< WiFi connection timeout / WiFi接続タイムアウト

        /// Default constructor / デフォルトコンストラクタ
        Config() :
            vehicle_ssid_prefix("StampFly_"),
            vehicle_password(""),
            vehicle_ip(udp::DEFAULT_VEHICLE_IP),
            control_port(udp::CONTROL_PORT),
            telemetry_port(udp::TELEMETRY_PORT),
            connection_timeout_ms(10000) {}
    };

    /**
     * @brief Callback type for telemetry reception
     *        テレメトリ受信時のコールバック型
     */
    using TelemetryCallback = std::function<void(const udp::TelemetryPacket&)>;

    /**
     * @brief Initialize the UDP client
     *        UDPクライアントを初期化
     *
     * @param config Client configuration / クライアント設定
     * @return ESP_OK on success / 成功時ESP_OK
     */
    esp_err_t init(const Config& config = Config());

    /**
     * @brief Start WiFi connection and UDP communication
     *        WiFi接続とUDP通信を開始
     *
     * @return ESP_OK on success / 成功時ESP_OK
     */
    esp_err_t start();

    /**
     * @brief Stop UDP communication and disconnect WiFi
     *        UDP通信を停止しWiFiを切断
     *
     * @return ESP_OK on success / 成功時ESP_OK
     */
    esp_err_t stop();

    /**
     * @brief Check if client is running
     *        クライアントが動作中か確認
     */
    bool isRunning() const { return running_; }

    /**
     * @brief Check if WiFi is connected
     *        WiFiが接続されているか確認
     */
    bool isWiFiConnected() const { return wifi_connected_; }

    /**
     * @brief Check if communication is active
     *        通信がアクティブか確認
     */
    bool isConnected() const { return wifi_connected_ && sock_fd_ >= 0; }

    /**
     * @brief Set callback for telemetry reception
     *        テレメトリ受信時のコールバックを設定
     */
    void setTelemetryCallback(TelemetryCallback callback) { telemetry_callback_ = callback; }

    // ========================================================================
    // Control Sending
    // 制御送信
    // ========================================================================

    /**
     * @brief Send control packet
     *        制御パケットを送信
     *
     * @param throttle Throttle value [0-4095] / スロットル値
     * @param roll Roll value [0-4095], 2048=center / ロール値
     * @param pitch Pitch value [0-4095], 2048=center / ピッチ値
     * @param yaw Yaw value [0-4095], 2048=center / ヨー値
     * @param flags Control flags / 制御フラグ
     * @return ESP_OK on success / 成功時ESP_OK
     */
    esp_err_t sendControl(uint16_t throttle, uint16_t roll,
                          uint16_t pitch, uint16_t yaw, uint8_t flags);

    // ========================================================================
    // Telemetry Access
    // テレメトリアクセス
    // ========================================================================

    /**
     * @brief Check if telemetry is available
     *        テレメトリが利用可能か確認
     */
    bool hasTelemetry() const;

    /**
     * @brief Get last received telemetry packet
     *        最後に受信したテレメトリパケットを取得
     *
     * @param pkt Output packet / 出力パケット
     * @return true if valid packet available / 有効なパケットがあればtrue
     */
    bool getLastTelemetry(udp::TelemetryPacket& pkt) const;

    /**
     * @brief Get timestamp of last telemetry packet
     *        最後のテレメトリパケットのタイムスタンプを取得
     */
    uint32_t getLastTelemetryTime() const { return last_telemetry_time_ms_; }

    // ========================================================================
    // Statistics
    // 統計情報
    // ========================================================================

    uint32_t getTxCount() const { return tx_count_; }
    uint32_t getRxCount() const { return rx_count_; }
    uint32_t getErrorCount() const { return error_count_; }
    void resetStats();

    // ========================================================================
    // WiFi Management
    // WiFi管理
    // ========================================================================

    /**
     * @brief Scan for Vehicle APs
     *        Vehicle APをスキャン
     *
     * @param ssid_out Buffer to store found SSID / 見つかったSSIDを格納するバッファ
     * @param ssid_len Length of buffer / バッファ長
     * @return ESP_OK if found, ESP_ERR_NOT_FOUND otherwise
     */
    esp_err_t scanForVehicle(char* ssid_out, size_t ssid_len);

    /**
     * @brief Connect to specified SSID
     *        指定SSIDに接続
     *
     * @param ssid SSID to connect / 接続するSSID
     * @param password Password (empty for open) / パスワード
     * @return ESP_OK on success / 成功時ESP_OK
     */
    esp_err_t connectToAP(const char* ssid, const char* password = "");

private:
    UDPClient() = default;
    ~UDPClient() = default;

    /// RX task function / 受信タスク関数
    static void rxTask(void* arg);

    /// WiFi event handler / WiFiイベントハンドラ
    static void wifiEventHandler(void* arg, esp_event_base_t event_base,
                                  int32_t event_id, void* event_data);

    /// Process received telemetry / 受信テレメトリを処理
    void processTelemetry(const udp::TelemetryPacket& pkt);

    // Configuration
    Config config_;
    bool initialized_ = false;
    bool running_ = false;

    // WiFi state
    bool wifi_connected_ = false;
    esp_event_handler_instance_t wifi_event_handler_ = nullptr;
    esp_event_handler_instance_t ip_event_handler_ = nullptr;

    // Socket
    int sock_fd_ = -1;
    SockAddrIn vehicle_addr_ = {};

    // Sequence number
    uint8_t sequence_ = 0;

    // Last telemetry
    udp::TelemetryPacket last_telemetry_ = {};
    uint32_t last_telemetry_time_ms_ = 0;
    mutable SemaphoreHandle_t mutex_ = nullptr;

    // Callback
    TelemetryCallback telemetry_callback_ = nullptr;

    // Statistics
    uint32_t tx_count_ = 0;
    uint32_t rx_count_ = 0;
    uint32_t error_count_ = 0;

    // RX task
    TaskHandle_t rx_task_handle_ = nullptr;

    // Constants
    static constexpr uint32_t TELEMETRY_TIMEOUT_MS = 1000;
    static constexpr size_t RX_BUFFER_SIZE = 64;
    static constexpr uint32_t RX_TASK_STACK_SIZE = 4096;
    static constexpr UBaseType_t RX_TASK_PRIORITY = 5;
};

}  // namespace stampfly
