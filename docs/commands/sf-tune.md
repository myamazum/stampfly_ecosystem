# sf tune

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

ドローンの全制御パラメータを体系的にチューニングするための統合ツール。ESKF（状態推定）、レート制御、姿勢制御、高度制御、位置制御の全ループを対象とする。

### 特徴

- **config.hpp が SSOT（Single Source of Truth）** — Python ツール側にハードコードのデフォルト値なし
- **グラウンドトゥルース不要** — NIS（正規化イノベーション二乗値）ベースの自己一貫性評価
- **ログリプレイ + 物理シミュレーション** の使い分け
- **GUI ダッシュボード** — スライダーでリアルタイムシミュレーション
- **マンインザループ** — ツールが分析・提案・ビルド・書込を主導、人間は飛行のみ

## 2. サブコマンド

| サブコマンド | 説明 |
|-------------|------|
| `gui` | インタラクティブ Streamlit ダッシュボード起動 |
| `auto` | マンインザループ自動チューニング |
| `eskf` | ESKF パラメータスイープ（ログリプレイ） |
| `position` | 位置制御 PID スイープ（シミュレーション） |
| `params` | 現在の config.hpp パラメータ一覧表示 |

## 3. sf tune gui

ブラウザベースのインタラクティブチューニングダッシュボードを起動する。

```bash
sf tune gui
sf tune gui --port 8502
```

### 機能

| 機能 | 説明 |
|------|------|
| パラメータスライダー | タブ別（ESKF/Position/Altitude/Attitude/Rate） |
| リアルタイムシミュレーション | スライダー変更で即座にグラフ更新 |
| ログ読込 | JSONL/CSV フライトログの解析・表示 |
| 帯域計算 | ESKF の速度推定帯域を Q/R から自動計算 |
| 性能指標 | 位置精度、整定時間、最大傾斜角 |

### 必要なパッケージ

```bash
pip install streamlit plotly
```

## 4. sf tune auto

マンインザループの自動チューニングセッションを実行する。ツールが分析→パラメータ提案→承認待ち→ビルド→飛行指示→ログ取得→評価のサイクルを主導する。

```bash
sf tune auto                    # 全フェーズ
sf tune auto --phase eskf       # ESKF のみ
sf tune auto --phase position   # 位置制御のみ
```

### チューニングフェーズ

| 順序 | フェーズ | 飛行モード | 時間 | 収束条件 |
|------|---------|-----------|------|---------|
| 1 | ESKF Q/R | ALT_HOLD ホバリング | 30s | NIS ≈ 自由度 |
| 2 | 高度制御 | ALT_HOLD 高度変更 | 30s | 高度 std < 0.05m |
| 3 | 位置制御 | POS_HOLD 静止+外乱 | 30s | 位置 std < 0.15m |

### ワークフロー

```
1. ツール: ログ分析 → パラメータ提案表示
2. 人間:   承認（Enter）/ 修正 / スキップ
3. ツール: config.hpp 書換 → ビルド → 書込
4. ツール: 飛行指示を表示
5. 人間:   飛行実施
6. ツール: sf log wifi でログ自動取得
7. ツール: ログ分析 → 改善度評価 → 収束判定
8. 収束していなければ 1 に戻る
```

## 5. sf tune eskf

フライトログを ESKF でリプレイし、Q/R パラメータの最適値を探索する。

```bash
sf tune eskf --log logs/stampfly_udp_20260406T165353.jsonl
sf tune eskf --log logs/latest.jsonl --top 5
```

### 評価指標（NIS ベース）

| 指標 | 意味 | 目標 |
|------|------|------|
| Flow NIS | フロー観測の Q/R バランス | 2.0（2自由度） |
| ToF NIS | ToF 観測の Q/R バランス | 1.0（1自由度） |
| BA drift rate | 加速度バイアスのドリフト速度 | < 0.01 m/s²/s |
| Innovation autocorr | イノベーションの白色性 | < 0.1 |
| Position span | 推定位置の振幅 | 小さいほど良い |

### デフォルトスイープ範囲

| パラメータ | 範囲 |
|-----------|------|
| ACCEL_NOISE | [0.1, 0.2, 0.3, 0.5] |
| FLOW_NOISE | [0.1, 0.2, 0.3, 0.5] |

## 6. sf tune position

閉ループシミュレーションで位置制御 PID の最適ゲインを探索する。

```bash
sf tune position
sf tune position --disturbance 0.5 --top 5
```

### デフォルトスイープ範囲

| パラメータ | 範囲 |
|-----------|------|
| POS_KP | [0.5, 1.0, 1.5, 2.0] |
| VEL_KP | [0.15, 0.3, 0.5] |

### 評価指標

| 指標 | 意味 |
|------|------|
| pos_x_rms | 位置 X の RMS 誤差 |
| settle_time | 整定時間（5% バンド） |
| pitch_max_deg | 最大ピッチ角 |

## 7. sf tune params

config.hpp から全パラメータを読み取って表示する。

```bash
sf tune params
```

19 の namespace から 212 パラメータを抽出する。

## 8. アーキテクチャ

```
config.hpp (SSOT)
    │
    ▼
tools/common/config_parser.py ← パース
    │
    ├─► tools/eskf_sim/eskf.py     ← ESKFConfig.from_firmware()
    ├─► tools/sim/closed_loop.py   ← 全 PID ゲイン
    ├─► tools/tuning/sweep.py      ← パラメータスイープ
    ├─► tools/tuning/dashboard.py  ← GUI
    └─► tools/tuning/orchestrator.py ← 自動チューニング
```

### ファイル一覧

| ファイル | 役割 |
|---------|------|
| `tools/common/config_parser.py` | config.hpp パーサー |
| `tools/eskf_sim/eskf.py` | ESKF Python 実装 + NIS 記録 |
| `tools/eskf_sim/metrics.py` | 自己一貫性評価（NIS ベース） |
| `tools/eskf_sim/loader.py` | ログローダー（CSV + JSONL） |
| `tools/sim/pid.py` | PID コントローラ |
| `tools/sim/drone_plant.py` | ドローン物理モデル |
| `tools/sim/closed_loop.py` | 閉ループシミュレータ |
| `tools/tuning/sweep.py` | パラメータスイープエンジン |
| `tools/tuning/dashboard.py` | Streamlit GUI |
| `tools/tuning/orchestrator.py` | オーケストレータ |

---

<a id="english"></a>

## 1. Overview

Integrated tool for systematic tuning of all drone control parameters: ESKF (state estimation), rate control, attitude control, altitude control, and position control.

### Key Features

- **config.hpp as SSOT** — No hardcoded defaults in Python tools
- **No ground truth required** — NIS-based self-consistency evaluation
- **Log replay + physics simulation** combined approach
- **GUI dashboard** — Real-time simulation with parameter sliders
- **Man-in-the-loop** — Tool drives analysis/proposals/build; human only flies

## 2. Subcommands

| Subcommand | Description |
|------------|-------------|
| `gui` | Launch interactive Streamlit dashboard |
| `auto` | Man-in-the-loop auto-tuning session |
| `eskf` | ESKF parameter sweep (log replay) |
| `position` | Position PID parameter sweep (simulation) |
| `params` | Display current config.hpp parameters |

## 3. sf tune gui

Launch browser-based interactive tuning dashboard.

```bash
sf tune gui
sf tune gui --port 8502
```

Requires: `pip install streamlit plotly`

## 4. sf tune auto

Run man-in-the-loop auto-tuning session. The tool drives the cycle: analyze → propose → approve → build → flash → fly → log → evaluate → repeat.

```bash
sf tune auto                    # All phases
sf tune auto --phase eskf       # ESKF only
sf tune auto --phase position   # Position control only
```

### Tuning Phases

| Order | Phase | Flight Mode | Duration | Convergence |
|-------|-------|-------------|----------|-------------|
| 1 | ESKF Q/R | ALT_HOLD hover | 30s | NIS ≈ DOF |
| 2 | Altitude | ALT_HOLD altitude change | 30s | Alt std < 0.05m |
| 3 | Position | POS_HOLD static+disturbance | 30s | Pos std < 0.15m |

## 5. sf tune eskf

Replay flight log through ESKF and find optimal Q/R parameters.

```bash
sf tune eskf --log logs/latest.jsonl --top 5
```

### Evaluation Metrics (NIS-based)

| Metric | Meaning | Target |
|--------|---------|--------|
| Flow NIS | Flow Q/R balance | 2.0 (2 DOF) |
| ToF NIS | ToF Q/R balance | 1.0 (1 DOF) |
| BA drift rate | Accel bias drift | < 0.01 m/s²/s |

## 6. sf tune position

Find optimal position PID gains via closed-loop simulation.

```bash
sf tune position --disturbance 0.5 --top 5
```

## 7. sf tune params

Display all parameters parsed from config.hpp (212 parameters, 19 namespaces).

```bash
sf tune params
```

## 8. Architecture

```
config.hpp (SSOT)
    │
    ▼
tools/common/config_parser.py ← Parse
    │
    ├─► tools/eskf_sim/          ← ESKF replay + NIS
    ├─► tools/sim/               ← Closed-loop simulation
    └─► tools/tuning/            ← Sweep + GUI + Orchestrator
```
