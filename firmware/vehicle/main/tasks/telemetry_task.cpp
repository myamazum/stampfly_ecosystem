/**
 * @file telemetry_task.cpp
 * @brief テレメトリタスク - 400Hz統一WebSocketブロードキャスト
 *
 * Unified 400Hz telemetry with extended data (ESKF estimates + sensors).
 * 400Hz統一テレメトリ（ESKF推定値 + センサデータ含む）
 *
 * Sends ExtendedSample batches (4 samples @ 100fps = 400Hz effective).
 * ExtendedSampleバッチ送信（4サンプル × 100fps = 実効400Hz）
 *
 * Synchronized with IMU task via semaphore to ensure unique samples.
 * セマフォでIMUタスクと同期し各サンプルがユニークなデータを保証。
 */

#include "tasks_common.hpp"
#include "sensor_fusion.hpp"

static const char* TAG = "TelemetryTask";

using namespace config;
using namespace globals;

void TelemetryTask(void* pvParameters)
{
    ESP_LOGI(TAG, "TelemetryTask started - 400Hz unified mode");

    auto& telemetry = stampfly::Telemetry::getInstance();
    auto& state = stampfly::StampFlyState::getInstance();

    // Extended batch packet (552 bytes)
    // 拡張バッチパケット（552バイト）
    stampfly::TelemetryExtendedBatchPacket batch_pkt = {};
    int batch_index = 0;

    // Read index for ring buffer
    // リングバッファ読み取りインデックス
    int telemetry_read_index = 0;

    // Send counter for debugging
    // デバッグ用送信カウンタ
    static uint32_t send_counter = 0;

    // Overrun tracking
    // オーバーラン追跡
    uint32_t overrun_count = 0;
    bool batch_has_gap = false;

    ESP_LOGI(TAG, "400Hz IMU-synced sampling, batch of %d, frame rate ~100Hz",
             stampfly::FFT_BATCH_SIZE);
    ESP_LOGI(TAG, "Extended packet: %d bytes/sample, %d bytes/batch",
             (int)sizeof(stampfly::ExtendedSample),
             (int)sizeof(stampfly::TelemetryExtendedBatchPacket));

    // Wait for IMU to start populating the buffer
    // IMUがバッファにデータを入れ始めるのを待つ
    vTaskDelay(pdMS_TO_TICKS(100));
    telemetry_read_index = g_accel_buf.raw_index();

    while (true) {
        // Wait for IMU update (400Hz, synchronized with IMU task)
        // IMU更新を待機（400Hz、IMUタスクと同期）
        if (xSemaphoreTake(g_telemetry_imu_semaphore, pdMS_TO_TICKS(10)) != pdTRUE) {
            // Timeout - IMU task might be stuck, skip this iteration
            continue;
        }

        // Detect ring buffer overrun: read_index lapped by writer
        // リングバッファオーバーラン検出: read_index がライターに追い越された
        if (g_accel_buf.is_overrun(telemetry_read_index)) {
            overrun_count++;
            batch_has_gap = true;
            int new_idx = g_accel_buf.safe_read_index(10);
            ESP_LOGW(TAG, "Ring buffer overrun #%lu, resetting read index %d→%d",
                     overrun_count, telemetry_read_index, new_idx);
            telemetry_read_index = new_idx;
        }

        // Get current sample slot
        // 現在のサンプルスロットを取得
        auto& sample = batch_pkt.samples[batch_index];

        // === Core sensor data (same as FFTSample) ===
        // コアセンサデータ（FFTSampleと同等）

        // Timestamp in microseconds for better precision
        // 高精度のためマイクロ秒タイムスタンプ
        sample.timestamp_us = esp_timer_get_time();

        // Read from ring buffer at current read index
        // リングバッファから現在の読み取りインデックスで読む
        const auto& accel = g_accel_buf.raw_at(telemetry_read_index);
        const auto& gyro = g_gyro_buf.raw_at(telemetry_read_index);

        // Raw gyro/accel (LPF only, no bias correction)
        // 生ジャイロ/加速度（LPFのみ、バイアス補正なし）
        sample.gyro_x = gyro.x;
        sample.gyro_y = gyro.y;
        sample.gyro_z = gyro.z;
        sample.accel_x = accel.x;
        sample.accel_y = accel.y;
        sample.accel_z = accel.z;

        // Bias-corrected gyro (what control loop sees)
        // バイアス補正済みジャイロ（制御ループが見る値）
        stampfly::Vec3 accel_corrected, gyro_corrected;
        state.getIMUCorrected(accel_corrected, gyro_corrected);
        sample.gyro_corrected_x = gyro_corrected.x;
        sample.gyro_corrected_y = gyro_corrected.y;
        sample.gyro_corrected_z = gyro_corrected.z;

        // Controller inputs (normalized)
        // コントローラ入力（正規化済み）
        state.getControlInput(sample.ctrl_throttle, sample.ctrl_roll,
                              sample.ctrl_pitch, sample.ctrl_yaw);

        // === ESKF estimates ===
        // ESKF推定値

        // Get ESKF state directly for quaternion access
        // クォータニオンアクセスのためESKF状態を直接取得
        auto& eskf = g_fusion.getESKF();
        auto eskf_state = eskf.getState();

        // Quaternion [w, x, y, z]
        sample.quat_w = eskf_state.orientation.w;
        sample.quat_x = eskf_state.orientation.x;
        sample.quat_y = eskf_state.orientation.y;
        sample.quat_z = eskf_state.orientation.z;

        // Position NED [m]
        sample.pos_x = eskf_state.position.x;
        sample.pos_y = eskf_state.position.y;
        sample.pos_z = eskf_state.position.z;

        // Velocity NED [m/s]
        sample.vel_x = eskf_state.velocity.x;
        sample.vel_y = eskf_state.velocity.y;
        sample.vel_z = eskf_state.velocity.z;

        // Gyro bias (scaled to int16: value * 10000)
        // ジャイロバイアス（int16スケール: 値×10000）
        sample.gyro_bias_x = static_cast<int16_t>(eskf_state.gyro_bias.x * 10000.0f);
        sample.gyro_bias_y = static_cast<int16_t>(eskf_state.gyro_bias.y * 10000.0f);
        sample.gyro_bias_z = static_cast<int16_t>(eskf_state.gyro_bias.z * 10000.0f);

        // Accel bias (scaled to int16: value * 10000)
        // 加速度バイアス（int16スケール: 値×10000）
        sample.accel_bias_x = static_cast<int16_t>(eskf_state.accel_bias.x * 10000.0f);
        sample.accel_bias_y = static_cast<int16_t>(eskf_state.accel_bias.y * 10000.0f);
        sample.accel_bias_z = static_cast<int16_t>(eskf_state.accel_bias.z * 10000.0f);

        // ESKF status: bit0 = initialized
        // ESKF状態: bit0 = 初期化済み
        sample.eskf_status = state.isESKFInitialized() ? 0x01 : 0x00;

        // Bias-corrected accel
        // バイアス補正済み加速度
        sample.accel_corrected_x = accel.x - eskf_state.accel_bias.x;
        sample.accel_corrected_y = accel.y - eskf_state.accel_bias.y;
        sample.accel_corrected_z = accel.z - eskf_state.accel_bias.z;

        // Clear padding
        sample.padding1[0] = 0;
        sample.padding1[1] = 0;
        sample.padding1[2] = 0;

        // === Additional sensor data ===
        // 追加センサデータ

        // Barometer
        // 気圧センサー
        float baro_alt, baro_press;
        state.getBaroData(baro_alt, baro_press);
        sample.baro_altitude = baro_alt;
        sample.baro_pressure = baro_press;

        // ToF distances and status
        // ToF距離とステータス
        float tof_bottom, tof_front;
        state.getToFData(tof_bottom, tof_front);
        sample.tof_bottom = tof_bottom;
        sample.tof_front = tof_front;

        uint8_t tof_bottom_status, tof_front_status;
        state.getToFStatus(tof_bottom_status, tof_front_status);
        sample.tof_bottom_status = tof_bottom_status;
        sample.tof_front_status = tof_front_status;

        // Optical flow raw data
        // 光学フロー生データ
        int16_t flow_dx, flow_dy;
        uint8_t flow_squal;
        state.getFlowRawData(flow_dx, flow_dy, flow_squal);
        sample.flow_x = flow_dx;
        sample.flow_y = flow_dy;
        sample.flow_quality = flow_squal;

        // Magnetometer (calibrated, body frame NED)
        // 地磁気（キャリブレーション済み、機体座標系NED）
        sample.padding2 = 0;
        stampfly::Vec3 mag_data;
        state.getMagData(mag_data);
        sample.mag_x = mag_data.x;
        sample.mag_y = mag_data.y;
        sample.mag_z = mag_data.z;

        // Raw IMU (pre-LPF)
        // LPF前のIMU生値
        const auto& accel_raw = g_accel_raw_buf.raw_at(telemetry_read_index);
        const auto& gyro_raw = g_gyro_raw_buf.raw_at(telemetry_read_index);
        sample.gyro_raw_x = gyro_raw.x;
        sample.gyro_raw_y = gyro_raw.y;
        sample.gyro_raw_z = gyro_raw.z;
        sample.accel_raw_x = accel_raw.x;
        sample.accel_raw_y = accel_raw.y;
        sample.accel_raw_z = accel_raw.z;

        // Internal timestamps
        // 内部タイムスタンプ
        // Guard against ring buffer read-ahead: ensure monotonically increasing
        // リングバッファの読み越し防止: 単調増加を保証
        {
            uint32_t imu_ts = g_accel_raw_buf.raw_timestamp_at(telemetry_read_index);
            static uint32_t last_imu_ts = 0;
            if (imu_ts >= last_imu_ts) {
                last_imu_ts = imu_ts;
            } else {
                imu_ts = last_imu_ts;  // Use previous if non-monotonic
            }
            sample.imu_timestamp_us = imu_ts;
        }
        sample.baro_timestamp_us = g_baro_last_timestamp_us;
        sample.tof_timestamp_us = g_tof_last_timestamp_us;
        sample.mag_timestamp_us = g_mag_last_timestamp_us;
        sample.flow_timestamp_us = g_flow_last_timestamp_us;
        sample.padding3 = 0;

        // Advance read index (ring buffer wrap)
        // 読み取りインデックスを進める（リングバッファ循環）
        telemetry_read_index = (telemetry_read_index + 1) % IMU_BUFFER_SIZE;

        batch_index++;

        // Send when batch is full (4 samples)
        // バッチが満杯（4サンプル）になったら送信
        if (batch_index >= stampfly::FFT_BATCH_SIZE) {
            if (telemetry.hasClients()) {
                // Rate control: log mode = every frame (100fps=400Hz),
                // browser only = every 8th frame (12.5fps≈50Hz)
                // レート制御: ログモード=全フレーム(100fps=400Hz),
                // ブラウザのみ=8フレームに1回(12.5fps≈50Hz)
                bool should_send = telemetry.isLogModeActive()
                                 || (send_counter % 8 == 0);

                if (should_send) {
                    // Fill header
                    batch_pkt.header = 0xBD;  // Extended batch packet
                    batch_pkt.packet_type = 0x32;
                    batch_pkt.sample_count = stampfly::FFT_BATCH_SIZE;
                    // Gap marker: bit0 = data gap due to ring buffer overrun
                    // 欠損マーカー: bit0 = リングバッファオーバーランによるデータ欠損
                    batch_pkt.reserved = batch_has_gap ? 0x01 : 0x00;
                    batch_has_gap = false;  // Reset for next batch

                    // Calculate checksum (XOR of bytes before checksum)
                    // チェックサム計算（checksum前のバイトのXOR）
                    uint8_t checksum = 0;
                    const uint8_t* data = reinterpret_cast<const uint8_t*>(&batch_pkt);
                    constexpr size_t checksum_offset = offsetof(stampfly::TelemetryExtendedBatchPacket, checksum);
                    for (size_t i = 0; i < checksum_offset; i++) {
                        checksum ^= data[i];
                    }
                    batch_pkt.checksum = checksum;

                    telemetry.broadcast(&batch_pkt, sizeof(batch_pkt));
                }
                send_counter++;
            }

            // Reset batch index
            batch_index = 0;
        }

        // No vTaskDelayUntil - timing controlled by IMU semaphore
        // vTaskDelayUntilなし - タイミングはIMUセマフォで制御
    }
}
