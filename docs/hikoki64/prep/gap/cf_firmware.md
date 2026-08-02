# Bitcraze Crazyflie 公式ファームウェア到達点調査

調査日: 2026-08-02
調査方法: WebFetch による bitcraze.io 公式ドキュメント / GitHub `bitcraze/crazyflie-firmware`（master ブランチ）の一次情報確認。**推測・記憶での補完は行っていない。確認できなかった項目は「未確認」と明記する。**
用途: 37g自作機 StampFly のエコシステムが Crazyflie に「並ぶ」ためのギャップ分析の基礎資料。

---

## 1. 状態推定の選択肢

出典: https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/sensor-to-control/state_estimators/ 、GitHub `src/modules/interface/kalman_core/kalman_core.h` 、`src/modules/src/kalman_core/` 、`docs/functional-areas/sensor-to-control/configure_estimator_controller.md`

実装ファイル名（`estimator_complementary.c`/`sensfusion6.c` 等）はドキュメントページの記述をそのまま引用している。実ソースコードの中身までは検証していない（ファイル名の実在は未確認）。

### 1-1. 相補フィルタ（Complementary Filter）— デフォルト
- コンパイル時デフォルトの推定器。
- 推定対象: 姿勢（ロール・ピッチ・ヨー）と高度（Z方向）。
- 対応センサ: ジャイロ、加速度計、（Z-ranger deck 搭載時）ToF距離。

### 1-2. 拡張カルマンフィルタ（EKF, `estimator_kalman`）
- **状態次元数: 9状態**（GitHub `kalman_core.h` の `KC_STATE_DIM = 9` を直接確認）。
  - X, Y, Z（グローバル位置、3状態）
  - 機体座標系 X/Y/Z 速度（PX, PY, PZ、3状態）
  - 姿勢誤差 D0, D1, D2（error-state、3状態）
  - 姿勢そのものは四元数として状態ベクトル外部で別途保持（誤差状態カルマンフィルタ＝ESKF構成）。
  - ジャイロバイアスは状態ベクトルに明示的に含まれていない（ヘッダ定義上は未確認＝確認できた範囲では非搭載）。
- 測定モデル（GitHub `src/modules/src/kalman_core/` のファイル一覧を直接確認、計11種類）:
  `mm_absolute_height.c`, `mm_distance.c`, `mm_distance_robust.c`, `mm_flow.c`, `mm_pose.c`, `mm_position.c`, `mm_sweep_angles.c`, `mm_tdoa.c`, `mm_tdoa_robust.c`, `mm_tof.c`, `mm_yaw_error.c`
- 対応デック（ドキュメント記載）: Flow deck v2（オプティカルフロー）、Loco Positioning deck（UWB TDoA/TWR）、Lighthouse deck（sweep angle）、Motion Capture deck（受動/能動マーカー、フルポーズ）。
- 監視: `kalman_supervisor.c` が範囲外の推定値を検出した際にリセットを行う（ドキュメント記載、ソース未検証）。

### 1-3. Unscented Kalman Filter（UKF）
- 実験段階の推定器。kbuild で明示的に有効化する必要がある（既定では無効）。
- 対応測定: Loco-Positioning TDoA、Flow-Deck v2。
- 外れ値除去: Flow deck の ToF 測定に簡易な外れ値除去スキームを実装（地上障害物通過時の高さジャンプ防止）。パラメータ `ukf.qualityGateTof` で品質ゲートを調整可能（ドキュメントに明記）。

### 選択方法
- ランタイム: パラメータ `stabilizer.estimator` を `StateEstimatorType` の値に設定（Pythonクライアント/ライブラリ/オンボードアプリいずれからも可能）。
- コンパイル時: kbuild設定 `ESTIMATOR`（例 `ESTIMATOR=kalman`）。
- 出典: `docs/functional-areas/sensor-to-control/configure_estimator_controller.md`（GitHub raw で直接確認）。

---

## 2. 制御器の選択肢

出典: https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/sensor-to-control/controllers/ 、GitHub `src/modules/interface/controller/controller.h` 、`src/modules/src/controller/controller_indi.c` 、`controller_brescianini.c`

### 2-1. `ControllerType` enum（GitHub `controller.h` を直接確認、定義順）
1. `ControllerTypeAutoSelect`
2. `ControllerTypePID`
3. `ControllerTypeMellinger`
4. `ControllerTypeINDI`
5. `ControllerTypeBrescianini`
6. `ControllerTypeLee`
7. `ControllerTypeOot`（`CONFIG_CONTROLLER_OOT` 有効時のみ — out-of-tree アプリでユーザ独自制御器をこの枠に差し込める）

ランタイムでパラメータ `stabilizer.controller` により切替可能、コンパイル時は kbuild `CONTROLLER`（例 `CONTROLLER=Mellinger`）。デフォルトは PID controller。

### 2-2. カスケードPIDコントローラ（デフォルト）
- 制御レベルごとに個別のPIDコントローラを持つ階層（カスケード）構造。
- 微分キック（Dキック）回避メカニズムを実装（ドキュメント記載、詳細未確認）。
- 実行周波数: 姿勢レートコントローラ 500Hz、姿勢コントローラ 500Hz、位置・速度コントローラ 100Hz。

### 2-3. Mellinger controller
- 微分フラットネスの数学的性質を利用する反応的幾何制御器。
- 実行周波数: 姿勢コントローラ 250Hz、位置コントローラ 100Hz。
- Iゲイン、角速度に対するD項を追加実装。
- 「プラットフォーム質量をファームウェアのプラットフォーム設定で更新する必要がある」とドキュメントに明記。

### 2-4. INDI controller（Incremental Nonlinear Dynamic Inversion）
- 出典論文: "Adaptive Incremental Nonlinear Dynamic Inversion for Attitude Control of Micro Aerial Vehicles"（*Journal of Guidance, Control, and Dynamics*、Smeur et al., 2015、GitHub ソース冒頭コメントで直接確認）。
- 制御対象: 姿勢角（ロール・ピッチ・ヨー）と角速度。内側ループ（姿勢）・外側ループ（位置）の二層構成に対応（`position_controller_indi.c` が別途存在）。
- 制御効果（G1・G2パラメータ）とアクチュエータダイナミクスを組み込んだ適応型設計。

### 2-5. Brescianini controller
- 出典論文: "Nonlinear Quadrocopter Attitude Control"（Brescianini, Hehn, D'Andrea、ETH Zurich, 2013、GitHub ソース冒頭コメントで直接確認）。
- 特徴: 線形位置制御（位置誤差・速度誤差→目標加速度）、推力制御、削減型姿勢制御（推力方向のみ）と完全型姿勢制御（ロール・ピッチ・ヨー個別）の融合。ヨー制御の時間定数をロール/ピッチと同水準に調整可能。
- 「プラットフォーム質量は計算に必須」とドキュメントに明記。
- GPLv3で公開。

### 2-6. Lee controller
- Mellingerと同じく微分フラットネスを利用する反応的幾何制御器。実行周波数はMellingerと同じ（姿勢250Hz、位置100Hz）。
- Mellingerとの違い: 角速度誤差の定義、姿勢コントローラの高次項が異なる。Iゲイン追加で性能向上。

### 2-7. 用途の書き分け（ページに明示的な飛行体タイプ別対応記載なし）
- ページ上に「この制御器はこの機体タイプ専用」という明示的な対応表は確認できなかった（未確認）。ただしMellinger/Brescianiniは質量パラメータの手動更新が必須と明記されており、機体（Crazyflie / Bolt / 独自機体）ごとの質量差し替えが前提の設計であることは確認できる。

### 2-8. Out-of-tree（OOT）カスタム制御器の追加
- `examples/app_out_of_tree_controller/README.md`（GitHub raw で直接確認）: Crazyflie 2.x 対応、app layer の仕組みを使ってビルトインPID以外の独自制御ロジックをファームウェアに追加できる。ブログ記事タイトルから「推定器（estimator）または制御器（controller）」を追加できる設計と読み取れる（記事本文は未確認）。

---

## 3. High-level Commander と軌道機能

出典: https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/sensor-to-control/commanders_setpoints/ 、trajectory_formats/ ページ

- 「high level commander generates setpoints from within the firmware based on a predefined trajectory」（ファームウェア内部で軌道からセットポイントを生成）。
- 軌道生成は **7次多項式（7th order polynomials）** を使用。
- ドキュメントに明示されているアクション: **take off / go to / land**（+ upload trajectory）。
- 軌道の内部表現（`trajectory_formats/` ページで直接確認）:
  - 生形式（raw）: 7次多項式係数をそのまま保存。
  - 圧縮形式: ベジェ曲線制御点を使用。座標ごとに次数を選択可能（0次=定数、1次=線形、3次=三次ベジェ、7次=完全多項式）。
  - **「circle」「poly4d」等の個別軌道タイプ名はこのページには記載されていなかった**（未確認 — CFlib側のヘルパー関数名の可能性はあるが今回未確認）。
- Python CFlib側: `HighLevelCommander` クラス（直接操作）、`PositionHlCommander` クラス（簡易API）。`commanderRelaxPriority()` でHigh-Level Commanderへ復帰、`send_notify_setpoint_stop()` でLow-level setpointからの切替を通知。
- 「Trajectory formats」への詳細ページは別途存在（上記で内容確認済み）。

---

## 4. App layer / out-of-tree アプリの仕組み

出典: https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/userguides/app_layer/ 、GitHub `examples/` ディレクトリ一覧

- `CONFIG_APP_ENABLE=y` でコンパイルすると、起動後に `void appMain()` が呼ばれる。**`appMain()` は戻ってはいけない**（呼び出されたきり動き続ける想定）。
- より細かい制御が必要な場合は `void appInit()` を定義可能。こちらは「戻る必要があり」、Crazyflie初期化シーケンスの続行を許す。
- スタックサイズはデフォルトで300バイトに設定可能（ドキュメント記載、単位はそのまま引用）。
- ビルド: out-of-tree構成では `Makefile` に `CRAZYFLIE_BASE` と `OOT_CONFIG` を指定し、`make clean && make`、またはtoolbeltの `tb make_app` コマンドを使用。
- 利用可能API:
  - ログ・パラメータAPI: `src/modules/interface/log.h` / `param.h` の内部アクセス関数。
  - LED制御: `src/hal/interface/ledseq.h`。
  - Appchannel: 最大30バイトの無線パケットで双方向通信（`src/modules/interface/app_channel.h`）。
- 公式サンプル一覧（GitHub `examples/` ディレクトリを直接列挙、13件）:
  `app_appchannel_test`, `app_color_led_cycle`, `app_color_led_effects`, `app_generic_led_cycle`, `app_hello_file_tree`, `app_hello_rs`（Rust）, `app_hello_world-cpp`, `app_hello_world`, `app_internal_param_log`, `app_out_of_tree_controller`, `app_p2p_DTR`, `app_peer_to_peer`, `app_persistent_param`, `app_stm_gap8_cpx`, および `demos` ディレクトリ。
- `app_out_of_tree_controller` の存在により、独自の推定器・制御器をアプリ層経由でファームウェアの選択肢（`ControllerTypeOot`）に差し込める仕組みが確認できる（§2-8参照）。

---

## 5. パラメータ・ログのフレームワーク

出典: https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/userguides/logparam/

- **TOC（Table of Contents）方式**: コンパイル時に各変数（ログ用・パラメータ用それぞれ）の型とアクセス制限を保持するテーブルが生成される。ログ用・パラメータ用で別々のTOCが1つずつ作成され、地上局クライアント接続時にダウンロードされる。
- **レート計測**: `statsCntRateCounter_t` 構造体と `STATS_CNT_RATE_INIT` マクロで、イベント/秒のレートをファームウェア内部で計測できる仕組みがある（ミリ秒単位の更新間隔を指定）。
- **無線帯域制約**: ロギング変数の**総長が26バイトを超えてはならない**という制限が明記されている。グループ名・変数名にドット（`.`）を含められない制約もある。
- **パラメータの実行時読み書き**: 可能だが「スレッド保護がない」ため32ビット変数までが安全、と明記。
- **永続化**: `PARAM_PERSISTENT` フラグで再起動後も値を保持する永続パラメータを実装可能。
- 制御ループ全体の実行レート（参考、§7参照）: メインの stabilizer loop は **1kHz**（GitHub `src/modules/src/stabilizer.c` のコメント「The stabilizer loop runs at 1kHz」を直接確認。`rateSupervisorInit` の許容範囲は997〜1003Hzで、実測1000Hz付近を監視している）。ログ・パラメータ通信自体の具体的な無線スループット（bps単位）はCRTPページに記載がなく**未確認**。

---

## 6. 安全機構（Supervisor / Arming / Emergency Stop）

出典: https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/supervisor/ 、supervisor/arming/ サブページ、GitHub `src/modules/interface/supervisor_state_machine.h`

### 6-1. Supervisor 状態機械
GitHub `supervisor_state_machine.h` の enum を直接確認。**全13状態**（`supervisorState_NrOfStates` を含む）:
1. `supervisorStateNotInitialized`
2. `supervisorStatePreFlChecksNotPassed`
3. `supervisorStatePreFlChecksPassed`
4. `supervisorStateArming`
5. `supervisorStateReadyToFly`
6. `supervisorStateFlying`
7. `supervisorStateLanded`
8. `supervisorStateReset`
9. `supervisorStateWarningLevelOut`
10. `supervisorStateExceptFreeFall`
11. `supervisorStateLocked`
12. `supervisorStateCrashed`
13. `supervisorState_NrOfStates`（状態総数を表すセンチネル、状態そのものではない）

動作: センサ/システムからデータ収集 → 状態遷移条件判定 → 遷移時にアクション実行 → 状態更新、の4段階サイクル。未武装状態や機体が逆さまの状態ではモーターを回転させない（高レベルコマンダーもブロック）。タンブリング（横転）検知時はモーターを停止し自由落下させる（`supervisorStateExceptFreeFall` / `supervisorStateCrashed` に対応すると推定されるが、遷移条件の一対一対応はドキュメント本文レベルでは未確認）。

### 6-2. Arming
- `supervisorStatePreFlChecksPassed` → `supervisorStateReadyToFly` への遷移に、Arming（アーミング）が必要（パイロットがシステムを制御可能であることを確認する必須アクション）。
- Armingリクエスト方法: CRTP経由でArmingメッセージを送信、またはオンボードアプリから `supervisorRequestArming()` 関数を呼び出し。
- **オートアーミング**: ブラシ付きモータ搭載の小型・安全なプラットフォーム（Crazyflie 2.0 / 2.1+）で利用可能。デフォルトで有効（`CONFIG_MOTORS_REQUIRE_ARMING=y` でコンパイル時設定）。有効時は `PreFlChecksPassed` 状態で自動的にarming要求が実行される。
- アイドルスラスト: Arming状態を示すためのモータ回転値。デフォルト0（回転しない）。ブラシレスモータ機種では回転値を明示的に設定する必要がある。

### 6-3. Emergency Stop
- **即時型**: 即時緊急停止コマンドを受けるとモーターを直ちに停止し、**ロック状態（`supervisorStateLocked`）に移行して再起動が必要**になる。
- **ウォッチドッグ型**: 周期的なキープアライブ信号が必要で、**1000ms以内に受信されない場合に緊急停止が発動**する。

---

## 7. 制御ループレート・対応MCU

### 7-1. 制御ループレート（GitHub `src/modules/src/stabilizer.c` を直接確認）
- **メインの stabilizer loop: 1kHz（1000Hz）**。ソースコメント「The stabilizer loop runs at 1kHz」、`rateSupervisorInit(&rateSupervisorContext, xTaskGetTickCount(), M2T(1000), 997, 1003, 1)` により実測997〜1003Hzで監視。
- 制御器ごとの内訳（§2で既出、controllers ドキュメントで直接確認）:
  - PIDカスケード: レート制御500Hz、姿勢制御500Hz、位置/速度制御100Hz。
  - Mellinger / Lee: 姿勢制御250Hz、位置制御100Hz。
- IMU更新周波数の明示的な数値定義はstabilizer.cには見当たらなかった（`sensorsWaitDataReady()` がメインループ1kHzと同期していると推定されるのみ、正確な値は未確認）。

### 7-2. 対応MCU / プラットフォーム
- GitHub README（`bitcraze/crazyflie-firmware`）記載の対応プラットフォーム: **Crazyflie Nano Quadcopter、Crazyflie Bolt Quadcopter、Roadrunner Positioning Tag**。
- ドキュメント（build.md）記載のサポート対象: **Crazyflie 2.0, 2.1(+)、Crazyflie 2.1 Brushless、Crazyflie Bolt**。
- **メインMCU: STM32F405**（GitHub `docs/development/dfu.md` に「新しいファームウェアをSTM32F405に読み込む」と明記。加えて `src/lib/STM32F4xx_StdPeriph_Driver/` ディレクトリ、`tools/make/F405/linker/DEF_CLOAD.ld` の存在をGitHubコード検索で直接確認）。STM32F4シリーズ（Cortex-M4）であることは確実だが、クロック周波数・フラッシュ/RAM容量などの詳細スペック値は今回未確認。
- 無線/電源管理用の第二SoCについて: Crazyflie 2.1 製品ページ（store.bitcraze.io）に「Dual-MCU architecture with dedicated radio/power management SoC」との記載を確認したが、**型番（nRF51822等）はこのページには明記されておらず未確認**。
- Crazyflie 2.1 の重量: store.bitcraze.io 製品ページに **27g**、バッテリー容量 250mAh LiPo と明記。飛行時間の具体的な数値は今回のページからは確認できなかった（未確認）。

---

## 未確認事項一覧（今回のソースで確認できなかったもの）

- CRTP / Crazyradio 無線リンクの具体的なスループット（bps）・パケットレート上限の数値。
- IMUの型番・更新周波数の正確な数値。
- 無線/電源管理SoCの型番（nRF51822等の記載は今回のページからは未確認）。
- Crazyflie 2.1 の公称飛行時間。
- Supervisor各状態間の遷移条件の完全な対応表（状態一覧は確認できたが、状態同士の遷移条件の一対一対応は `supervisor/transitions/` 等のサブページ本文までは読めなかった）。
- 「circle」「poly4d」等、CFlib側の軌道ヘルパー関数の個別名称・API仕様。
- App layer のログ・パラメータAPIにおけるアクセス権限レベル（読み取り専用/読み書き可否のグループ分け）の詳細。
- INDI / Brescianini / Lee 各制御器が「どの機体タイプに標準採用されているか」の公式な対応表（機体側の質量パラメータ差し替えが前提という設計思想は確認できたが、機種別デフォルト制御器の一覧は未確認）。

---

## 主要出典URL一覧

- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/sensor-to-control/state_estimators/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/sensor-to-control/controllers/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/sensor-to-control/commanders_setpoints/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/trajectory_formats/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/userguides/app_layer/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/userguides/logparam/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/supervisor/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/supervisor/arming/
- https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/crtp/
- https://github.com/bitcraze/crazyflie-firmware（README、examples/ ディレクトリ一覧）
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/docs/development/dfu.md
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/docs/functional-areas/sensor-to-control/configure_estimator_controller.md
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/src/modules/src/stabilizer.c
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/src/modules/interface/kalman_core/kalman_core.h
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/src/modules/interface/controller/controller.h
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/src/modules/src/controller/controller_indi.c
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/src/modules/src/controller/controller_brescianini.c
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/src/modules/interface/supervisor_state_machine.h
- https://raw.githubusercontent.com/bitcraze/crazyflie-firmware/master/examples/app_out_of_tree_controller/README.md
- https://store.bitcraze.io/products/crazyflie-2-1
- GitHub API code search（`gh api search/code`）: `bitcraze/crazyflie-firmware` 内のファイル一覧・文字列検索
