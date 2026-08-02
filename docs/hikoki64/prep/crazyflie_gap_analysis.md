# Crazyflie 到達点 × StampFly 現在地 — 対比と追随優先順位（2026-08-02）

目的: 「先行する Crazyflie に並ぶために、彼らがどこまで到達し、我々が今追随すべきは
どこか」を明らかにする（著者指示 2026-08-02）。
出典: 5系統の並列調査（Crazyflie 側=公式 docs/GitHub/ストアの直接確認3系統、
StampFly 側=リポジトリ実装の実在確認2系統）。調査原本は `gap/` 配下の5ファイル。
各行の確認レベルは原本に明記（二次情報・未確認は本文でも注記）。

## 1. 次元別対比表

| # | 次元 | Crazyflie 到達点 | StampFly 現在地 | 判定 |
|---|------|------------------|-----------------|------|
| 1 | 状態推定 | 相補（既定）＋ **EKF 9状態**（誤差状態、11種の測定モデル: Flow/Loco/Lighthouse/MoCap対応）＋実験UKF | **ESKF 15状態**（バイアス6状態込み、χ²ゲート・active_mask隔離）＋相補代替 | ほぼ並び。状態数はSF、**外部測位対応の測定モデル多様性はCF** |
| 2 | 制御器 | **6種を実行時切替**（PID既定/Mellinger/INDI/Brescianini/Lee/out-of-tree枠）。レート・姿勢500Hz、位置100Hz、メイン1kHz | カスケードPID一本（**400Hz全段**）＋B⁻¹物理配分＋DOB(opt-in)＋条件付きAW。**IController差替インターフェースは実装済みだが実装はPID 1本** | **CF先行**（代替制御器群とOOT枠）。ただしCFの既定運用もPID |
| 3 | 軌道・上位コマンド | **High-level commander**（7次多項式軌道、takeoff/go_to/land/軌道アップロード、圧縮ベジェ表現） | 自動離着陸・位置保持・スティックリポジショニング・Tello互換API | **CF明確に先行**——最大のギャップ候補 |
| 4 | 測位方式 | Flow v2／**Loco UWB**（TWR≈10cm・TDoAで多機）／**Lighthouse**（絶対<10cm・相対<1mm公称、独立検証2-4cm）／MoCap／AI deck | **Flow＋ToFのみ**（相対測位・デッドレコニング） | **CF大幅先行**。群飛行・軌道の土台 |
| 5 | 群飛行 | Crazyswarm 49機（※二次情報・一次未裏取り）、Crazyswarm2=ROS2で活発 | 1機（ESP-NOW 1:1ペアリング） | **CF大幅先行** |
| 6 | オンボードAI | AI deck（GAP8）。自律航行実証は第三者研究（PULP-DroNet等） | なし | CF先行（研究レベル） |
| 7 | ユーザ拡張の器 | App layer（appMain/OOT枠）で自作制御器・推定器を差込可 | **4階層アクセス**（L0 Sketch=workshop別ファーム/L1 Topic API/L2 HAL/L3 BSP）＋Blockly | 思想は同格。**教育体系性はSF**、研究利用実績はCF |
| 8 | パラメータ・ログ | TOC方式。**ログはパケット26バイト・無線帯域制約** | params SSOT＋NVS＋ライブreload。**400Hz全状態UDPログ** | **SF優位の稀有な次元**。フルレートログはCFの無線では不可＝システム同定教材として強み |
| 9 | SIL/シミュレーション | **公式は Webots サンプルのみ（「非現実的・非活発」と自認）**。CrazySim=実機書込禁止の改造フォーク、他は外部プロジェクト | **Code Identity SIL**（無改変コンパイル＋決定論RTOSエミュ＋シナリオ40本/expect33本＋G1〜G4ゲート＋model-match gate＋ノイズn0-n2＋GUI） | **SF明確に先行**（本調査で確定） |
| 10 | 教育資産 | 大学講義採用（Princeton MAE345、UCB、Chalmers）＋DroneBlocks K-12提携。公式教育ポータルは404 | workshop 15レッスン＋Blockly＋examples＋スライド＋GUIインストーラ | 体系性はSF、**採用実績・裾野はCF** |
| 11 | コミュニティ・流通 | GitHub 77リポ・firmware★1,520・Discussions・月例開発者会議・直販（本体$240、デッキ20種、バンドル〜$7,200） | M5Stack流通（安価）・リリース7回・コミュニティ未形成 | **CF大幅先行** |
| 12 | 安全機構 | Supervisor 13状態機械＋Arming＋E-stop 2種 | フェイルセーフ・ペアリング・静止ゲート・電圧監視 | ほぼ並び（状態機械の体系性はCF） |
| 13 | 学術文書化 | 同定（Förster）・設計（Greiff）・プラットフォーム（Giernacki）等が**複数文献に分散** | 統合設計文書群＋**初論文をこれから** | 量はCF。**単一文書統合と xy 保持精度の公表は SF が先行できる** |

## 2. 制御理論の到達点（「私はPIDまで、他はどうなのか」への答え）

- Crazyflie の**既定・主力運用も カスケードPID**（レート・姿勢500Hz/位置100Hz）。
- 差は2点: (a) Mellinger・INDI・Brescianini・Lee が**ファーム同梱の選択肢**として存在
  （各実装はソース冒頭で学術論文への準拠を明記）、(b) OOT枠で自作制御器・推定器の
  差替研究が実際に回っている。
- 外側に、プラットフォームを使った外部研究（MPC・強化学習・適応制御等）が多数あるが、
  これは「本体の到達」と区別して数える。
- StampFly は PID 構造だが周辺に B⁻¹配分・DOB・条件付きAW・フェーズ別Ti・
  変動域ロバスト設計・15状態ESKF を実装済み。論文表記は「カスケードPID＋古典的補償構造」
  が正確。**差替インターフェース（sf_controller/IController）は実装済みで、実装が1本
  しかないだけ**——(b)の器は既にある。

## 3. 追随の優先順位（提言）

判断基準: 教育研究基盤としての価値 × 既存資産との接続 × 実現コスト。

| 優先 | 項目 | 根拠 |
|------|------|------|
| 1 | **軌道機能（high-level commander 相当）**: go_to・多項式軌道 | 最大ギャップ。POS_HOLD・ESKF・pos_sp の器が既にあり、SILで検証可能。誘導制御の教材価値大 |
| 2 | **代替制御器の1本目**（INDI または幾何学的制御を IController 実装で追加） | 器は準備済み。「制御を学ぶ人の基盤」の主張を実体化。SIL+model-match gate で安全に開発可能 |
| 3 | **外部測位の観測経路1本**（まずは MoCap/外部位置入力を ESKF 観測に追加） | 絶対測位ギャップの最小着手点。研究利用（真値比較・軌道実験）が開く。UWB/Lighthouse級のハード開発は長期課題として分離 |
| 4 | 群飛行の下地（ESP-NOW の多機対応設計） | 測位（#3）が前提。ESP-NOW自体は多機に向く素性 |
| 5 | 文書の英語化・コミュニティ形成（architecture.md 英訳完了 M1c 等） | 裾野の差はここから。論文発表はその第一歩 |
| 対象外（当面） | オンボードAI（AI deck相当） | ハード前提が異なり優先度低 |

## 4. 論文（v2構成）への反映

- **5章 SILS基盤**: 「Crazyflie 公式には実機同一コードのSILが存在しない
  （公式がWebotsサンプルを非現実的と自認、CrazySim は実機書込禁止の改造フォーク）」を
  事実として対比。400Hz フルレートログ（無線制約のCFでは不可）も教材面の差として言及可
- **6章 考察**: 本対比の要約1段落＋「今後の方向」として軌道機能・代替制御器・外部測位を
  淡々と挙げる（追随宣言として誠実）
- **2章**: パラメータ開示表に Crazyflie 対応値を併記（モータ時定数 T_m: CF≈65〜73ms vs
  SF=20ms、質量 27g vs 37g、EKF 9状態 vs ESKF 15状態 等）
- 位置保持精度 ±6〜7cm は「Crazyflie 文献に直接比較可能な xy 閉ループ公表値が
  見当たらない」（2026-08-01調査）ことを添えて提示

## 5. 正直な注記（過大主張の予防）

- StampFly 側の文書と実体の乖離（sf-firmware/sf-ecosystem 調査で検出）:
  (1) `ws::` L0 Sketch API の実装は別ファーム `firmware/workshop/`（vehicleコンポーネント
  をCMake再利用する別バイナリ）、(2) `protocol/generated`・`protocol/tools` は空
  （自動コード生成は未実装、実体は `firmware/common/protocol/` の手書き共有ヘッダ）、
  (3) `examples/protocol_roundtrip`・`pid_tuning` は .gitkeep のみ。
  **論文で「エコシステム」を語る際はこれらを含めない**か、正確な現状表現にする
- Crazyflie 側の未確認事項: Crazyswarm「49機」は二次情報、Lighthouse カバレッジは
  出典間で不一致（5×5m/8×8×3m）、教育ポータル本文404。引用時は原本の確認レベルに従う
- モデル一致ゲートの現況: roll/pitch PASS・yaw FAIL（sf sil sysid-gate 実測）——
  SILの忠実度主張はこの範囲で
