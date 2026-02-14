# Lesson 4: IMU Sensor

## Goal / 目標
Read IMU (gyroscope + accelerometer) data and visualize via telemetry.

## API / 使用するAPI
| Function | Description | Unit |
|----------|-------------|------|
| `ws::gyro_x/y/z()` | Angular velocity | rad/s |
| `ws::accel_x/y/z()` | Linear acceleration | m/s^2 |
| `ws::telemetry_send(name, val)` | Send via WiFi | - |

## Coordinate System / 座標系
```
   X (forward)
   ^
   |
   +---> Y (right)
   |
   v Z (down, NED)
```

## Steps / 手順
1. `sf lesson switch 4`
2. Read and print gyro/accel values
3. Tilt the drone by hand and observe changes
4. Send values via telemetry: `sf log wifi`
5. Expected: accel_z ≈ 9.81 m/s^2 when flat

## Key Concepts / キーコンセプト
- BMI270 6-axis IMU (400Hz)
- NED (North-East-Down) coordinate system
- WiFi telemetry for real-time visualization
