# Lesson 10: API Overview & App Development

## Goal / 目標
Understand the full ws:: API, access all sensors via StampFlyState, and create a custom firmware project.

ws:: API の全体像を理解し、StampFlyState で全センサにアクセスし、独自ファームウェアプロジェクトを作成する。

## API / 使用するAPI

### ws:: API (Workshop wrapper)
| Function | Description | Unit |
|----------|-------------|------|
| `ws::gyro_x/y/z()` | Angular velocity | rad/s |
| `ws::accel_x/y/z()` | Linear acceleration | m/s^2 |
| `ws::estimated_roll/pitch/yaw()` | ESKF attitude estimate | rad |
| `ws::estimated_altitude()` | ESKF altitude estimate | m |
| `ws::battery_voltage()` | Battery voltage | V |
| `ws::print(fmt, ...)` | Serial print (Teleplot compatible) | - |

### StampFlyState (Direct sensor access)
| Method | Sensor | Data |
|--------|--------|------|
| `getBaroData()` | BMP280 Barometer | altitude [m], pressure [Pa] |
| `getMagData()` | BMM150 Magnetometer | x, y, z [uT] |
| `getToFData(pos)` | VL53L3CX ToF | distance [m] |
| `getFlowData()` | PMW3901 Optical Flow | vx, vy [m/s] |
| `getFlowRawData()` | PMW3901 Raw | delta_x, delta_y, squal |
| `getPowerData()` | Power monitor | voltage [V], current [A] |

## Hardware Sensors / ハードウェアセンサ

| Sensor | Model | Sample Rate | Measurement |
|--------|-------|-------------|-------------|
| IMU | BMI270 | 400 Hz | Acceleration + Gyroscope |
| Barometer | BMP280 | 50 Hz | Pressure → Altitude |
| Magnetometer | BMM150 | 10-30 Hz | Magnetic vector |
| ToF (bottom) | VL53L3CX | 30 Hz | Ground distance (0-2 m) |
| ToF (front) | VL53L3CX | 30 Hz | Front distance (0-2 m) |
| Optical Flow | PMW3901 | 100 Hz | Ground-relative velocity |

## Custom Firmware Project / カスタムファームウェアプロジェクト

### Create with sf app new / sf app new で作成

```bash
# Create new project / 新しいプロジェクトを作成
sf app new my_sensor_app

# Build and flash / ビルドして書き込み
sf build my_sensor_app
sf flash my_sensor_app -m
```

This creates `firmware/my_sensor_app/` with access to all vehicle components via `EXTRA_COMPONENT_DIRS`.

### Project Structure / プロジェクト構成
```
firmware/my_sensor_app/
├── CMakeLists.txt       # References vehicle/components and common
├── sdkconfig.defaults   # Hardware config (from vehicle)
├── partitions.csv       # Flash partitions (from vehicle)
└── main/
    ├── CMakeLists.txt   # Component registration
    └── main.cpp         # Your custom entry point
```

## Steps / 手順

### Workshop version (sf lesson switch 10) / ワークショップ版
1. `sf lesson switch 10`
2. Uncomment the StampFlyState sensor access code in `user_code.cpp`
3. Build and flash: `sf lesson build` → `sf lesson flash`
4. Open Teleplot in VSCode to visualize all sensor data
5. Compare barometric altitude vs ToF vs ESKF altitude
6. Calculate magnetic heading from magnetometer data

### Custom project version / カスタムプロジェクト版
1. `sf app new my_sensor_app`
2. Edit `firmware/my_sensor_app/main/main.cpp`
3. `sf build my_sensor_app` → `sf flash my_sensor_app -m`

## Teleplot Setup / Teleplotセットアップ

1. Install VSCode extension: `alexnesnes.teleplot`
2. Connect via `sf monitor`
3. Open Teleplot panel in VSCode
4. Data in `>name:value` format will be graphed automatically

### Teleplot Channels / チャンネル例
| Channel | Description |
|---------|-------------|
| `>baro_alt` | Barometric altitude [m] |
| `>tof_bottom` | ToF ground distance [m] |
| `>tof_front` | ToF front distance [m] |
| `>eskf_alt` | ESKF estimated altitude [m] |
| `>mag_x/y/z` | Magnetic field [uT] |
| `>heading` | Magnetic heading [deg] |
| `>flow_vx/vy` | Optical flow velocity [m/s] |
| `>voltage` | Battery voltage [V] |

## Key Concepts / キーコンセプト
- ws:: API is a simplified workshop wrapper around StampFlyState
- StampFlyState provides direct access to all sensors and estimation data
- `sf app new` creates a custom firmware project that reuses vehicle components
- Teleplot enables real-time visualization of any sensor data
- Multiple altitude sources (baro, ToF, ESKF) can be compared for understanding sensor fusion
