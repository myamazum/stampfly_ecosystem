#include "workshop_api.hpp"
#include "stampfly_state.hpp"
#include <cmath>

// Tick counter for decimation
// デシメーション用のtickカウンタ
static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 10: API Overview & App Development");

    // TODO: Set your WiFi channel (1, 6, or 11)
    // TODO: 自分のWiFiチャンネルを設定する（1, 6, 11のいずれか）
    // ws::set_channel(1);
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

    // TODO: Get barometric data and output as Teleplot
    // TODO: 気圧データを取得してTeleplot形式で出力
    // auto baro = state.getBaroData();
    // ws::print(">baro_alt:%.2f", baro.altitude);

    // TODO: Get ToF (Time-of-Flight) distance
    // TODO: ToF距離を取得
    // auto tof = state.getToFData(ToFPosition::BOTTOM);
    // ws::print(">tof_bottom:%.3f", tof.distance);

    // TODO: Compare barometric altitude with ws::estimated_altitude()
    // TODO: 気圧高度とws::estimated_altitude()を比較
    // ws::print(">eskf_alt:%.2f", ws::estimated_altitude());

    // TODO: Get magnetic data and compute heading
    // TODO: 磁気データを取得して方位角を計算
    // auto mag = state.getMagData();
    // float heading = atan2f(-mag.y, mag.x) * 57.3f;
    // ws::print(">heading:%.1f", heading);

    // TODO: Get optical flow velocity
    // TODO: 光学フロー速度を取得
    // auto flow = state.getFlowData();
    // ws::print(">flow_vx:%.3f", flow.vx);
    // ws::print(">flow_vy:%.3f", flow.vy);

    // TODO: Get battery voltage
    // TODO: バッテリ電圧を取得
    // ws::print(">voltage:%.2f", ws::battery_voltage());
}
