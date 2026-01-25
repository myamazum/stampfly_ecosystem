# WiFi Communication Plan

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### 目的

StampFlyの通信機能を拡張し、以下を実現する：

1. **Phase 1**: Controller-Vehicle間のUDP通信
2. **Phase 2**: WiFi CLI（Telnetサーバー）
3. **Phase 3**: WiFi STA Mode（ルーター接続）

### ステータス

| 項目 | 状態 |
|------|------|
| 計画策定 | ✅ 完了 (2026-01) |
| Phase 1: UDP通信 | ✅ 完了 (2026-01) |
| Phase 2: WiFi CLI | ✅ 完了 (2026-01) |
| Phase 3: WiFi STA | ✅ 完了 (2026-01) |

### 背景

現在のStampFlyはESP-NOW（P2P無線プロトコル）でController-Vehicle間通信を行っている。これをUDPに変更/追加することで以下のメリットが得られる：

- PC同時アクセス（Controller + GCS/ROS2）
- Wiresharkでのデバッグ容易性
- 複数機体制御への拡張
- シミュレータ連携の容易化

## 2. 現状アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     現在: ESP-NOW通信                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────┐      ESP-NOW       ┌────────────────┐              │
│  │   Controller   │ ◄───────────────► │    Vehicle     │              │
│  │    (ESP32)     │   50Hz Control    │   (ESP32-S3)   │              │
│  │                │   + Telemetry     │                │              │
│  └────────────────┘                   └───────┬────────┘              │
│                                               │                        │
│                                               │ WebSocket (400Hz)      │
│                                               ▼                        │
│                                        ┌────────────┐                  │
│                                        │  PC (GCS)  │                  │
│                                        │ Telemetry  │                  │
│                                        │   only     │                  │
│                                        └────────────┘                  │
│                                                                         │
│  課題:                                                                  │
│  - PCからの制御入力経路がない                                           │
│  - CLIはUSB接続時のみ                                                   │
│  - ESP-NOWはWiresharkで解析困難                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## 3. 目標アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     目標: ESP-NOW / UDP 併存 + WiFi CLI                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌────────────────┐     ESP-NOW      ┌────────────────────────────┐   │
│  │   Controller   │ ◄──────────────► │        Vehicle             │   │
│  │    (ESP32)     │   (モード1)      │       (ESP32-S3)           │   │
│  │                │                  │      192.168.4.1           │   │
│  │  ┌──────────┐  │ ─── WiFi AP ───► │                            │   │
│  │  │ WiFi STA │  │   (モード2)      │  ┌──────────────────────┐  │   │
│  │  └──────────┘  │ ◄─── UDP ──────► │  │   ESP-NOW Receiver   │  │   │
│  │  192.168.4.x   │  :8888/:8889     │  │   (既存)             │  │   │
│  └────────────────┘                  │  └──────────────────────┘  │   │
│                                      │                            │   │
│  ※ControllerはESP-NOW/UDP両方対応    │  ┌──────────────────────┐  │   │
│    CLIコマンドで切り替え可能          │  │   UDP Server         │  │   │
│                                      │  │   - Control RX       │  │   │
│  ┌────────────────┐                  │  │   - Telemetry TX     │  │   │
│  │   PC (GCS)     │ ─── WiFi ──────► │  └──────────────────────┘  │   │
│  │  192.168.4.y   │  Connect to AP   │                            │   │
│  │                │                  │  ┌──────────────────────┐  │   │
│  │                │ ◄─ WebSocket ──► │  │   Telemetry Server   │  │   │
│  │                │   400Hz Telem    │  │   (既存)             │  │   │
│  │                │   + Control      │  └──────────────────────┘  │   │
│  │                │                  │                            │   │
│  │                │ ◄── Telnet ────► │  ┌──────────────────────┐  │   │
│  │                │     CLI :23      │  │   WiFi CLI Server    │  │   │
│  └────────────────┘                  │  │   (新規)             │  │   │
│                                      │  └──────────────────────┘  │   │
│                                      │                            │   │
│                                      │  ┌──────────────────────┐  │   │
│                                      │  │   Control Arbiter    │  │   │
│                                      │  │ ESP-NOW/UDP/WebSocket│  │   │
│                                      │  └──────────────────────┘  │   │
│                                      └────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 通信モード比較

| 項目 | ESP-NOW | UDP (WiFi AP) |
|------|---------|---------------|
| レイテンシ | 1-5ms（最速） | 5-15ms |
| インフラ | 不要 | Vehicle AP必要 |
| デバッグ | 困難 | Wireshark可 |
| PC同時接続 | 不可 | 可能 |
| 推奨用途 | 通常飛行、屋外 | 開発、研究、デバッグ |

**重要:** ESP-NOWとUDPは併存し、用途に応じて切り替え可能。移行ではなく選択肢の追加。

### 運用方針

| シナリオ | 推奨方式 | 理由 |
|----------|----------|------|
| 単機飛行（通常） | ESP-NOW | 低レイテンシ、安定 |
| 単機飛行（開発・デバッグ） | UDP | Wireshark解析、PC連携 |
| 複数機飛行（現状） | ESP-NOW + TDMA | 実績あり、3ch分離で安定 |
| 複数機飛行（将来：群制御） | UDP + WiFi | 研究課題 |

**Phase 1の目標：** 単機でのUDP飛行を確立する（ESP-NOWの代替としてではなく、新たな選択肢として）

---

# Phase 1: Controller-Vehicle UDP通信

## 4. UDPプロトコル設計

### ポート割り当て

| ポート | 方向 | 用途 |
|--------|------|------|
| 8888 | Controller → Vehicle | 制御パケット |
| 8889 | Vehicle → Controller | テレメトリパケット |

### Control Packet (16 bytes)

Controller → Vehicle、50Hz

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 1 | header | uint8 | 0xAA |
| 1 | 1 | packet_type | uint8 | 0x01 = Control |
| 2 | 1 | sequence | uint8 | シーケンス番号 |
| 3 | 1 | device_id | uint8 | 送信元ID (0=Controller) |
| 4 | 2 | throttle | uint16 | スロットル [0-4095] |
| 6 | 2 | roll | uint16 | ロール [0-4095], 2048=中央 |
| 8 | 2 | pitch | uint16 | ピッチ [0-4095], 2048=中央 |
| 10 | 2 | yaw | uint16 | ヨー [0-4095], 2048=中央 |
| 12 | 1 | flags | uint8 | ARM, FLIP, MODE, ALT_MODE |
| 13 | 1 | reserved | uint8 | 予約 |
| 14 | 2 | checksum | uint16 | CRC16 |

**Flags:**
- bit0: ARM
- bit1: FLIP
- bit2: MODE
- bit3: ALT_MODE

### Telemetry Packet (20 bytes)

Vehicle → Controller、50Hz

| Offset | Size | Field | Type | Description |
|--------|------|-------|------|-------------|
| 0 | 1 | header | uint8 | 0xAA |
| 1 | 1 | packet_type | uint8 | 0x02 = Telemetry |
| 2 | 1 | sequence | uint8 | シーケンス番号 |
| 3 | 1 | flight_state | uint8 | FlightState enum |
| 4 | 2 | battery_mv | uint16 | バッテリー電圧 [mV] |
| 6 | 2 | roll_deg10 | int16 | ロール角 [0.1deg] |
| 8 | 2 | pitch_deg10 | int16 | ピッチ角 [0.1deg] |
| 10 | 2 | yaw_deg10 | int16 | ヨー角 [0.1deg] |
| 12 | 2 | altitude_cm | int16 | 高度 [cm] |
| 14 | 2 | velocity_z_cms | int16 | 垂直速度 [cm/s] |
| 16 | 1 | rssi | uint8 | 受信信号強度 |
| 17 | 1 | flags | uint8 | ステータスフラグ |
| 18 | 2 | checksum | uint16 | CRC16 |

## 5. Vehicle側実装

### 5.1 UDPサーバーコンポーネント

```
firmware/vehicle/components/sf_svc_udp/
├── CMakeLists.txt
├── include/
│   ├── udp_server.hpp
│   └── udp_protocol.hpp
└── udp_server.cpp
```

### 5.2 udp_protocol.hpp

```cpp
#pragma once

#include <cstdint>

namespace stampfly {
namespace udp {

// Ports
constexpr uint16_t CONTROL_PORT = 8888;
constexpr uint16_t TELEMETRY_PORT = 8889;

// Packet types
constexpr uint8_t PKT_TYPE_CONTROL = 0x01;
constexpr uint8_t PKT_TYPE_TELEMETRY = 0x02;
constexpr uint8_t PKT_TYPE_HEARTBEAT = 0x10;

// Control flags (same as ESP-NOW)
constexpr uint8_t CTRL_FLAG_ARM = (1 << 0);
constexpr uint8_t CTRL_FLAG_FLIP = (1 << 1);
constexpr uint8_t CTRL_FLAG_MODE = (1 << 2);
constexpr uint8_t CTRL_FLAG_ALT_MODE = (1 << 3);

#pragma pack(push, 1)

struct ControlPacket {
    uint8_t header;           // 0xAA
    uint8_t packet_type;      // PKT_TYPE_CONTROL
    uint8_t sequence;
    uint8_t device_id;        // 0=Controller, 1-255=GCS

    uint16_t throttle;        // [0, 4095]
    uint16_t roll;            // [0, 4095], 2048=center
    uint16_t pitch;           // [0, 4095], 2048=center
    uint16_t yaw;             // [0, 4095], 2048=center

    uint8_t flags;
    uint8_t reserved;
    uint16_t checksum;        // CRC16
};

static_assert(sizeof(ControlPacket) == 16, "ControlPacket size mismatch");

struct TelemetryPacket {
    uint8_t header;           // 0xAA
    uint8_t packet_type;      // PKT_TYPE_TELEMETRY
    uint8_t sequence;
    uint8_t flight_state;

    uint16_t battery_mv;
    int16_t roll_deg10;
    int16_t pitch_deg10;
    int16_t yaw_deg10;

    int16_t altitude_cm;
    int16_t velocity_z_cms;

    uint8_t rssi;
    uint8_t flags;
    uint16_t checksum;
};

static_assert(sizeof(TelemetryPacket) == 20, "TelemetryPacket size mismatch");

#pragma pack(pop)

// CRC16 calculation
uint16_t calculateCRC16(const uint8_t* data, size_t len);

// Packet validation
bool validateControlPacket(const ControlPacket& pkt);
bool validateTelemetryPacket(const TelemetryPacket& pkt);

}  // namespace udp
}  // namespace stampfly
```

### 5.3 udp_server.hpp

```cpp
#pragma once

#include "udp_protocol.hpp"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include <netinet/in.h>

namespace stampfly {

class UDPServer {
public:
    static UDPServer& getInstance();

    // Delete copy/move
    UDPServer(const UDPServer&) = delete;
    UDPServer& operator=(const UDPServer&) = delete;

    struct Config {
        uint16_t control_port = udp::CONTROL_PORT;
        uint16_t telemetry_port = udp::TELEMETRY_PORT;
        uint32_t control_timeout_ms = 500;
        uint32_t telemetry_rate_hz = 50;
    };

    esp_err_t init(const Config& config = Config());
    esp_err_t start();
    esp_err_t stop();

    bool isRunning() const { return running_; }

    // Control input access
    bool hasActiveControl() const;
    bool getLastControl(udp::ControlPacket& pkt) const;
    uint32_t getLastControlTime() const { return last_control_time_ms_; }

    // Client management
    int getClientCount() const { return client_count_; }

    // Send telemetry to all clients
    void sendTelemetry(const udp::TelemetryPacket& pkt);

    // Statistics
    uint32_t getRxCount() const { return rx_count_; }
    uint32_t getTxCount() const { return tx_count_; }
    uint32_t getErrorCount() const { return error_count_; }
    void resetStats();

private:
    UDPServer() = default;

    static void rx_task(void* arg);
    void processPacket(const uint8_t* data, size_t len,
                       const struct sockaddr_in* src_addr);
    void updateClient(const struct sockaddr_in* addr);
    void removeStaleClients();

    Config config_;
    int sock_fd_ = -1;
    bool running_ = false;

    // Client tracking
    static constexpr int MAX_CLIENTS = 4;
    struct ClientInfo {
        struct sockaddr_in addr;
        uint32_t last_seen_ms;
        bool active;
    };
    ClientInfo clients_[MAX_CLIENTS] = {};
    int client_count_ = 0;

    // Last control packet
    udp::ControlPacket last_control_ = {};
    uint32_t last_control_time_ms_ = 0;
    mutable SemaphoreHandle_t mutex_ = nullptr;

    // Statistics
    uint32_t rx_count_ = 0;
    uint32_t tx_count_ = 0;
    uint32_t error_count_ = 0;

    // Task handle
    TaskHandle_t rx_task_handle_ = nullptr;
};

}  // namespace stampfly
```

### 5.4 Control Arbiter

```cpp
// control_arbiter.hpp

#pragma once

#include <cstdint>

namespace stampfly {

class ControlArbiter {
public:
    enum class Source {
        NONE,
        UDP,         // UDP from Controller (highest for UDP mode)
        WEBSOCKET,   // WebSocket from GCS
        ESPNOW,      // ESP-NOW (for hybrid mode)
    };

    struct ControlInput {
        float throttle;   // [0, 1]
        float roll;       // [-1, 1]
        float pitch;      // [-1, 1]
        float yaw;        // [-1, 1]
        uint8_t flags;
        Source source;
        uint32_t timestamp_ms;
    };

    static ControlArbiter& getInstance();

    // Update from sources
    void updateUDP(uint16_t throttle, uint16_t roll, uint16_t pitch,
                   uint16_t yaw, uint8_t flags);
    void updateWebSocket(float throttle, float roll, float pitch,
                         float yaw, uint8_t flags);

    // Get active control (respects priority & timeout)
    ControlInput getActiveControl() const;
    Source getActiveSource() const;

    // Timeout configuration
    void setUDPTimeout(uint32_t ms) { udp_timeout_ms_ = ms; }
    void setWebSocketTimeout(uint32_t ms) { ws_timeout_ms_ = ms; }

private:
    ControlArbiter() = default;

    // Normalize ADC values to [-1, 1] or [0, 1]
    static float normalizeThrottle(uint16_t raw);
    static float normalizeAxis(uint16_t raw);

    ControlInput udp_input_ = {};
    ControlInput ws_input_ = {};

    uint32_t udp_timeout_ms_ = 500;
    uint32_t ws_timeout_ms_ = 200;
};

}  // namespace stampfly
```

## 6. Controller側実装

### 6.1 ディレクトリ構成

```
firmware/controller/components/sf_udp_client/
├── CMakeLists.txt
├── include/
│   └── udp_client.hpp
└── udp_client.cpp
```

### 6.2 udp_client.hpp

```cpp
#pragma once

#include "udp_protocol.hpp"  // 共通プロトコル定義
#include "esp_err.h"
#include <netinet/in.h>

namespace stampfly {

class UDPClient {
public:
    struct Config {
        const char* vehicle_ip = "192.168.4.1";
        uint16_t control_port = udp::CONTROL_PORT;
        uint16_t telemetry_port = udp::TELEMETRY_PORT;
    };

    esp_err_t init(const Config& config = Config());

    // WiFi connection
    esp_err_t connectToVehicleAP(const char* ssid, const char* password = "");
    bool isWiFiConnected() const;

    // Send control (call at 50Hz)
    esp_err_t sendControl(uint16_t throttle, uint16_t roll,
                          uint16_t pitch, uint16_t yaw, uint8_t flags);

    // Receive telemetry (non-blocking)
    bool receiveTelemetry(udp::TelemetryPacket& pkt);

    // Connection status
    bool isConnected() const { return connected_; }
    uint32_t getLastTelemetryTime() const { return last_telem_time_ms_; }

    // Statistics
    uint32_t getTxCount() const { return tx_count_; }
    uint32_t getRxCount() const { return rx_count_; }

private:
    Config config_;
    int sock_fd_ = -1;
    struct sockaddr_in vehicle_addr_ = {};
    bool connected_ = false;

    uint8_t sequence_ = 0;
    uint32_t last_telem_time_ms_ = 0;

    uint32_t tx_count_ = 0;
    uint32_t rx_count_ = 0;
};

}  // namespace stampfly
```

### 6.3 通信モード定義

```cpp
// comm_mode.hpp (shared between Vehicle and Controller)

#pragma once

namespace stampfly {

enum class CommMode : uint8_t {
    ESPNOW = 0,      // ESP-NOW direct (default)
    UDP = 1,         // UDP over Vehicle's AP
    USB_HID = 2,     // USB HID (Controller only)
};

// NVS key for storing mode
constexpr const char* NVS_KEY_COMM_MODE = "comm_mode";

}  // namespace stampfly
```

### 6.4 Controller LCDメニューによるモード切替

現在のControllerメニューシステムを活用し、「USB Mode」を「Comm Mode」に拡張する。

**現在のメニュー構成：**
```
1. Stick: Mode 2/3
2. USB Mode        ← ESP-NOW / USB HID の2択
3. Batt: 3.3V
...
```

**変更後のメニュー構成：**
```
1. Stick: Mode 2/3
2. Comm: ESP-NOW   ← ESP-NOW / UDP / USB HID の3択（サイクル切替）
3. Batt: 3.3V
...
```

**実装変更点（menu_system.cpp）：**

```cpp
// 現在
static const char* usb_mode_labels[] = {"ESP-NOW", "USB HID"};

// 変更後
typedef enum {
    COMM_MODE_ESPNOW = 0,
    COMM_MODE_UDP = 1,
    COMM_MODE_USB_HID = 2,
    COMM_MODE_COUNT = 3
} comm_mode_t;

static const char* comm_mode_labels[] = {"ESP-NOW", "UDP", "USB HID"};

// メニュー選択時のサイクル切替
void on_comm_mode_selected() {
    current_comm_mode = (current_comm_mode + 1) % COMM_MODE_COUNT;
    update_menu_label(MENU_ITEM_COMM, comm_mode_labels[current_comm_mode]);
    save_comm_mode_to_nvs(current_comm_mode);

    // モード変更後は再起動が必要
    if (needs_restart) {
        esp_restart();
    }
}
```

**LCD表示例：**

```
┌────────────────────┐
│   StampFly Menu    │
├────────────────────┤
│ > Comm: ESP-NOW    │  ← 選択でサイクル
│   Comm: UDP        │
│   Comm: USB HID    │
├────────────────────┤
│ [Mode] Select      │
│ [M5]   Back        │
└────────────────────┘
```

## 7. ESP-NOW / UDP 併存戦略

### 7.1 併存アーキテクチャ

ESP-NOWとUDPは**どちらも正式な通信方式**として維持する。用途に応じて選択可能。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        併存戦略                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【ESP-NOW モード】（デフォルト）                                        │
│  - 最も低レイテンシ (1-5ms)                                             │
│  - インフラ不要、電源ONですぐ接続                                        │
│  - 通常飛行、屋外、競技用途に推奨                                        │
│                                                                         │
│  【UDP モード】                                                          │
│  - デバッグ容易 (Wireshark対応)                                         │
│  - PC/GCSと同時接続可能                                                 │
│  - 開発、研究、ログ解析に推奨                                            │
│                                                                         │
│  【切り替え方法】                                                        │
│  - Controller: LCDメニューで選択（Comm: ESP-NOW/UDP/USB HID）           │
│  - Vehicle: CLIコマンド（comm mode espnow/udp）                         │
│  - NVSに保存、次回起動時も維持                                          │
│  - モード変更時は再起動                                                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 7.2 実装ステップ

| Step | 内容 | Vehicle | Controller |
|------|------|---------|------------|
| 1 | UDP追加 | UDPサーバー追加 | UDPクライアント追加 |
| 2 | モード切替UI | CLIコマンド追加 | LCDメニュー拡張（USB Mode → Comm Mode） |
| 3 | NVS保存 | モード永続化 | 既存NVS活用 |
| 4 | 検証 | 両モードテスト | 両モードテスト |

**注意:** ESP-NOWは「レガシー」ではなく、低レイテンシが必要な場面での推奨モード。

### 7.3 Controller接続フロー

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  Controller接続フロー                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Controller起動                                                         │
│       │                                                                 │
│       ▼                                                                 │
│  ┌─────────────────┐                                                   │
│  │ NVSからモード読込 │  ※LCDメニューで事前設定済み                       │
│  └────────┬────────┘                                                   │
│           │                                                             │
│     ┌─────┴──────┐                                                     │
│     │ comm_mode? │                                                     │
│     └─────┬──────┘                                                     │
│           │                                                             │
│   ┌───────┼───────┐                                                    │
│   │       │       │                                                    │
│   ▼       ▼       ▼                                                    │
│ ESPNOW    UDP   USB_HID                                                 │
│   │       │       │                                                    │
│   ▼       ▼       ▼                                                    │
│ ┌────────────┐ ┌────────────────────────┐ ┌────────────┐               │
│ │ ESP-NOW    │ │ WiFi STA初期化         │ │ USB HID    │               │
│ │ 初期化     │ │ → "StampFly_XXXX"     │ │ 初期化     │               │
│ │ ペアリング │ │    APスキャン・接続    │ │ (既存)     │               │
│ │ 制御ループ │ │ → UDPソケット作成     │ │            │               │
│ │ 開始       │ │ → 制御ループ開始      │ │            │               │
│ └────────────┘ │    (50Hz TX/RX)        │ └────────────┘               │
│                └────────────────────────┘                               │
│                                                                         │
│  【モード切替方法】                                                      │
│  LCDメニュー → "Comm: ESP-NOW" 選択 → サイクル切替 → 再起動             │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

**LCDメニューでのモード切替手順：**

1. メニュー画面を開く（M5ボタン）
2. 「Comm: ESP-NOW」項目を選択
3. Modeボタンで切替（ESP-NOW → UDP → USB HID → ...）
4. 自動的に再起動、新モードで動作開始

---

# Phase 2: WiFi CLI

## 8. WiFi CLI設計

### 8.1 概要

既存のUSB CDCベースのCLIをWiFi経由でアクセス可能にする。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WiFi CLI アーキテクチャ                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  PC (Terminal)                        Vehicle                          │
│  ┌────────────────┐                  ┌────────────────────────────┐    │
│  │  telnet        │                  │                            │    │
│  │  192.168.4.1   │ ◄── TCP:23 ───► │  WiFi CLI Server           │    │
│  │  23            │                  │  ┌──────────────────────┐  │    │
│  └────────────────┘                  │  │ Telnet Handler       │  │    │
│                                      │  │ - Line buffering     │  │    │
│  または:                              │  │ - Echo               │  │    │
│  ┌────────────────┐                  │  │ - Command dispatch   │  │    │
│  │  nc (netcat)   │                  │  └──────────┬───────────┘  │    │
│  │  192.168.4.1   │                  │             │              │    │
│  │  23            │                  │  ┌──────────▼───────────┐  │    │
│  └────────────────┘                  │  │ CLI Command Handler  │  │    │
│                                      │  │ (既存CLIと共有)       │  │    │
│  または:                              │  └──────────────────────┘  │    │
│  ┌────────────────┐                  │                            │    │
│  │  sf cli wifi   │                  │  ┌──────────────────────┐  │    │
│  │  (sf CLI)      │                  │  │ USB CDC CLI (既存)   │  │    │
│  └────────────────┘                  │  └──────────────────────┘  │    │
│                                      └────────────────────────────┘    │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 8.2 コンポーネント構成

```
firmware/vehicle/components/sf_svc_wifi_cli/
├── CMakeLists.txt
├── include/
│   └── wifi_cli.hpp
└── wifi_cli.cpp
```

### 8.3 wifi_cli.hpp

```cpp
#pragma once

#include "cli.hpp"
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include <netinet/in.h>

namespace stampfly {

class WiFiCLI {
public:
    static WiFiCLI& getInstance();

    // Delete copy/move
    WiFiCLI(const WiFiCLI&) = delete;
    WiFiCLI& operator=(const WiFiCLI&) = delete;

    struct Config {
        uint16_t port = 23;           // Telnet standard port
        uint8_t max_clients = 2;      // Max simultaneous connections
        size_t rx_buffer_size = 256;
        uint32_t idle_timeout_ms = 300000;  // 5 min idle timeout
    };

    esp_err_t init(const Config& config = Config());
    esp_err_t start();
    esp_err_t stop();

    bool isRunning() const { return running_; }

    // Set CLI command handler (shared with USB CLI)
    void setCLI(CLI* cli) { cli_ = cli; }

    // Broadcast message to all clients (for async output)
    void broadcast(const char* message);

    // Client info
    int getClientCount() const { return client_count_; }
    bool hasClients() const { return client_count_ > 0; }

    // Disconnect specific or all clients
    void disconnectAll();

private:
    WiFiCLI() = default;

    static void accept_task(void* arg);
    static void client_task(void* arg);

    struct ClientContext {
        WiFiCLI* server;
        int client_fd;
        struct sockaddr_in addr;
        char rx_buffer[256];
        size_t rx_pos;
        uint32_t last_activity_ms;
    };

    void handleClient(ClientContext* ctx);
    void processLine(ClientContext* ctx, const char* line);
    void sendToClient(int fd, const char* data, size_t len);
    void sendPrompt(int fd);

    Config config_;
    CLI* cli_ = nullptr;
    int server_fd_ = -1;
    bool running_ = false;

    // Client tracking
    static constexpr int MAX_CLIENTS = 2;
    ClientContext* clients_[MAX_CLIENTS] = {};
    int client_count_ = 0;
    SemaphoreHandle_t client_mutex_ = nullptr;

    TaskHandle_t accept_task_handle_ = nullptr;
};

}  // namespace stampfly
```

### 8.4 CLIコマンドハンドラ共有

```cpp
// 既存CLIクラスに以下を追加

class CLI {
public:
    // ... 既存メンバー ...

    // Output interface for multiple backends (USB, WiFi)
    class OutputInterface {
    public:
        virtual void write(const char* data, size_t len) = 0;
        virtual void flush() = 0;
        virtual ~OutputInterface() = default;
    };

    // Execute command with specified output
    void executeCommand(const char* line, OutputInterface* output);

    // Register output interface
    void addOutput(OutputInterface* output);
    void removeOutput(OutputInterface* output);

private:
    // Multiple output backends
    static constexpr int MAX_OUTPUTS = 3;
    OutputInterface* outputs_[MAX_OUTPUTS] = {};
    int output_count_ = 0;
};
```

### 8.5 sf CLI統合

```bash
# PC側からの接続（sf CLI経由）
sf cli wifi                    # Telnet接続 (192.168.4.1:23)
sf cli wifi --ip 192.168.1.100 # 指定IPに接続

# または直接
telnet 192.168.4.1 23
nc 192.168.4.1 23
```

## 9. CLIコマンド追加

### Vehicle側

```
# 通信モード
comm               Communication mode settings
  comm status        - Show current mode and connection status
  comm mode espnow   - Use ESP-NOW (default)
  comm mode udp      - Use UDP over AP
  comm stats         - Show TX/RX statistics
  comm restart       - Restart communication subsystem

# WiFi CLI
wifi_cli           WiFi CLI server settings
  wifi_cli status    - Show server status and clients
  wifi_cli kick      - Disconnect all clients
  wifi_cli port <n>  - Set server port (requires restart)

# UDP制御
udp                UDP server settings
  udp status         - Show UDP server status
  udp clients        - List connected clients
  udp timeout <ms>   - Set control timeout
```

### Controller側

```
# WiFi接続
wifi               WiFi connection settings
  wifi status        - Show connection status
  wifi scan          - Scan for StampFly APs
  wifi connect       - Connect to saved AP
  wifi forget        - Clear saved AP

# 通信モード
comm               Communication mode
  comm mode espnow   - Use ESP-NOW
  comm mode udp      - Use UDP
  comm stats         - Show statistics
```

---

# Phase 3: WiFi STA Mode（ルーター接続）

## WiFi STA Mode概要

StampFly VehicleにWiFi STAモードを追加し、WiFiルーター（アクセスポイント）に接続できるようにする。これにより、以下が可能になる：

| 機能 | 説明 |
|------|------|
| ROS2連携 | 外部PCのROS2ノードと通信（STA IP経由） |
| インターネットアクセス | OTA更新、クラウドロギング、NTP時刻同期 |
| 複数環境対応 | 研究室と自宅など、複数のWiFi環境を保存（最大5個） |
| 群制御準備 | 複数ドローンを同じルーターに接続（将来） |
| APモード併用 | デバッグ用APモード（192.168.4.1）も維持 |

### WiFi APSTA Mode

ESP32の **APSTA Mode** を活用し、AP（アクセスポイント）とSTA（ステーション）を同時に動作させる。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     WiFi APSTA Mode Architecture                        │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【APモード（既存）】                                                    │
│  ┌────────────┐                  ┌────────────────────────────┐        │
│  │ PC/Phone   │ ◄── WiFi AP ───► │  Vehicle (StampFly)        │        │
│  │            │   192.168.4.x    │  - AP: 192.168.4.1         │        │
│  │            │                  │  - Telnet: 23              │        │
│  └────────────┘                  │  - WebSocket: 80           │        │
│                                  │  - UDP: 8888/8889          │        │
│  【STAモード（新規）】            │                            │        │
│  ┌────────────────┐              │                            │        │
│  │ WiFi Router    │              │  ┌──────────────────────┐  │        │
│  │ (Lab/Home)     │ ◄── STA ───► │  │  WiFi STA Client     │  │        │
│  │ 192.168.x.x    │              │  │  - Connect to AP     │  │        │
│  │                │              │  │  - Multi-AP (max 5)  │  │        │
│  └────┬───────────┘              │  │  - Auto failover     │  │        │
│       │                          │  └──────────────────────┘  │        │
│       │ Router                   │                            │        │
│       ▼                          │  STA IP: 192.168.x.y       │        │
│  ┌────────────┐                  └────────────────────────────┘        │
│  │ ROS2 Node  │ ◄────── UDP ──────────┐                                │
│  │ (PC)       │    via STA IP         │                                │
│  └────────────┘                       │                                │
│                                       │                                │
└───────────────────────────────────────┼────────────────────────────────┘
                                        │
                                        ▼
                              ROS2制御、インターネット接続
```

### Multi-AP対応

複数のWiFi環境（研究室、自宅、カフェなど）を保存し、優先順位順に自動接続：

```
【保存例】
  [0] Lab-WiFi        (優先度1)
  [1] Home-WiFi       (優先度2)
  [2] Mobile-Hotspot  (優先度3)

【動作】
  起動時:
    1. Lab-WiFiに接続試行 → 成功 → 使用
    2. 失敗 → Home-WiFiに接続試行 → 成功 → 使用
    3. 失敗 → Mobile-Hotspotに接続試行 → ...
    4. 全て失敗 → 最初から再試行（5秒待機）
```

## 実装内容

### データ構造

```cpp
// controller_comm.hpp
struct STAConfig {
    char ssid[32];
    char password[64];
    bool is_valid;
};

static constexpr int MAX_STA_CONFIGS = 5;  // 最大5個のAP設定

STAConfig sta_configs_[MAX_STA_CONFIGS] = {};
int sta_config_count_ = 0;
int current_sta_index_ = -1;  // 現在接続中のAP index
bool sta_auto_connect_ = true;  // デフォルトON
bool sta_connected_ = false;
char sta_ip_addr_[16] = {0};
```

### WiFi/IPイベントハンドラ

```cpp
// 自動フェイルオーバー機能
void onSTADisconnected(void* event_data) {
    // 切断時、次のAPを試行
    if (sta_auto_connect_ && sta_config_count_ > 0) {
        connection_attempt_index_++;
        if (connection_attempt_index_ >= sta_config_count_) {
            connection_attempt_index_ = 0;  // 最初に戻る
            vTaskDelay(pdMS_TO_TICKS(5000));  // 5秒待機
        }
        connectSTA(connection_attempt_index_);
    }
}
```

### CLIコマンド

| コマンド | 説明 |
|---------|------|
| `wifi sta list` | 保存されたAP一覧を優先順位順に表示 |
| `wifi sta add <ssid> <password>` | 新しいAP設定を追加（最大5個） |
| `wifi sta remove <index>` | インデックス指定でAP削除 |
| `wifi sta connect [index]` | 接続（自動または指定） |
| `wifi sta disconnect` | 切断 |
| `wifi sta auto [on\|off]` | 起動時自動接続の有効/無効 |
| `wifi status` | WiFi全体の状態（AP + STA） |

### NVS永続化

```cpp
// NVSキー
static constexpr const char* NVS_KEY_STA_COUNT = "sta_count";  // u8
static constexpr const char* NVS_KEY_STA_AUTO  = "sta_auto";   // u8
static constexpr const char* NVS_KEY_STA_SSID_FMT = "sta_%d_ssid";  // string (0-4)
static constexpr const char* NVS_KEY_STA_PASS_FMT = "sta_%d_pass";  // string (0-4)
```

- 起動時に自動的にNVSからAP設定を読み込み
- `wifi sta add/remove` 時に自動的にNVSに保存
- 再起動後も設定を保持

### チャンネル制約

ESP32のAPSTA制約により、**STAとAPは同じチャンネル**を使用：

- STAが接続したAPのチャンネルに、自機のAPも自動的に追従
- ESP-NOW通信もチャンネルに依存するため、チャンネル変更を検出してログで警告

```cpp
// チャンネル変更警告
if (sta_connected_) {
    ESP_LOGW(TAG, "STA is connected - channel change may disconnect AP");
    ESP_LOGW(TAG, "STA will override this channel when reconnected");
}
```

## 使用シナリオ

### シナリオ1: ROS2開発（STA IP経由）

```bash
# StampFly側
wifi sta add "Lab-WiFi" "lab-password"
wifi sta connect

# PC側（同じLab-WiFiに接続）
ping 192.168.1.123  # StampFlyのSTA IP
ros2 topic echo /stampfly/telemetry
```

### シナリオ2: 研究室と自宅の行き来

```bash
# 初回設定
wifi sta add "Lab-WiFi" "lab-pass"
wifi sta add "Home-WiFi" "home-pass"
wifi sta auto on

# 研究室で起動 → Lab-WiFiに自動接続
# 自宅で起動 → Home-WiFiに自動接続
```

### シナリオ3: フィールド飛行（STA不要）

```bash
# 自動接続を無効化して起動高速化
wifi sta auto off
reboot
```

## 実装ファイル

| ファイル | 変更内容 |
|---------|---------|
| `controller_comm.hpp` | STAConfig構造体、公開インターフェース追加 |
| `controller_comm.cpp` | WiFi/IPイベントハンドラ、init()修正、STA接続/NVS関数実装 |
| `cmd_comm.cpp` | `wifi sta` コマンド追加（6つのサブコマンド） |

## 参考資料

| ドキュメント | 説明 |
|-------------|------|
| [wifi-sta-setup.md](../wifi-sta-setup.md) | ユーザー向けセットアップガイド |
| [ESP-IDF WiFi Driver](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi.html) | WiFi APIリファレンス |
| [APSTA Mode](https://docs.espressif.com/projects/esp-idf/en/latest/esp32/api-guides/wifi.html#station-ap-coexistence) | APSTAモード公式ドキュメント |

---

## 10. 実装スケジュール

### Phase 1: UDP通信

| Step | 内容 | ファイル |
|------|------|----------|
| 1.1 | プロトコル定義 | `udp_protocol.hpp` (共通) |
| 1.2 | Vehicle UDPサーバー | `sf_svc_udp/` |
| 1.3 | Controller UDPクライアント | `sf_udp_client/` |
| 1.4 | Control Arbiter | `control_arbiter.hpp/cpp` |
| 1.5 | モード切り替えCLI | `cli.cpp` 修正 |
| 1.6 | テスト・検証 | - |

### Phase 2: WiFi CLI

| Step | 内容 | ファイル |
|------|------|----------|
| 2.1 | WiFi CLIサーバー | `sf_svc_wifi_cli/` |
| 2.2 | CLI出力抽象化 | `cli.hpp/cpp` 修正 |
| 2.3 | sf CLI統合 | `lib/sfcli/` |
| 2.4 | テスト・検証 | - |

### Phase 3: WiFi STA Mode

| Step | 内容 | ファイル |
|------|------|----------|
| 3.1 | データ構造追加 | `controller_comm.hpp` |
| 3.2 | WiFi/IPイベントハンドラ | `controller_comm.cpp` |
| 3.3 | STA接続/切断関数 | `controller_comm.cpp` |
| 3.4 | NVS永続化 | `controller_comm.cpp` |
| 3.5 | CLIコマンド追加 | `cmd_comm.cpp` |
| 3.6 | チャンネル警告 | `controller_comm.cpp` |
| 3.7 | テスト・検証 | - |
| 3.8 | ドキュメント整備 | `docs/wifi-sta-setup.md` |

---

## 11. 将来構想：WiFiによる群制御

### 背景

複数機の群制御（Swarm Control）はStampFlyの将来の研究課題。現在はESP-NOW + TDMAで複数機飛行を実現しているが、WiFi/UDPベースの群制御も視野に入れる。

### 現状と将来

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        複数機制御のロードマップ                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  【現在】ESP-NOW + TDMA                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                              │
│  │Controller│  │Controller│  │Controller│                              │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                              │
│       │ESP-NOW      │ESP-NOW      │ESP-NOW                             │
│       │Ch1/Slot0    │Ch6/Slot0    │Ch11/Slot0                          │
│       ▼             ▼             ▼                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                              │
│  │ Vehicle1 │  │ Vehicle2 │  │ Vehicle3 │                              │
│  └──────────┘  └──────────┘  └──────────┘                              │
│  → 3チャンネル分離 + TDMA で安定飛行を実現                               │
│                                                                         │
│  【将来】WiFi群制御                                                      │
│  ┌──────────────────────────────────────────┐                          │
│  │           Ground Station (PC)            │                          │
│  │         群制御アルゴリズム実行            │                          │
│  └──────────────────┬───────────────────────┘                          │
│                     │ WiFi (UDP Broadcast / Multicast)                 │
│       ┌─────────────┼─────────────┐                                    │
│       ▼             ▼             ▼                                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                              │
│  │ Vehicle1 │  │ Vehicle2 │  │ Vehicle3 │                              │
│  │  (STA)   │  │  (STA)   │  │  (STA)   │                              │
│  └──────────┘  └──────────┘  └──────────┘                              │
│  → 全機がルーター/PCのAPに接続                                          │
│  → PCから一括制御指令                                                   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 群制御のアーキテクチャ候補

| 方式 | 構成 | メリット | デメリット |
|------|------|---------|-----------|
| A: インフラモード | 全機STA、ルーター経由 | 帯域広い、PC制御容易 | ルーター必要、レイテンシ |
| B: メッシュ | ESP-WIFI-MESH | インフラ不要 | 実装複雑 |
| C: ハイブリッド | ESP-NOW + WiFi | 柔軟性高い | 複雑 |

### Phase 1との関係

Phase 1（単機UDP）は将来の群制御の基盤となる：

1. **UDP通信の確立** → 群制御でも同じプロトコルを流用
2. **Vehicle STAモード** → 群制御時は全機STAとしてルーターに接続
3. **Control Arbiter** → 複数指令源（PC群制御 + 緊急手動介入）の管理

### 研究課題

- 同一チャンネルでの複数機通信の遅延特性
- UDP Broadcast/Multicastの実用性
- 時刻同期（NTP/PTPまたはソフトウェア同期）
- フェイルセーフ（通信断時の自律ホバリング/着陸）

---

## 12. 参考情報

### ESP-IDF ドキュメント

| トピック | URL |
|----------|-----|
| UDP Socket | https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-guides/lwip.html |
| WiFi STA | https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/api-reference/network/esp_wifi.html |
| TCP Server | https://github.com/espressif/esp-idf/tree/master/examples/protocols/sockets |

### レイテンシ目安

| 通信方式 | 期待レイテンシ |
|----------|--------------|
| ESP-NOW | 1-5ms |
| UDP (同一AP) | 5-15ms |
| UDP (Router経由) | 10-30ms |
| TCP (Telnet) | 10-50ms |

---

<a id="english"></a>

## 1. Overview

### Purpose

Extend StampFly communication capabilities:

1. **Phase 1**: UDP communication between Controller and Vehicle
2. **Phase 2**: WiFi CLI (Telnet server)
3. **Phase 3**: WiFi STA Mode (Router connection)

### Status

| Item | Status |
|------|--------|
| Planning | ✅ Complete (2026-01) |
| Phase 1: UDP Comm | ✅ Complete (2026-01) |
| Phase 2: WiFi CLI | ✅ Complete (2026-01) |
| Phase 3: WiFi STA | ✅ Complete (2026-01) |

## 2. Current vs Target Architecture

See Japanese section for detailed diagrams.

**Current:** ESP-NOW for Controller-Vehicle, WebSocket for telemetry only.

**Target:** ESP-NOW and UDP **coexisting** for Controller-Vehicle (switchable), Telnet for CLI, WebSocket maintained for high-rate telemetry.

### Communication Mode Comparison

| Aspect | ESP-NOW | UDP (WiFi AP) |
|--------|---------|---------------|
| Latency | 1-5ms (fastest) | 5-15ms |
| Infrastructure | None required | Vehicle AP needed |
| Debugging | Difficult | Wireshark compatible |
| PC concurrent access | No | Yes |
| Recommended for | Normal flight, outdoor | Development, research |

**Important:** ESP-NOW and UDP coexist as equal options. This is not a migration but adding choices.

## 3. UDP Protocol

### Ports

| Port | Direction | Purpose |
|------|-----------|---------|
| 8888 | Controller → Vehicle | Control packets |
| 8889 | Vehicle → Controller | Telemetry packets |

### Control Packet (16 bytes)

See Japanese section for detailed structure.

### Telemetry Packet (20 bytes)

See Japanese section for detailed structure.

## 4. Implementation Phases

### Phase 1: UDP Communication

1. Protocol definition (shared header)
2. Vehicle UDP server
3. Controller UDP client
4. Control arbiter
5. CLI commands for mode switching
6. Testing and validation

### Phase 2: WiFi CLI

1. Telnet server implementation
2. CLI output abstraction
3. sf CLI integration
4. Testing and validation

## 5. Coexistence Strategy

ESP-NOW and UDP are **both official communication methods**, selectable based on use case.

| Mode | Default | Use Case | Latency |
|------|---------|----------|---------|
| ESP-NOW | Yes | Normal flight, outdoor, competition | 1-5ms |
| UDP | No | Development, research, debugging | 5-15ms |

**Switching Methods:**
- CLI command: `comm mode espnow` or `comm mode udp`
- Saved to NVS (persists across reboots)
- Runtime switching supported (no reboot required)

**Note:** ESP-NOW is not "legacy" - it remains the recommended mode for low-latency requirements.

## 6. References

See Japanese section for ESP-IDF documentation links.
