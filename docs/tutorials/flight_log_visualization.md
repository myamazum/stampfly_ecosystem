# フライトログの取得と可視化チュートリアル

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このチュートリアルについて

StampFlyのフライトログを取得し、ESKF状態推定の結果を可視化する手順を説明します。

### 前提条件

- 開発環境がセットアップ済み（`source setup_env.sh`）
- StampFlyがWiFiモードで起動している
- Python 3.x と必要なライブラリ（numpy, matplotlib）がインストール済み

## 2. ログ取得

### WiFi経由でのログ取得

StampFlyのWiFi APに接続した状態で、以下のコマンドを実行：

```bash
# 開発環境のセットアップ
source setup_env.sh

# WiFi経由で400Hzテレメトリを取得（30秒間）
sf log wifi -d 30 -o logs/flight_001.csv
```

オプション：

| オプション | 説明 |
|-----------|------|
| `-d, --duration` | 取得時間（秒）デフォルト: 30 |
| `-o, --output` | 出力ファイル名 |
| `-i, --ip` | StampFlyのIPアドレス（デフォルト: 192.168.4.1） |
| `--fft` | 取得後にFFT解析を実行 |

### USB経由でのログ取得

バイナリログをUSB経由で取得する場合：

```bash
# USB経由でバイナリログを取得（60秒間）
sf log capture -d 60 -o logs/flight_001.bin

# CSVに変換
sf log convert logs/flight_001.bin
```

### ログファイルの確認

```bash
# 最近のログファイル一覧
sf log list

# ログファイルの情報を表示
sf log info logs/flight_001.csv
```

出力例：
```
File: flight_001.csv
Size: 2345.6 KB
Samples: 12000
Columns: 35
Duration: 30.00 seconds
Rate: 400.0 Hz
```

## 3. 基本的な可視化

### sf log viz を使用

最もシンプルな可視化方法：

```bash
# 最新のCSVログを可視化
sf log viz

# 特定のファイルを可視化
sf log viz logs/flight_001.csv

# 画像として保存
sf log viz logs/flight_001.csv --save flight_analysis.png

# 時間範囲を指定
sf log viz logs/flight_001.csv --time-range 5 15
```

表示モード：

| モード | 説明 |
|-------|------|
| `--mode all` | 全データ（デフォルト） |
| `--mode sensors` | センサーデータのみ |
| `--mode attitude` | 姿勢のみ |
| `--mode position` | 位置のみ |

## 4. ESKF状態の可視化

### sf eskf plot を使用

ESKF状態推定結果の詳細可視化：

```bash
# ESKF状態をプロット
sf eskf plot logs/flight_001.csv

# 画像として保存
sf eskf plot logs/flight_001.csv -o eskf_states.png

# 位置のみ表示
sf eskf plot logs/flight_001.csv --mode position
```

### 2つのログの比較（オーバーレイ）

```bash
# 参照ログをオーバーレイして表示
sf eskf plot estimated.csv --overlay reference.csv -o comparison.png
```

## 5. ESKFリプレイと比較

### パラメータを変えてリプレイ

センサーログからESKFを再計算し、パラメータチューニングの効果を確認：

```bash
# デフォルトパラメータを確認
sf eskf params show

# カスタムパラメータでリプレイ
sf eskf replay logs/flight_001.csv --params custom_params.yaml -o replay_result.csv

# 可視化（元ログとオーバーレイ）
sf eskf plot replay_result.csv --overlay logs/flight_001.csv -o comparison.png
```

### 誤差メトリクスの計算

```bash
# リプレイ結果と元のESKF出力を比較
sf eskf compare replay_result.csv --ref logs/flight_001.csv
```

出力例：
```
============================================================
ESKF Error Metrics Summary
============================================================
Samples: 12000, Duration: 30.00s

Position [m]:
  RMSE: X=0.0234, Y=0.0189, Z=0.0156
  MAE:  X=0.0156, Y=0.0123, Z=0.0098
  Max:  X=0.0789, Y=0.0654, Z=0.0432

Velocity [m/s]:
  RMSE: X=0.0567, Y=0.0456, Z=0.0234

Attitude [deg]:
  RMSE: R=1.23, P=0.98, Y=2.34
  MAE:  R=0.89, P=0.67, Y=1.56

Total Position RMSE: 0.0341 m
============================================================
```

## 6. パラメータ最適化

### 自動パラメータチューニング

```bash
# 焼きなまし法でパラメータ最適化
sf eskf tune logs/flight_001.csv -o optimized.yaml --method sa --iter 500

# 複数ログで最適化（より堅牢）
sf eskf tune logs/flight_001.csv logs/flight_002.csv -o optimized.yaml
```

### 最適化パラメータの検証

```bash
# 最適化前後のパラメータ比較
sf eskf params diff default.yaml optimized.yaml

# 最適化パラメータでリプレイして効果を確認
sf eskf replay logs/flight_001.csv --params optimized.yaml | sf eskf compare --ref logs/flight_001.csv
```

## 7. 典型的なワークフロー

### 基本フロー

```bash
# 1. ログ取得
sf log wifi -d 30 -o logs/test_flight.csv

# 2. 基本可視化
sf log viz logs/test_flight.csv --save test_flight.png

# 3. ESKF状態の詳細確認
sf eskf plot logs/test_flight.csv --mode all -o eskf_detail.png
```

### チューニングフロー

```bash
# 1. 複数のテストフライトログを取得
sf log wifi -d 30 -o logs/tune_01.csv
sf log wifi -d 30 -o logs/tune_02.csv

# 2. パラメータ最適化
sf eskf tune logs/tune_01.csv logs/tune_02.csv -o tuned.yaml

# 3. 新パラメータで効果確認
sf eskf replay logs/tune_01.csv --params tuned.yaml -o replayed.csv
sf eskf plot replayed.csv --overlay logs/tune_01.csv -o comparison.png

# 4. メトリクス確認
sf eskf compare replayed.csv --ref logs/tune_01.csv
```

### パイプライン活用

Unix哲学に基づくパイプ連携：

```bash
# リプレイ → 比較（中間ファイル不要）
sf eskf replay flight.csv --params tuned.yaml | sf eskf compare --ref flight.csv

# JSON形式で誤差出力
sf eskf compare estimated.csv --ref reference.csv --format json > metrics.json
```

## 8. トラブルシューティング

### よくある問題

**WiFi接続できない**
```bash
# StampFlyのAP（SSID: StampFly_XXXX）に接続されているか確認
# IPアドレスを明示的に指定
sf log wifi -i 192.168.4.1
```

**ログが空またはエラー**
```bash
# ログファイルの情報を確認
sf log info logs/flight.csv

# フォーマット検出
python3 -c "from tools.eskf_sim import detect_csv_format, load_csv; print(detect_csv_format(...))"
```

**matplotlibエラー**
```bash
# 必要なパッケージをインストール
pip install matplotlib numpy scipy pyyaml
```

---

<a id="english"></a>

## 1. Overview

### About This Tutorial

This tutorial explains how to capture flight logs from StampFly and visualize ESKF state estimation results.

### Prerequisites

- Development environment set up (`source setup_env.sh`)
- StampFly running in WiFi mode
- Python 3.x with required libraries (numpy, matplotlib)

## 2. Log Capture

### WiFi Telemetry Capture

Connect to StampFly's WiFi AP and run:

```bash
# Activate development environment
source setup_env.sh

# Capture 400Hz telemetry via WiFi (30 seconds)
sf log wifi -d 30 -o logs/flight_001.csv
```

### USB Binary Log Capture

```bash
# Capture binary log via USB (60 seconds)
sf log capture -d 60 -o logs/flight_001.bin

# Convert to CSV
sf log convert logs/flight_001.bin
```

## 3. Basic Visualization

```bash
# Visualize latest CSV log
sf log viz

# Visualize specific file
sf log viz logs/flight_001.csv

# Save as image
sf log viz logs/flight_001.csv --save flight_analysis.png
```

## 4. ESKF State Visualization

```bash
# Plot ESKF states
sf eskf plot logs/flight_001.csv

# Overlay two logs for comparison
sf eskf plot estimated.csv --overlay reference.csv -o comparison.png
```

## 5. ESKF Replay and Comparison

```bash
# Replay with custom parameters
sf eskf replay logs/flight_001.csv --params custom.yaml -o replay.csv

# Compare error metrics
sf eskf compare replay.csv --ref logs/flight_001.csv
```

## 6. Parameter Optimization

```bash
# Optimize parameters using Simulated Annealing
sf eskf tune logs/flight_001.csv -o optimized.yaml --method sa

# Verify with replay
sf eskf replay logs/flight_001.csv --params optimized.yaml | sf eskf compare --ref logs/flight_001.csv
```

## 7. Typical Workflow

```bash
# Capture -> Visualize -> Tune -> Verify
sf log wifi -d 30 -o logs/test.csv
sf log viz logs/test.csv --save overview.png
sf eskf tune logs/test.csv -o tuned.yaml
sf eskf replay logs/test.csv --params tuned.yaml | sf eskf compare --ref logs/test.csv
```
