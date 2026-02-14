# Lesson 1: Motor Control

## Goal / 目標
Understand motor numbering and control individual motors with PWM.

## Motor Layout / モーター配置
```
           Front
      FL (M4)   FR (M1)
         \   ^   /
          \  |  /
           \ | /
            \|/
             X      <- Center
            /|\
           / | \
          /  |  \
      RL (M3)  RR (M2)
           Rear
```

## API / 使用するAPI
| Function | Description |
|----------|-------------|
| `ws::motor_set_duty(id, duty)` | Set motor duty (id=1-4, duty=0.0-1.0) |
| `ws::motor_set_all(duty)` | Set all motors to same duty |
| `ws::motor_stop_all()` | Stop all motors |

## Steps / 手順
1. Switch to this lesson: `sf lesson switch 1`
2. Spin motor 1 at 10% duty
3. Verify which propeller spins (FR = front-right)
4. Try each motor to confirm numbering
5. **WARNING**: Hold the drone firmly! Do not exceed 15% duty!

## Challenge / チャレンジ
Cycle through all 4 motors, spinning each for 2 seconds.
