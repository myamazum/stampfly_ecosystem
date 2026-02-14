# ワークショップスライド / Workshop Slides

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このディレクトリについて

StampFly ワークショップ（Lesson 0--3）の講義スライドを LaTeX Beamer と PowerPoint の2形式で提供します。全ダイアグラムは TikZ で作成し、両形式で共有しています。

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

## 3. ダイアグラム一覧

| ファイル | 内容 | 使用レッスン |
|---------|------|------------|
| `motor_layout.tex` | モータ配置・回転方向 | L1 |
| `pwm_waveform.tex` | PWM 波形概念図 | L1 |
| `open_loop.tex` | オープンループ制御ブロック図 | L2 |
| `build_flash_flow.tex` | ビルド→フラッシュ→モニタフロー | L0 |
| `espnow_dataflow.tex` | ESP-NOW 通信フロー | L2 |
| `led_state_machine.tex` | LED 状態遷移図 | L3 |

## 4. カスタマイズ

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

Workshop slides for StampFly Lessons 0--3, available in both LaTeX Beamer and PowerPoint formats. All diagrams are created with TikZ and shared between both formats.

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

## 3. Diagram List

| File | Content | Lesson |
|------|---------|--------|
| `motor_layout.tex` | Motor layout & rotation | L1 |
| `pwm_waveform.tex` | PWM waveform | L1 |
| `open_loop.tex` | Open-loop control block diagram | L2 |
| `build_flash_flow.tex` | Build → Flash → Monitor flow | L0 |
| `espnow_dataflow.tex` | ESP-NOW communication flow | L2 |
| `led_state_machine.tex` | LED state machine | L3 |

## 4. Customization

Edit `beamer/stampfly_slides.sty` for Beamer theme or `pptx/generate_slides.py` constants for PowerPoint styling.
