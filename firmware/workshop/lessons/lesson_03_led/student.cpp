#include "workshop_api.hpp"

// =========================================================================
// Lesson 3: LED Control
// レッスン 3: LED制御
// =========================================================================
//
// Goal: Display flight state using LED color.
// 目標: LEDの色で飛行状態を表示する
//
// ws::led_color(r, g, b) - Set LED color (0-255)
// ws::is_armed()         - Check ARM state
// ws::battery_voltage()  - Get battery voltage (V)

void setup()
{
    ws::print("Lesson 3: LED Control");
}

void loop_400Hz(float dt)
{
    // TODO: Show ARM status with LED color
    // TODO: ARM状態をLEDの色で表示する
    // ARM時 = 緑、非ARM時 = 赤
    //
    // if (ws::is_armed()) {
    //     ws::led_color(0, 255, 0);   // Green / 緑
    // } else {
    //     ws::led_color(255, 0, 0);   // Red / 赤
    // }

    // TODO: (Challenge) Show battery voltage as color gradient
    // TODO: (チャレンジ) バッテリー電圧を色のグラデーションで表示
    // Low battery = red, full = green
    // 低電圧 = 赤、満充電 = 緑
}
