# Lesson 5: Rate P-Control + First Flight

## Goal / 目標
Implement proportional (P) feedback control on angular rate and achieve your first controlled flight.

角速度に対する比例(P)フィードバック制御を実装し、初めての制御された飛行を行う。

## Prerequisites / 前提条件
- Lesson 1-4 completed (motor, controller, LED, IMU)
- Propellers installed correctly (check rotation direction!)
- Propeller guards installed
- Clear open space (3m x 3m minimum)

## Key Concept: Feedback Control / フィードバック制御

Open loop (Lesson 2) vs. Closed loop (this lesson):

```
Open Loop (Lesson 2):
  stick --> motor        No correction! Unstable.
                         補正なし！不安定

Closed Loop (P-Control):
  stick --> [scale] --> target -->(+)--> error --> [Kp] --> motor_mixer --> motors
                                  ^(-)                                      |
                                  |                                         v
                                  +-------- gyro <-------- drone physics <--+

  The gyro measures the actual rate and feeds it back.
  ジャイロが実際の角速度を計測しフィードバックする
```

### How P-Control Works / P制御の仕組み

```
error = target_rate - actual_rate
output = Kp * error
```

| Parameter | Description | 説明 |
|-----------|-------------|------|
| `target_rate` | Desired angular rate from stick | スティック入力からの目標角速度 |
| `actual_rate` | Measured rate from gyro | ジャイロ計測値 |
| `error` | Difference (target - actual) | 偏差（目標 - 実際） |
| `Kp` | Proportional gain | 比例ゲイン |
| `output` | Control signal to mixer | ミキサーへの制御信号 |

### Tuning Kp / Kp の調整

| Kp | Behavior | 挙動 |
|----|----------|------|
| Too low | Sluggish, poor tracking | 応答が鈍い、追従性が悪い |
| Just right | Quick response, small steady-state error | 素早い応答、小さい定常偏差 |
| Too high | Oscillation, vibration | 振動、発振 |

**Important:** P-control alone has **steady-state error**. The drone will drift slightly. This is normal and will be fixed in Lesson 6 (PID).

**重要:** P制御だけでは**定常偏差**が残る。ドローンは多少ドリフトする。これは正常で、レッスン6(PID)で解消する。

## API / 使用するAPI

| Function | Description | Range |
|----------|-------------|-------|
| `ws::gyro_x()` | Roll rate [rad/s] | ~-10 to +10 |
| `ws::gyro_y()` | Pitch rate [rad/s] | ~-10 to +10 |
| `ws::gyro_z()` | Yaw rate [rad/s] | ~-10 to +10 |
| `ws::rc_roll()` | Roll stick | -1.0 to +1.0 |
| `ws::rc_pitch()` | Pitch stick | -1.0 to +1.0 |
| `ws::rc_yaw()` | Yaw stick | -1.0 to +1.0 |
| `ws::rc_throttle()` | Throttle stick | 0.0 to 1.0 |
| `ws::motor_mixer(T,R,P,Y)` | Apply thrust + control | |
| `ws::is_armed()` | Check ARM state | true/false |
| `ws::telemetry_send(name, val)` | Send telemetry data | |

## Steps / 手順
1. `sf lesson switch 5`
2. Fill in the TODO sections in `student.cpp`
3. Build and flash: `sf build workshop && sf flash workshop -m`
4. **Safety checklist before flight:**
   - Propeller guards installed
   - Battery fully charged
   - Throttle stick at minimum
   - Clear area around drone
5. ARM the drone
6. Slowly increase throttle to ~40-50%
7. Observe: does the drone resist tilting?
8. If oscillating: reduce `Kp`. If sluggish: increase `Kp`.

## Safety / 安全注意事項

| Rule | 説明 |
|------|------|
| Always have propeller guards | 必ずプロペラガードを装着 |
| Start with low throttle | 低スロットルから始める |
| Immediately disarm if unstable | 不安定ならすぐディスアーム |
| Test over soft surface | 柔らかい面の上でテスト |
| Keep fingers away from propellers | プロペラに指を近づけない |

## Challenge / チャレンジ
- Try different Kp values (0.2, 0.5, 1.0, 2.0) and observe the response
- Add `ws::telemetry_send()` to log error and output values
- Can you hover for 5 seconds?
