# ワークショップスライド / Workshop Slides

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このディレクトリについて

StampFly ワークショップ（Lesson 0--13）の講義スライドを LaTeX Beamer で提供します。全ダイアグラムは TikZ で作成しています。全レッスンは `beamer/main.tex` に統合された1つの PDF として配布します。

### ディレクトリ構成

| ディレクトリ | 内容 |
|------------|------|
| `beamer/` | LaTeX Beamer スライド |
| `beamer/chapters/` | レッスン別チャプターファイル（内容ベース命名） |
| `beamer/main.tex` | 統合メインファイル（全チャプターを `\input`） |
| `beamer/stampfly_slides.sty` | 共通スタイル |
| `beamer/preamble.tex` | 追加プリアンブル設定 |
| `tikz/` | TikZ ダイアグラムソース（.tex） |
| `images/` | 生成された PNG |

## 2. ビルド方法

### 前提条件

```bash
# TeX Live (lualatex + luatexja)
lualatex --version
```

### ビルドコマンド

```bash
make all       # 全ビルド（tikz + main）
make main      # 統合PDF（全レッスン）
make tikz      # TikZ → PDF → PNG のみ
make chapter NAME=led_control  # 単一チャプター（高速イテレーション用）
make beamer    # レガシー個別PDF
make clean     # 中間ファイル削除
```

### 個別ビルド

```bash
# TikZ 単体
cd tikz && lualatex motor_layout.tex

# 統合PDF
cd beamer && lualatex main.tex && lualatex main.tex
```

## 3. レッスン一覧

| レッスン | チャプターファイル | タイトル |
|---------|------------------|---------|
| L00 | `environment_setup.tex` | 環境セットアップ |
| L01 | `motor_control.tex` | モータ制御 |
| L02 | `controller_input.tex` | コントローラ入力 |
| L03 | `led_control.tex` | LED制御 |
| L04 | `imu_sensor.tex` | IMUセンサー |
| L05 | `rate_p_control.tex` | レートP制御 + 初フライト |
| L06 | `system_modeling.tex` | システムモデリング |
| L07 | `system_identification.tex` | システム同定 |
| L08 | `pid_control.tex` | PID制御 |
| L09 | `attitude_estimation.tex` | 姿勢推定 |
| L10 | `api_reference.tex` | ws:: APIリファレンス |
| L11 | `custom_firmware.tex` | 独自ファームウェア開発 |
| L12 | `python_sdk.tex` | Python SDK プログラム飛行 |
| L13 | `precision_landing.tex` | 精密着陸競技会 |

## 4. コードスニペット連携

ファームウェアソースからスライド内のコードを自動抽出できます:

```bash
# スニペットの検証
python3 tools/extract_snippets.py check -v

# 展開（.build_chapters/ に出力）
python3 tools/extract_snippets.py expand
```

ソースファイルに `@@snippet: name` / `@@end-snippet: name` マーカーを設置し、
`.tex` 側で `%%SNIPPET:lesson_03_led/solution.cpp:setup+loop%%` で参照します。

## 5. カスタマイズ

### Beamer スタイル

`beamer/stampfly_slides.sty` でテーマ色・フォント・コードスタイルを変更可能:

| 項目 | 変数 | デフォルト |
|------|------|----------|
| メインカラー | `sfblue` | `RGB(0, 120, 200)` |
| 日本語フォント | `\setmainjfont` | Hiragino Kaku Gothic ProN |
| コードスタイル | `sfcpp` / `sfbash` | listings ベース |

---

<a id="english"></a>

## 1. Overview

### About This Directory

Workshop slides for StampFly Lessons 0--13 in LaTeX Beamer format. All diagrams are created with TikZ. All lessons are unified into a single PDF via `beamer/main.tex`.

## 2. Build Instructions

### Prerequisites

```bash
# TeX Live (lualatex + luatexja)
lualatex --version
```

### Build Commands

```bash
make all       # Build everything (tikz + main)
make main      # Unified PDF (all lessons)
make tikz      # TikZ → PDF → PNG only
make chapter NAME=led_control  # Single chapter (fast iteration)
make beamer    # Legacy individual PDFs
make clean     # Remove build artifacts
```

## 3. Lesson List

| Lesson | Chapter File | Title |
|--------|-------------|-------|
| L00 | `environment_setup.tex` | Environment Setup |
| L01 | `motor_control.tex` | Motor Control |
| L02 | `controller_input.tex` | Controller Input |
| L03 | `led_control.tex` | LED Control |
| L04 | `imu_sensor.tex` | IMU Sensor |
| L05 | `rate_p_control.tex` | Rate P-Control + First Flight |
| L06 | `system_modeling.tex` | System Modeling |
| L07 | `system_identification.tex` | System Identification |
| L08 | `pid_control.tex` | PID Control |
| L09 | `attitude_estimation.tex` | Attitude Estimation |
| L10 | `api_reference.tex` | ws:: API Reference |
| L11 | `custom_firmware.tex` | Custom Firmware Development |
| L12 | `python_sdk.tex` | Python SDK Programmatic Flight |
| L13 | `precision_landing.tex` | Precision Landing Competition |

## 4. Code Snippet Integration

Auto-extract code from firmware source into slides:

```bash
python3 tools/extract_snippets.py check -v   # Verify snippets
python3 tools/extract_snippets.py expand      # Expand to .build_chapters/
```

## 5. Customization

Edit `beamer/stampfly_slides.sty` for Beamer theme customization.
