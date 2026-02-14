# Lesson 2: Controller Input

## Goal / 目標
Read controller stick values and map them to motors (open loop).

## Prerequisites / 前提条件
- Controller paired with StampFly (3-second button press to pair)

## API / 使用するAPI
| Function | Description | Range |
|----------|-------------|-------|
| `ws::rc_throttle()` | Throttle stick | 0.0 to 1.0 |
| `ws::rc_roll()` | Roll stick | -1.0 to +1.0 |
| `ws::rc_pitch()` | Pitch stick | -1.0 to +1.0 |
| `ws::rc_yaw()` | Yaw stick | -1.0 to +1.0 |
| `ws::is_armed()` | ARM status | true/false |

## Steps / 手順
1. `sf lesson switch 2`
2. Pair controller (3s button hold on StampFly)
3. ARM (click button or controller ARM switch)
4. Move throttle stick and observe motor response
5. Monitor: `sf monitor`

## Key Concepts / キーコンセプト
- ESP-NOW wireless protocol
- Open-loop control (no feedback)
- Stick normalization (ADC -> 0~1 / -1~+1)
