# StampFly 制御工学カリキュラム シラバス

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 科目情報

| 項目 | 内容 |
|------|------|
| 科目名 | 制御工学実習 — ドローン制御入門 |
| 開講期間 | 半期 15 回（各 90 分） |
| 対象 | 工学系学部 3-4 年生 |
| 前提知識 | 線形代数、微分方程式 |
| 機材 | 1 人 1 台 StampFly + ノート PC |

## 2. 到達目標

本科目を修了した学生は以下ができるようになる：

1. フィードバック制御の基本概念を説明し、PID コントローラを設計できる
2. ドローンの運動方程式を導出し、ホバー条件を計算できる
3. カスケード制御の構造を理解し、帯域設計の原則を説明できる
4. センサデータから Allan 分散を計算し、ノイズ特性を評価できる
5. Python SDK を使ってドローンの自律飛行プログラムを実装できる

## 3. カリキュラム

### Phase A: ワクワク期 (Week 1-2)

| 回 | テーマ | 内容 | ノートブック |
|----|--------|------|------------|
| 1 | StampFly とドローン制御の世界 | SDK 接続、初飛行、テレメトリ | `01_hello_stampfly.ipynb` |
| 2 | プログラムで自律飛行 | 矩形パス飛行、ログ取得、軌跡プロット | `02_autonomous_flight.ipynb` |

### Phase B: 基礎理論期 (Week 3-5)

| 回 | テーマ | 内容 | ノートブック |
|----|--------|------|------------|
| 3 | フィードバック制御入門 | P 制御、開/閉ループ比較、定常偏差 | `03_feedback_basics.ipynb` |
| 4 | PID 制御の理論と実装 | P/I/D 各項、ボード線図、微分フィルタ | `04_pid_theory.ipynb` |
| 5 | 実機で PID を感じる | レート PID チューニング、ステップ応答 | `05_rate_control_tuning.ipynb` |

### Phase C: ディープダイブ期 (Week 6-8)

| 回 | テーマ | 内容 | ノートブック |
|----|--------|------|------------|
| 6 | ドローンの数学モデル | 6DoF 運動方程式、モータモデル、ホバー条件 | `06_drone_dynamics.ipynb` |
| 7 | システム同定 | Allan 分散、センサノイズ分析 | `07_system_identification.ipynb` |
| 8 | センサフュージョンとカルマンフィルタ | ジャイロドリフト、相補フィルタ、ESKF | `08_sensor_fusion.ipynb` |

### Phase D: 応用制御期 (Week 9-11)

| 回 | テーマ | 内容 | ノートブック |
|----|--------|------|------------|
| 9 | 姿勢制御 — カスケードの概念 | 内側/外側ループ、帯域分離 | `09_cascade_attitude.ipynb` |
| 10 | 高度制御 — FF とアンチワインドアップ | ホバー推力 FF、AW 効果 | `10_altitude_control.ipynb` |
| 11 | 位置制御 — 座標変換と外乱抑制 | NED/Body 変換、4 段カスケード | `11_position_control.ipynb` |

### Phase E: 応用・ミッション期 (Week 12-13)

| 回 | テーマ | 内容 | ノートブック |
|----|--------|------|------------|
| 12 | ウェイポイント飛行 | 複数点経由の自律飛行、精度評価 | `12_waypoint_mission.ipynb` |
| 13 | カスタムコントローラ | 外部 PID ループ実装 | `13_custom_controller.ipynb` |

### Phase F: 最終プロジェクト (Week 14-15)

| 回 | テーマ | 内容 | ノートブック |
|----|--------|------|------------|
| 14 | 最終プロジェクト実装 | 自由課題の実装 | `14_project_template.ipynb` |
| 15 | プレゼンテーション + デモフライト | 成果発表 | - |

## 4. 評価方法

| 評価項目 | 比率 | 内容 |
|---------|------|------|
| ノートブック提出 | 40% | 各セッションの考察課題 |
| 中間レポート | 20% | Session 8 終了時点のまとめ |
| 最終プロジェクト | 30% | 実装 + プレゼン + デモ |
| 授業参加 | 10% | 出席・質疑応答 |

## 5. 参考資料

| 資料 | 説明 |
|------|------|
| `docs/education/setup_guide.md` | 環境構築手順 |
| `docs/education/safety_guide.md` | 飛行安全ガイド |
| `docs/education/assessment_rubric.md` | 評価ルーブリック |

---

<a id="english"></a>

## 1. Course Information

| Item | Details |
|------|---------|
| Course | Control Engineering Lab — Introduction to Drone Control |
| Duration | 15 sessions (90 min each) |
| Target | 3rd-4th year engineering students |
| Prerequisites | Linear algebra, differential equations |
| Equipment | 1 StampFly + laptop per student |

## 2. Learning Objectives

Upon completion, students will be able to:

1. Explain feedback control concepts and design PID controllers
2. Derive drone equations of motion and calculate hover conditions
3. Understand cascade control structure and bandwidth design principles
4. Compute Allan variance and evaluate sensor noise characteristics
5. Implement autonomous flight programs using Python SDK

## 3. Schedule

See Japanese section above for detailed session-by-session breakdown.

## 4. Assessment

| Component | Weight | Description |
|-----------|--------|-------------|
| Notebook submissions | 40% | Discussion questions per session |
| Mid-term report | 20% | Summary after Session 8 |
| Final project | 30% | Implementation + presentation + demo |
| Participation | 10% | Attendance and Q&A |
