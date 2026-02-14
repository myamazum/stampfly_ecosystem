# Lesson 7: Telemetry + Step Response

## Goal / 目標
Use WiFi telemetry to capture step response data and analyze PID controller performance.

WiFiテレメトリを使ってステップ応答データをキャプチャし、PIDコントローラの性能を分析する。

## Prerequisites / 前提条件
- Lesson 6 completed (PID control working)
- WiFi connection to StampFly AP (see setup below)
- `sf log wifi` command available

## Key Concept: Step Response / ステップ応答

A step response test applies a sudden change (step) to the target and measures how the system responds. This reveals key performance characteristics.

ステップ応答テストは目標に突然の変化（ステップ）を加え、システムの応答を計測する。これにより主要な性能特性がわかる。

### Experiment Timeline / 実験タイムライン

```
Roll Rate
[rad/s]
  ^
  |
0.5|              +-----------+
  |              |           |
  |              |           |
0.0|------+------+           +---------->  time [s]
  |      |                   |
  |   baseline    step       recovery
  |    (2s)       (1s)        (1s)
  0      2        3          4
```

### What to Measure / 計測項目

| Metric | Description | 説明 |
|--------|-------------|------|
| Rise time | Time to reach 90% of target | 目標の90%に達する時間 |
| Overshoot | Peak value above target | 目標を超えるピーク値 |
| Settling time | Time to stay within 5% of target | 目標の5%以内に安定する時間 |
| Steady-state error | Final offset from target | 最終的な目標からのずれ |

```
Roll Rate
  ^
  |   overshoot
  |      /\
0.5|----/--\-----------  <-- target
  |  /    \  settling
  | /      --------->
  |/
0.0+--|----|-->
     rise  settling
     time  time
```

## WiFi Telemetry Setup / WiFiテレメトリ設定

### Step 1: Connect to StampFly WiFi / StampFly WiFiに接続

| Setting | Value |
|---------|-------|
| SSID | `StampFly_XXXX` |
| Password | (none / open) |
| IP | `192.168.4.1` |

### Step 2: Capture Data / データキャプチャ

```bash
# Start WiFi telemetry capture
# WiFiテレメトリキャプチャを開始
sf log wifi

# Capture to a specific file
# 特定ファイルに保存
sf log wifi -o step_response_01.csv
```

### Step 3: Run Experiment / 実験実行

1. ARM the drone
2. Raise throttle above 30% to trigger the step experiment
3. Hold the drone firmly (or fly if confident)
4. Wait for "experiment complete" message
5. Stop `sf log wifi` capture (Ctrl+C)

### Step 4: Analyze / 分析

```bash
# View captured data
# キャプチャデータを表示
sf log analyze step_response_01.csv

# Visualize step response
# ステップ応答を可視化
sf log viz step_response_01.csv
```

## Telemetry API / テレメトリAPI

| Function | Description |
|----------|-------------|
| `ws::telemetry_send(name, val)` | Send named float value via WiFi |

### Sending Data / データ送信

```cpp
// Send at any rate - typically 400Hz during experiments
// 任意のレートで送信 - 実験中は通常400Hz
ws::telemetry_send("step_target", target_value);
ws::telemetry_send("step_actual", gyro_value);
ws::telemetry_send("step_error",  error_value);
```

### Data Format / データ形式

The telemetry data is sent as CSV with columns:

テレメトリデータはCSV形式で送信される:

```
timestamp_ms, step_target, step_actual, step_error, step_output, step_P, step_I, step_D
0,            0.000,       0.001,      -0.001,      0.000,       ...
2000,         0.500,       0.012,       0.488,       0.312,       ...
```

## Steps / 手順
1. `sf lesson switch 7`
2. Fill in the TODO sections:
   - Set `roll_step` based on experiment phase
   - Send telemetry data with `ws::telemetry_send()`
3. Build and flash: `sf build workshop && sf flash workshop -m`
4. Connect to StampFly WiFi on your PC
5. Start capture: `sf log wifi -o step_test.csv`
6. ARM, raise throttle > 30%, wait for experiment to complete
7. Analyze the captured data

## Challenge / チャレンジ
- Capture step responses with different Kp values (0.3, 0.5, 1.0) and compare
- Measure rise time and overshoot for each Kp setting
- Try step response on pitch axis instead of roll
- Plot the P, I, D terms separately to see each contribution
