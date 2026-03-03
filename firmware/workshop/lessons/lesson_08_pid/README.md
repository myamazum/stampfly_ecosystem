# Lesson 8: PID Control

## Goal / 目標
Add Integral (I) and Derivative (D) terms to the P controller from Lesson 5. Eliminate steady-state error and reduce overshoot.

レッスン5のP制御に積分(I)項と微分(D)項を追加する。定常偏差を除去し、オーバーシュートを低減する。

## Prerequisites / 前提条件
- Lesson 5 completed (P-control working, first flight achieved)
- Lesson 6 completed (System Modeling, model-based Kp design)
- Lesson 7 completed (System Identification, flight data analysis)

## Key Concept: PID Control / PID制御

### Block Diagram / ブロック図

```
                              +-->[Kp * e]----------+
                              |                      |
target -->(+)--> error(e) ----+-->[Ki * integral]--->+--> output --> mixer
            ^(-)              |                      |
            |                 +-->[Kd * de/dt]------>+
       gyro (actual)
```

### Three Terms / 3つの項

| Term | Formula | Role | 役割 |
|------|---------|------|------|
| **P** (Proportional) | `Kp * error` | React to current error | 現在の誤差に反応 |
| **I** (Integral) | `Ki * sum(error * dt)` | Eliminate steady-state error | 定常偏差を除去 |
| **D** (Derivative) | `Kd * (error - prev_error) / dt` | Dampen overshoot | オーバーシュートを抑制 |

### What Each Term Does / 各項の役割

```
P only:     Fast response but steady-state error remains
            速い応答だが定常偏差が残る

P + I:      Eliminates steady-state error but may overshoot
            定常偏差を除去するが、オーバーシュートの可能性

P + I + D:  Best response - fast, accurate, and well-damped
            最良の応答 - 速く、正確で、よく減衰する
```

### Anti-Windup / アンチワインドアップ

The integral term accumulates error over time. Without limits, it can grow very large ("wind up") and cause dangerous overshoot.

積分項は時間とともに誤差を蓄積する。制限がないと非常に大きくなり（「ワインドアップ」）、危険なオーバーシュートを引き起こす。

```
Solution: Clamp the integral accumulator
解決策: 積分累積値をクランプする

  roll_integral += roll_error * dt;
  if (roll_integral >  0.5f) roll_integral =  0.5f;  // Anti-windup
  if (roll_integral < -0.5f) roll_integral = -0.5f;   // アンチワインドアップ
```

**Why this matters:** If you hold the drone still while armed, the integral accumulates. When released, all that stored energy causes a violent snap. Anti-windup prevents this.

**なぜ重要か:** アーム状態でドローンを手で押さえると積分値が蓄積する。離すと蓄積されたエネルギーで急激に動く。アンチワインドアップはこれを防ぐ。

### State Reset on Disarm / ディスアーム時の状態リセット

Always reset integral and previous error when disarmed:

ディスアーム時は必ず積分値と前回誤差をリセットする:

```cpp
if (!ws::is_armed()) {
    roll_integral = 0.0f;
    roll_prev_error = 0.0f;
    // ... same for pitch and yaw
}
```

## PID Gains / PIDゲイン

### Recommended Starting Values / 推奨初期値

| Axis | Kp | Ki | Kd |
|------|----|----|----|
| Roll | 0.25 | 0.3 | 0.005 |
| Pitch | 0.36 | 0.3 | 0.005 |
| Yaw | 2.0 | 0.5 | 0.01 |

### Tuning Guide / チューニングガイド

**Step 1:** Start with P-only (Ki=0, Kd=0). Find a Kp that gives fast response with mild oscillation.

**Step 2:** Add D term to dampen the oscillation. Increase Kd until oscillation stops.

**Step 3:** Add I term to eliminate steady-state error. Start small (Ki=0.1) and increase slowly.

| Symptom | Adjustment | 調整 |
|---------|------------|------|
| Slow response | Increase Kp | Kp を増やす |
| Oscillation (fast) | Increase Kd or decrease Kp | Kd を増やす or Kp を減らす |
| Steady-state drift | Increase Ki | Ki を増やす |
| Slow oscillation | Decrease Ki | Ki を減らす |
| Motor buzz/vibration | Decrease Kd | Kd を減らす |

## API / 使用するAPI

| Function | Description |
|----------|-------------|
| `ws::gyro_x/y/z()` | Angular rate [rad/s] |
| `ws::rc_roll/pitch/yaw()` | Stick inputs [-1, +1] |
| `ws::rc_throttle()` | Throttle [0, 1] |
| `ws::motor_mixer(T,R,P,Y)` | Apply control |
| `ws::telemetry_send(name, val)` | Send telemetry |

## Steps / 手順
1. `sf lesson switch 8`
2. Add I and D terms to each axis in `student.cpp`
3. Implement anti-windup (clamp integral to +/-0.5)
4. Add output limiting (clamp output to +/-1.0)
5. Reset state on disarm
6. Build, flash, and test: `sf lesson build && sf lesson flash`
7. Start with recommended gains, then tune

## Challenge / チャレンジ
- Add telemetry for P, I, D terms separately and observe with `sf log wifi`
- Try flying without the D term. What happens?
- Try flying without anti-windup. What happens when you hold the drone and release?
- Can you achieve a stable 10-second hover?
