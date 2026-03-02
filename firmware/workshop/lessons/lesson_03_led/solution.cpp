#include "workshop_api.hpp"

// =========================================================================
// Lesson 3: LED Control - Solution
// レッスン 3: LED制御 - 解答
// =========================================================================

void setup()
{
    ws::print("Lesson 3: LED Control - Solution");

    // Disable system LED updates so ws::led_color() takes effect
    // システムLED更新を無効化して ws::led_color() が反映されるようにする
    ws::disable_led_task();

    // Set WiFi channel (use 1, 6, or 11 to avoid interference)
    // WiFiチャンネルを設定（混信を避けるため1, 6, 11のいずれかを使用）
    ws::set_channel(1);
}

void loop_400Hz(float dt)
{
    if (ws::is_armed()) {
        // Armed: green
        // ARM時: 緑
        ws::led_color(0, 255, 0);
    } else {
        // Disarmed: show battery level as color gradient
        // 非ARM時: バッテリー残量を色のグラデーションで表示
        float vbat = ws::battery_voltage();

        // Map 3.3V-4.2V to 0-1 range
        // 3.3V〜4.2V を 0〜1 の範囲にマッピング
        float level = (vbat - 3.3f) / (4.2f - 3.3f);
        if (level < 0.0f) level = 0.0f;
        if (level > 1.0f) level = 1.0f;

        // Red = low battery, green = full
        // 赤 = 低電圧、緑 = 満充電
        uint8_t r = (uint8_t)(255 * (1.0f - level));
        uint8_t g = (uint8_t)(255 * level);
        ws::led_color(r, g, 0);
    }
}
