# Lesson 3: LED Control

## Goal / 目標
Use LED to display system state visually.

## API / 使用するAPI
| Function | Description |
|----------|-------------|
| `ws::led_color(r, g, b)` | Set LED color (0-255 per channel) |
| `ws::is_armed()` | Check ARM status |
| `ws::battery_voltage()` | Get battery voltage [V] |

## Steps / 手順
1. `sf lesson switch 3`
2. Show green when armed, red when disarmed
3. (Challenge) Display battery level as color gradient

## Key Concepts / キーコンセプト
- WS2812 addressable LED
- State visualization
- Battery monitoring (3.3V-4.2V range for LiPo)
