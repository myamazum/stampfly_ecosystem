# Lesson 7: システム同定 / System Identification

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このレッスンについて

フライトデータからプラントモデル $G_p(s) = K / (s(\tau_m s + 1))$ のパラメータ $K$, $\tau_m$ を同定する。
L5 の P 制御で飛行し、WiFi テレメトリでデータを取得した後、`sf sysid fit` でモデルフィッティングを行う。

### 前提知識

- L05: レート P 制御と初フライト（Kp, rate_max の値を使う）
- L06: システムモデリング（伝達関数、プラントモデル）

## 2. システム同定の仕組み

### アルゴリズム概要

$K_p$ が既知なので、テレメトリデータからプラントの入出力を復元できる:

```
テレメトリに記録されるデータ:
  ctrl_roll   : スティック入力 [-1, +1]
  gyro_corrected_x : 角速度 [rad/s]

プラント入出力の復元:
  target   = ctrl_roll × rate_max
  u_plant  = Kp × (target − gyro)     ← プラントへの入力
  y_plant  = gyro                      ← プラントの出力

開ループモデルをフィッティング:
  G_p(s) = K / (s·(τm·s + 1))
  minimize |y_simulated − y_plant|²   → K, τm を同定
```

### なぜ開ループ同定が可能か

閉ループデータでも $K_p$ が既知なら、プラントへの入力 $u(t)$ を計算できる。
そのため、閉ループモデルを経由せずに開ループモデルを直接同定できる。

## 3. 手順

### ステップ 1: ファームウェア準備

1. `sf lesson switch 7` でテンプレートを `user_code.cpp` にコピー
2. `user_code.cpp` を開き、$K_p$ を設定（例: 0.5、L5 で使った値）
3. WiFi チャンネルを設定
4. ビルド & 書き込み: `sf lesson build` → `sf lesson flash`

### ステップ 2: フライト & データ取得

1. PC でテレメトリ受信を開始: `sf log wifi -o flight.csv`
2. ARM → ホバリング → スティック操作でロール・ピッチ入力
3. 2〜3回のスティック操作で十分
4. 着陸 → DISARM

### ステップ 3: 同定

```bash
# 全軸を同定（roll/pitch は rate_max=1.0、yaw は 5.0 を自動使用）
sf sysid fit flight.csv --kp 0.5 --plot

# 特定軸のみ
sf sysid fit flight.csv --kp 0.5 --axis roll --plot

# 結果を YAML に保存
sf sysid fit flight.csv --kp 0.5 -o my_plant.yaml
```

### ステップ 4: L6 理論値と比較

| 軸 | K (同定) | K (L6理論) | τm (同定) | τm (理論) |
|-----|---------|-----------|----------|----------|
| Roll | ? | 102.0 | ? | 0.020 |
| Pitch | ? | 70.0 | ? | 0.020 |
| Yaw | ? | 19.0 | ? | 0.020 |

同定した K, τm から設計 Kp を計算: $K_p = 1/(4\zeta^2 K \tau_m)$

## 4. API

| 関数 | 説明 | 値域 |
|------|------|------|
| `ws::gyro_x/y/z()` | 角速度 | rad/s |
| `ws::rc_roll/pitch/yaw()` | スティック入力 | -1.0 〜 +1.0 |
| `ws::rc_throttle()` | スロットル | 0.0 〜 1.0 |
| `ws::motor_mixer(T,R,P,Y)` | モーターミキサー | --- |
| `ws::led_color(r,g,b)` | LED 色設定 | 0〜255 |
| `ws::set_channel(ch)` | WiFi チャンネル | 1, 6, 11 |

## 5. チャレンジ

- 異なる Kp（例: 0.3, 0.7）で飛行し、同定結果がどう変わるか比較する
- `--time-range` オプションで特定区間のみ分析する
- 同定した K, τm でシミュレーション応答と実測を重ねてプロットする

---

<a id="english"></a>

## 1. Overview

### About This Lesson

Identify plant model parameters $K$ and $\tau_m$ from flight data where
$G_p(s) = K / (s(\tau_m s + 1))$.
Fly with L5's P controller, capture WiFi telemetry, then run `sf sysid fit` for model fitting.

### Prerequisites

- L05: Rate P control and first flight (need Kp, rate_max values)
- L06: System Modeling (transfer function, plant model)

## 2. How System Identification Works

### Algorithm Overview

Since $K_p$ is known, plant I/O can be reconstructed from telemetry:

```
Telemetry data:
  ctrl_roll        : stick input [-1, +1]
  gyro_corrected_x : angular rate [rad/s]

Plant I/O reconstruction:
  target   = ctrl_roll × rate_max
  u_plant  = Kp × (target − gyro)     <- plant input
  y_plant  = gyro                      <- plant output

Open-loop model fitting:
  G_p(s) = K / (s·(τm·s + 1))
  minimize |y_simulated − y_plant|²   → identify K, τm
```

### Why Open-Loop Identification Works

Even with closed-loop data, if $K_p$ is known, the plant input $u(t)$
can be computed directly. This allows open-loop model identification
without going through the closed-loop model.

## 3. Procedure

### Step 1: Firmware Setup

1. Run `sf lesson switch 7` to copy the template to `user_code.cpp`
2. Open `user_code.cpp` and set $K_p$ (e.g., 0.5, same as L5)
3. Set WiFi channel
4. Build & flash: `sf lesson build` → `sf lesson flash`

### Step 2: Flight & Data Capture

1. Start telemetry on PC: `sf log wifi -o flight.csv`
2. ARM → hover → apply roll/pitch stick inputs
3. 2-3 stick inputs are sufficient
4. Land → DISARM

### Step 3: Identification

```bash
# Identify all axes (rate_max auto: 1.0 for roll/pitch, 5.0 for yaw)
sf sysid fit flight.csv --kp 0.5 --plot

# Single axis only
sf sysid fit flight.csv --kp 0.5 --axis roll --plot

# Save results to YAML
sf sysid fit flight.csv --kp 0.5 -o my_plant.yaml
```

### Step 4: Compare with L6 Theory

| Axis | K (identified) | K (L6 theory) | τm (identified) | τm (theory) |
|------|---------------|---------------|-----------------|-------------|
| Roll | ? | 102.0 | ? | 0.020 |
| Pitch | ? | 70.0 | ? | 0.020 |
| Yaw | ? | 19.0 | ? | 0.020 |

Compute design Kp from identified parameters: $K_p = 1/(4\zeta^2 K \tau_m)$

## 4. API

| Function | Description | Range |
|----------|-------------|-------|
| `ws::gyro_x/y/z()` | Angular rate | rad/s |
| `ws::rc_roll/pitch/yaw()` | Stick input | -1.0 to +1.0 |
| `ws::rc_throttle()` | Throttle | 0.0 to 1.0 |
| `ws::motor_mixer(T,R,P,Y)` | Motor mixer | --- |
| `ws::led_color(r,g,b)` | LED color | 0-255 |
| `ws::set_channel(ch)` | WiFi channel | 1, 6, 11 |

## 5. Challenge

- Fly with different Kp values (e.g., 0.3, 0.7) and compare identification results
- Use `--time-range` option to analyze specific segments
- Overlay simulation response using identified K, τm with measured data
