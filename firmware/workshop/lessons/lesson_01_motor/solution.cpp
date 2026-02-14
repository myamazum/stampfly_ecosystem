#include "workshop_api.hpp"

static uint32_t motor_timer = 0;
static int current_motor = 1;

void setup()
{
    ws::print("Lesson 1: Motor Control - Solution");
}

void loop_400Hz(float dt)
{
    // Cycle through motors: each motor spins for 2 seconds
    motor_timer++;

    // 400Hz * 2s = 800 ticks per motor
    int phase = (motor_timer / 800) % 4;
    current_motor = phase + 1;

    // Stop all motors first, then spin current one
    ws::motor_stop_all();
    ws::motor_set_duty(current_motor, 0.1f);

    // Print which motor is active every 2 seconds
    if (motor_timer % 800 == 0) {
        ws::print("Motor %d active", current_motor);
    }
}
