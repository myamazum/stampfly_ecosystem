# Lesson 12: Precision Landing Competition

## Goal / 目標
Optimize your controller for precise 3m landing on a helipad.

自分のコントローラを最適化し、3m先のヘリポートに精密着陸する。

## Overview / 概要

This is the final lesson. You use the rate PID controller you built in Lessons 5/8
and optimize the gains to achieve the most precise landing possible.
The competition is simple: **who can land on the helipad the fastest?**

これが最終レッスン。レッスン 5/8 で実装した角速度PID制御のゲインを最適化し、
最も精密な着陸を目指す。
競技はシンプル: **誰が一番速くヘリポートに着陸できるか？**

## Competition Rules / 競技会ルール

| Item / 項目 | Rule / ルール |
|---|---|
| Objective / 目的 | Land precisely on helipad 3m away / 3m先のヘリポートに精密着陸 |
| Helipad / ヘリポート | 40cm x 40cm |
| Distance / 距離 | 3m from pilot / パイロットから3m |
| Time limit / 制限時間 | 60 seconds / 60秒 |
| Attempts / 試行 | 3 times (best time counts) / 3回（ベストタイム採用） |
| Scoring / 判定 | ARM → takeoff → land on helipad time / ARM→離陸→ヘリポート着陸のタイム |
| Pilot / パイロット | Must stay at start position / 定位置から動かない |
| Disqualification / 失格 | Flying outside safety area, hand intervention, pilot movement |

### What's Allowed / できること

- Tune PID gains (Kp, Ki, Kd) / PIDゲイン調整
- Add yaw control / ヨー制御追加
- Add D-term filtering / D項フィルタ追加
- Use telemetry / テレメトリ使用

### What's NOT Allowed / できないこと

- Cascade control (attitude -> rate) / カスケード制御
- Automatic altitude hold / 自動高度保持
- Copy other's code / 他人のコードコピー

## Starting Template / スタートテンプレート

The `student.cpp` provides a **rate PID controller** (same structure as Lesson 8):
```
Stick Input ──> [Scale] ──> Target Rate ──>(+)──> Error ──> [PID] ──> Motor Mixer
                                            ^(-)
                                            |
                                          Gyro
```

| Parameter | Default Value | Description / 説明 |
|-----------|--------------|-------------------|
| `Kp` (roll/pitch) | 0.5 | Rate P-gain / 角速度P ゲイン |
| `Ki` (roll/pitch) | 0.3 | Rate I-gain / 角速度I ゲイン |
| `Kd` (roll/pitch) | 0.005 | Rate D-gain / 角速度D ゲイン |
| `Kp_yaw` | 2.0 | Yaw P-gain / ヨーPゲイン |
| `Ki_yaw` | 0.5 | Yaw I-gain / ヨーIゲイン |
| `Kd_yaw` | 0.01 | Yaw D-gain / ヨーDゲイン |

## Tuning Strategy / チューニング戦略

| Step / 手順 | Action / アクション | What to observe / 観察するもの |
|-------------|---------------------|-------------------------------|
| 1 | Increase Kp until oscillation / Kpを振動するまで上げる | Response speed / 応答速度 |
| 2 | Back off Kp by 20% / Kpを20%下げる | Stability margin / 安定余裕 |
| 3 | Add Kd to reduce overshoot / Kdでオーバーシュート抑制 | Damping / 減衰 |
| 4 | Add Ki to remove steady-state error / Kiで定常偏差除去 | Offset correction / オフセット補正 |
| 5 | Repeat with telemetry analysis / テレメトリ解析しながら反復 | Convergence / 収束 |

## Tips / ヒント

### Use Telemetry / テレメトリを活用する

```cpp
ws::telemetry_send("roll_error", roll_error);
ws::telemetry_send("roll_out", roll_output);
```

```bash
sf log wifi     # View real-time telemetry / リアルタイムテレメトリ確認
```

### D-Term Filtering / D項フィルタリング

```cpp
// Low-pass filter on D-term to reduce noise
// D項にローパスフィルタをかけてノイズを低減
static float d_filtered = 0;
float d_raw = (error - prev_error) / dt;
d_filtered = 0.8f * d_filtered + 0.2f * d_raw;  // alpha = 0.8
```

### Tuning Tips / チューニングのコツ

- Change one parameter at a time / パラメータは1つずつ変更
- Always record telemetry before and after / 変更前後のテレメトリを記録
- If unstable, reduce all gains by 50% / 不安定なら全ゲインを50%に
- Battery voltage affects thrust - check `ws::battery_voltage()` / バッテリ電圧で推力が変わる

## Steps / 手順

1. `sf lesson switch 12`
2. Build and test the default PID controller / デフォルトPIDをビルドしてテスト
3. Practice takeoff and landing / 離着陸を練習
4. Tune gains: P → D → I / ゲイン調整: P → D → I の順
5. Use telemetry to analyze / テレメトリで解析
6. Iterate until satisfied / 満足するまで反復
7. Competition! / 本番！

## Safety / 安全注意事項

| Rule / ルール | Description / 説明 |
|---------------|-------------------|
| Wear safety glasses / 保護メガネ着用 | Required in flight area / フライトエリア内必須 |
| Start with low throttle / 低スロットルから | Increase gradually / 徐々に上げる |
| Immediately disarm if unstable / 不安定ならすぐDISARM | Safety first / 安全第一 |
| Stay in flight area / フライトエリア内で | 3m x 3m boundary / 3m x 3m の範囲内 |
| Do not move from pilot position / パイロット位置から動かない | Disqualification if moved / 動いたら失格 |

> **Note / 注:** StampFly はプロペラガード一体型で、極めて小型のためプロペラの危険性は低いです。
