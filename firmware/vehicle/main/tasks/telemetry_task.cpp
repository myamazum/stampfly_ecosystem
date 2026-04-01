/**
 * @file telemetry_task.cpp
 * @brief Dual-mode telemetry: UDP full-data + WebSocket visualization
 *
 * デュアルモードテレメトリ: UDP フルデータ + WebSocket 可視化
 *
 * Architecture: Producer-Consumer with FreeRTOS queue
 * アーキテクチャ: FreeRTOS キューによる生産者-消費者パターン
 *
 *   IMU semaphore (400Hz)
 *     → TelemetryTask: read sensors, fill batches, enqueue (non-blocking)
 *
 *   TelemetrySendTask: dequeue and sendto() (blocking OK, isolated)
 *     → UDP or WebSocket depending on mode
 *
 * The send task runs independently so sendto() blocking (2-3ms)
 * never delays the telemetry data collection loop.
 * 送信タスクは独立して動くので、sendto() のブロック（2-3ms）が
 * テレメトリデータ収集ループを遅延させることはない。
 */

#include "tasks_common.hpp"
#include "sensor_fusion.hpp"
#include "udp_telemetry.hpp"
#include "esp_timer.h"

static const char* TAG = "TelemetryTask";

using namespace config;
using namespace globals;
using namespace stampfly::udp_telem;

// =============================================================================
// Send queue: decouples data collection from WiFi transmission
// 送信キュー: データ収集と WiFi 送信を分離
// =============================================================================

// Generic send item: packet type + data
// 汎用送信アイテム: パケット型 + データ
struct SendItem {
    uint8_t data[340];   // Max packet size (ImuEskfBatchPacket = 325B)
    uint16_t len;
};

static QueueHandle_t g_send_queue = nullptr;
static constexpr int SEND_QUEUE_SIZE = 16;

// =============================================================================
// Send task: dequeues and sends via UDP or WebSocket
// 送信タスク: キューから取り出して UDP または WebSocket で送信
// =============================================================================

static void TelemetrySendTask(void* pvParameters)
{
    ESP_LOGI(TAG, "TelemetrySendTask started");

    auto& telemetry = stampfly::Telemetry::getInstance();
    auto& udp_log = UDPLogServer::getInstance();

    SendItem item;
    static uint32_t udp_bytes_sent = 0;
    static uint32_t udp_stats_time = 0;

    while (true) {
        // Block until a packet is available
        // パケットが来るまでブロック
        if (xQueueReceive(g_send_queue, &item, portMAX_DELAY) != pdTRUE) {
            continue;
        }

        if (udp_log.isActive()) {
            int sent = udp_log.send(item.data, item.len);
            if (sent > 0) udp_bytes_sent += sent;
        }

        // Bandwidth stats (every 5 seconds)
        // 帯域統計（5秒ごと）
        uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000);
        if (now_ms - udp_stats_time > 5000) {
            if (udp_bytes_sent > 0) {
                float kbps = (float)udp_bytes_sent / 5.0f / 1024.0f;
                ESP_LOGI(TAG, "UDP: %.1f KB/s (%lu bytes/5s), queue free: %d/%d",
                         kbps, udp_bytes_sent,
                         (int)uxQueueSpacesAvailable(g_send_queue), SEND_QUEUE_SIZE);
                udp_bytes_sent = 0;
            }
            udp_stats_time = now_ms;
        }
    }
}

// =============================================================================
// Helper: enqueue a completed batch packet (non-blocking)
// ヘルパー: 完成したバッチパケットをキューに投入（ノンブロッキング）
// =============================================================================

static inline void enqueue(const void* pkt, size_t len)
{
    SendItem item;
    if (len > sizeof(item.data)) return;
    memcpy(item.data, pkt, len);
    item.len = (uint16_t)len;
    // Non-blocking: drop if queue full (better than blocking the 400Hz loop)
    // ノンブロッキング: キュー満杯ならドロップ（400Hzループのブロックより良い）
    xQueueSend(g_send_queue, &item, 0);
}

// =============================================================================
// Fill helpers
// 充填ヘルパー
// =============================================================================

static void fillImuEskf(ImuEskfSample& s, int read_idx, uint32_t ts)
{
    s.timestamp_us = ts;

    const auto& accel = g_accel_buf.raw_at(read_idx);
    const auto& gyro = g_gyro_buf.raw_at(read_idx);
    s.gyro_x = gyro.x;   s.gyro_y = gyro.y;   s.gyro_z = gyro.z;
    s.accel_x = accel.x;  s.accel_y = accel.y;  s.accel_z = accel.z;

    const auto& accel_raw = g_accel_raw_buf.raw_at(read_idx);
    const auto& gyro_raw = g_gyro_raw_buf.raw_at(read_idx);
    s.gyro_raw_x = gyro_raw.x;  s.gyro_raw_y = gyro_raw.y;  s.gyro_raw_z = gyro_raw.z;
    s.accel_raw_x = accel_raw.x; s.accel_raw_y = accel_raw.y; s.accel_raw_z = accel_raw.z;

    auto eskf_state = g_fusion.getESKF().getState();
    s.quat_w = eskf_state.orientation.w;
    s.quat_x = eskf_state.orientation.x;
    s.quat_y = eskf_state.orientation.y;
    s.quat_z = eskf_state.orientation.z;
    s.gyro_bias_x = static_cast<int16_t>(eskf_state.gyro_bias.x * 10000.0f);
    s.gyro_bias_y = static_cast<int16_t>(eskf_state.gyro_bias.y * 10000.0f);
    s.gyro_bias_z = static_cast<int16_t>(eskf_state.gyro_bias.z * 10000.0f);
    s.accel_bias_x = static_cast<int16_t>(eskf_state.accel_bias.x * 10000.0f);
    s.accel_bias_y = static_cast<int16_t>(eskf_state.accel_bias.y * 10000.0f);
    s.accel_bias_z = static_cast<int16_t>(eskf_state.accel_bias.z * 10000.0f);
}

static void fillPosVel(PosVelSample& s, uint32_t ts)
{
    s.timestamp_us = ts;
    auto eskf_state = g_fusion.getESKF().getState();
    s.pos_x = eskf_state.position.x;
    s.pos_y = eskf_state.position.y;
    s.pos_z = eskf_state.position.z;
    s.vel_x = eskf_state.velocity.x;
    s.vel_y = eskf_state.velocity.y;
    s.vel_z = eskf_state.velocity.z;
}

// =============================================================================
// Main telemetry task: collect data, fill batches, enqueue
// メインテレメトリタスク: データ収集、バッチ充填、キュー投入
// =============================================================================

void TelemetryTask(void* pvParameters)
{
    ESP_LOGI(TAG, "TelemetryTask started - producer-consumer mode");

    auto& telemetry = stampfly::Telemetry::getInstance();
    auto& state = stampfly::StampFlyState::getInstance();
    auto& udp_log = UDPLogServer::getInstance();

    // Create send queue and send task
    // 送信キューと送信タスクを作成
    g_send_queue = xQueueCreate(SEND_QUEUE_SIZE, sizeof(SendItem));
    if (!g_send_queue) {
        ESP_LOGE(TAG, "Failed to create send queue");
        vTaskDelete(nullptr);
        return;
    }

    xTaskCreatePinnedToCore(
        TelemetrySendTask,
        "TelemSend",
        4096,
        nullptr,
        10,    // Lower priority than telemetry collection
        nullptr,
        0      // Core 0 (protocol core)
    );

    // --- UDP mode: batch accumulators (static to save stack) ---
    static BatchAccumulator<ImuEskfBatchPacket, ImuEskfSample> imu_eskf_acc;
    static BatchAccumulator<PosVelBatchPacket, PosVelSample> pos_vel_acc;
    static BatchAccumulator<ControlBatchPacket, ControlSample> ctrl_acc;
    static BatchAccumulator<FlowBatchPacket, FlowSample> flow_acc;
    static BatchAccumulator<ToFBatchPacket, ToFSample> tof_acc;
    static BatchAccumulator<BaroBatchPacket, BaroSample> baro_acc;
    static BatchAccumulator<MagBatchPacket, MagSample> mag_acc;

    // --- WebSocket mode state ---
    stampfly::TelemetryExtendedBatchPacket ws_batch_pkt = {};
    int ws_batch_index = 0;
    int ws_decimation_counter = 0;
    constexpr int WS_DECIMATION = 8;  // 400/8 = 50Hz

    // --- Common state ---
    int telemetry_read_index = 0;
    uint32_t overrun_count = 0;

    // UDP control decimation
    int udp_cycle_counter = 0;

    // Timestamp-based sensor new-data detection (no flag race with imu_task)
    // タイムスタンプベースのセンサ新データ検出（imu_task とのフラグ競合なし）
    uint32_t last_flow_ts = 0;
    uint32_t last_tof_ts = 0;
    uint32_t last_baro_ts = 0;
    uint32_t last_mag_ts = 0;

    // Status packet counter (1Hz)
    int status_counter = 0;

    ESP_LOGI(TAG, "Send queue: %d items, send task on core 0", SEND_QUEUE_SIZE);

    // Wait for IMU to start populating the buffer
    vTaskDelay(pdMS_TO_TICKS(100));
    telemetry_read_index = g_accel_buf.raw_index();

    while (true) {
        // Wait for IMU update (400Hz)
        if (xSemaphoreTake(g_telemetry_imu_semaphore, pdMS_TO_TICKS(10)) != pdTRUE) {
            continue;
        }

        // Proactive catch-up
        {
            constexpr int MAX_LAG = 40;
            int head = g_accel_buf.raw_index();
            int lag = (head - telemetry_read_index + IMU_BUFFER_SIZE) % IMU_BUFFER_SIZE;
            if (lag > MAX_LAG) {
                telemetry_read_index = (head - 4 + IMU_BUFFER_SIZE) % IMU_BUFFER_SIZE;
                ws_batch_index = 0;
                imu_eskf_acc.reset();
                pos_vel_acc.reset();
            }
        }

        // Fallback overrun detection
        if (g_accel_buf.is_overrun(telemetry_read_index)) {
            overrun_count++;
            telemetry_read_index = g_accel_buf.safe_read_index(10);
        }

        uint32_t imu_ts = g_accel_raw_buf.raw_timestamp_at(telemetry_read_index);

        // =================================================================
        // UDP full-data mode
        // =================================================================
        if (udp_log.isActive()) {
            // Reset all accumulators on capture start to discard stale data
            // キャプチャ開始時に全アキュムレータをリセットして古いデータを破棄
            if (udp_log.consumeStartEvent()) {
                imu_eskf_acc.reset();
                pos_vel_acc.reset();
                ctrl_acc.reset();
                flow_acc.reset();
                tof_acc.reset();
                baro_acc.reset();
                mag_acc.reset();
                udp_cycle_counter = 0;
                status_counter = 0;
                // Drain send queue to discard any stale packets
                // 送信キューを空にして古いパケットを破棄
                SendItem dummy;
                while (xQueueReceive(g_send_queue, &dummy, 0) == pdTRUE) {}
                ESP_LOGI(TAG, "UDP capture started — accumulators reset");
            }

            udp_cycle_counter++;

            // --- 400Hz: IMU + ESKF → enqueue when batch full ---
            ImuEskfSample imu_sample;
            fillImuEskf(imu_sample, telemetry_read_index, imu_ts);
            auto* imu_pkt = imu_eskf_acc.addSample(imu_sample, PKT_IMU_ESKF);
            if (imu_pkt) enqueue(imu_pkt, sizeof(*imu_pkt));

            // --- 400Hz: Position + Velocity ---
            PosVelSample pv_sample;
            fillPosVel(pv_sample, imu_ts);
            auto* pv_pkt = pos_vel_acc.addSample(pv_sample, PKT_POS_VEL);
            if (pv_pkt) enqueue(pv_pkt, sizeof(*pv_pkt));

            // --- 50Hz: Control input ---
            if ((udp_cycle_counter & 7) == 0) {
                ControlSample ctrl_sample;
                ctrl_sample.timestamp_us = imu_ts;
                state.getControlInput(ctrl_sample.throttle, ctrl_sample.roll,
                                      ctrl_sample.pitch, ctrl_sample.yaw);
                auto* ctrl_pkt = ctrl_acc.addSample(ctrl_sample, PKT_CONTROL);
                if (ctrl_pkt) enqueue(ctrl_pkt, sizeof(*ctrl_pkt));
            }

            // --- Sensor data: timestamp change = new data ---

            // Optical Flow (~100Hz)
            {
                uint32_t ts = g_flow_last_timestamp_us;
                if (ts != last_flow_ts && ts != 0) {
                    last_flow_ts = ts;
                    FlowSample s;
                    s.timestamp_us = ts;
                    int16_t dx, dy; uint8_t sq;
                    state.getFlowRawData(dx, dy, sq);
                    s.flow_dx = dx; s.flow_dy = dy; s.quality = sq;
                    auto* pkt = flow_acc.addSample(s, PKT_FLOW);
                    if (pkt) enqueue(pkt, sizeof(*pkt));
                }
            }

            // ToF (~30Hz)
            {
                uint32_t ts = g_tof_last_timestamp_us;
                if (ts != last_tof_ts && ts != 0) {
                    last_tof_ts = ts;
                    ToFSample s;
                    s.timestamp_us = ts;
                    float tb, tf;
                    state.getToFData(tb, tf);
                    s.tof_bottom = tb; s.tof_front = tf;
                    uint8_t sb, sf_s;
                    state.getToFStatus(sb, sf_s);
                    s.status_bottom = sb; s.status_front = sf_s;
                    auto* pkt = tof_acc.addSample(s, PKT_TOF);
                    if (pkt) enqueue(pkt, sizeof(*pkt));
                }
            }

            // Barometer (~50Hz)
            {
                uint32_t ts = g_baro_last_timestamp_us;
                if (ts != last_baro_ts && ts != 0) {
                    last_baro_ts = ts;
                    BaroSample s;
                    s.timestamp_us = ts;
                    float ba, bp;
                    state.getBaroData(ba, bp);
                    s.altitude = ba; s.pressure = bp;
                    auto* pkt = baro_acc.addSample(s, PKT_BARO);
                    if (pkt) enqueue(pkt, sizeof(*pkt));
                }
            }

            // Magnetometer (~25Hz)
            {
                uint32_t ts = g_mag_last_timestamp_us;
                if (ts != last_mag_ts && ts != 0) {
                    last_mag_ts = ts;
                    MagSample s;
                    s.timestamp_us = ts;
                    stampfly::Vec3 mag_data;
                    state.getMagData(mag_data);
                    s.mag_x = mag_data.x; s.mag_y = mag_data.y; s.mag_z = mag_data.z;
                    auto* pkt = mag_acc.addSample(s, PKT_MAG);
                    if (pkt) enqueue(pkt, sizeof(*pkt));
                }
            }

            // --- 1Hz: Status ---
            if (++status_counter >= 400) {
                status_counter = 0;
                StatusPacket sp = {};
                sp.header.packet_id = PKT_STATUS;
                sp.header.sequence = 0;
                sp.header.sample_count = 1;
                sp.uptime_ms = (uint32_t)(esp_timer_get_time() / 1000);
                sp.voltage = state.getVoltage();
                sp.flight_state = static_cast<uint8_t>(state.getFlightState());
                sp.eskf_status = state.isESKFInitialized() ? 0x01 : 0x00;
                sp.checksum = computeChecksum(&sp, sizeof(sp));
                enqueue(&sp, sizeof(sp));
            }
        }
        // =================================================================
        // WebSocket visualization mode (low rate, 50Hz)
        // =================================================================
        else if (telemetry.hasClients()) {
            ws_decimation_counter++;
            if (ws_decimation_counter >= WS_DECIMATION) {
                ws_decimation_counter = 0;

                auto& sample = ws_batch_pkt.samples[ws_batch_index];
                sample.timestamp_us = esp_timer_get_time();

                const auto& accel = g_accel_buf.raw_at(telemetry_read_index);
                const auto& gyro = g_gyro_buf.raw_at(telemetry_read_index);
                sample.gyro_x = gyro.x;  sample.gyro_y = gyro.y;  sample.gyro_z = gyro.z;
                sample.accel_x = accel.x; sample.accel_y = accel.y; sample.accel_z = accel.z;

                stampfly::Vec3 ac, gc;
                state.getIMUCorrected(ac, gc);
                sample.gyro_corrected_x = gc.x;
                sample.gyro_corrected_y = gc.y;
                sample.gyro_corrected_z = gc.z;

                state.getControlInput(sample.ctrl_throttle, sample.ctrl_roll,
                                      sample.ctrl_pitch, sample.ctrl_yaw);

                auto eskf_state = g_fusion.getESKF().getState();
                sample.quat_w = eskf_state.orientation.w;
                sample.quat_x = eskf_state.orientation.x;
                sample.quat_y = eskf_state.orientation.y;
                sample.quat_z = eskf_state.orientation.z;
                sample.pos_x = eskf_state.position.x;
                sample.pos_y = eskf_state.position.y;
                sample.pos_z = eskf_state.position.z;
                sample.vel_x = eskf_state.velocity.x;
                sample.vel_y = eskf_state.velocity.y;
                sample.vel_z = eskf_state.velocity.z;
                sample.gyro_bias_x = static_cast<int16_t>(eskf_state.gyro_bias.x * 10000.0f);
                sample.gyro_bias_y = static_cast<int16_t>(eskf_state.gyro_bias.y * 10000.0f);
                sample.gyro_bias_z = static_cast<int16_t>(eskf_state.gyro_bias.z * 10000.0f);
                sample.accel_bias_x = static_cast<int16_t>(eskf_state.accel_bias.x * 10000.0f);
                sample.accel_bias_y = static_cast<int16_t>(eskf_state.accel_bias.y * 10000.0f);
                sample.accel_bias_z = static_cast<int16_t>(eskf_state.accel_bias.z * 10000.0f);
                sample.eskf_status = state.isESKFInitialized() ? 0x01 : 0x00;
                sample.accel_corrected_x = accel.x - eskf_state.accel_bias.x;
                sample.accel_corrected_y = accel.y - eskf_state.accel_bias.y;
                sample.accel_corrected_z = accel.z - eskf_state.accel_bias.z;
                memset(sample.padding1, 0, sizeof(sample.padding1));

                float ba, bp;
                state.getBaroData(ba, bp);
                sample.baro_altitude = ba;
                sample.baro_pressure = bp;

                float tb, tf;
                state.getToFData(tb, tf);
                sample.tof_bottom = tb;
                sample.tof_front = tf;
                uint8_t sb, sf_s;
                state.getToFStatus(sb, sf_s);
                sample.tof_bottom_status = sb;
                sample.tof_front_status = sf_s;

                int16_t fdx, fdy; uint8_t fsq;
                state.getFlowRawData(fdx, fdy, fsq);
                sample.flow_x = fdx; sample.flow_y = fdy; sample.flow_quality = fsq;

                sample.padding2 = 0;
                stampfly::Vec3 mag;
                state.getMagData(mag);
                sample.mag_x = mag.x; sample.mag_y = mag.y; sample.mag_z = mag.z;

                const auto& ar = g_accel_raw_buf.raw_at(telemetry_read_index);
                const auto& gr = g_gyro_raw_buf.raw_at(telemetry_read_index);
                sample.gyro_raw_x = gr.x;  sample.gyro_raw_y = gr.y;  sample.gyro_raw_z = gr.z;
                sample.accel_raw_x = ar.x;  sample.accel_raw_y = ar.y;  sample.accel_raw_z = ar.z;

                sample.imu_timestamp_us = imu_ts;
                sample.baro_timestamp_us = g_baro_last_timestamp_us;
                sample.tof_timestamp_us = g_tof_last_timestamp_us;
                sample.mag_timestamp_us = g_mag_last_timestamp_us;
                sample.flow_timestamp_us = g_flow_last_timestamp_us;
                sample.padding3 = 0;

                ws_batch_index++;
                if (ws_batch_index >= stampfly::FFT_BATCH_SIZE) {
                    ws_batch_pkt.header = 0xBD;
                    ws_batch_pkt.packet_type = 0x32;
                    ws_batch_pkt.sample_count = stampfly::FFT_BATCH_SIZE;
                    ws_batch_pkt.reserved = 0;

                    uint8_t checksum = 0;
                    const uint8_t* d = reinterpret_cast<const uint8_t*>(&ws_batch_pkt);
                    constexpr size_t co = offsetof(stampfly::TelemetryExtendedBatchPacket, checksum);
                    for (size_t i = 0; i < co; i++) checksum ^= d[i];
                    ws_batch_pkt.checksum = checksum;

                    telemetry.broadcast(&ws_batch_pkt, sizeof(ws_batch_pkt));
                    ws_batch_index = 0;
                }
            }
        }

        // Advance read index (always, regardless of mode)
        // 読み取りインデックスを進める（モードに関わらず常に）
        telemetry_read_index = (telemetry_read_index + 1) % IMU_BUFFER_SIZE;
    }
}
