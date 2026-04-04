# StampFly 物理パラメータリファレンス（シミュレータ＆ファームウェア）

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このドキュメントについて

本ドキュメントは、StampFly のシミュレータおよびファームウェアで使用される物理定数・パラメータの一覧である。
シミュレータのパラメータは実機の測定・同定結果に基づいており、各モジュールに散在している値を一箇所にまとめたものである。
ファームウェアのパラメータは `config.hpp` を Single Source of Truth（SSOT）として記載している。

### 対象読者

- シミュレータを使用・改良する開発者
- ファームウェアの制御パラメータを確認・調整する開発者
- 制御系を設計する学生・研究者
- モデルパラメータの根拠を確認したい人

### PID 表記の違い

シミュレータとファームウェアでは PID ゲインの表記形式が異なる。

| 項目 | シミュレータ | ファームウェア |
|------|------------|--------------|
| 表記形式 | Kp / Ki / Kd | Kp / Ti / Td |
| 名称 | 標準形式 | 時定数形式 |

ファームウェアの時定数形式の伝達関数：

```
C(s) = Kp × (1 + 1/(Ti·s) + Td·s / (η·Td·s + 1))
```

標準形式との変換関係：

| 変換 | 式 |
|------|-----|
| Ki → Ti | Ti = Kp / Ki |
| Kd → Td | Td = Kd / Kp |
| Ti → Ki | Ki = Kp / Ti |
| Td → Kd | Kd = Kp × Td |

η は不完全微分フィルタ係数（デフォルト 0.125）。微分項の高周波ゲインを 1/η に制限する。

### 参照ファイル

#### シミュレータ

| モジュール | ファイルパス |
|-----------|-------------|
| 機体ダイナミクス | `simulator/core/dynamics.py` |
| モーター・プロペラ | `simulator/core/motors.py` |
| 剛体物理 | `simulator/core/physics.py` |
| 空気力学 | `simulator/core/aerodynamics.py` |
| IMUセンサ | `simulator/sensors/imu.py` |
| 気圧センサ | `simulator/sensors/barometer.py` |
| モーターミキサー | `simulator/control/motor_mixer.py` |

#### ファームウェア

| モジュール | ファイルパス |
|-----------|-------------|
| パラメータ設定（SSOT） | `firmware/vehicle/main/config.hpp` |
| レート制御 | `firmware/vehicle/main/rate_controller.hpp` |
| 姿勢制御 | `firmware/vehicle/main/attitude_controller.hpp` |
| 高度制御 | `firmware/vehicle/main/altitude_controller.hpp` |
| 位置制御 | `firmware/vehicle/main/position_controller.hpp` |
| ESKF | `firmware/vehicle/components/sf_algo_eskf/include/eskf.hpp` |
| PID | `firmware/vehicle/components/sf_algo_pid/include/pid.hpp` |
| 制御割当 | `firmware/vehicle/components/sf_algo_control/include/control_allocation.hpp` |
| モーターモデル | `firmware/vehicle/components/sf_algo_control/include/motor_model.hpp` |

## 2. 機体パラメータ

### 質量特性

| パラメータ | 記号 | シミュレータ | ファームウェア | 単位 | 備考 |
|-----------|------|------------|--------------|------|------|
| 機体質量 | m | 0.035 | 0.037 | kg | バッテリー込み |
| Roll慣性モーメント | Ixx | 9.16×10⁻⁶ | - | kg·m² | |
| Pitch慣性モーメント | Iyy | 13.3×10⁻⁶ | - | kg·m² | |
| Yaw慣性モーメント | Izz | 20.4×10⁻⁶ | - | kg·m² | |

> **注記:** ファームウェアの機体質量 0.037 kg は高度制御の重力補償（`altitude_control::MASS`）で使用される。シミュレータの 0.035 kg との差は個体差・バッテリー重量の違いによる。

### 機体形状

```
               Front
          FL (M4)   FR (M1)
             ╲   ▲   ╱
              ╲  │  ╱
               ╲ │ ╱
                ╲│╱
                 ╳         ← Center
                ╱│╲
               ╱ │ ╲
              ╱  │  ╲
             ╱   │   ╲
          RL (M3)    RR (M2)
                Rear
```

| パラメータ | 値 | 単位 | 備考 |
|-----------|-----|------|------|
| モーター間距離（対角） | 0.065 | m | 2 × アーム長 |
| アーム長（中心→モーター） | 0.0325 | m | √(x² + y²) = 0.023 × √2 |
| モーメントアーム | 0.023 | m | X/Y座標オフセット（= アーム長/√2） |
| モーター高さ（重心から） | 0.005 | m | |

### 空気抵抗

| パラメータ | 値 | 単位 | 備考 |
|-----------|-----|------|------|
| 並進抗力係数 | 0.1 | - | F_drag = 0.1 × v² |
| 回転抗力係数 | 1×10⁻⁵ | - | τ_drag = 1e-5 × ω² |
| 空気密度 | 1.225 | kg/m³ | 標準大気 |

## 3. モーター・プロペラパラメータ

### モーター配置と回転方向

| モーター | 位置 | X座標 (m) | Y座標 (m) | 回転方向 |
|---------|------|-----------|-----------|----------|
| M1 (FR) | 前右 | +0.023 | +0.023 | CCW |
| M2 (RR) | 後右 | -0.023 | +0.023 | CW |
| M3 (RL) | 後左 | -0.023 | -0.023 | CCW |
| M4 (FL) | 前左 | +0.023 | -0.023 | CW |

### モーター電気特性

| パラメータ | 記号 | 値 | 単位 | 測定方法 |
|-----------|------|-----|------|----------|
| 巻線抵抗 | Rm | 0.34 | Ω | LCRメータ測定 |
| 巻線インダクタンス | Lm | 1.0×10⁻⁶ | H | LCRメータ測定 |
| 回転子慣性モーメント | Jmp | 2.01×10⁻⁸ | kg·m² | 形状・重量から推定 |

### 回転数-電圧特性

電圧 V と角速度 ω の関係は以下のモデルで記述される：

```
V = Am × ω² + Bm × ω + Cm
```

| パラメータ | 記号 | 値 | 単位 | 備考 |
|-----------|------|-----|------|------|
| 2次係数 | Am | 5.39×10⁻⁸ | V/(rad/s)² | 実験同定 |
| 1次係数 | Bm | 6.33×10⁻⁴ | V/(rad/s) | 実験同定 |
| 定数項 | Cm | 1.53×10⁻² | V | 実験同定 |

### 推力・トルク特性

| パラメータ | 記号 | 値 | 単位 | 備考 |
|-----------|------|-----|------|------|
| 推力係数 | Ct | 1.00×10⁻⁸ | N/(rad/s)² | T = Ct × ω² |
| トルク係数 | Cq | 9.71×10⁻¹¹ | N·m/(rad/s)² | Q = Cq × ω² |
| トルク/推力比 | κ | 9.71×10⁻³ | m | κ = Cq/Ct |

### 派生パラメータ

モデルから導出されるパラメータ：

| パラメータ | 記号 | 計算式 | 値 |
|-----------|------|--------|-----|
| 逆起電力定数 | Km | Cq×Rm/Am | 6.12×10⁻⁴ V/(rad/s) |
| 粘性摩擦係数 | Dm | (Bm - Cq×Rm/Am)×(Cq/Am) | 計算値 |
| 静止摩擦 | Qf | Cm×Cq/Am | 計算値 |

### ホバリング条件

機体重量 0.035 kg × 9.81 m/s² = 0.343 N を4モーターで分担：

| 条件 | 値 | 単位 |
|------|-----|------|
| 1モーターあたり推力 | 0.0858 | N |
| ホバリング角速度 | 約2930 | rad/s |
| ホバリング電圧 | 約2.1 | V |

## 4. センサパラメータ

### IMU (BMI270)

| パラメータ | 値 | 単位 | 備考 |
|-----------|-----|------|------|
| サンプルレート | 400 | Hz | |
| ジャイロフルスケール | 2000 | deg/s | 設定可能: 125/250/500/1000/2000 |
| 加速度フルスケール | 8 | g | 設定可能: 2/4/8/16 |
| ジャイロ分解能 | 16 | bit | |
| 加速度分解能 | 16 | bit | |
| ジャイロノイズ密度 | 0.007 | deg/s/√Hz | データシート値 |
| 加速度ノイズ密度 | 120 | µg/√Hz | データシート値 |
| バイアス不安定性（ジャイロ） | 0.1 | deg/s | |
| バイアス不安定性（加速度） | 0.002 | g | |

### 気圧計 (BMP280)

| パラメータ | 値 | 単位 | 備考 |
|-----------|-----|------|------|
| 気圧分解能 | 0.16 | Pa | X16オーバーサンプリング時 |
| 温度分解能 | 0.01 | °C | |
| 気圧ノイズ | 1.3 | Pa RMS | X16オーバーサンプリング時 |
| 温度ノイズ | 0.005 | °C | |
| 基準海面気圧 | 101325 | Pa | 標準大気 |

### 物理定数

| 定数 | 記号 | シミュレータ | ファームウェア | 単位 | 備考 |
|------|------|------------|--------------|------|------|
| 重力加速度 | g | 9.80665 | 9.81 | m/s² | シミュレータは精密値、FWは簡易値 |
| 空気モル質量 | M | 0.0289644 | - | kg/mol | 気圧高度計算用 |
| 気体定数 | R | 8.31447 | - | J/(mol·K) | 気圧高度計算用 |
| 温度減率 | L | 0.0065 | - | K/m | 気圧高度計算用 |

## 5. シミュレータ制御パラメータ

### モーターミキサー

```
m1 = throttle + scale × (-roll + pitch + yaw)   # FR (M1)
m2 = throttle + scale × (-roll - pitch - yaw)   # RR (M2)
m3 = throttle + scale × (+roll - pitch + yaw)   # RL (M3)
m4 = throttle + scale × (+roll + pitch - yaw)   # FL (M4)
```

| パラメータ | 値 | 備考 |
|-----------|-----|------|
| 出力スケール | 0.0676 | 0.25/3.7 |
| アイドル出力 | 0.05 | ARM時スロットル0で5% |
| 最大推力/モーター | 0.15 N | 推定値 |

### PIDゲイン（シミュレータデフォルト）

> **注記:** シミュレータは標準形式（Kp/Ki/Kd）を使用する。ファームウェアの時定数形式との変換は「PID 表記の違い」節を参照。

#### 姿勢制御（角度→角速度）

| 軸 | Kp | Ki | Kd |
|----|-----|-----|-----|
| Roll | 5.0 | 1.0 | 0.0 |
| Pitch | 5.0 | 1.0 | 0.0 |
| Yaw | 0.5 | 0.01 | 0.0 |

#### 角速度制御（角速度→電圧）

| 軸 | Kp | Ki | Kd |
|----|-----|-----|-----|
| Roll rate | 0.2 | 10.0 | 0.002 |
| Pitch rate | 0.2 | 10.0 | 0.002 |
| Yaw rate | 1.0 | 2.0 | 0.001 |

#### 高度制御

| Kp | Ki | Kd |
|-----|-----|-----|
| 10.0 | 5.0 | 5.0 |

### 制御タイミング

| パラメータ | 値 | 単位 |
|-----------|-----|------|
| シミュレーション刻み | 0.001 | s (1 kHz) |
| 制御周期 | 0.01 | s (100 Hz) |
| バッテリー電圧（公称） | 3.7 | V |

## 6. 外乱モデル

シミュレーションでは以下の外乱を付加可能：

| パラメータ | デフォルト値 | 単位 | 備考 |
|-----------|-------------|------|------|
| モーメント外乱（L） | 4.4×10⁻⁶ | N·m | 正規分布σ |
| モーメント外乱（M） | 4.4×10⁻⁶ | N·m | 正規分布σ |
| モーメント外乱（N） | 4.0×10⁻⁶ | N·m | 正規分布σ |
| 力外乱（X, Y, Z） | 1×10⁻⁶ | N | 正規分布σ |

## 7. ファームウェア制御パラメータ

ファームウェアの制御パラメータは `firmware/vehicle/main/config.hpp` で一元管理されている。
PID は時定数形式（Kp/Ti/Td）を使用する（「PID 表記の違い」節参照）。

### レート制御

`config.hpp` namespace: `rate_control`

現在は物理単位モード（`USE_PHYSICAL_UNITS = 1`）がアクティブ。

#### 物理単位モード（出力: トルク [Nm]）

| 軸 | Kp [Nm/(rad/s)] | Ti [s] | Td [s] |
|----|-----------------|--------|--------|
| Roll | 9.10×10⁻⁴ | 0.7 | 0.01 |
| Pitch | 1.33×10⁻³ | 0.7 | 0.01 |
| Yaw | 1.77×10⁻³ | 0.8 | 0.01 |

不完全微分フィルタ係数: η = 0.125

#### レガシー電圧モード（出力: 電圧 [V]）

| 軸 | Kp [V/(rad/s)] | Ti [s] | Td [s] |
|----|----------------|--------|--------|
| Roll | 0.65 | 0.7 | 0.01 |
| Pitch | 0.95 | 0.7 | 0.025 |
| Yaw | 3.0 | 0.8 | 0.01 |

### 姿勢制御

`config.hpp` namespace: `attitude_control`

| 軸 | Kp [(rad/s)/rad] | Ti [s] | Td [s] |
|----|-----------------|--------|--------|
| Roll | 5.0 | 4.0 | 0.04 |
| Pitch | 5.0 | 4.0 | 0.04 |

| パラメータ | 値 | 単位 | 備考 |
|-----------|-----|------|------|
| MAX_RATE_SETPOINT | 3.0 | rad/s | 角速度指令の上限 |
| η | 0.125 | - | 不完全微分フィルタ係数 |

### 高度制御

`config.hpp` namespace: `altitude_control`

| パラメータ | 値 | 単位 |
|-----------|-----|------|
| MASS | 0.037 | kg |
| GRAVITY | 9.81 | m/s² |

#### 高度 PID（位置→速度）

| Kp | Ti [s] | Td [s] | OutputMax [m/s] |
|-----|--------|--------|-----------------|
| 2.0 | 3.0 | 0.1 | 1.0 |

#### 速度 PID（速度→力）

| Kp | Ti [s] | Td [s] | OutputMax [N] |
|-----|--------|--------|---------------|
| 0.3 | 1.0 | 0.02 | 0.2 |

### 位置制御

`config.hpp` namespace: `position_control`

#### 位置 PID（位置→速度）

| Kp | Ti [s] | Td [s] | OutputMax [m/s] |
|-----|--------|--------|-----------------|
| 1.0 | 5.0 | 0.1 | 0.5 |

#### 速度 PID（速度→姿勢角）

| Kp | Ti [s] | Td [s] | OutputMax [rad] |
|-----|--------|--------|-----------------|
| 0.3 | 2.0 | 0.02 | 0.20 |

### ESKF パラメータ

`config.hpp` namespace: `eskf`

| パラメータ | 値 | 単位 |
|-----------|-----|------|
| GRAVITY | 9.81 | m/s² |

#### プロセスノイズ

| パラメータ | 値 | 備考 |
|-----------|-----|------|
| GYRO_NOISE | 0.009655 | ジャイロ測定ノイズ |
| ACCEL_NOISE | 0.062885 | 加速度測定ノイズ |
| GYRO_BIAS_NOISE | 0.000013 | ジャイロバイアスランダムウォーク |
| ACCEL_BIAS_NOISE | 0.001 | 加速度バイアスランダムウォーク |

#### 観測ノイズ

| パラメータ | 値 | 備考 |
|-----------|-----|------|
| BARO_NOISE | 0.1 | 気圧高度 |
| TOF_NOISE | 0.03 | ToF測距 |
| MAG_NOISE | 1.0 | 地磁気 |
| FLOW_NOISE | 0.01 | オプティカルフロー |
| ACCEL_ATT_NOISE | 0.06 | 加速度ベース姿勢 |

#### χ² ゲート閾値

| 観測 | 閾値 | 自由度 |
|------|------|--------|
| BARO | 3.84 | 1 |
| TOF | 3.84 | 1 |
| MAG | 7.81 | 3 |
| FLOW | 5.99 | 2 |
| ACCEL_ATT | 7.81 | 3 |

### LPF 設定

`config.hpp` namespace: `lpf`

| パラメータ | 値 | 単位 |
|-----------|-----|------|
| ACCEL_CUTOFF_HZ | 50.0 | Hz |
| GYRO_CUTOFF_HZ | 100.0 | Hz |

#### ジャイロノッチフィルタ

| パラメータ | 値 | 備考 |
|-----------|-----|------|
| ENABLED | false | デフォルト無効 |
| CENTER_FREQ | 12.0 | Hz |
| Q | 5.0 | Q値 |

### 安全パラメータ

`config.hpp` namespace: `safety`

| パラメータ | 値 | 単位 | 備考 |
|-----------|-----|------|------|
| IMPACT_ACCEL_THRESHOLD | 3.0 | G | 衝撃検出閾値 |
| IMPACT_GYRO_THRESHOLD | 800 | deg/s | 衝撃検出閾値 |

---

<a id="english"></a>

## 1. Overview

### About This Document

This document provides a comprehensive list of physical constants and parameters used in both the StampFly simulator and firmware.
Simulator parameters are based on measurements and system identification from the actual aircraft, consolidated from various simulator modules.
Firmware parameters are documented with `config.hpp` as the Single Source of Truth (SSOT).

### Target Audience

- Developers using or improving the simulator
- Developers checking or tuning firmware control parameters
- Students and researchers designing control systems
- Anyone verifying the basis of model parameters

### PID Notation Differences

The simulator and firmware use different PID gain notations.

| Item | Simulator | Firmware |
|------|-----------|----------|
| Notation | Kp / Ki / Kd | Kp / Ti / Td |
| Name | Standard form | Time-constant form |

Firmware time-constant form transfer function:

```
C(s) = Kp × (1 + 1/(Ti·s) + Td·s / (η·Td·s + 1))
```

Conversion between forms:

| Conversion | Formula |
|-----------|---------|
| Ki → Ti | Ti = Kp / Ki |
| Kd → Td | Td = Kd / Kp |
| Ti → Ki | Ki = Kp / Ti |
| Td → Kd | Kd = Kp × Td |

η is the incomplete derivative filter coefficient (default 0.125). It limits the high-frequency gain of the derivative term to 1/η.

### Reference Files

#### Simulator

| Module | File Path |
|--------|-----------|
| Vehicle Dynamics | `simulator/core/dynamics.py` |
| Motor & Propeller | `simulator/core/motors.py` |
| Rigid Body Physics | `simulator/core/physics.py` |
| Aerodynamics | `simulator/core/aerodynamics.py` |
| IMU Sensor | `simulator/sensors/imu.py` |
| Barometric Sensor | `simulator/sensors/barometer.py` |
| Motor Mixer | `simulator/control/motor_mixer.py` |

#### Firmware

| Module | File Path |
|--------|-----------|
| Parameter Config (SSOT) | `firmware/vehicle/main/config.hpp` |
| Rate Control | `firmware/vehicle/main/rate_controller.hpp` |
| Attitude Control | `firmware/vehicle/main/attitude_controller.hpp` |
| Altitude Control | `firmware/vehicle/main/altitude_controller.hpp` |
| Position Control | `firmware/vehicle/main/position_controller.hpp` |
| ESKF | `firmware/vehicle/components/sf_algo_eskf/include/eskf.hpp` |
| PID | `firmware/vehicle/components/sf_algo_pid/include/pid.hpp` |
| Control Allocation | `firmware/vehicle/components/sf_algo_control/include/control_allocation.hpp` |
| Motor Model | `firmware/vehicle/components/sf_algo_control/include/motor_model.hpp` |

## 2. Vehicle Parameters

### Mass Properties

| Parameter | Symbol | Simulator | Firmware | Unit | Notes |
|-----------|--------|-----------|----------|------|-------|
| Vehicle Mass | m | 0.035 | 0.037 | kg | Including battery |
| Roll Moment of Inertia | Ixx | 9.16×10⁻⁶ | - | kg·m² | |
| Pitch Moment of Inertia | Iyy | 13.3×10⁻⁶ | - | kg·m² | |
| Yaw Moment of Inertia | Izz | 20.4×10⁻⁶ | - | kg·m² | |

> **Note:** The firmware mass of 0.037 kg is used for gravity compensation in altitude control (`altitude_control::MASS`). The difference from the simulator's 0.035 kg is due to unit variation and battery weight differences.

### Vehicle Geometry

```
               Front
          FL (M4)   FR (M1)
             ╲   ▲   ╱
              ╲  │  ╱
               ╲ │ ╱
                ╲│╱
                 ╳         ← Center
                ╱│╲
               ╱ │ ╲
              ╱  │  ╲
             ╱   │   ╲
          RL (M3)    RR (M2)
                Rear
```

| Parameter | Value | Unit | Notes |
|-----------|-------|------|-------|
| Motor-to-motor distance (diagonal) | 0.065 | m | 2 × arm length |
| Arm length (center to motor) | 0.0325 | m | √(x² + y²) = 0.023 × √2 |
| Moment arm | 0.023 | m | X/Y coordinate offset (= arm length/√2) |
| Motor height (from CG) | 0.005 | m | |

### Aerodynamic Drag

| Parameter | Value | Unit | Notes |
|-----------|-------|------|-------|
| Translational drag coefficient | 0.1 | - | F_drag = 0.1 × v² |
| Rotational drag coefficient | 1×10⁻⁵ | - | τ_drag = 1e-5 × ω² |
| Air density | 1.225 | kg/m³ | Standard atmosphere |

## 3. Motor & Propeller Parameters

### Motor Layout and Rotation Direction

| Motor | Position | X (m) | Y (m) | Rotation |
|-------|----------|-------|-------|----------|
| M1 (FR) | Front-Right | +0.023 | +0.023 | CCW |
| M2 (RR) | Rear-Right | -0.023 | +0.023 | CW |
| M3 (RL) | Rear-Left | -0.023 | -0.023 | CCW |
| M4 (FL) | Front-Left | +0.023 | -0.023 | CW |

### Motor Electrical Characteristics

| Parameter | Symbol | Value | Unit | Method |
|-----------|--------|-------|------|--------|
| Winding Resistance | Rm | 0.34 | Ω | LCR meter |
| Winding Inductance | Lm | 1.0×10⁻⁶ | H | LCR meter |
| Rotor Inertia | Jmp | 2.01×10⁻⁸ | kg·m² | Estimated from geometry |

### Speed-Voltage Relationship

The relationship between voltage V and angular velocity ω:

```
V = Am × ω² + Bm × ω + Cm
```

| Parameter | Symbol | Value | Unit | Notes |
|-----------|--------|-------|------|-------|
| Quadratic coefficient | Am | 5.39×10⁻⁸ | V/(rad/s)² | Experimental |
| Linear coefficient | Bm | 6.33×10⁻⁴ | V/(rad/s) | Experimental |
| Constant term | Cm | 1.53×10⁻² | V | Experimental |

### Thrust & Torque Characteristics

| Parameter | Symbol | Value | Unit | Notes |
|-----------|--------|-------|------|-------|
| Thrust coefficient | Ct | 1.00×10⁻⁸ | N/(rad/s)² | T = Ct × ω² |
| Torque coefficient | Cq | 9.71×10⁻¹¹ | N·m/(rad/s)² | Q = Cq × ω² |
| Torque/Thrust ratio | κ | 9.71×10⁻³ | m | κ = Cq/Ct |

### Derived Parameters

| Parameter | Symbol | Formula | Value |
|-----------|--------|---------|-------|
| Back-EMF constant | Km | Cq×Rm/Am | 6.12×10⁻⁴ V/(rad/s) |
| Viscous friction | Dm | (Bm - Cq×Rm/Am)×(Cq/Am) | computed |
| Static friction | Qf | Cm×Cq/Am | computed |

### Hover Conditions

Vehicle weight 0.035 kg × 9.81 m/s² = 0.343 N shared by 4 motors:

| Condition | Value | Unit |
|-----------|-------|------|
| Thrust per motor | 0.0858 | N |
| Hover angular velocity | ~2930 | rad/s |
| Hover voltage | ~2.1 | V |

## 4. Sensor Parameters

### IMU (BMI270)

| Parameter | Value | Unit | Notes |
|-----------|-------|------|-------|
| Sample rate | 400 | Hz | |
| Gyro full scale | 2000 | deg/s | Configurable: 125/250/500/1000/2000 |
| Accel full scale | 8 | g | Configurable: 2/4/8/16 |
| Gyro resolution | 16 | bit | |
| Accel resolution | 16 | bit | |
| Gyro noise density | 0.007 | deg/s/√Hz | From datasheet |
| Accel noise density | 120 | µg/√Hz | From datasheet |
| Gyro bias instability | 0.1 | deg/s | |
| Accel bias instability | 0.002 | g | |

### Barometer (BMP280)

| Parameter | Value | Unit | Notes |
|-----------|-------|------|-------|
| Pressure resolution | 0.16 | Pa | X16 oversampling |
| Temperature resolution | 0.01 | °C | |
| Pressure noise | 1.3 | Pa RMS | X16 oversampling |
| Temperature noise | 0.005 | °C | |
| Sea level pressure | 101325 | Pa | Standard atmosphere |

### Physical Constants

| Constant | Symbol | Simulator | Firmware | Unit | Notes |
|----------|--------|-----------|----------|------|-------|
| Gravity | g | 9.80665 | 9.81 | m/s² | Simulator uses precise value, FW uses simplified |
| Molar mass of air | M | 0.0289644 | - | kg/mol | For barometric altitude |
| Gas constant | R | 8.31447 | - | J/(mol·K) | For barometric altitude |
| Temperature lapse rate | L | 0.0065 | - | K/m | For barometric altitude |

## 5. Simulator Control Parameters

### Motor Mixer

```
m1 = throttle + scale × (-roll + pitch + yaw)   # FR (M1)
m2 = throttle + scale × (-roll - pitch - yaw)   # RR (M2)
m3 = throttle + scale × (+roll - pitch + yaw)   # RL (M3)
m4 = throttle + scale × (+roll + pitch - yaw)   # FL (M4)
```

| Parameter | Value | Notes |
|-----------|-------|-------|
| Output scale | 0.0676 | 0.25/3.7 |
| Idle output | 0.05 | 5% when armed at zero throttle |
| Max thrust/motor | 0.15 N | Estimated |

### PID Gains (Simulator Default)

> **Note:** The simulator uses standard form (Kp/Ki/Kd). See "PID Notation Differences" for conversion to firmware time-constant form.

#### Attitude Control (angle → rate)

| Axis | Kp | Ki | Kd |
|------|-----|-----|-----|
| Roll | 5.0 | 1.0 | 0.0 |
| Pitch | 5.0 | 1.0 | 0.0 |
| Yaw | 0.5 | 0.01 | 0.0 |

#### Rate Control (rate → voltage)

| Axis | Kp | Ki | Kd |
|------|-----|-----|-----|
| Roll rate | 0.2 | 10.0 | 0.002 |
| Pitch rate | 0.2 | 10.0 | 0.002 |
| Yaw rate | 1.0 | 2.0 | 0.001 |

#### Altitude Control

| Kp | Ki | Kd |
|-----|-----|-----|
| 10.0 | 5.0 | 5.0 |

### Control Timing

| Parameter | Value | Unit |
|-----------|-------|------|
| Simulation step | 0.001 | s (1 kHz) |
| Control period | 0.01 | s (100 Hz) |
| Battery voltage (nominal) | 3.7 | V |

## 6. Disturbance Model

The following disturbances can be added in simulation:

| Parameter | Default | Unit | Notes |
|-----------|---------|------|-------|
| Moment disturbance (L) | 4.4×10⁻⁶ | N·m | Normal dist. σ |
| Moment disturbance (M) | 4.4×10⁻⁶ | N·m | Normal dist. σ |
| Moment disturbance (N) | 4.0×10⁻⁶ | N·m | Normal dist. σ |
| Force disturbance (X, Y, Z) | 1×10⁻⁶ | N | Normal dist. σ |

## 7. Firmware Control Parameters

Firmware control parameters are centrally managed in `firmware/vehicle/main/config.hpp`.
PID uses time-constant form (Kp/Ti/Td) — see "PID Notation Differences" for details.

### Rate Control

`config.hpp` namespace: `rate_control`

Currently the physical-units mode (`USE_PHYSICAL_UNITS = 1`) is active.

#### Physical-Units Mode (output: torque [Nm])

| Axis | Kp [Nm/(rad/s)] | Ti [s] | Td [s] |
|------|-----------------|--------|--------|
| Roll | 9.10×10⁻⁴ | 0.7 | 0.01 |
| Pitch | 1.33×10⁻³ | 0.7 | 0.01 |
| Yaw | 1.77×10⁻³ | 0.8 | 0.01 |

Incomplete derivative filter coefficient: η = 0.125

#### Legacy Voltage Mode (output: voltage [V])

| Axis | Kp [V/(rad/s)] | Ti [s] | Td [s] |
|------|----------------|--------|--------|
| Roll | 0.65 | 0.7 | 0.01 |
| Pitch | 0.95 | 0.7 | 0.025 |
| Yaw | 3.0 | 0.8 | 0.01 |

### Attitude Control

`config.hpp` namespace: `attitude_control`

| Axis | Kp [(rad/s)/rad] | Ti [s] | Td [s] |
|------|-----------------|--------|--------|
| Roll | 5.0 | 4.0 | 0.04 |
| Pitch | 5.0 | 4.0 | 0.04 |

| Parameter | Value | Unit | Notes |
|-----------|-------|------|-------|
| MAX_RATE_SETPOINT | 3.0 | rad/s | Rate command upper limit |
| η | 0.125 | - | Incomplete derivative filter coefficient |

### Altitude Control

`config.hpp` namespace: `altitude_control`

| Parameter | Value | Unit |
|-----------|-------|------|
| MASS | 0.037 | kg |
| GRAVITY | 9.81 | m/s² |

#### Altitude PID (position → velocity)

| Kp | Ti [s] | Td [s] | OutputMax [m/s] |
|-----|--------|--------|-----------------|
| 2.0 | 3.0 | 0.1 | 1.0 |

#### Velocity PID (velocity → force)

| Kp | Ti [s] | Td [s] | OutputMax [N] |
|-----|--------|--------|---------------|
| 0.3 | 1.0 | 0.02 | 0.2 |

### Position Control

`config.hpp` namespace: `position_control`

#### Position PID (position → velocity)

| Kp | Ti [s] | Td [s] | OutputMax [m/s] |
|-----|--------|--------|-----------------|
| 1.0 | 5.0 | 0.1 | 0.5 |

#### Velocity PID (velocity → attitude angle)

| Kp | Ti [s] | Td [s] | OutputMax [rad] |
|-----|--------|--------|-----------------|
| 0.3 | 2.0 | 0.02 | 0.20 |

### ESKF Parameters

`config.hpp` namespace: `eskf`

| Parameter | Value | Unit |
|-----------|-------|------|
| GRAVITY | 9.81 | m/s² |

#### Process Noise

| Parameter | Value | Notes |
|-----------|-------|-------|
| GYRO_NOISE | 0.009655 | Gyro measurement noise |
| ACCEL_NOISE | 0.062885 | Accelerometer measurement noise |
| GYRO_BIAS_NOISE | 0.000013 | Gyro bias random walk |
| ACCEL_BIAS_NOISE | 0.001 | Accelerometer bias random walk |

#### Observation Noise

| Parameter | Value | Notes |
|-----------|-------|-------|
| BARO_NOISE | 0.1 | Barometric altitude |
| TOF_NOISE | 0.03 | ToF ranging |
| MAG_NOISE | 1.0 | Magnetometer |
| FLOW_NOISE | 0.01 | Optical flow |
| ACCEL_ATT_NOISE | 0.06 | Accelerometer-based attitude |

#### Chi-squared Gate Thresholds

| Observation | Threshold | Degrees of Freedom |
|-------------|-----------|-------------------|
| BARO | 3.84 | 1 |
| TOF | 3.84 | 1 |
| MAG | 7.81 | 3 |
| FLOW | 5.99 | 2 |
| ACCEL_ATT | 7.81 | 3 |

### LPF Settings

`config.hpp` namespace: `lpf`

| Parameter | Value | Unit |
|-----------|-------|------|
| ACCEL_CUTOFF_HZ | 50.0 | Hz |
| GYRO_CUTOFF_HZ | 100.0 | Hz |

#### Gyro Notch Filter

| Parameter | Value | Notes |
|-----------|-------|-------|
| ENABLED | false | Disabled by default |
| CENTER_FREQ | 12.0 | Hz |
| Q | 5.0 | Quality factor |

### Safety Parameters

`config.hpp` namespace: `safety`

| Parameter | Value | Unit | Notes |
|-----------|-------|------|-------|
| IMPACT_ACCEL_THRESHOLD | 3.0 | G | Impact detection threshold |
| IMPACT_GYRO_THRESHOLD | 800 | deg/s | Impact detection threshold |
