# StampFly 勉強会 競技会ルールブック

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### 競技会について

StampFly 勉強会の最終日（Day 5）に開催するドローンレース競技会のルールブックです。4日間のワークショップで学んだ制御技術を実践で発揮します。

### 種目一覧

| 種目 | 内容 | 配点 |
|------|------|------|
| タイムトライアル | 4 ゲート通過コース | 40 点 |
| 精密ホバリング | 指定高度で 10 秒間保持 | 30 点 |
| 精密着陸 | 50cm からマーカーに着陸 | 30 点 |

## 2. タイムトライアル (40点)

### ルール

| 項目 | 内容 |
|------|------|
| コース | 4 ゲート通過（直線 or L 字） |
| ゲート | 幅 60cm x 高さ 60cm |
| ゲート間距離 | 2-3m |
| 制限時間 | 120 秒 |
| 試行回数 | 2 回（ベストタイム採用） |
| 操縦方式 | コントローラ操縦 or Python 自律飛行（選択可） |

### 採点基準

| 順位 | 得点 |
|------|------|
| 1 位 | 40 点 |
| 2 位 | 35 点 |
| 3 位 | 30 点 |
| 4 位以降 | 25 点 |
| ゲート未通過 | 通過数 x 8 点（最大 32 点） |
| タイムアウト | 通過数 x 5 点 |

### 計測方法

```bash
sf competition timer --team "TeamName" --gates 4
```

### コースレイアウト例

```
Start                                                    Goal
  │                                                        │
  │    ┌──────┐         ┌──────┐         ┌──────┐         │
  ●───►│Gate 1│────────►│Gate 2│────────►│Gate 3│────────► ●
  │    └──────┘         └──────┘         └──────┘         │
  │         2m               2m               2m           │
  │                    ┌──────┐                            │
  │                    │Gate 4│◄───────────────────────────│
  │                    └──────┘                            │
```

## 3. 精密ホバリング (30点)

### ルール

| 項目 | 内容 |
|------|------|
| 目標高度 | 30cm |
| 計測時間 | 10 秒間 |
| 評価指標 | 高度の標準偏差（sigma） |
| 試行回数 | 2 回（ベストスコア採用） |
| 操縦方式 | C++ 内部制御のみ（コントローラ操縦不可） |

### 採点基準

| sigma (cm) | 得点 | 評価 |
|------------|------|------|
| < 1.0 | 30 点 | Excellent |
| 1.0 - 2.0 | 25 点 | Good |
| 2.0 - 3.0 | 20 点 | Fair |
| 3.0 - 5.0 | 15 点 | Needs improvement |
| > 5.0 | 10 点 | |
| 離陸失敗 | 5 点 | |

### 計測方法

```bash
sf competition hover --team "TeamName" --target 0.3 --duration 10
```

WiFi テレメトリ経由で高度データを 10 秒間収集し、標準偏差を自動計算します。

### 参加者向けヒント

- Lesson 5-6 の PID チューニングが直接影響
- 高度制御は ToF センサ（VL53L3CX）を使用
- `ws::estimated_altitude()` で推定高度を取得可能
- テレメトリでリアルタイム確認: `sf log wifi`

## 4. 精密着陸 (30点)

### ルール

| 項目 | 内容 |
|------|------|
| 開始高度 | 50cm |
| 目標 | 地面のマーカー（直径 10cm の円） |
| 評価指標 | 着地点からマーカー中心までの距離 |
| 試行回数 | 3 回（ベストスコア採用） |
| 操縦方式 | コントローラ操縦 or Python 自律飛行（選択可） |

### 採点基準

| 着地誤差 (cm) | 得点 |
|--------------|------|
| < 5 | 30 点 |
| 5 - 10 | 25 点 |
| 10 - 15 | 20 点 |
| 15 - 20 | 15 点 |
| 20 - 30 | 10 点 |
| > 30 | 5 点 |
| 着陸失敗 | 0 点 |

### 計測方法

マーカー中心から機体中心までの距離を定規で計測。

## 5. 総合順位

### 計算方法

```
総合スコア = タイムトライアル得点 + ホバリング得点 + 着陸得点
最大: 100 点
```

### スコア表示

```bash
sf competition score
```

### 同点の場合

1. タイムトライアルの順位が上の方を優先
2. それも同じ場合、ホバリング sigma が小さい方を優先

## 6. 一般ルール

### 機体規定

| 項目 | 規定 |
|------|------|
| 機体 | StampFly 標準仕様のみ |
| プロペラ | 標準プロペラのみ |
| バッテリー | 標準バッテリーのみ |
| ファームウェア | Workshop Skeleton ベースのみ |
| 外部センサ | 追加不可 |

### 禁止事項

- 機体の物理的改造
- 標準外のプロペラ/バッテリーの使用
- 他チームのコードのコピー
- 競技中の他チームへの妨害

### 安全規定

- 保護メガネの着用（フライトエリア内の全員）
- 審判の指示に従う
- バッテリー残量 3.3V 以下は使用禁止
- 異常動作時は即座に DISARM

## 7. タイムスケジュール

| 時間 | 内容 |
|------|------|
| 9:00-9:30 | 機体調整・最終テスト |
| 9:30-10:00 | 開会式・ルール確認 |
| 10:00-11:30 | タイムトライアル |
| 11:30-12:00 | 精密ホバリング |
| 12:00-13:00 | 昼休み |
| 13:00-14:00 | 精密着陸 |
| 14:00-14:30 | 集計 |
| 14:30-15:00 | 表彰式・講評 |

---

<a id="english"></a>

## 1. Overview

Competition rulebook for the StampFly Workshop final day (Day 5).

### Events

| Event | Description | Points |
|-------|-------------|--------|
| Time Trial | 4-gate course | 40 pts |
| Precision Hover | Hold altitude for 10s | 30 pts |
| Precision Landing | Land on target marker | 30 pts |

## 2. Time Trial (40 pts)

- 4 gates (60cm x 60cm), 2-3m apart
- Time limit: 120 seconds, 2 attempts (best time)
- Controller or Python autonomous flight
- Measured with: `sf competition timer --team "Name"`

## 3. Precision Hover (30 pts)

- Target: 30cm altitude, 10 seconds
- Evaluation: altitude sigma (standard deviation)
- C++ internal control only (no controller)
- Measured with: `sf competition hover --team "Name"`

| Sigma | Points |
|-------|--------|
| < 1cm | 30 |
| 1-2cm | 25 |
| 2-3cm | 20 |
| 3-5cm | 15 |
| > 5cm | 10 |

## 4. Precision Landing (30 pts)

- Start at 50cm, land on 10cm diameter marker
- 3 attempts (best score)
- Manual distance measurement

| Error | Points |
|-------|--------|
| < 5cm | 30 |
| 5-10cm | 25 |
| 10-15cm | 20 |
| 15-20cm | 15 |
| 20-30cm | 10 |
| > 30cm | 5 |

## 5. Overall Ranking

Total = Time Trial + Hover + Landing (max 100 pts)

```bash
sf competition score
```

## 6. General Rules

- Standard StampFly only (no modifications)
- Workshop Skeleton firmware only
- Safety glasses required
- Follow referee instructions
- Battery cutoff at 3.3V
