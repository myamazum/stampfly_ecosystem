#include "workshop_api.hpp"

static uint32_t tick = 0;

void setup()
{
    ws::print("Lesson 4: IMU Sensor - Solution");
}

void loop_400Hz(float dt)
{
    tick++;

    float gx = ws::gyro_x();
    float gy = ws::gyro_y();
    float gz = ws::gyro_z();
    float ax = ws::accel_x();
    float ay = ws::accel_y();
    float az = ws::accel_z();

    // Send via WiFi telemetry (viewable with sf log wifi)
    ws::telemetry_send("gyro_x", gx);
    ws::telemetry_send("gyro_y", gy);
    ws::telemetry_send("gyro_z", gz);
    ws::telemetry_send("accel_z", az);

    // Print every 100ms
    if (tick % 40 == 0) {
        ws::print("G=(%.3f,%.3f,%.3f) A=(%.2f,%.2f,%.2f)",
                  gx, gy, gz, ax, ay, az);
    }
}
