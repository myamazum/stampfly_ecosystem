# StampFly Ecosystem — firmware/vehicle・firmware/controller 機能棚卸し

調査日: 2026-08-02　調査対象コミット: `9910aacd`（main branch HEAD）
調査方法: `docs/feature_status.md` 等の記載を仮説とし、対応する実装ファイルの存在・内容を `grep`/`Read` で直接確認。**文書のみで実装が見当たらなかったものは「文書のみ」と明記**。表中の出典パスは全て `firmware/vehicle/` または `firmware/controller/` 基準（別記なき限り `/Users/kouhei/tmp/github/stampfly_ecosystem/` 配下）。

---

## 0. 総括

`docs/feature_status.md` の記載は、今回確認した範囲では実装との齟齬は見つからなかった（同文書は「完了」の定義を「実装済みかつSIL/実機で検証済み」としており、その分類自体は妥当）。ただし1点、**文書の言葉遣いが実体を誤解させ得る**箇所がある: 「L0 Sketch API (`ws::*`)」はアーキテクチャ設計文書上 `firmware/vehicle` の一部として表になっているが、実装は別ファーム `firmware/workshop/` にある（vehicleのコンポーネントをCMakeで再利用する形）。vehicle 単体のバイナリには `ws::` 名前空間は含まれない。詳細は §5。

---

## 1. 飛行モード（ACRO/STABILIZE/ALT_HOLD/POS_HOLD、自動離着陸、フェーズ管理）

| 機能 | 実装 | 出典 |
|------|------|------|
| 4モード列挙 | `enum class FlightMode { ACRO=0, STABILIZE=1, ALT_HOLD=2, POS_HOLD=3 }` | `components/sf_state/include/flight_state.hpp:74-79` |
| モード別カスケード | ACRO=レートPIDのみ、STABILIZE以上=姿勢PID→レートPID、ALT_HOLD以上=高度ループ追加、POS_HOLDは位置ループ追加。単一 `compute()` 内で `current_mode_` 分岐（並列実装ではない） | `components/sf_controller_pid/pid_controller.cpp:17-18, 251-280` |
| フライト状態機械（7状態） | `INIT→IDLE_GROUND↔IDLE_HELD→ARMED_GROUND→TAKEOFF→FLYING→LANDING`、StateManager単一所有 | `components/sf_state/include/flight_state.hpp:37-45`, `components/sf_state/state_manager.cpp` |
| 自動離着陸・鉛直フェーズ管理 | `VerticalPhase{Grounded, TakeoffClimb, Airborne, Landing}` を制御器内に保持し、INV-1（フェーズは鉛直チャンネルのみ変更）に従う | `components/sf_controller_pid/include/pid_controller.hpp:90-150` |
| フェーズ別 `ti`（積分時間）切替 | `alt_vel_.ti` を Airborne=`altitude.vel.ti_hover`、それ以外=`altitude.vel.ti` に切替。全 `phase_` 遷移ハンドラから呼ぶ設計（ライブreload時もフェーズ一致を保証） | `components/sf_controller_pid/pid_controller.cpp:106-114, 210-211` |
| takeoff/landing シーケンス | `sf_takeoff_landing` コンポーネント（`0.3 m/s` 自動離陸など） | `components/sf_takeoff_landing/takeoff_landing.cpp` (211行) |
| フェイルセーフ自動着陸 | 通信断／電池EMERGENCYで `−0.3 m/s` の着陸、モード非依存（ACRO/STABILIZEからの着陸でも姿勢カスケードのみ起動） | `components/sf_controller_pid/pid_controller.cpp:271-278, 465-468` |

判定: **実装確認済み**。`docs/feature_status.md` §2 の記載と一致。

---

## 2. 状態推定（ESKF 15状態、ロバスト化、相補フィルタ代替）

| 機能 | 実装 | 出典 |
|------|------|------|
| 15状態ESKF | `EskfCore`、状態インデックス `ATT_X/VEL_X/BG_X/BA_X/POS_X` 等 | `components/sf_estimator_eskf/eskf_core.cpp` (1053行), `include/eskf_core.hpp` |
| χ²ゲート | `mag_chi2_gate=7.81`（χ²(3,0.95)）、`accel_chi2_gate=7.81`、各観測更新 (`vectorUpdate3`) でゲート判定 | `include/eskf_core.hpp:82-83`, `eskf_core.cpp:381-460, 642, 726` |
| P行列隔離（active_mask） | `active_mask_`（15bitマスク）で無効状態のプロセスノイズ加算・更新をスキップ、`recomputeActiveMask()` | `eskf_core.cpp:297-308, 863-899, 972, 1001` |
| 疎構造化predict | コメントに「720積和」への削減の記述あり、`active_mask_ & (1<<...)` の条件加算で実現 | `eskf_core.cpp:297-308` |
| 推定器差し替え（IEstimator） | `IEstimator` 抽象、`estimator.type` パラメータ（0/1）でESKF/相補フィルタを選択 | `components/sf_estimator/include/estimator.hpp:54`, `components/sf_core/params.cpp:275, 708` |
| 相補フィルタ代替 | `ComplementaryEstimator` 実装あり（356行相当ファイル） | `components/sf_estimator_complementary/complementary_estimator.cpp` |

判定: **実装確認済み**。ロバスト化（χ²ゲート＋active_mask）はコード上でも二重に実装されており、`feature_status.md` の「χ²ゲート・active_maskによるP行列隔離・疎構造化」の記述と一致。

---

## 3. 制御器（カスケードPID、B⁻¹ミキサ、フェーズ別ti、DOB opt-in、リミット）

| 機能 | 実装 | 出典 |
|------|------|------|
| カスケードPID | `PidController`（1638行）、`IController` 差し替え可能 | `components/sf_controller_pid/pid_controller.cpp` |
| B⁻¹ミキサ（X-quad、物理単位） | `mixerCompute()` — 推力[N]・トルク[Nm]から4モータduty、ライブ電池電圧補償 (`vbat`引数) | `components/sf_actuator/actuator.cpp:203-330` |
| ヨー配分 `1/κ` の修正 | コメントに「旧簡易ミキサはκ倍していたため1.59倍過大」との既知修正の記録あり | `components/sf_actuator/actuator.cpp:91, 220` |
| フェーズ別ti | §1参照。`alt_vel_ti_climb_=2.5`, `alt_vel_ti_hover_=2.5` を個別パラメータで管理 | `components/sf_controller_pid/include/pid_controller.hpp:149-150` |
| DOB（加速度ベース外乱オブザーバ、opt-in） | `altitude.dob.fc`（既定0=無効）、Direct Form IIバイキャッド・ウォッシュアウト・遅延ライン・prime/engageランプを実装。Airborneフェーズ限定 | `components/sf_controller_pid/include/pid_controller.hpp:417-563`, `pid_controller.cpp:119-134` |
| 出力リミット一式 | `max_angle_=0.5236rad`(30°), `max_att_rate_sp_=3.0rad/s`, `rate_yaw_max_torque` (`1.83e-3` Nm既定), `max_thrust_correction_=0.15N`, `max_pos_vel_`, `max_pos_tilt_` 等、各PIDインスタンスに `output_limit` として配線 | `include/pid_controller.hpp:159-168`, `pid_controller.cpp:173-183`, `components/sf_core/params.cpp:677` |

判定: **実装確認済み**。

---

## 4. 適応・学習機能（hover thrust learning、姿勢トリム学習、autotune、magcal）

| 機能 | 実装 | 出典 |
|------|------|------|
| ホバー推力オンボード学習 | `learnHoverThrust()` — Airborne定常ホバーの速度積分残差から `hover_thrust_` を時定数 `kHoverLearnTau` で更新、着地エッジで `hover.thrust_corr` にNVS永続化。`hover.learn.enable` パラメータで有効化（既定値は §6 param表参照） | `pid_controller.cpp:968-1018`, `components/sf_core/params.cpp:487-493, 746` |
| 姿勢トリム学習（常時オンライン） | `learnTrim()` — ホバーゲートされたドリフトから `roll_trim_`/`pitch_trim_` を推定、離着陸エッジでNVS永続化。`attitude.trim.learn`（既定1=有効）で無効化可 | `pid_controller.cpp:840-905`, params: `attitude.roll.trim`, `attitude.pitch.trim`, `attitude.trim.learn` (`params.cpp:729-731`) |
| オンボードautotune | ステップドサイン掃引→プラント同定→PID設計。`sf_autotune`（純数学、ホストテスト可能）＋ `ApiTask::cmdAutotune()` が実行系。Tello風テキストコマンド `autotune` で起動（UDP:8889） | `components/sf_autotune/autotune.cpp` (341行), `tasks/api_task.cpp:593-755, 1046` |
| 地磁気校正（magcal） | `MagCalibrator`実装＋CLI `magcal [start|stop|status|save|clear]`、MagTask所有 | `components/sf_hal_bmm150/mag_calibration.cpp`, `tasks/cli_task.cpp:1147` |
| 校正データのNVS永続化 | **意図的に未配線**（`saveToNvs()`関数は実装済みだが呼び出されていない）。理由: NVS commit のフラッシュ消去が400Hzループを>10ms停止させるため保留、と実装コメントに明記 | `components/sf_calibration/calibration.cpp:47-71, 301-309`（コード上のコメントで確認、文書 `feature_status.md` §3 の記載と一致） |

判定: **実装確認済み**（校正NVS永続化のみ「意図的保留」で文書と一致、機能自体は文書通り未完了）。

---

## 5. API層（`ws::` Sketch API / `sf::api` Topic API / Tello SDK互換 / ブロックプログラミング対応）

| 機能 | 実装 | 出典 |
|------|------|------|
| `sf::api`（L1 Topic API） | `firmware/vehicle/components/sf_api/include/sf_api.hpp`（164行）— センサ・推定値・制御出力・モードの **read-only** スナップショット関数群（`imu_latest()`, `estimate_latest()`, `control_latest()`, `current_mode()`, `is_armed()` 等）。ヘッダ内コメントに「アクチュエータ制御・状態要求はスコープ外（M5=Workshop統合で対応予定）」と明記 | `components/sf_api/include/sf_api.hpp:25-43` |
| `ws::` L0 Sketch API | **`firmware/vehicle` には実装なし。** 実体は別ファーム `firmware/workshop/`（`workshop_api.cpp`/`.hpp`, `ws_internal.hpp`）にあり、`ws::motor_set_duty()` 等30+関数を提供。`firmware/workshop/CMakeLists.txt` が `../vehicle/components` をコンポーネント検索パスに追加し、vehicleの `sf_*` コンポーネント群・タスク（imu/state/flow/mag/baro/tof/power/comm/telemetry/button/notify/cli/log/api）をソースごと再利用する構成（別バイナリ、vehicleと同一コンポーネント基盤の上に構築） | `firmware/workshop/main/workshop_api.cpp:9-30`, `firmware/workshop/CMakeLists.txt:1-18`, `firmware/workshop/main/CMakeLists.txt` |
| Tello SDK互換 | `ApiTask` — UDP:8889でTelloテキストコマンド（`command`/`takeoff`/`land`/`emergency`/`stop`/移動/回頭/`rc a b c d`/クエリ）を受理、UDP:8890で状態文字列を配信（`TelloStateTask`）。移動はTello流に「目標値へ合成」 | `tasks/api_task.cpp`（1312行）, `components/sf_telemetry/include/tello_state.hpp` |
| ブロックプログラミング対応 | vehicle側に専用プロトコルなし。`lib/sfcli/commands/blocks.py`（ローカルHTTPブリッジ、ブラウザBlockly UI ↔ 上記Tello風UDP API）が仲介。つまりブロックプログラミングは**既存のTello API層に乗る形**で実現（vehicle側の追加実装は不要） | `lib/sfcli/commands/blocks.py:1-14, 52`, `lib/sfcli/assets/blocks.html`, `lib/sfcli/assets/vendor/blockly/` |

判定: `sf::api`・Tello API・ブロックプログラミング=**実装確認済み**（vehicle内）。`ws::` API=**実装は存在するが `firmware/vehicle` ではなく別ファーム `firmware/workshop` にある**。architecture.md/coding_and_education.md の階層表では `firmware/vehicle` の一部であるかのように書かれており（`ws::* → ws_api.hpp`)、実際のファイル配置と読み手に混同を生みうる。`workshop_migration.md` 内に「本計画（M5）は2026-07-18に実施した」との追記があり、移行は完了扱い（ただし移行後もバイナリはvehicleとworkshopで別）。

---

## 6. パラメータ基盤／ログ・テレメトリ

### パラメータ基盤

| 機能 | 実装 | 出典 |
|------|------|------|
| params.cpp = SSOT | 全パラメータをテーブル `{"name", type, &var, default, min, max, reload_cb}` で一元管理（1231行） | `components/sf_core/params.cpp` |
| CLI `param` コマンド | `param [list|get <name>|set <name> <value>|save]` | `tasks/cli_task.cpp:1137` |
| NVS永続化 | パラメータ用NVS（校正データとは別系統。校正のみ未配線、パラメータ自体は既定で保存対象） | `components/sf_core/params.cpp` 内 `param save`/NVS記述（コマンドテーブルに`save`動詞あり） |
| ライブreload | `param set` が所有タスクのコマンドトピックへ `ReloadParams` verbを発行（`notifyControllerReload()` 等）。全ての `rate.*`/`attitude.*` パラメータに配線済み | `components/sf_core/params.cpp:630-677` |

### ログ・テレメトリ

| 機能 | 実装 | 出典 |
|------|------|------|
| Telemetry（UDP 50Hz） | 状態モニタ用、`sf telemetry`（ターミナル/`--web`でSSEプロキシ経由ブラウザ） | `components/sf_telemetry/telemetry.cpp` |
| Data Stream（400Hz、UDP:8890、バイナリ） | 統合パケット `0x50`（50Hz送信、8制御周期分をバッチ化=400Hz相当）: `[Header 4B][ImuEskf 80B×8][PosVel 28B×8][RateRef 6B×8][entry_count][SensorEntry...][XOR checksum]`。ステータスパケット `0x4F`（1Hz、57B: 電池電圧/電流・状態・レートPIDゲイン）。旧vehicle電文と完全互換を意図した設計 | `components/sf_telemetry/include/data_stream_wire.hpp:30-70`, `data_stream.cpp` (412行) |
| Blackbox（SPIFFS） | 記載は `feature_status.md`（「ARM→DISARMで1セッション」）にあり、`sf_logger` コンポーネントが対応すると推測されるが、SPIFFS書き込み処理そのものの深掘りは未実施（**未確認**: `logger.cpp` の中身までは今回読んでいない） | `components/sf_logger/logger.cpp`（存在確認のみ） |

判定: パラメータ基盤・Data Stream・Telemetryは**実装確認済み**。Blackbox（SPIFFS）はファイル存在のみ確認、記録トリガー・フォーマットの詳細確認は**未確認**として明示。

---

## 7. 安全機構（フェイルセーフ、ペアリング、静止ゲート、電圧監視）

| 機能 | 実装 | 出典 |
|------|------|------|
| フェイルセーフ | `Failsafe`クラス — 通信断/電池EMERGENCY監視、衝撃検出（`G=9.80665` 定数でΔaccelから判定）、`system_alert` トピックへアラート発行。10Hz監視＋400Hz監視（`ImuAnomalyDetector`）の2系統 | `components/sf_failsafe/failsafe.cpp` (306行) |
| ペアリング | 相互MAC学習・PairingPacket（11B、SSOT準拠）・混信フィルタ・NVS復元（`loadPairingFromNvs()`）。StateManagerがPairingStateを所有、通信層は実行のみ | `components/sf_comm/comm.cpp:65-395` |
| 静止ゲート（起動校正） | `StillnessConfig`＋`updateStillness()` — 動き検出で蓄積破棄・やり直し、窓内分散チェック | `components/sf_calibration/calibration.cpp:105-195`, `include/calibration.hpp:44-149` |
| 電圧監視 | `PowerMonitor`（INA3221想定、`power_monitor.cpp`）＋`Failsafe`の電池EMERGENCY監視 | `components/sf_hal_power/power_monitor.cpp`, `components/sf_failsafe/failsafe.cpp` |
| controller側ペアリング・チャネル | `peering_process()`、MAC画面表示、SPIFFSペア情報保存、TDMA（20msフレーム/2msスロット/10スロット、`espnow_tdma.h`） | `firmware/controller/main/main.cpp:2170, 2302-2319`, `components/espnow_tdma/include/espnow_tdma.h:1-40` |
| controller側ARM | ジョイスティックのARMボタンをモーメンタリ（押している間のみ）読み取り、送信ビットに反映 | `firmware/controller/main/main.cpp:933-2059`（`joy_get_arm_button()`） |

判定: **実装確認済み**（vehicle・controller双方）。

---

## 8. 諸元: `docs/feature_status.md` と実装の突き合わせ結果一覧

| feature_status.md の主張 | 突き合わせ結果 |
|---|---|
| §2 4階層アクセス＋R1-R16、Pub-Subトピック | 確認済み（`sf_core/include/topics.hpp`、各コンポーネントの `@design` タグに `[OK]` 記載を多数確認） |
| §2 パラメータSSOT＋NVS＋ライブreload | 確認済み（§6参照） |
| §2 15状態ESKF・χ²ゲート・active_mask | 確認済み（§2参照） |
| §2 推定器差し替え（ESKF/相補フィルタ） | 確認済み（§2参照） |
| §2 カスケードPID・ミキサー（B⁻¹、物理単位） | 確認済み（§3参照） |
| §2 POS_HOLD実機検証済み（±6-7cm, RMS16mm） | 実機データそのものは今回未検証（ログ未参照）。コード上は POS_HOLD モードの実装自体は確認済み。**数値の再検証は範囲外・未確認** |
| §2 フライト状態機械・フェイルセーフ・ペアリング | 確認済み（§1, §7参照） |
| §2 Data Stream（旧vehicle電文互換）・Telemetry・CLI（USB+TCP:23） | Data Stream/Telemetryは確認済み。**TCP:23 CLIの実装箇所は今回未確認**（`cli_task.cpp` はUSB CDC REPLコマンドテーブルのみ確認、TCPサーバ部分のソケット処理は未読） |
| §3 Tello API「コア実装済み」 | 確認済み（§5参照）。「拡張コマンド（flip/curve等）・実機飛行検証は未了」との記載は、コード上でも `flip`/`curve` 相当のverbは見当たらず（**flip/curve系コマンドの不在を確認**、文書の「未了」記載と整合） |
| §3 校正のNVS永続化＝意図的保留 | 確認済み（§4参照、コード上のコメントで理由も一致） |
| §3 前方ToF＝HALあり・未ブリングアップ | HALファイル（`vl53l3cx_wrapper`等）の存在は確認。ブリングアップ（front ToF専用タスクや起動シーケンス配線）は今回のgrepでは見当たらず、文書の「未ブリングアップ」と矛盾しない（**能動的な未配線確認までは未実施**） |
| §3 磁気ヨー融合「既定off」 | `eskf.use_mag` 相当のフラグ配線は確認したが、パラメータ名の厳密な一致（`eskf.use_mag`）は params.cpp 全文grepでは今回未実施（**未確認**、`mag_task.cpp`/`eskf_estimator.cpp` に使用フラグの分岐はあると推定） |
| §5 vehicle_oldのCLIコマンド群(~50)が未移植 | vehicleのCLIコマンドテーブルは11個（`param/status/sensor/version/pair/unpair/sound/led/motor/wifi/magcal/reboot`）のみで、`takeoff`/`land`/`hover`等の自律飛行verbはCLIには存在しない（ただしTello API側=`api_task.cpp`には`takeoff`/`land`がテキストコマンドとして存在）。文書の「CLI経由の自律コマンドは未移植、Tello API側で代替」という主張と整合 |
| §5 WebSocketテレメトリ廃止 | 廃止の直接証拠（削除されたことの確認）は「WebSocket関連コードが存在しない」という消極的確認のみ（`grep`でWebSocket関連ヒットなし）。**「意図的に廃止した」という経緯自体はdocsの記載のみで、コードからは不在の事実しか確認できない** |

---

## 未確認事項（明示）

- Blackbox（SPIFFS）ログの記録トリガー・フォーマットの詳細（`logger.cpp` 内部は未読）
- CLI の TCP:23 経路（ソケットサーバ実装箇所）
- `eskf.use_mag` パラメータ名の厳密照合
- 前方ToFの「未ブリングアップ」の積極的確認（タスク配線が本当に無いことの網羅的grep）
- POS_HOLD実機保持精度（±6-7cm, RMS16mm）の生ログでの再検証（ドキュメント記載を実装確認の範囲に含めていない）
- controller側の完全なコマンドテーブル・メニュー階層（`menu_system.cpp` の中身は未読、ファイル存在のみ確認）
- vehicle_old（凍結レガシー、87実飛行）側との比較は範囲外としたため実施していない

---

## 主要出典ファイル一覧（抜粋）

```
firmware/vehicle/docs/feature_status.md
firmware/vehicle/components/sf_state/include/flight_state.hpp
firmware/vehicle/components/sf_state/state_manager.cpp
firmware/vehicle/components/sf_controller_pid/pid_controller.cpp
firmware/vehicle/components/sf_controller_pid/include/pid_controller.hpp
firmware/vehicle/components/sf_actuator/actuator.cpp
firmware/vehicle/components/sf_estimator_eskf/eskf_core.cpp
firmware/vehicle/components/sf_estimator_complementary/complementary_estimator.cpp
firmware/vehicle/components/sf_autotune/autotune.cpp
firmware/vehicle/components/sf_calibration/calibration.cpp
firmware/vehicle/components/sf_hal_bmm150/mag_calibration.cpp
firmware/vehicle/components/sf_api/include/sf_api.hpp
firmware/vehicle/tasks/api_task.cpp
firmware/vehicle/tasks/cli_task.cpp
firmware/vehicle/components/sf_core/params.cpp
firmware/vehicle/components/sf_telemetry/data_stream.cpp
firmware/vehicle/components/sf_telemetry/include/data_stream_wire.hpp
firmware/vehicle/components/sf_failsafe/failsafe.cpp
firmware/vehicle/components/sf_comm/comm.cpp
firmware/vehicle/components/sf_takeoff_landing/takeoff_landing.cpp
firmware/workshop/main/workshop_api.cpp
firmware/workshop/CMakeLists.txt
firmware/controller/main/main.cpp
firmware/controller/components/espnow_tdma/include/espnow_tdma.h
lib/sfcli/commands/blocks.py
```
