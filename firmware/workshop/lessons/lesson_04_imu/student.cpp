#include "workshop_api.hpp"

void setup()
{
    ws::print("Lesson 4: IMU Sensor");
}

void loop_400Hz(float dt)
{
    // TODO: Read gyroscope values
    // float gx = ws::gyro_x();  // Roll rate [rad/s]
    // float gy = ws::gyro_y();  // Pitch rate [rad/s]
    // float gz = ws::gyro_z();  // Yaw rate [rad/s]

    // TODO: Read accelerometer values
    // float ax = ws::accel_x();  // Forward [m/s^2]
    // float ay = ws::accel_y();  // Right [m/s^2]
    // float az = ws::accel_z();  // Down [m/s^2] (≈9.81 when flat)

    // TODO: Send values via telemetry
    // ws::telemetry_send("gyro_x", gx);
    // ws::telemetry_send("gyro_y", gy);
    // ws::telemetry_send("gyro_z", gz);

    // TODO: Print values every 100ms (40 ticks)
}
