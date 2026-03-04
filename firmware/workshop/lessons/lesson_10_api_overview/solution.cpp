#include "workshop_api.hpp"
#include "stampfly_state.hpp"
#include <cmath>

// Tick counter for decimation
// デシメーション用のtickカウンタ
static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 10: API Overview & App Development - Solution");

    // Set WiFi channel (use 1, 6, or 11 to avoid interference)
    // WiFiチャンネルを設定（混信を避けるため1, 6, 11のいずれかを使用）
    ws::set_channel(1);
}

void loop_400Hz(float dt)
{
    tick++;

    // Decimation: output at 50 Hz (every 8 ticks at 400 Hz)
    // デシメーション: 50Hz出力（400Hzの8tick毎）
    if (tick % 8 != 0) return;

    // Get StampFlyState singleton
    // StampFlyStateシングルトンを取得
    auto& state = StampFlyState::getInstance();

    // Barometric data / 気圧データ
    auto baro = state.getBaroData();
    ws::print(">baro_alt:%.2f", baro.altitude);

    // ToF (Time-of-Flight) distance / ToF距離
    auto tof_bottom = state.getToFData(ToFPosition::BOTTOM);
    auto tof_front  = state.getToFData(ToFPosition::FRONT);
    ws::print(">tof_bottom:%.3f", tof_bottom.distance);
    ws::print(">tof_front:%.3f", tof_front.distance);

    // ESKF estimated altitude for comparison
    // 比較用のESKF推定高度
    ws::print(">eskf_alt:%.2f", ws::estimated_altitude());

    // Magnetic data and heading / 磁気データと方位角
    auto mag = state.getMagData();
    ws::print(">mag_x:%.1f", mag.x);
    ws::print(">mag_y:%.1f", mag.y);
    ws::print(">mag_z:%.1f", mag.z);
    float heading = atan2f(-mag.y, mag.x) * 57.3f;
    ws::print(">heading:%.1f", heading);

    // Optical flow velocity / 光学フロー速度
    auto flow = state.getFlowData();
    ws::print(">flow_vx:%.3f", flow.vx);
    ws::print(">flow_vy:%.3f", flow.vy);

    // Battery voltage / バッテリ電圧
    ws::print(">voltage:%.2f", ws::battery_voltage());
}
