# Lesson 7: システム同定 / System Identification

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このレッスンについて

L6 で導出したプラントモデルの予測をフライトデータで検証する。
2 種類の Kp 設定（L5 の一律 Kp=0.5 と L6 のモデルベース Kp）で飛行し、
オーバーシュート比から減衰比 ζ を推定してモデルの妥当性を確認する。

### 前提知識

- L05: レート P 制御と初フライト
- L06: システムモデリング（伝達関数、設計式 Kp = 1/(4ζ²Kτm)）

## 2. システム同定とは

### 概念

入出力データからプラントのパラメータ（K, τm）を推定する手法。

```
u(t) → [Plant G_p(s)] → y(t) → [Parameter Estimation] → K̂, τ̂m
```

### なぜ重要か

- L6 のモデルは理論値（データシートや CAD）に基づく
- 実機には製造ばらつき・組立誤差がある
- データで検証することでモデルの信頼度が上がる

## 3. 実験計画

### 2 つの Kp モード

| モード | Kp 設定 | 理論 ζ (Roll) | 期待される挙動 |
|--------|---------|--------------|----------------|
| Mode 0 (L5) | 0.5（全軸同一） | 0.50 | やや振動的（~16% OS） |
| Mode 1 (L6) | 軸ごと設計 | 0.70 | ほぼ振動なし（~5% OS） |

### 手順

1. `sf lesson switch 7`
2. `student.cpp` の TODO を実装
3. `kp_mode = 0` でビルド・フラッシュ → 飛行 → `sf log wifi` でデータ取得
4. `kp_mode = 1` に変更 → 再ビルド → 飛行 → データ取得
5. 2 つのデータを比較分析

## 4. データ分析

### オーバーシュート比 → ζ

```
OS ≈ e^(-πζ/√(1-ζ²))
```

| OS | ζ |
|----|-----|
| 16% | 0.50 |
| 5% | 0.70 |
| 0% | ≥ 1.0 |

### 分析コマンド

```bash
sf log analyze data_mode0.csv
sf log analyze data_mode1.csv
sf log viz data_mode0.csv
```

## 5. モデル検証表

| 項目 | Mode 0 理論 | Mode 0 実測 | Mode 1 理論 | Mode 1 実測 |
|------|------------|------------|------------|------------|
| ζ (Roll) | 0.50 | ? | 0.70 | ? |
| OS (Roll) | 16% | ? | 5% | ? |
| ζ (Pitch) | 0.60 | ? | 0.70 | ? |
| ζ (Yaw) | 1.15 | ? | 0.70 | ? |

### 考察ポイント

- 理論と実測のずれ → 無駄時間・モデル誤差が原因
- Yaw の Mode 0: 過減衰 → 応答遅い
- 軸ごとの Kp 設計がなぜ重要かをデータで実感

## 6. API

| 関数 | 説明 |
|------|------|
| `ws::gyro_x/y/z()` | 角速度 [rad/s] |
| `ws::rc_roll/pitch/yaw()` | スティック入力 [-1, +1] |
| `ws::rc_throttle()` | スロットル [0, 1] |
| `ws::motor_mixer(T,R,P,Y)` | モーターミキサー |
| `ws::led_color(r,g,b)` | LED 色設定 |

## 7. チャレンジ

- `sf log wifi` でロール軸の過渡応答を記録し、立ち上がり時間を計測する
- 理論的なステップ応答波形と実測を重ねてプロットする
- τm を変えてモデル予測がどう変わるか試す

---

<a id="english"></a>

## 1. Overview

### About This Lesson

Verify the L6 plant model predictions using flight data.
Fly with two Kp configurations (L5 uniform Kp=0.5 and L6 model-based Kp),
estimate damping ratio ζ from overshoot, and validate the model.

### Prerequisites

- L05: Rate P control and first flight
- L06: System Modeling (transfer function, design formula Kp = 1/(4ζ²Kτm))

## 2. What is System Identification?

### Concept

Estimate plant parameters (K, τm) from input-output data.

```
u(t) → [Plant G_p(s)] → y(t) → [Parameter Estimation] → K̂, τ̂m
```

### Why It Matters

- L6 model is based on theoretical values (datasheets, CAD)
- Real hardware has manufacturing variations and assembly errors
- Data verification increases model confidence

## 3. Experiment Plan

### Two Kp Modes

| Mode | Kp Setting | Theoretical ζ (Roll) | Expected Behavior |
|------|-----------|---------------------|-------------------|
| Mode 0 (L5) | 0.5 (uniform) | 0.50 | Slightly oscillatory (~16% OS) |
| Mode 1 (L6) | Per-axis design | 0.70 | Nearly no oscillation (~5% OS) |

### Procedure

1. `sf lesson switch 7`
2. Implement TODOs in `student.cpp`
3. Build with `kp_mode = 0` → fly → capture with `sf log wifi`
4. Change to `kp_mode = 1` → rebuild → fly → capture
5. Compare both datasets

## 4. Data Analysis

### Overshoot Ratio → ζ

```
OS ≈ e^(-πζ/√(1-ζ²))
```

| OS | ζ |
|----|-----|
| 16% | 0.50 |
| 5% | 0.70 |
| 0% | ≥ 1.0 |

### Analysis Commands

```bash
sf log analyze data_mode0.csv
sf log analyze data_mode1.csv
sf log viz data_mode0.csv
```

## 5. Model Verification Table

| Metric | Mode 0 Theory | Mode 0 Measured | Mode 1 Theory | Mode 1 Measured |
|--------|--------------|-----------------|--------------|-----------------|
| ζ (Roll) | 0.50 | ? | 0.70 | ? |
| OS (Roll) | 16% | ? | 5% | ? |
| ζ (Pitch) | 0.60 | ? | 0.70 | ? |
| ζ (Yaw) | 1.15 | ? | 0.70 | ? |

### Discussion Points

- Gap between theory and measurement → dead time, model error
- Yaw Mode 0: overdamped → sluggish response
- Data demonstrates why per-axis Kp design matters

## 6. API

| Function | Description |
|----------|-------------|
| `ws::gyro_x/y/z()` | Angular rate [rad/s] |
| `ws::rc_roll/pitch/yaw()` | Stick inputs [-1, +1] |
| `ws::rc_throttle()` | Throttle [0, 1] |
| `ws::motor_mixer(T,R,P,Y)` | Motor mixer |
| `ws::led_color(r,g,b)` | LED color |

## 7. Challenge

- Record roll transient response with `sf log wifi` and measure rise time
- Overlay theoretical step response with measured data
- Try changing τm and observe how model predictions change
