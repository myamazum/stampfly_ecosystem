# StampFly Workshop Skeleton

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このファームウェアについて

Workshop Skeleton は StampFly 勉強会のための簡易ファームウェアです。車両ファームウェアの複雑さ（FreeRTOS タスク、HAL 抽象化、センサフュージョン等）を `ws::` 名前空間の簡易 API で隠蔽し、学生は `setup()` と `loop_400Hz()` の2つの関数だけを実装します。

### 構成

```
firmware/workshop/
├── CMakeLists.txt              # ESP-IDF プロジェクト設定
├── sdkconfig.defaults          # ESP32-S3 設定（vehicle から流用）
├── partitions.csv              # パーティションテーブル
├── main/
│   ├── workshop_api.hpp        # ★ 学生向け簡易 API（これだけ読めばOK）
│   ├── user_code.cpp           # ★ 学生が編集するファイル（sf lesson switch で差替え）
│   ├── workshop_main.cpp       # タスク起動（触らない）
│   ├── workshop_task.cpp       # 400Hz ループ実行（触らない）
│   ├── workshop_api.cpp        # ws:: API 実装（触らない）
│   └── workshop_globals.*      # 内部グローバル（触らない）
└── lessons/
    ├── lesson_00_setup/        # Lesson 0: 環境セットアップ
    │   ├── student.cpp         # スケルトン（TODO 付き）
    │   ├── solution.cpp        # 解答
    │   └── README.md           # ハンドアウト
    ├── lesson_01_motor/        # Lesson 1: モータ制御
    ├── ...
    └── lesson_11_competition/  # Lesson 11: 競技会
```

## 2. クイックスタート

### 環境準備

```bash
# ESP-IDF 環境を有効化
source ~/esp/esp-idf/export.sh

# 環境診断
sf doctor
```

### レッスンの切り替え

```bash
# レッスン一覧を表示
sf lesson list

# レッスン 1 に切り替え
sf lesson switch 1

# ビルド & フラッシュ（モニタ付き）
sf lesson build
sf lesson flash
```

### ビルド & フラッシュ（直接）

```bash
sf build workshop
sf flash workshop -m
```

## 3. 学生向け API

### 基本構造

```cpp
#include "workshop_api.hpp"

void setup()
{
    // 起動時に一度だけ呼ばれる
    ws::print("Hello StampFly!");
}

void loop_400Hz(float dt)
{
    // ARM 時に 400Hz で呼ばれる
    // dt = 0.0025 (秒)
}
```

### API 一覧

| カテゴリ | 関数 | 説明 |
|---------|------|------|
| **Motor** | `ws::motor_set_duty(id, duty)` | モータ個別制御 (id=1-4, duty=0.0-1.0) |
| | `ws::motor_set_all(duty)` | 全モータ同一 duty |
| | `ws::motor_stop_all()` | 全モータ停止 |
| | `ws::motor_mixer(T, R, P, Y)` | ミキサー (thrust/roll/pitch/yaw) |
| **Controller** | `ws::rc_throttle()` | スロットル (0.0-1.0) |
| | `ws::rc_roll()` | ロール (-1.0 to 1.0) |
| | `ws::rc_pitch()` | ピッチ (-1.0 to 1.0) |
| | `ws::rc_yaw()` | ヨー (-1.0 to 1.0) |
| | `ws::is_armed()` | ARM 状態 |
| **LED** | `ws::led_color(r, g, b)` | LED 色設定 (0-255) |
| **IMU** | `ws::gyro_x/y/z()` | 角速度 (rad/s) |
| | `ws::accel_x/y/z()` | 加速度 (m/s^2) |
| **Telemetry** | `ws::telemetry_send(name, value)` | テレメトリ送信 |
| **Estimation** | `ws::estimated_roll/pitch/yaw()` | 推定姿勢角 (rad) |
| | `ws::estimated_altitude()` | 推定高度 (m) |
| **Utility** | `ws::millis()` | 起動後ミリ秒 |
| | `ws::battery_voltage()` | バッテリ電圧 (V) |
| | `ws::print(msg)` | シリアル出力 |

### モータ配置

```
           Front
      FL (M4)   FR (M1)
         ╲   ▲   ╱
          ╲  │  ╱
           ╲ │ ╱
            ╲│╱
             ╳
            ╱│╲
           ╱ │ ╲
          ╱  │  ╲
         ╱   │   ╲
      RL (M3)   RR (M2)
           Rear

M1(FR): CCW  M2(RR): CW  M3(RL): CCW  M4(FL): CW
```

## 4. レッスン一覧

| Day | Lesson | 内容 | API |
|-----|--------|------|-----|
| Day 1 | 00 | 環境セットアップ | `ws::print()` |
| | 01 | モータ制御 | `ws::motor_set_duty()` |
| | 02 | コントローラ入力 | `ws::rc_*()` |
| | 03 | LED 表示 | `ws::led_color()` |
| | 04 | IMU センサ | `ws::gyro_*()`, `ws::telemetry_send()` |
| Day 2 | 05 | 角速度 P 制御 | `ws::motor_mixer()` |
| | 06 | PID 制御 | I 項/D 項追加 |
| | 07 | テレメトリ活用 | `sf log wifi`, `sf log viz` |
| Day 3 | 08 | モデリング/制御系設計 | Loop Shaping Tool |
| | 09 | 姿勢推定 | 相補フィルタ, ESKF 比較 |
| Day 4 | 10 | Python SDK | `StampFly`, Jupyter |
| | 11 | ホバリングタイム競技 | PIDゲイン最適化 |

## 5. sf CLI コマンド

```bash
# レッスン管理
sf lesson list              # 一覧表示
sf lesson switch <N>        # レッスン N に切り替え
sf lesson solution <N>      # 解答を diff 表示
sf lesson build             # ビルド
sf lesson flash             # フラッシュ（モニタ付き）

# 競技会ツール
sf competition hover-time   # ホバリングタイム計測
sf competition score        # スコア・ランキング表示

# テレメトリ
sf log wifi                 # WiFi テレメトリ取得
sf log viz                  # ログ可視化
```

## 6. トラブルシューティング

| 症状 | 対処 |
|------|------|
| ビルドエラー | `sf lesson build -c` でクリーンビルド |
| ポート未検出 | USB ケーブルを確認、`sf doctor` で診断 |
| モータが回らない | ARM 状態か確認 (`ws::is_armed()`) |
| テレメトリが来ない | WiFi AP に接続されているか確認 |

---

<a id="english"></a>

## 1. Overview

### About This Firmware

Workshop Skeleton is a simplified firmware for the StampFly workshop. It hides the vehicle firmware's complexity (FreeRTOS tasks, HAL abstraction, sensor fusion, etc.) behind a simple `ws::` namespace API. Students only need to implement two functions: `setup()` and `loop_400Hz()`.

## 2. Quick Start

```bash
# Activate ESP-IDF
source ~/esp/esp-idf/export.sh

# Switch to a lesson
sf lesson switch 1

# Build and flash
sf lesson build
sf lesson flash
```

## 3. Student API

```cpp
#include "workshop_api.hpp"

void setup() {
    ws::print("Hello StampFly!");
}

void loop_400Hz(float dt) {
    // Called at 400Hz when armed
    // dt = 0.0025 seconds
}
```

See the Japanese section above for the complete API reference table.

## 4. Lesson List

| Day | Lesson | Topic | Key API |
|-----|--------|-------|---------|
| Day 1 | 00-04 | Setup, Motors, Controller, LED, IMU | `ws::motor_*`, `ws::rc_*`, `ws::gyro_*` |
| Day 2 | 05-07 | P control, PID, Telemetry | `ws::motor_mixer()`, `sf log wifi` |
| Day 3 | 08-09 | Modeling, Estimation | Loop Shaping, ESKF |
| Day 4 | 10-11 | Python SDK, Competition | `StampFly`, Jupyter |

## 5. CLI Commands

```bash
sf lesson list / switch / solution / build / flash
sf competition hover-time / score
```
