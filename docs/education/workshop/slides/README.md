# ワークショップスライド / Workshop Slides

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このディレクトリについて

StampFly ワークショップ（Lesson 0--12）の講義スライドを LaTeX Beamer と PowerPoint の2形式で提供します。全ダイアグラムは TikZ で作成し、両形式で共有しています。

### ディレクトリ構成

| ディレクトリ | 内容 |
|------------|------|
| `tikz/` | TikZ ダイアグラムソース（.tex） |
| `images/` | 生成された PNG（Beamer/PPTX 共用） |
| `beamer/` | LaTeX Beamer スライド（.tex + .sty） |
| `pptx/` | PowerPoint 生成スクリプト + 出力 |
| `diagrams/` | draw.io ソース（参考用） |

## 2. ビルド方法

### 前提条件

```bash
# TeX Live (lualatex + luatexja)
lualatex --version

# Python (python-pptx)
pip install python-pptx Pillow
```

### ビルドコマンド

```bash
make all      # 全ビルド（tikz + beamer + pptx）
make tikz     # TikZ → PDF → PNG のみ
make beamer   # Beamer PDF のみ
make pptx     # PPTX のみ
make clean    # 中間ファイル削除
```

### 個別ビルド

```bash
# TikZ 単体
cd tikz && lualatex motor_layout.tex

# Beamer 単体
cd beamer && lualatex lesson_00.tex

# PPTX 単体
python3 pptx/generate_slides.py --lesson 0
```

## 3. レッスン一覧

| レッスン | タイトル | 内容 |
|---------|---------|------|
| L00 | 環境セットアップ | ビルド → フラッシュ → モニタ |
| L01 | モータ制御 | PWM、duty cycle、モータ配置 |
| L02 | コントローラ入力 | ESP-NOW、スティック値、開ループ |
| L03 | LED 表示 | WS2812、ARM 状態表示 |
| L04 | IMU センサ取得 | 座標系、テレメトリ可視化 |
| L05 | 角速度 P 制御 | P 制御、初フライト |
| L06 | システムモデリング | 伝達関数、Kp 設計 |
| L07 | システム同定 | ログ解析、モデル検証 |
| L08 | PID 制御 | I 項/D 項、アンチワインドアップ |
| L09 | 姿勢推定 | 相補フィルタ + Madgwick/EKF/ESKF 紹介 |
| L10 | API 総覧とアプリケーション開発 | ws:: API 全体 + StampFlyState + sf app new |
| L11 | Python SDK プログラム飛行 | Tello 互換 Python SDK の将来像 |
| L12 | 精密着陸競技会 | 3m 先ヘリポートへの精密着陸タイム競技 |

## 4. ダイアグラム一覧

| ファイル | 内容 | 使用レッスン |
|---------|------|------------|
| `build_flash_flow.tex` | ビルド→フラッシュ→モニタフロー | L0 |
| `motor_layout.tex` | モータ配置・回転方向 | L1 |
| `pwm_waveform.tex` | PWM 波形概念図 | L1 |
| `open_loop.tex` | オープンループ制御ブロック図 | L2 |
| `espnow_dataflow.tex` | ESP-NOW 通信フロー | L2 |
| `led_state_machine.tex` | LED 状態遷移図 | L3 |
| `imu_axes.tex` | IMU 座標系（NED/FRD） | L4 |
| `feedback_block.tex` | フィードバック制御ブロック図 | L5 |
| `pid_block.tex` | PID 制御器ブロック図 | L6 |
| `step_response.tex` | ステップ応答波形 | L7 |
| `mixer_matrix.tex` | モーターミキサー行列 | L8 |
| `gyro_drift.tex` | ジャイロドリフト問題 | L9 |
| `comp_filter.tex` | 相補フィルタブロック図 | L9 |
| `python_sdk_arch.tex` | Python SDK アーキテクチャ | L11 |

## 5. カスタマイズ

### Beamer スタイル

`beamer/stampfly_slides.sty` でテーマ色・フォント・コードスタイルを変更可能:

| 項目 | 変数 | デフォルト |
|------|------|----------|
| メインカラー | `sfblue` | `RGB(0, 120, 200)` |
| 日本語フォント | `\setmainjfont` | Hiragino Kaku Gothic ProN |
| コードスタイル | `sfcpp` / `sfbash` | listings ベース |

### PPTX スタイル

`pptx/generate_slides.py` の定数でフォント・色を変更:

| 項目 | 変数 | デフォルト |
|------|------|----------|
| 日本語フォント | `FONT_JP` | Meiryo |
| コードフォント | `FONT_CODE` | Consolas |
| メインカラー | `SF_BLUE` | `RGB(0, 120, 200)` |

---

<a id="english"></a>

## 1. Overview

### About This Directory

Workshop slides for StampFly Lessons 0--12, available in both LaTeX Beamer and PowerPoint formats. All diagrams are created with TikZ and shared between both formats.

## 2. Build Instructions

### Prerequisites

```bash
# TeX Live (lualatex + luatexja)
lualatex --version

# Python (python-pptx)
pip install python-pptx Pillow
```

### Build Commands

```bash
make all      # Build everything (tikz + beamer + pptx)
make tikz     # TikZ → PDF → PNG only
make beamer   # Beamer PDF only
make pptx     # PPTX only
make clean    # Remove build artifacts
```

## 3. Lesson List

| Lesson | Title | Content |
|--------|-------|---------|
| L00 | Environment Setup | Build → Flash → Monitor |
| L01 | Motor Control | PWM, duty cycle, motor layout |
| L02 | Controller Input | ESP-NOW, stick values, open loop |
| L03 | LED Display | WS2812, ARM state indication |
| L04 | IMU Sensors | Coordinate system, telemetry visualization |
| L05 | P Control + First Flight | P control implementation |
| L06 | System Modeling | Transfer function, Kp design |
| L07 | System Identification | Log analysis, model verification |
| L08 | PID Control | I/D terms, anti-windup |
| L09 | Attitude Estimation | Complementary filter + Madgwick/EKF/ESKF intro |
| L10 | API Overview & App Development | Full ws:: API + StampFlyState + sf app new |
| L11 | Python SDK Programmatic Flight | Tello-compatible Python SDK vision |
| L12 | Precision Landing Competition | 3m helipad precision landing time trial |

## 4. Diagram List

| File | Content | Lesson |
|------|---------|--------|
| `build_flash_flow.tex` | Build → Flash → Monitor flow | L0 |
| `motor_layout.tex` | Motor layout & rotation | L1 |
| `pwm_waveform.tex` | PWM waveform | L1 |
| `open_loop.tex` | Open-loop control block diagram | L2 |
| `espnow_dataflow.tex` | ESP-NOW communication flow | L2 |
| `led_state_machine.tex` | LED state machine | L3 |
| `imu_axes.tex` | IMU axes (NED/FRD) | L4 |
| `feedback_block.tex` | Feedback control block diagram | L5 |
| `pid_block.tex` | PID controller block diagram | L6 |
| `step_response.tex` | Step response waveform | L7 |
| `mixer_matrix.tex` | Motor mixer matrix | L8 |
| `gyro_drift.tex` | Gyro drift problem | L9 |
| `comp_filter.tex` | Complementary filter block diagram | L9 |
| `python_sdk_arch.tex` | Python SDK architecture | L11 |

## 5. Customization

Edit `beamer/stampfly_slides.sty` for Beamer theme or `pptx/generate_slides.py` constants for PowerPoint styling.
