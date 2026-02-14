# StampFly 勉強会 講師ガイド

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このガイドについて

本ガイドは StampFly 勉強会（4+1日間）の講師向け運営マニュアルです。Workshop Skeleton ファームウェアと sf CLI を使用した教育カリキュラムの進め方を説明します。

### カリキュラム設計思想

| 原則 | 説明 |
|------|------|
| シンプルさ | 学生は `setup()` / `loop_400Hz()` の 2 関数だけ実装 |
| 段階的学習 | Lesson 0（Hello World）→ Lesson 11（競技会）まで段階的に難易度が上がる |
| ツール活用 | sf CLI / WiFi テレメトリ / Python SDK を各レッスンに統合 |
| 実践重視 | 理論 30% : 実習 70% の配分 |

## 2. 事前準備

### 環境構築チェックリスト

各学生の PC で以下を確認:

```bash
# 1. ESP-IDF インストール確認
source ~/esp/esp-idf/export.sh
idf.py --version    # v5.4 以上

# 2. sf CLI 動作確認
sf doctor

# 3. Workshop ビルド確認
sf lesson switch 0
sf lesson build

# 4. Python 環境（Day 4 用）
python3 -c "import stampfly_sdk"
```

### 機材チェックリスト

- [ ] StampFly 全台の動作確認（モータ回転、LED 点灯）
- [ ] コントローラ全台の充電・ペアリング確認
- [ ] 予備バッテリーの充電
- [ ] 安全ネット / フェンスの設置
- [ ] WiFi ルーター（開発用）の設置
- [ ] プロジェクター / スクリーンの準備

## 3. レッスン運営ガイド

### 各レッスンの進め方

```
1. 講義（10-15分）: 理論・概念の説明
2. デモ（5分）: solution.cpp を使ったデモフライト
3. 実習（30-40分）: student.cpp の TODO を埋める
4. テスト（10-15分）: ビルド → フラッシュ → 動作確認
5. まとめ（5分）: 質疑応答
```

### Lesson 0: 環境セットアップ

**目的:** ビルド → フラッシュ → シリアルモニタの流れを体験

**手順:**
1. `sf lesson switch 0` で Lesson 0 に切り替え
2. `sf lesson build` でビルド
3. `sf lesson flash` でフラッシュ（モニタ自動起動）
4. シリアルモニタで `"Hello StampFly!"` の出力を確認

**よくある問題:**
- ポート未検出 → USB ケーブルがデータ対応か確認、`sf doctor` 実行
- ビルドエラー → ESP-IDF のバージョン確認、`sf lesson build -c` でクリーンビルド

### Lesson 1: モータ制御

**目的:** PWM 制御の基礎、モータ番号と配置の理解

**安全注意:**
- プロペラは外した状態で実施
- duty は 0.2 以下で開始
- モータの回転方向を確認

**確認ポイント:**
- 各モータが個別に回転するか
- duty 値と回転速度の関係を理解しているか

### Lesson 2: コントローラ入力

**目的:** ESP-NOW 通信、スティック値のマッピング

**手順:**
1. コントローラの電源を入れペアリング
2. `ws::rc_throttle()` でスロットル値をシリアル出力
3. スティック操作とモータ出力の対応を実装

### Lesson 3: LED 表示

**目的:** 状態表示の実装

**ポイント:** ARM/DISARM 状態を色で表現する

### Lesson 4: IMU センサ

**目的:** ジャイロ/加速度センサの読み取りとテレメトリ送信

**デモ:** `sf log wifi` で WiFi テレメトリを取得し、リアルタイムでセンサ値を確認

### Lesson 5: P 制御 + 初フライト

**安全注意:**
- 初フライトは広い場所で実施
- 保護メガネ必須
- Kp は小さい値（0.5 程度）から開始
- 講師が横で監視

**手順:**
1. 角速度偏差を計算
2. Kp を掛けてモータミキサーに入力
3. Kp = 0.5 からテスト、徐々に上げる

### Lesson 6: PID 制御

**ポイント:**
- I 項のアンチワインドアップが重要
- D 項のノイズ対策（ローパスフィルタ）
- ゲイン調整の体系的アプローチ: P → D → I の順

**チューニングのコツ:**
1. まず P ゲインだけで振動の手前まで上げる
2. D ゲインで振動を抑える
3. 最後に I ゲインを少しずつ追加

### Lesson 7: テレメトリ活用

**デモ:**
```bash
# WiFi テレメトリ取得
sf log wifi

# ログ可視化
sf log viz <logfile>
```

**ポイント:** ステップ応答の解析方法（立ち上がり時間、オーバーシュート、定常偏差）

### Lesson 8: モデリング・制御系設計

**前提知識:** ラプラス変換、伝達関数の基礎

**ツール:** Loop Shaping Tool でボード線図を確認

### Lesson 9: 姿勢推定

**ポイント:**
- 相補フィルタの直感的理解（ジャイロは短期信頼、加速度は長期信頼）
- ESKF との性能比較

### Lesson 10: Python SDK

**環境:** Jupyter Notebook を使用

**手順:**
1. `connect_or_simulate()` でシミュレータに接続
2. RC 制御コマンドでホバリング
3. テレメトリ取得で外部 PID を実装

### Lesson 11: 競技会準備

**内容:** ルール説明 + 自由練習時間

## 4. 安全管理

### 基本ルール

| ルール | 詳細 |
|--------|------|
| 保護メガネ | フライト時は全員着用 |
| フライトエリア | ネット/フェンスで囲う |
| バッテリー | 3.3V 以下で使用禁止 |
| プロペラ | 地上テストは外した状態 |
| 緊急停止 | コントローラの DISARM ボタンを常に意識 |

### 事故対応

1. 即座にモータ停止（DISARM）
2. バッテリーを外す
3. 機体の破損確認
4. 人的被害の確認
5. 原因調査

## 5. トラブルシューティング

### よくある問題

| 症状 | 原因 | 対処 |
|------|------|------|
| ビルドエラー | ESP-IDF 未初期化 | `source ~/esp/esp-idf/export.sh` |
| ポート未検出 | USB ケーブル | データ対応ケーブルに交換 |
| フラッシュ失敗 | Boot モード | BOOT ボタン押しながらリセット |
| モータ不安定 | PID ゲイン過大 | P ゲインを 50% に下げる |
| ドリフト | IMU バイアス | `sf cal gyro` でキャリブレーション |
| WiFi テレメトリ切断 | 距離/干渉 | WiFi チャンネル変更、距離を近づける |

---

<a id="english"></a>

## 1. Overview

### About This Guide

This is the instructor's manual for the StampFly Workshop (4+1 days). It covers how to run the educational curriculum using the Workshop Skeleton firmware and sf CLI.

### Curriculum Design Principles

| Principle | Description |
|-----------|-------------|
| Simplicity | Students only implement `setup()` / `loop_400Hz()` |
| Progressive | Difficulty increases from Lesson 0 to Lesson 11 |
| Tool integration | sf CLI, WiFi telemetry, Python SDK in each lesson |
| Practice-focused | 30% theory : 70% hands-on |

## 2. Preparation

### Environment Checklist

```bash
source ~/esp/esp-idf/export.sh
sf doctor
sf lesson switch 0 && sf lesson build
```

## 3. Lesson Guides

Each lesson follows: Lecture (10-15 min) → Demo (5 min) → Hands-on (30-40 min) → Test (10-15 min) → Wrap-up (5 min).

See the Japanese section above for detailed lesson-by-lesson instructions.

## 4. Safety

- Safety glasses required during flight
- Flight area must be enclosed
- Battery cutoff at 3.3V
- Ground tests without propellers
- Always be ready to DISARM

## 5. Troubleshooting

See the Japanese troubleshooting table above for common issues and solutions.
