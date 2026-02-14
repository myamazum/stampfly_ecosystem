#include "workshop_api.hpp"

void setup()
{
    ws::print("Lesson 3: LED Control - Solution");
}

void loop_400Hz(float dt)
{
    if (ws::is_armed()) {
        // Armed: green
        ws::led_color(0, 255, 0);
    } else {
        // Disarmed: show battery level as color gradient
        float vbat = ws::battery_voltage();
        // Map 3.3V-4.2V to 0-1 range
        float level = (vbat - 3.3f) / (4.2f - 3.3f);
        if (level < 0.0f) level = 0.0f;
        if (level > 1.0f) level = 1.0f;

        uint8_t r = (uint8_t)(255 * (1.0f - level));
        uint8_t g = (uint8_t)(255 * level);
        ws::led_color(r, g, 0);
    }
}
