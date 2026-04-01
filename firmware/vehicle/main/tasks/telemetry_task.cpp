/**
 * @file telemetry_task.cpp
 * @brief Dual-mode telemetry task: UDP full-data + WebSocket visualization
 *
 * デュアルモードテレメトリタスク: UDP フルデータ + WebSocket 可視化
 *
 * Mode 1 (default): WebSocket low-rate for browser visualization
 * Mode 2 (sf log wifi): UDP sensor-independent packets at native rates
 *
 * モード1（デフォルト）: WebSocket 低レートでブラウザ可視化
 * モード2（sf log wifi）: UDP センサ独立パケットを固有レートで送信
 *
 * Synchronized with IMU task via semaphore (400Hz).
 * セマフォでIMUタスクと同期（400Hz）。
 */

#include "tasks_common.hpp"
#include "sensor_fusion.hpp"
#include "udp_telemetry.hpp"

static const char* TAG = "TelemetryTask";

using namespace config;
using namespace globals;
using namespace stampfly::udp_telem;

// =============================================================================
// UDP mode: fill sensor samples from current state
// UDP モード: 現在の状態からセンササンプルを充填
// =============================================================================

/// Fill IMU+ESKF sample from ring buffer and ESKF state
/// リングバッファとESKF状態からIMU+ESKFサンプルを充填
static void fillImuEskf(ImuEskfSample& s, int read_idx, uint32_t ts)
{
    s.timestamp_us = ts;

    // IMU LPF filtered
    const auto& accel = g_accel_buf.raw_at(read_idx);
    const auto& gyro = g_gyro_buf.raw_at(read_idx);
    s.gyro_x = gyro.x;   s.gyro_y = gyro.y;   s.gyro_z = gyro.z;
    s.accel_x = accel.x;  s.accel_y = accel.y;  s.accel_z = accel.z;

    // IMU raw (pre-LPF)
    const auto& accel_raw = g_accel_raw_buf.raw_at(read_idx);
    const auto& gyro_raw = g_gyro_raw_buf.raw_at(read_idx);
    s.gyro_raw_x = gyro_raw.x;  s.gyro_raw_y = gyro_raw.y;  s.gyro_raw_z = gyro_raw.z;
    s.accel_raw_x = accel_raw.x; s.accel_raw_y = accel_raw.y; s.accel_raw_z = accel_raw.z;

    // ESKF attitude + bias
    auto& eskf = g_fusion.getESKF();
    auto eskf_state = eskf.getState();
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

/// Fill Position+Velocity sample from ESKF state
/// ESKF状態から位置+速度サンプルを充填
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
// Telemetry Task
// =============================================================================

void TelemetryTask(void* pvParameters)
{
    ESP_LOGI(TAG, "TelemetryTask started - dual mode (UDP/WebSocket)");

    auto& telemetry = stampfly::Telemetry::getInstance();
    auto& state = stampfly::StampFlyState::getInstance();
    auto& udp_log = UDPLogServer::getInstance();

    // --- WebSocket mode state ---
    stampfly::TelemetryExtendedBatchPacket ws_batch_pkt = {};
    int ws_batch_index = 0;
    static uint32_t ws_send_counter = 0;

    // --- UDP mode: batch accumulators ---
    // static to avoid stack overflow (WiFi CLI task has limited stack)
    static BatchAccumulator<ImuEskfBatchPacket, ImuEskfSample> imu_eskf_acc;
    static BatchAccumulator<PosVelBatchPacket, PosVelSample> pos_vel_acc;
    static BatchAccumulator<ControlBatchPacket, ControlSample> ctrl_acc;
    static BatchAccumulator<FlowBatchPacket, FlowSample> flow_acc;
    static BatchAccumulator<ToFBatchPacket, ToFSample> tof_acc;
    static BatchAccumulator<BaroBatchPacket, BaroSample> baro_acc;
    static BatchAccumulator<MagBatchPacket, MagSample> mag_acc;

    // --- Common state ---
    int telemetry_read_index = 0;
    uint32_t overrun_count = 0;

    // Counters for WebSocket decimation (400Hz → 10-50Hz)
    // WebSocket 間引きカウンタ（400Hz → 10-50Hz）
    int ws_decimation_counter = 0;
    constexpr int WS_DECIMATION = 8;  // 400/8 = 50Hz

    // UDP mode: cycle counter for control input decimation (400Hz → 50Hz)
    // UDP モード: 制御入力間引き用サイクルカウンタ
    int udp_cycle_counter = 0;

    // Status packet counter (1Hz)
    int status_counter = 0;

    // Last-seen timestamps for sensor data_ready detection (no flag race)
    // センサ新データ検出用の前回タイムスタンプ（フラグ競合なし）
    uint32_t last_flow_ts = 0;
    uint32_t last_tof_ts = 0;
    uint32_t last_baro_ts = 0;
    uint32_t last_mag_ts = 0;

    // Bandwidth monitoring
    static uint32_t udp_bytes_sent = 0;
    static uint32_t udp_stats_time = 0;

    ESP_LOGI(TAG, "Modes: UDP (port %d) / WebSocket (port 80)", UDP_LOG_PORT);

    // Wait for IMU to start populating the buffer
    // IMUがバッファにデータを入れ始めるのを待つ
    vTaskDelay(pdMS_TO_TICKS(100));
    telemetry_read_index = g_accel_buf.raw_index();

    while (true) {
        // Wait for IMU update (400Hz, synchronized with IMU task)
        // IMU更新を待機（400Hz、IMUタスクと同期）
        if (xSemaphoreTake(g_telemetry_imu_semaphore, pdMS_TO_TICKS(10)) != pdTRUE) {
            continue;
        }

        // Proactive catch-up: limit max lag to prevent large data gaps
        // プロアクティブ追いつき: 大きなデータ欠損を防ぐため最大遅延を制限
        {
            constexpr int MAX_LAG = 40;
            int head = g_accel_buf.raw_index();
            int lag = (head - telemetry_read_index + IMU_BUFFER_SIZE) % IMU_BUFFER_SIZE;
            if (lag > MAX_LAG) {
                int new_idx = (head - 4 + IMU_BUFFER_SIZE) % IMU_BUFFER_SIZE;
                telemetry_read_index = new_idx;
                ws_batch_index = 0;
                imu_eskf_acc.reset();
                pos_vel_acc.reset();
            }
        }

        // Fallback overrun detection
        // フォールバックオーバーラン検出
        if (g_accel_buf.is_overrun(telemetry_read_index)) {
            overrun_count++;
            telemetry_read_index = g_accel_buf.safe_read_index(10);
        }

        // Get IMU timestamp
        // IMU タイムスタンプ取得
        uint32_t imu_ts = g_accel_raw_buf.raw_timestamp_at(telemetry_read_index);

        // =================================================================
        // UDP full-data mode
        // UDP フルデータモード
        // =================================================================
        if (udp_log.isActive()) {

            udp_cycle_counter++;

            // --- 400Hz: IMU + ESKF ---
            // Accumulate sample every cycle, sendto only when batch full
            // 毎サイクルサンプル蓄積、バッチ満杯時のみ sendto
            ImuEskfSample imu_sample;
            fillImuEskf(imu_sample, telemetry_read_index, imu_ts);
            auto* imu_pkt = imu_eskf_acc.addSample(imu_sample, PKT_IMU_ESKF);

            // --- 400Hz: Position + Velocity ---
            PosVelSample pv_sample;
            fillPosVel(pv_sample, imu_ts);
            auto* pv_pkt = pos_vel_acc.addSample(pv_sample, PKT_POS_VEL);

            // Send IMU and PosVel batches when ready
            // Stagger sends: IMU on even cycles, PosVel on odd to avoid
            // two consecutive sendto() calls blocking for ~5ms total
            // 送信をずらす: 偶数サイクルで IMU、奇数で PosVel（連続 sendto 回避）
            if (imu_pkt) {
                int sent = udp_log.send(imu_pkt, sizeof(*imu_pkt));
                if (sent > 0) udp_bytes_sent += sent;
            }
            if (pv_pkt) {
                // PosVel batch fires at the same time as IMU batch (every 4th cycle).
                // Delay send to next cycle to avoid double sendto blocking.
                // PosVel は IMU と同時にバッチ完了するため、送信を分散できない。
                // やむなく連続送信するが、バッチ化で頻度は 100Hz（10ms間隔）なので
                // 2回の sendto (~4-6ms) は 10ms 周期内に収まる。
                int sent = udp_log.send(pv_pkt, sizeof(*pv_pkt));
                if (sent > 0) udp_bytes_sent += sent;
            }

            // --- 50Hz: Control input (every 8th cycle) ---
            if ((udp_cycle_counter & 7) == 0) {
                ControlSample ctrl_sample;
                ctrl_sample.timestamp_us = imu_ts;
                state.getControlInput(ctrl_sample.throttle, ctrl_sample.roll,
                                      ctrl_sample.pitch, ctrl_sample.yaw);
                auto* ctrl_pkt = ctrl_acc.addSample(ctrl_sample, PKT_CONTROL);
                if (ctrl_pkt) {
                    int sent = udp_log.send(ctrl_pkt, sizeof(*ctrl_pkt));
                    if (sent > 0) udp_bytes_sent += sent;
                }
            }

            // --- Sensor data: detect new data via timestamp change ---
            // --- (avoids race condition with imu_task's data_ready flags) ---
            // センサデータ: タイムスタンプ変化で新データを検出
            // （imu_task の data_ready フラグとの競合を回避）

            // Optical Flow (~100Hz)
            {
                uint32_t ts = g_flow_last_timestamp_us;
                if (ts != last_flow_ts && ts != 0) {
                    last_flow_ts = ts;
                    FlowSample flow_sample;
                    flow_sample.timestamp_us = ts;
                    int16_t dx, dy;
                    uint8_t sq;
                    state.getFlowRawData(dx, dy, sq);
                    flow_sample.flow_dx = dx;
                    flow_sample.flow_dy = dy;
                    flow_sample.quality = sq;
                    auto* flow_pkt = flow_acc.addSample(flow_sample, PKT_FLOW);
                    if (flow_pkt) {
                        int sent = udp_log.send(flow_pkt, sizeof(*flow_pkt));
                        if (sent > 0) udp_bytes_sent += sent;
                    }
                }
            }

            // ToF (~30Hz)
            {
                uint32_t ts = g_tof_last_timestamp_us;
                if (ts != last_tof_ts && ts != 0) {
                    last_tof_ts = ts;
                    ToFSample tof_sample;
                    tof_sample.timestamp_us = ts;
                    float tb, tf;
                    state.getToFData(tb, tf);
                    tof_sample.tof_bottom = tb;
                    tof_sample.tof_front = tf;
                    uint8_t sb, sf_s;
                    state.getToFStatus(sb, sf_s);
                    tof_sample.status_bottom = sb;
                    tof_sample.status_front = sf_s;
                    auto* tof_pkt = tof_acc.addSample(tof_sample, PKT_TOF);
                    if (tof_pkt) {
                        int sent = udp_log.send(tof_pkt, sizeof(*tof_pkt));
                        if (sent > 0) udp_bytes_sent += sent;
                    }
                }
            }

            // Barometer (~50Hz)
            {
                uint32_t ts = g_baro_last_timestamp_us;
                if (ts != last_baro_ts && ts != 0) {
                    last_baro_ts = ts;
                    BaroSample baro_sample;
                    baro_sample.timestamp_us = ts;
                    float ba, bp;
                    state.getBaroData(ba, bp);
                    baro_sample.altitude = ba;
                    baro_sample.pressure = bp;
                    auto* baro_pkt = baro_acc.addSample(baro_sample, PKT_BARO);
                    if (baro_pkt) {
                        int sent = udp_log.send(baro_pkt, sizeof(*baro_pkt));
                        if (sent > 0) udp_bytes_sent += sent;
                    }
                }
            }

            // Magnetometer (~25Hz)
            {
                uint32_t ts = g_mag_last_timestamp_us;
                if (ts != last_mag_ts && ts != 0) {
                    last_mag_ts = ts;
                    MagSample mag_sample;
                    mag_sample.timestamp_us = ts;
                    stampfly::Vec3 mag_data;
                    state.getMagData(mag_data);
                    mag_sample.mag_x = mag_data.x;
                    mag_sample.mag_y = mag_data.y;
                    mag_sample.mag_z = mag_data.z;
                    auto* mag_pkt = mag_acc.addSample(mag_sample, PKT_MAG);
                    if (mag_pkt) {
                        int sent = udp_log.send(mag_pkt, sizeof(*mag_pkt));
                        if (sent > 0) udp_bytes_sent += sent;
                    }
                }
            }

            // --- 1Hz: Status packet ---
            if (++status_counter >= 400) {
                status_counter = 0;
                StatusPacket status_pkt = {};
                status_pkt.header.packet_id = PKT_STATUS;
                status_pkt.header.sequence = 0;
                status_pkt.header.sample_count = 1;
                status_pkt.uptime_ms = (uint32_t)(esp_timer_get_time() / 1000);
                status_pkt.voltage = state.getVoltage();
                status_pkt.flight_state = static_cast<uint8_t>(state.getFlightState());
                status_pkt.eskf_status = state.isESKFInitialized() ? 0x01 : 0x00;
                status_pkt.checksum = computeChecksum(&status_pkt, sizeof(status_pkt));
                udp_log.send(&status_pkt, sizeof(status_pkt));
            }

            // --- Bandwidth stats (every 5 seconds) ---
            uint32_t now_ms = (uint32_t)(esp_timer_get_time() / 1000);
            if (now_ms - udp_stats_time > 5000) {
                float kbps = (float)udp_bytes_sent / 5.0f / 1024.0f;
                ESP_LOGI(TAG, "UDP: %.1f KB/s (%lu bytes/5s)",
                         kbps, udp_bytes_sent);
                udp_bytes_sent = 0;
                udp_stats_time = now_ms;
            }
        }
        // =================================================================
        // WebSocket visualization mode (low rate)
        // WebSocket 可視化モード（低レート）
        // =================================================================
        else if (telemetry.hasClients()) {
            ws_decimation_counter++;
            if (ws_decimation_counter >= WS_DECIMATION) {
                ws_decimation_counter = 0;

                // Reuse existing ExtendedSample format for WebSocket
                // WebSocket 用に既存の ExtendedSample フォーマットを再利用
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

                int16_t fdx, fdy;
                uint8_t fsq;
                state.getFlowRawData(fdx, fdy, fsq);
                sample.flow_x = fdx;
                sample.flow_y = fdy;
                sample.flow_quality = fsq;

                sample.padding2 = 0;
                stampfly::Vec3 mag;
                state.getMagData(mag);
                sample.mag_x = mag.x;
                sample.mag_y = mag.y;
                sample.mag_z = mag.z;

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
                    const uint8_t* data = reinterpret_cast<const uint8_t*>(&ws_batch_pkt);
                    constexpr size_t co = offsetof(stampfly::TelemetryExtendedBatchPacket, checksum);
                    for (size_t i = 0; i < co; i++) checksum ^= data[i];
                    ws_batch_pkt.checksum = checksum;

                    telemetry.broadcast(&ws_batch_pkt, sizeof(ws_batch_pkt));
                    ws_send_counter++;
                    ws_batch_index = 0;
                }
            }
        }

        // Advance read index
        // 読み取りインデックスを進める
        telemetry_read_index = (telemetry_read_index + 1) % IMU_BUFFER_SIZE;
    }
}
