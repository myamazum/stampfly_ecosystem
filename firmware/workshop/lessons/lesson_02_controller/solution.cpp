#include "workshop_api.hpp"

static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 2: Controller Input - Solution");
}

void loop_400Hz(float dt)
{
    tick++;

    float throttle = ws::rc_throttle();
    float roll = ws::rc_roll();
    float pitch = ws::rc_pitch();
    float yaw = ws::rc_yaw();

    // Direct throttle-to-motor mapping (open loop)
    ws::motor_set_all(throttle);

    // Print values every 200ms
    if (tick % 80 == 0) {
        ws::print("T=%.2f R=%.2f P=%.2f Y=%.2f", throttle, roll, pitch, yaw);
    }
}
