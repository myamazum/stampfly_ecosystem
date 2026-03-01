# Lesson 8: Modeling - Quadrotor Dynamics

## Goal / 目標
Understand quadrotor dynamics and implement the motor mixer from first principles.

クアッドロータの力学を理解し、第一原理からモーターミキサーを実装する。

## Prerequisites / 前提条件
- Lesson 6 completed (PID control working)
- Basic understanding of forces and torques

## Key Concept: Quadrotor Dynamics / クアッドロータの力学

### Motor Layout / モーター配置

```
              Front
         FL (M4)    FR (M1)
         CCW  \  ^  /  CW
               \ | /
                \|/
                 X          <- Center of mass
                /|\
               / | \
         CW  /  |  \  CCW
         RL (M3)   RR (M2)
              Rear

  CW  = Clockwise (generates negative yaw torque)
  CCW = Counter-clockwise (generates positive yaw torque)
  L = 0.023 m (arm length from center to motor)
```

### Forces and Torques / 力とトルク

Each motor produces a thrust force (F) and a reaction torque (Q):

各モーターは推力(F)と反力トルク(Q)を生成する:

```
F = kt * omega^2    (thrust proportional to RPM squared)
Q = kq * F          (reaction torque proportional to thrust)
```

### Equations of Motion / 運動方程式

From Newton-Euler equations for a rigid body:

剛体のニュートン・オイラー方程式から:

| Equation | Formula | 説明 |
|----------|---------|------|
| Total thrust | `T = F1 + F2 + F3 + F4` | 全推力 |
| Roll torque | `tau_roll = (F1 + F2 - F3 - F4) * L` | ロールトルク |
| Pitch torque | `tau_pitch = (-F1 + F2 + F3 - F4) * L` | ピッチトルク |
| Yaw torque | `tau_yaw = (-Q1 + Q2 - Q3 + Q4)` | ヨートルク |

In matrix form:

行列形式:

```
[ T          ]   [ 1     1     1     1    ] [ F1 ]
[ tau_roll   ] = [ L     L    -L    -L    ] [ F2 ]
[ tau_pitch  ]   [-L     L     L    -L    ] [ F3 ]
[ tau_yaw    ]   [-kq    kq   -kq    kq   ] [ F4 ]
```

### Mixer: Inverse Mapping / ミキサー: 逆変換

To compute motor forces from desired thrust and torques, invert the matrix:

推力とトルクからモーター出力を計算するため、行列を逆変換する:

```
[ F1 ]   [ 1/4    1/(4L)   -1/(4L)   -1/(4kq) ] [ T          ]
[ F2 ] = [ 1/4    1/(4L)    1/(4L)    1/(4kq)  ] [ tau_roll   ]
[ F3 ]   [ 1/4   -1/(4L)    1/(4L)   -1/(4kq)  ] [ tau_pitch  ]
[ F4 ]   [ 1/4   -1/(4L)   -1/(4L)    1/(4kq)  ] [ tau_yaw    ]
```

### Implementation / 実装

```cpp
// Motor 1 (FR, CW):  +roll, -pitch, -yaw
M1 = T/4 + tau_roll/(4*L) - tau_pitch/(4*L) - tau_yaw/(4*kq)

// Motor 2 (RR, CCW): +roll, +pitch, +yaw
M2 = T/4 + tau_roll/(4*L) + tau_pitch/(4*L) + tau_yaw/(4*kq)

// Motor 3 (RL, CW):  -roll, +pitch, -yaw
M3 = T/4 - tau_roll/(4*L) + tau_pitch/(4*L) - tau_yaw/(4*kq)

// Motor 4 (FL, CCW): -roll, -pitch, +yaw
M4 = T/4 - tau_roll/(4*L) - tau_pitch/(4*L) + tau_yaw/(4*kq)
```

### Physical Parameters / 物理パラメータ

| Parameter | Value | Description | 説明 |
|-----------|-------|-------------|------|
| L | 0.023 m | Arm length (center to motor) | アーム長（中心からモーター） |
| kq | 0.01 | Torque-to-thrust ratio | トルク対推力比 |
| Mass | ~0.025 kg | Total vehicle mass | 機体総質量 |
| 1/(4L) | ~10.87 | Roll/pitch mixing gain | ロール/ピッチ混合ゲイン |
| 1/(4kq) | 25.0 | Yaw mixing gain | ヨー混合ゲイン |

## Why Build a Custom Mixer? / なぜカスタムミキサーを作るのか

In Lessons 5-6, `ws::motor_mixer()` handled the mixing internally. By implementing it yourself, you:

レッスン5-6では `ws::motor_mixer()` が内部でミキシングを処理していた。自分で実装することで:

1. **Understand the physics** connecting control commands to motor outputs
2. **Can modify the mixer** for different frame geometries
3. **Prepare for advanced control** (MPC, adaptive control) that needs the plant model
4. **Debug better** when you know exactly what each motor should be doing

## Comparison: motor_mixer vs Custom / 比較

```cpp
// Before (black box):
ws::motor_mixer(throttle, roll_out, pitch_out, yaw_out);

// After (transparent):
float m1 = T/4 + roll/(4*L) - pitch/(4*L) - yaw/(4*kq);
float m2 = T/4 + roll/(4*L) + pitch/(4*L) + yaw/(4*kq);
float m3 = T/4 - roll/(4*L) + pitch/(4*L) - yaw/(4*kq);
float m4 = T/4 - roll/(4*L) - pitch/(4*L) + yaw/(4*kq);
ws::motor_set_duty(1, clamp(m1));
ws::motor_set_duty(2, clamp(m2));
ws::motor_set_duty(3, clamp(m3));
ws::motor_set_duty(4, clamp(m4));
```

## Steps / 手順
1. `sf lesson switch 8`
2. Implement the mixer equations in `student.cpp`
3. Use `ws::motor_set_duty()` for each motor individually
4. Clamp all motor values to [0.0, 1.0]
5. Build and flash: `sf lesson build && sf lesson flash`
6. Compare behavior with Lesson 6 (should be identical!)
7. Try changing L and observe the effect

## Further Reading / 参考資料

| Resource | Description |
|----------|-------------|
| Loop Shaping Tool (`sf sim run loop_shaping`) | Interactive PID tuning with plant model |
| `tools/sysid/defaults.py` | Default physical parameters |
| `simulator/vpython/` | 3D visualization of quadrotor dynamics |

## Challenge / チャレンジ
- What happens if you double L in the code? (Hint: roll/pitch response changes)
- What happens if you set kq to 0? (Hint: yaw gain goes to infinity - do NOT fly!)
- Add telemetry to compare your mixer output vs `ws::motor_mixer()` output
- Can you derive the mixer for a "+" configuration instead of "X"?
