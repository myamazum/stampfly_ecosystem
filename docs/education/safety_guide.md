# StampFly 飛行安全ガイド

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 安全の基本原則

### 絶対に守ること

| ルール | 理由 |
|--------|------|
| プロペラガードの損傷がないか確認 | 手指の怪我防止（StampFly は一体型ガード標準搭載） |
| 飛行エリアを確保（2m x 2m 以上） | 衝突回避 |
| バッテリー 30% 以下で飛行しない | 制御不能リスク |
| 緊急停止方法を事前に確認 | 即座に停止できるように |
| 長い髪はまとめる | プロペラへの巻き込み防止 |

### 緊急停止の方法

```python
# Python SDK からの緊急停止
# Emergency stop from Python SDK
drone.emergency()

# sf CLI からの緊急停止
# Emergency stop from sf CLI
# ターミナルで: sf emergency
```

## 2. 飛行前チェックリスト

飛行前に以下を確認してください：

| # | 確認項目 | チェック |
|---|---------|---------|
| 1 | プロペラガードに破損・変形がない | [ ] |
| 2 | プロペラに損傷がない | [ ] |
| 3 | バッテリーが十分に充電されている（30%以上） | [ ] |
| 4 | 飛行エリアが確保されている（障害物なし） | [ ] |
| 5 | 周囲に人がいないことを確認 | [ ] |
| 6 | WiFi 接続が安定している | [ ] |
| 7 | 緊急停止方法を確認した | [ ] |

## 3. 飛行中の注意事項

### 室内飛行

- エアコンの風に注意（外乱になる）
- 天井までの距離を確認
- 機体の真上に顔を出さない

### 屋外飛行

- 風速 3m/s 以下で飛行
- 直射日光を避ける（バッテリー温度上昇）
- 飛行エリアを明確に区切る

## 4. バッテリー管理

| 状態 | 電圧 | 対応 |
|------|------|------|
| 満充電 | 4.2V | 飛行可能 |
| 通常 | 3.7-4.0V | 飛行可能 |
| 低電圧 | 3.5-3.7V | 着陸推奨 |
| 危険 | 3.5V 以下 | 即時着陸 |

### 充電時の注意

- 専用充電器を使用
- 充電中は目を離さない
- 高温・直射日光を避ける

## 5. 事故発生時の対応

1. **即座に `emergency()` を実行**
2. バッテリーを外す
3. 怪我の有無を確認
4. 教員に報告

---

<a id="english"></a>

## 1. Fundamental Safety Principles

### Mandatory Rules

| Rule | Reason |
|------|--------|
| Check propeller guards for damage | Prevent finger injuries (StampFly has built-in guards) |
| Ensure flight area (2m x 2m minimum) | Collision avoidance |
| Do not fly below 30% battery | Risk of loss of control |
| Confirm emergency stop method beforehand | Immediate stop capability |
| Tie back long hair | Prevent propeller entanglement |

### Emergency Stop

```python
# Emergency stop from Python SDK
drone.emergency()

# Emergency stop from sf CLI
# In terminal: sf emergency
```

## 2. Pre-Flight Checklist

| # | Check Item | Done |
|---|-----------|------|
| 1 | Propeller guards undamaged | [ ] |
| 2 | No propeller damage | [ ] |
| 3 | Battery sufficiently charged (>30%) | [ ] |
| 4 | Flight area clear (no obstacles) | [ ] |
| 5 | No people in flight area | [ ] |
| 6 | Stable WiFi connection | [ ] |
| 7 | Emergency stop method confirmed | [ ] |

## 3. In-Flight Precautions

### Indoor Flight

- Beware of air conditioning (acts as disturbance)
- Check ceiling clearance
- Never place face directly above the drone

### Outdoor Flight

- Fly only in winds below 3 m/s
- Avoid direct sunlight (battery temperature rise)
- Clearly mark the flight area

## 4. Battery Management

| State | Voltage | Action |
|-------|---------|--------|
| Full | 4.2V | Ready to fly |
| Normal | 3.7-4.0V | Ready to fly |
| Low | 3.5-3.7V | Land recommended |
| Critical | Below 3.5V | Land immediately |

## 5. Accident Response

1. **Execute `emergency()` immediately**
2. Disconnect battery
3. Check for injuries
4. Report to instructor
