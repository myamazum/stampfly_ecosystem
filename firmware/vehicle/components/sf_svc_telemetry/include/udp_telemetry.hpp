/**
 * @file udp_telemetry.hpp
 * @brief UDP Telemetry Packet Definitions and Log Server
 *
 * UDP テレメトリパケット定義 & ログサーバー
 *
 * Design: Method A — Independent sensor packets with batching.
 * 設計方針: 方式A — センサ独立パケット + バッチ化
 *
 * Each sensor type has its own packet ID and is batched at its native rate.
 * Sent via UDP (fire-and-forget, no ACK). PC receives with Python script.
 * 各センサは固有のパケットIDを持ち、固有レートでバッチ送信。
 * UDP で送りっぱなし（ACK なし）。PC 側は Python で受信。
 *
 * Common packet structure:
 *   [header 4B][samples N×size][checksum 1B]
 *
 * Header: [packet_id 1B][sequence 2B][sample_count 1B]
 * Footer: [checksum 1B] (XOR of all preceding bytes)
 *
 * Packet IDs:
 *   0x40  IMU + ESKF attitude (400Hz, batch 4)
 *   0x41  Position + Velocity (400Hz, batch 4)
 *   0x42  Control Input (50Hz, batch 4)
 *   0x43  Optical Flow (100Hz, batch 4)
 *   0x44  ToF (30Hz, batch 4)
 *   0x45  Barometer (50Hz, batch 4)
 *   0x46  Magnetometer (25Hz, batch 4)
 *   0x4F  Status / Heartbeat (1Hz, no batch)
 *   0xF0  Start log command (PC → Vehicle)
 *   0xF1  Stop log command (PC → Vehicle)
 *   0xF2  Heartbeat (PC → Vehicle)
 *
 * @see docs/plans/lucky-squishing-pearl.md for design rationale
 */

#pragma once

#include <cstdint>
#include <cstring>
#include <atomic>
#include "esp_err.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// =============================================================================
// Packet IDs
// パケットID
// =============================================================================

namespace stampfly {
namespace udp_telem {

// Vehicle → PC (data packets)
// Vehicle → PC（データパケット）
inline constexpr uint8_t PKT_IMU_ESKF      = 0x40;
inline constexpr uint8_t PKT_POS_VEL       = 0x41;
inline constexpr uint8_t PKT_CONTROL       = 0x42;
inline constexpr uint8_t PKT_FLOW          = 0x43;
inline constexpr uint8_t PKT_TOF           = 0x44;
inline constexpr uint8_t PKT_BARO          = 0x45;
inline constexpr uint8_t PKT_MAG           = 0x46;
inline constexpr uint8_t PKT_STATUS        = 0x4F;

// PC → Vehicle (commands)
// PC → Vehicle（コマンド）
inline constexpr uint8_t CMD_START_LOG     = 0xF0;
inline constexpr uint8_t CMD_STOP_LOG      = 0xF1;
inline constexpr uint8_t CMD_HEARTBEAT     = 0xF2;

inline constexpr int BATCH_SIZE = 4;
inline constexpr int UDP_LOG_PORT = 8890;
inline constexpr int HEARTBEAT_TIMEOUT_MS = 5000;

// =============================================================================
// Common header (4 bytes)
// 共通ヘッダ（4バイト）
// =============================================================================

#pragma pack(push, 1)

struct PacketHeader {
    uint8_t  packet_id;      // Sensor type identifier
    uint16_t sequence;       // Per-type rolling counter (for loss detection)
    uint8_t  sample_count;   // Number of samples in this batch (1-4)
};

static_assert(sizeof(PacketHeader) == 4, "PacketHeader size mismatch");

// =============================================================================
// 0x40: IMU + ESKF Attitude (80B/sample, batch 4 → 325B)
// IMU 6軸 + ESKF姿勢（80B/サンプル、4バッチ → 325B）
// =============================================================================

struct ImuEskfSample {
    uint32_t timestamp_us;       // μs since boot

    // IMU LPF filtered (what ESKF sees as input)
    // IMU LPFフィルタ済み（ESKFの入力）
    float gyro_x, gyro_y, gyro_z;       // [rad/s]
    float accel_x, accel_y, accel_z;    // [m/s²]

    // IMU raw (pre-LPF, for system identification)
    // IMU 生値（LPF前、システム同定用）
    float gyro_raw_x, gyro_raw_y, gyro_raw_z;    // [rad/s]
    float accel_raw_x, accel_raw_y, accel_raw_z;  // [m/s²]

    // ESKF attitude quaternion [w, x, y, z]
    // ESKF姿勢クォータニオン
    float quat_w, quat_x, quat_y, quat_z;

    // Bias estimates (scaled: value × 10000)
    // バイアス推定値（スケール: 値×10000）
    int16_t gyro_bias_x, gyro_bias_y, gyro_bias_z;    // [0.0001 rad/s]
    int16_t accel_bias_x, accel_bias_y, accel_bias_z;  // [0.0001 m/s²]
};

static_assert(sizeof(ImuEskfSample) == 80, "ImuEskfSample size mismatch");

struct ImuEskfBatchPacket {
    PacketHeader header;
    ImuEskfSample samples[BATCH_SIZE];
    uint8_t checksum;
};

static_assert(sizeof(ImuEskfBatchPacket) == 325, "ImuEskfBatchPacket size mismatch");

// =============================================================================
// 0x41: Position + Velocity (28B/sample, batch 4 → 117B)
// 位置 + 速度（28B/サンプル、4バッチ → 117B）
// =============================================================================

struct PosVelSample {
    uint32_t timestamp_us;
    float pos_x, pos_y, pos_z;    // NED [m]
    float vel_x, vel_y, vel_z;    // NED [m/s]
};

static_assert(sizeof(PosVelSample) == 28, "PosVelSample size mismatch");

struct PosVelBatchPacket {
    PacketHeader header;
    PosVelSample samples[BATCH_SIZE];
    uint8_t checksum;
};

static_assert(sizeof(PosVelBatchPacket) == 117, "PosVelBatchPacket size mismatch");

// =============================================================================
// 0x42: Control Input (20B/sample, batch 4 → 85B)
// 制御入力（20B/サンプル、4バッチ → 85B）
// =============================================================================

struct ControlSample {
    uint32_t timestamp_us;
    float throttle;     // [0-1]
    float roll;         // [-1, 1]
    float pitch;        // [-1, 1]
    float yaw;          // [-1, 1]
};

static_assert(sizeof(ControlSample) == 20, "ControlSample size mismatch");

struct ControlBatchPacket {
    PacketHeader header;
    ControlSample samples[BATCH_SIZE];
    uint8_t checksum;
};

static_assert(sizeof(ControlBatchPacket) == 85, "ControlBatchPacket size mismatch");

// =============================================================================
// 0x43: Optical Flow (9B/sample, batch 4 → 41B)
// 光学フロー（9B/サンプル、4バッチ → 41B）
// =============================================================================

struct FlowSample {
    uint32_t timestamp_us;
    int16_t flow_dx;        // [pixels/frame]
    int16_t flow_dy;        // [pixels/frame]
    uint8_t quality;        // [0-255]
};

static_assert(sizeof(FlowSample) == 9, "FlowSample size mismatch");

struct FlowBatchPacket {
    PacketHeader header;
    FlowSample samples[BATCH_SIZE];
    uint8_t checksum;
};

static_assert(sizeof(FlowBatchPacket) == 41, "FlowBatchPacket size mismatch");

// =============================================================================
// 0x44: ToF (14B/sample, batch 4 → 61B)
// ToF距離（14B/サンプル、4バッチ → 61B）
// =============================================================================

struct ToFSample {
    uint32_t timestamp_us;
    float tof_bottom;          // [m]
    float tof_front;           // [m]
    uint8_t status_bottom;     // 0=valid
    uint8_t status_front;      // 0=valid
};

static_assert(sizeof(ToFSample) == 14, "ToFSample size mismatch");

struct ToFBatchPacket {
    PacketHeader header;
    ToFSample samples[BATCH_SIZE];
    uint8_t checksum;
};

static_assert(sizeof(ToFBatchPacket) == 61, "ToFBatchPacket size mismatch");

// =============================================================================
// 0x45: Barometer (12B/sample, batch 4 → 53B)
// 気圧計（12B/サンプル、4バッチ → 53B）
// =============================================================================

struct BaroSample {
    uint32_t timestamp_us;
    float altitude;        // [m] relative
    float pressure;        // [hPa]
};

static_assert(sizeof(BaroSample) == 12, "BaroSample size mismatch");

struct BaroBatchPacket {
    PacketHeader header;
    BaroSample samples[BATCH_SIZE];
    uint8_t checksum;
};

static_assert(sizeof(BaroBatchPacket) == 53, "BaroBatchPacket size mismatch");

// =============================================================================
// 0x46: Magnetometer (16B/sample, batch 4 → 69B)
// 地磁気（16B/サンプル、4バッチ → 69B）
// =============================================================================

struct MagSample {
    uint32_t timestamp_us;
    float mag_x, mag_y, mag_z;   // [μT] calibrated, body frame NED
};

static_assert(sizeof(MagSample) == 16, "MagSample size mismatch");

struct MagBatchPacket {
    PacketHeader header;
    MagSample samples[BATCH_SIZE];
    uint8_t checksum;
};

static_assert(sizeof(MagBatchPacket) == 69, "MagBatchPacket size mismatch");

// =============================================================================
// 0x4F: Status / Heartbeat (17B, no batch)
// ステータス / ハートビート（17B、バッチなし）
// =============================================================================

struct StatusPacket {
    PacketHeader header;         // packet_id=0x4F, sample_count=1
    uint32_t uptime_ms;
    float voltage;               // [V]
    uint8_t flight_state;
    uint8_t sensor_health;       // bitmask
    uint8_t eskf_status;
    uint8_t padding;
    uint8_t checksum;
};

static_assert(sizeof(StatusPacket) == 17, "StatusPacket size mismatch");

#pragma pack(pop)

// =============================================================================
// Checksum utility
// チェックサムユーティリティ
// =============================================================================

/// Compute XOR checksum of all bytes before the last byte (checksum field)
/// 最後のバイト（チェックサムフィールド）の前の全バイトの XOR を計算
inline uint8_t computeChecksum(const void* data, size_t total_size) {
    const uint8_t* bytes = static_cast<const uint8_t*>(data);
    uint8_t xor_val = 0;
    for (size_t i = 0; i < total_size - 1; i++) {
        xor_val ^= bytes[i];
    }
    return xor_val;
}

// =============================================================================
// Batch accumulator template
// バッチ蓄積テンプレート
// =============================================================================

/// Generic batch accumulator for sensor packets
/// センサパケット用の汎用バッチ蓄積器
template<typename PacketType, typename SampleType>
struct BatchAccumulator {
    PacketType pkt;
    int count = 0;
    uint16_t seq = 0;

    void reset() { count = 0; }

    /// Add a sample. Returns pointer to the filled packet when batch is full,
    /// or nullptr if more samples needed.
    /// サンプルを追加。バッチが満杯なら送信可能なパケットへのポインタを返す。
    PacketType* addSample(const SampleType& sample, uint8_t packet_id) {
        pkt.samples[count] = sample;
        count++;

        if (count >= BATCH_SIZE) {
            // Fill header
            pkt.header.packet_id = packet_id;
            pkt.header.sequence = seq++;
            pkt.header.sample_count = BATCH_SIZE;

            // Compute checksum
            pkt.checksum = computeChecksum(&pkt, sizeof(PacketType));

            count = 0;
            return &pkt;
        }
        return nullptr;
    }
};

// =============================================================================
// UDP Log Server
// UDP ログサーバー
// =============================================================================

/// UDP telemetry log server for full-rate data streaming
/// フルレートデータストリーミング用 UDP テレメトリログサーバー
class UDPLogServer {
public:
    static UDPLogServer& getInstance() {
        static UDPLogServer instance;
        return instance;
    }

    /// Initialize the UDP log server (create socket, bind port)
    /// UDP ログサーバーを初期化（ソケット作成、ポートバインド）
    esp_err_t init();

    /// Check if a UDP log client is actively connected
    /// UDP ログクライアントがアクティブに接続されているか
    bool isActive() const { return active_.load(); }

    /// Send data to the registered client (fire-and-forget)
    /// 登録されたクライアントにデータを送信（送りっぱなし）
    /// @return bytes sent, or -1 on error
    int send(const void* data, size_t len);

    /// Check heartbeat timeout and deactivate if expired
    /// ハートビートタイムアウトをチェックし、期限切れなら非アクティブ化
    void checkHeartbeat();

private:
    UDPLogServer() = default;

    /// RX task: listens for start/stop/heartbeat commands from PC
    /// 受信タスク: PC からの開始/停止/ハートビートコマンドを待ち受け
    static void rxTask(void* arg);

    int sock_fd_ = -1;
    struct sockaddr_in client_addr_ = {};
    bool client_registered_ = false;
    std::atomic<bool> active_{false};
    uint32_t last_heartbeat_ms_ = 0;
    TaskHandle_t rx_task_handle_ = nullptr;
};

}  // namespace udp_telem
}  // namespace stampfly
