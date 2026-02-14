#include "workshop_api.hpp"

void setup()
{
    ws::print("Lesson 3: LED Control");
}

void loop_400Hz(float dt)
{
    // TODO: Show ARM status with LED color
    // Green when armed, red when disarmed
    //
    // if (ws::is_armed()) {
    //     ws::led_color(0, 255, 0);  // Green
    // } else {
    //     ws::led_color(255, 0, 0);  // Red
    // }

    // TODO: (Challenge) Show battery voltage as color gradient
    // Low battery = red, full = green
}
