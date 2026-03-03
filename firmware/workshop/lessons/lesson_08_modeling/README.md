# Lesson 8: システムモデリング / System Modeling

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このレッスンについて

StampFly の1軸角速度制御系を伝達関数でモデル化し、2次系理論に基づいて P ゲインを設計する。
L05 で経験的に選んだ `Kp=0.5` がモデル上どのような減衰比 ζ を与えるかを確認し、
目標 ζ から逆算して各軸に最適な Kp を求める。

### 前提知識

- L05: レート P 制御と初フライト
- L06: PID 制御
- L07: ステップ応答実験

## 2. プラント伝達関数

### ブロック図

```
u ──▶ [Mixer + Motor: Km/(τm·s+1)] ──τ──▶ [Body: 1/(I·s)] ──▶ ω
```

### 統合伝達関数

```
G_p(s) = K / (s * (τ_m * s + 1)),    K = K_m / I
```

| ブロック | 物理的意味 | 伝達関数 |
|---------|----------|---------|
| Mixer + Motor | duty → トルク（1次遅れ） | Km / (τm·s + 1) |
| Body | トルク → 角速度（積分器） | 1 / (I·s) |

## 3. P 制御の閉ループ

### 閉ループ伝達関数

```
G_cl(s) = Kp·K / (τ_m·s² + s + Kp·K)
```

### 2次系パラメータ

```
ωn = √(Kp·K / τ_m)
ζ  = 1 / (2·√(Kp·K·τ_m))
```

### 設計式

```
Kp = 1 / (4·ζ²·K·τ_m)
```

## 4. StampFly のパラメータ

| パラメータ | 記号 | Roll | Pitch | Yaw | 単位 |
|-----------|------|------|-------|-----|------|
| 慣性モーメント | I | 9.16e-6 | 13.3e-6 | 20.4e-6 | kg·m² |
| モータ時定数 | τ_m | 0.02 | 0.02 | 0.02 | s |
| 実効プラントゲイン | K | ~102 | ~70 | ~19 | rad/s² |

### ゲイン設計表

| 軸 | K | Kp=0.5 の ζ | ζ=0.7 の Kp | ζ=1.0 の Kp |
|---|---|-----------|-----------|-----------|
| Roll | 102 | 0.50 | 0.25 | 0.12 |
| Pitch | 70 | 0.60 | 0.36 | 0.18 |
| Yaw | 19 | 1.15 | 1.34 | 0.66 |

### なぜ軸ごとに Kp を変えるべきか

- Roll: `Kp=0.5` → `ζ=0.50`（やや振動的、~16% オーバーシュート）
- Pitch: `Kp=0.5` → `ζ=0.60`（適度なオーバーシュート）
- Yaw: `Kp=0.5` → `ζ=1.15`（過減衰、応答が遅い）

全軸同じ Kp では最適な応答が得られない。モデルベースの設計で軸ごとに調整する。

## 5. 実習手順

### ステップ 1: 設計式を実装

`user_code.cpp` に設計式を書く:

```cpp
float zeta = 0.7f;
float Kp_roll  = 1.0f / (4.0f * zeta * zeta * K_roll  * tau_m);
float Kp_pitch = 1.0f / (4.0f * zeta * zeta * K_pitch * tau_m);
float Kp_yaw   = 1.0f / (4.0f * zeta * zeta * K_yaw   * tau_m);
```

### ステップ 2: 比較飛行

1. まず `zeta = 0.7` で飛行
2. `zeta = 0.5` に変更して飛行（L05 の Kp=0.5 相当）
3. `zeta = 1.0` に変更して飛行（臨界減衰）
4. 違いを体感する

### チャレンジ

- `sf log wifi` でステップ応答を記録し、理論値と比較する
- Roll と Yaw の応答の違いを ζ の差で説明する

## 6. 参考資料

| リソース | 説明 |
|---------|------|
| `tools/sysid/defaults.py` | デフォルト物理パラメータ |
| `sf sim run loop_shaping` | インタラクティブ PID チューニング |
| `sf log wifi` | リアルタイムテレメトリ取得 |

---

<a id="english"></a>

## 1. Overview

### About This Lesson

Model the single-axis angular rate control of StampFly using transfer functions,
then design P gains based on second-order system theory.
Verify what damping ratio ζ the empirical `Kp=0.5` from L05 actually provides,
and compute optimal per-axis Kp from a target ζ.

### Prerequisites

- L05: Rate P control and first flight
- L06: PID control
- L07: Step response experiment

## 2. Plant Transfer Function

### Block Diagram

```
u ──▶ [Mixer + Motor: Km/(τm·s+1)] ──τ──▶ [Body: 1/(I·s)] ──▶ ω
```

### Combined Transfer Function

```
G_p(s) = K / (s * (τ_m * s + 1)),    K = K_m / I
```

| Block | Physical Meaning | Transfer Function |
|-------|-----------------|-------------------|
| Mixer + Motor | duty → torque (1st-order lag) | Km / (τm·s + 1) |
| Body | torque → angular rate (integrator) | 1 / (I·s) |

## 3. Closed-Loop with P Control

### Closed-Loop Transfer Function

```
G_cl(s) = Kp·K / (τ_m·s² + s + Kp·K)
```

### Second-Order Parameters

```
ωn = √(Kp·K / τ_m)
ζ  = 1 / (2·√(Kp·K·τ_m))
```

### Design Formula

```
Kp = 1 / (4·ζ²·K·τ_m)
```

## 4. StampFly Parameters

| Parameter | Symbol | Roll | Pitch | Yaw | Unit |
|-----------|--------|------|-------|-----|------|
| Moment of inertia | I | 9.16e-6 | 13.3e-6 | 20.4e-6 | kg·m² |
| Motor time constant | τ_m | 0.02 | 0.02 | 0.02 | s |
| Effective plant gain | K | ~102 | ~70 | ~19 | rad/s² |

### Gain Design Table

| Axis | K | ζ at Kp=0.5 | Kp for ζ=0.7 | Kp for ζ=1.0 |
|------|---|-------------|-------------|-------------|
| Roll | 102 | 0.50 | 0.25 | 0.12 |
| Pitch | 70 | 0.60 | 0.36 | 0.18 |
| Yaw | 19 | 1.15 | 1.34 | 0.66 |

### Why Per-Axis Kp Matters

- Roll: `Kp=0.5` → `ζ=0.50` (slightly oscillatory, ~16% overshoot)
- Pitch: `Kp=0.5` → `ζ=0.60` (moderate overshoot)
- Yaw: `Kp=0.5` → `ζ=1.15` (overdamped, sluggish response)

A single Kp for all axes cannot achieve optimal response. Model-based design enables per-axis tuning.

## 5. Hands-on Procedure

### Step 1: Implement the Design Formula

Write the design formula in `user_code.cpp`:

```cpp
float zeta = 0.7f;
float Kp_roll  = 1.0f / (4.0f * zeta * zeta * K_roll  * tau_m);
float Kp_pitch = 1.0f / (4.0f * zeta * zeta * K_pitch * tau_m);
float Kp_yaw   = 1.0f / (4.0f * zeta * zeta * K_yaw   * tau_m);
```

### Step 2: Comparison Flights

1. Fly with `zeta = 0.7` first
2. Change to `zeta = 0.5` (equivalent to L05's Kp=0.5 for roll)
3. Change to `zeta = 1.0` (critically damped)
4. Feel the difference

### Challenge

- Record step responses with `sf log wifi` and compare with theoretical values
- Explain the difference between Roll and Yaw responses using ζ

## 6. References

| Resource | Description |
|----------|-------------|
| `tools/sysid/defaults.py` | Default physical parameters |
| `sf sim run loop_shaping` | Interactive PID tuning |
| `sf log wifi` | Real-time telemetry capture |
