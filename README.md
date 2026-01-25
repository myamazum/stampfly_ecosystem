# StampFly Ecosystem

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 自分の手で、ドローンを飛ばす制御を作りたいあなたへ

**StampFly Ecosystem** は、ドローン制御を**学び、実装し、実験する**ための
教育・研究プラットフォームです。

「PID制御を教科書で学んだけど、実際に動くものを作りたい」
「姿勢推定アルゴリズムを自分で実装して試したい」
「研究用の飛行実験プラットフォームが欲しい」

そんなあなたのために、このエコシステムは存在します。

---

## 何ができるのか？

| できること | 内容 |
|-----------|------|
| **シミュレータで練習** | 実機なしでドローン操縦を体験。制御アルゴリズムの検証にも |
| **すぐに飛ばせる** | ファームウェアをビルドして、実機で飛行 |
| **WiFi経由で制御** | PC/スマホから高レベルコマンド（jump, takeoff, land, hover）を実行 |
| **制御を自作できる** | 角速度制御のスケルトンコードを提供。姿勢制御、位置制御を自分で実装 |
| **センサーデータを見れる** | IMU、気圧、ToF、オプティカルフロー等のリアルタイムデータをCLI/WiFiで取得 |
| **実験データを解析できる** | ログを記録し、Pythonで解析・可視化 |

---

## 📦 インストール

```bash
git clone https://github.com/M5Fly-kanazawa/stampfly_ecosystem.git
cd stampfly-ecosystem
./install.sh
```

これだけで sf CLI とシミュレータ依存がインストールされます。
ESP-IDFが未インストールの場合は、インストーラが案内します。

**→ [セットアップガイド（詳細）](docs/setup/README.md)**

---

## 🎮 まずはシミュレータで飛ばしてみよう！

**実機がなくても大丈夫。** コントローラとPCがあれば、今すぐドローン操縦を体験できます。

### VPython版（軽量・ブラウザ表示）

```bash
sf sim run vpython
```

### Genesis版（高精度物理エンジン）

```bash
sf sim run genesis
```

コントローラをUSB HIDモードに切り替えてPCに接続すれば、
3Dビューでドローンを自由に飛ばせます。

| シミュレータ | 特徴 |
|-------------|------|
| VPython版 | 軽量、センサモデル充実、SIL/HIL対応 |
| Genesis版 | 2000Hz物理演算、物理量ベース制御 |

**→ [シミュレータで遊ぶ（詳細手順）](docs/getting-started.md#0-まずはシミュレータで遊んでみよう)**

---

## 🚀 sf CLI クイックスタート

**sf CLI** は、ビルド、書き込み、モニタ、ログ取得などをシンプルに実行できる統合コマンドラインツールです。

```bash
# 環境をアクティブ化
source ~/esp/esp-idf/export.sh

# 環境診断
sf doctor

# ビルド → 書き込み → モニタ
sf build vehicle && sf flash vehicle -m
```

### よく使うコマンド

| コマンド | 説明 |
|---------|------|
| `sf build vehicle` | 機体ファームウェアをビルド |
| `sf flash vehicle -m` | 書き込み後にモニタを開く |
| `sf monitor` | シリアルモニタを開く |
| `sf log wifi` | WiFiテレメトリをキャプチャ |
| `sf cal gyro` | ジャイロキャリブレーション |
| `sf sim run vpython` | シミュレータを起動 |

**→ [コマンドリファレンス](docs/commands/README.md)** | **[セットアップガイド](docs/setup/README.md)**

---

## ディレクトリ構成

```
stampfly-ecosystem/
├── docs/           # ドキュメント
├── firmware/       # 組込みファームウェア
│   ├── vehicle/    # 機体ファームウェア
│   ├── controller/ # 送信機ファームウェア
│   └── common/     # 共有コード（構築中）
├── protocol/       # 通信プロトコル仕様（構築中）
├── control/        # 制御設計資産（構築中）
├── analysis/       # 実験データ解析（構築中）
├── tools/          # 補助ツール（構築中）
├── simulator/      # 3Dフライトシミュレータ
└── third_party/    # 外部依存
```

---

## 始めよう

**→ [Getting Started（環境構築〜初フライト）](docs/getting-started.md)**

ESP-IDFのセットアップから、ファームウェアのビルド、
機体と送信機のペアリング、そして初フライトまで。
すべての手順をステップバイステップで解説しています。

---

## 技術仕様

| 項目 | 仕様 |
|------|------|
| MCU | ESP32-S3（M5Stamp S3） |
| フレームワーク | ESP-IDF v5.5.2 + FreeRTOS |
| 姿勢推定 | ESKF（Error-State Kalman Filter） |
| 通信 | ESP-NOW + WiFi（テレメトリ） |
| センサー | BMI270, BMM150, BMP280, VL53L3CX, PMW3901 |

---

## ライセンス

MIT License

---

---

<a id="english"></a>

# StampFly Ecosystem

## For those who want to build their own drone control

**StampFly Ecosystem** is an educational and research platform for
**learning, implementing, and experimenting** with drone control.

"I learned PID control from textbooks, but I want to build something that actually flies."
"I want to implement my own attitude estimation algorithm and test it."
"I need a flight experiment platform for my research."

This ecosystem exists for you.

---

## What can you do?

| Capability | Description |
|-----------|-------------|
| **Practice in simulator** | Experience drone piloting without real hardware. Also for testing control algorithms |
| **Fly immediately** | Build firmware and fly the real drone |
| **Build your own control** | Rate control skeleton provided. Implement attitude/position control yourself |
| **View sensor data** | Real-time IMU, barometer, ToF, optical flow data via CLI/WiFi |
| **Analyze experiments** | Record flight logs and analyze with Python |

---

## 📦 Installation

```bash
git clone https://github.com/M5Fly-kanazawa/stampfly_ecosystem.git
cd stampfly-ecosystem
./install.sh
```

This installs sf CLI and simulator dependencies.
If ESP-IDF is not installed, the installer will guide you.

**→ [Setup Guide (Details)](docs/setup/README.md)**

---

## 🎮 Try the Simulator First!

**No drone needed.** With just a controller and PC, you can experience drone piloting right now.

### VPython Version (Lightweight, Browser)

```bash
sf sim run vpython
```

### Genesis Version (High-Precision Physics)

```bash
sf sim run genesis
```

Switch the controller to USB HID mode and connect to your PC.
You can fly a drone freely in the 3D view.

| Simulator | Features |
|-----------|----------|
| VPython | Lightweight, rich sensor models, SIL/HIL |
| Genesis | 2000Hz physics, physical-unit control |

**→ [Play with the Simulator (Detailed Steps)](docs/getting-started.md#0-try-the-simulator-first)**

---

## 🚀 sf CLI Quick Start

**sf CLI** is an integrated command-line tool for build, flash, monitor, log capture, and more.

```bash
# Activate environment
source ~/esp/esp-idf/export.sh

# Run diagnostics
sf doctor

# Build → Flash → Monitor
sf build vehicle && sf flash vehicle -m
```

### Common Commands

| Command | Description |
|---------|-------------|
| `sf build vehicle` | Build vehicle firmware |
| `sf flash vehicle -m` | Flash and open monitor |
| `sf monitor` | Open serial monitor |
| `sf log wifi` | Capture WiFi telemetry |
| `sf cal gyro` | Gyro calibration |
| `sf sim run vpython` | Run simulator |

**→ [Command Reference](docs/commands/README.md)** | **[Setup Guide](docs/setup/README.md)**

---

## Directory Structure

```
stampfly-ecosystem/
├── docs/           # Documentation
├── firmware/       # Embedded firmware
│   ├── vehicle/    # Vehicle firmware
│   ├── controller/ # Transmitter firmware
│   └── common/     # Shared code (WIP)
├── protocol/       # Communication protocol spec (WIP)
├── control/        # Control design assets (WIP)
├── analysis/       # Experiment data analysis (WIP)
├── tools/          # Utility tools (WIP)
├── simulator/      # 3D flight simulator
└── third_party/    # External dependencies
```

---

## Get Started

**→ [Getting Started (Setup to First Flight)](docs/getting-started.md)**

From ESP-IDF setup to firmware build,
pairing vehicle and controller, and your first flight.
All steps explained step-by-step.

---

## Technical Specifications

| Item | Specification |
|------|---------------|
| MCU | ESP32-S3 (M5Stamp S3) |
| Framework | ESP-IDF v5.5.2 + FreeRTOS |
| Pose Estimation | ESKF (Error-State Kalman Filter) |
| Communication | ESP-NOW + WiFi (telemetry) |
| Sensors | BMI270, BMM150, BMP280, VL53L3CX, PMW3901 |

---

## License

MIT License
