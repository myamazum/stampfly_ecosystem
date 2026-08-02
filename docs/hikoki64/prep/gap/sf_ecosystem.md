# StampFly Ecosystem 資産棚卸し（ファーム以外）

調査日: 2026-08-02　調査対象: `/Users/kouhei/tmp/github/stampfly_ecosystem`（ブランチ main、クリーン）
方針: 実装（コード・生成物）が実在するものだけを事実として記載し、出典パスを付す。ドキュメントに記載があるが実装が見当たらないものは**「文書のみ」**と明記する。

---

## 1. sf CLI 全コマンド（`lib/sfcli/commands/`）

`lib/sfcli/commands/` には29モジュール（`__init__.py`含む）、合計12,556行。各モジュールの冒頭 docstring / `COMMAND_HELP` から役割を確認。

| コマンド | 実装ファイル | 役割 |
|---|---|---|
| `sf app` | `app.py` | firmware/ 配下のカスタムファームプロジェクト管理（new等） |
| `sf blocks` | `blocks.py` (783行) | Blockly（ブラウザのブロックプログラミングUI）↔ 機体 UDP API のローカルHTTPブリッジ。127.0.0.1限定bind、stdlib専用実装 |
| `sf build` | `build.py` | ESP-IDF経由のvehicle/controllerビルド |
| `sf cal` | `cal.py` (422行) | センサキャリブレーション（gyro/accel/mag/level/status/plot） |
| `sf competition` | `competition.py` | workshop Day5 ホバー競技用タイマー・スコア表示 |
| `sf docs` | `docs.py` | MkDocsドキュメントサイトのserve/build |
| `sf doctor` | `doctor.py` (698行) | 開発環境診断 |
| `sf flash` | `flash.py` (352行) | vehicle/controllerへの書き込み |
| `sf flasher` | `flasher.py` | ネイティブ StampFly Flasher GUI アプリのインストール/更新/削除/状態確認 |
| `sf flight` (`sf takeoff/land/...`) | `flight.py` (659行) | WiFi CLI経由のTello風飛行コマンド送信 |
| `sf lesson` | `lesson.py` (875行) | workshopレッスン管理（list/switch/solution/info/edit/build/flash） |
| `sf log` | `log.py` (902行) | list/capture/wifi/convert/info/analyze/viz の7サブコマンド |
| `sf monitor` | `monitor.py` | シリアルモニタ |
| `sf motor` | `motor.py` (207行) | ベンチ用モータ test/sweep/stop（DISARM時のみ、CW/CCW電流非対称診断） |
| `sf params` | `params.py` | 物理パラメータ整合検査（check/generate） |
| `sf battery/height/tof/baro/attitude/acceleration/speed` | `query.py` | Tello互換クエリコマンド |
| `sf rc` | `rc.py` (415行) | リアルタイムRC入力（ワンショット／対話キーボード） |
| `sf setup` | `setup.py` | オプション依存パッケージ導入（sim/full/list） |
| `sf sil` | `sil.py` (1990行、最大) | SIL操作: build/run/video/status/gate/scenario/regression/milestone/sysid-gate |
| `sf sim` | `sim.py` (592行) | フライトシミュレータ list/run/headless |
| `sf sysid` | `sysid.py` (1331行) | システム同定: noise/inertia/motor/drag/params/validate/fit/plan/rate-fit/rate-tune/rate-excite |
| `sf telemetry` | `telemetry.py`／`telemetry_web.py` | 50Hzテレメトリのターミナル表示／ブラウザ表示（UDP→SSE、stdlib限定） |
| `sf trim` | `trim.py` (354行) | ホバリングログからの平衡姿勢トリム同定 |
| `sf upgrade` | `upgrade.py` (975行) | リモート追従・ローカル変更保持・依存再同期・sdkconfig陳腐化検出。stdlibのみで動作する契約あり |
| `sf version` | `version.py` | バージョン・環境情報表示 |

出典: `lib/sfcli/commands/*.py`（各モジュール冒頭docstring・`COMMAND_HELP`変数）

---

## 2. SIL（`simulator/sil/`）

### 2.1 位置づけ・正典
設計の正は `simulator/sil/RESET_PLAN.md`。運用方針の最終的な正は `docs/architecture/simulation-policy.md`（2026-07-22制定、RESET_PLANとの食い違いはこちらを優先）。

### 2.2 Code Identity の実装方式
- vehicleファームの実ソースをホストでそのまま無改変コンパイル（`compat/`にESP-IDF/FreeRTOSのホスト用スタブ：`esp_log.h`, `esp_err.h`, `esp_timer.h`, `nvs.h`, `nvs_shim.cpp`, `clock_shim.cpp`, `freertos/`）
- `rtos/` に決定論的協調RTOSエミュレータ（単一トークン＋仮想時計の離散事象スケジューラ）
- 実際の Pub-Sub ループ（`imu_task → estimate_state → control_task → actuator_motor`）をそのままホスト上で実行（RESET_PLAN §3, `simulator/sil/README.md`）
- pybind11バインディング `stampfly_control`（P5 stage 1）: `pid.hpp` を無改変コンパイルしPythonから直接呼べる。`tools/log_analyzer/rate_sysid.py` の手動移植版 `replay_pid()` との一致を `simulator/tests/test_pid_lockstep.py` で数値照合（出典: `simulator/sil/README.md`）

### 2.3 決定論性
- ノイズ・外乱は全てシード付き乱数（`std::mt19937`、シードはConfig）。同シード→byte-identical出力を維持（`simulator/sil/RESET_PLAN.md` §13、`README.md`の`--param`説明）
- `sf sil fly`（リアルタイム操縦, P6 stage1）のみ壁時計ペーシング用環境変数(`SIL_EMU_REALTIME`)を使うが、未設定時の通常実行（`scenario`/`regression`）には無影響と明記

### 2.4 シナリオ・合格ゲート
- `.scn`シナリオ40本、対応する`.expect`33本（出典: `find simulator/sil/scenarios -name "*.scn"|"*.expect"` 実測）。CI (`sil-regression.yml`) コメントでは「32本」と記載 — わずかに食い違いあり（グロブが正、と同ワークフロー内に注記）
- ゲート体系 G1〜G4（`simulator/sil/scenarios/TEST_MATRIX.md`）:
  - G1 起動・状態遷移（ログ文字列判定）
  - G2 推定の追従（`att_rmse`/`alt_rmse`）
  - G3 閉ループの安定（`horizontal_drift_max`/`tilt_max`/`alt_band`）
  - G4 アクチュエータ健全性（`duty_max`）
- L1(ACRO)〜L4(POS_HOLD)の層別シナリオが軸別（roll/pitch/yaw）→複合の順で用意され、2026-06-06時点で全PASS（決定論・N0オフ条件、出典同ファイル §4）
- CI: `.github/workflows/sil-regression.yml`（main push時、`firmware/**`/`simulator/sil/**`/`control/**`/`lib/sfcli/**`/`protocol/**`変更で起動、ESP-IDF不使用・システムGCC＋CMakeで直接ビルド）

### 2.5 ノイズモデル
`SIL_EMU_NOISE`環境変数でn0/n1/n2を選択（`simulator/sil/emu/emu_main.cpp`, `emu_main_generic.cpp`実測）:
- n0: 静的白色ガウス＋起動バイアス＋バイアスRW
- n1: n0＋スロットル依存の広帯域振動 (`vib_enable`)
- n2: n1＋振動スペクトル帯域制限 (`vib_bandlimit`)＋ToF/Baro観測ノイズ (`obs_enable`)
- 設計文書: `firmware/vehicle/docs/noise_and_vibration_model.md`（データシート比×79〜×191の実測ノイズ乖離を記録）
- N3（フロー品質モデル）は `docs/architecture/simulation-policy.md` §6 バックログ#6で「未着手」と明記 — **文書のみ（計画段階）**

### 2.6 モデル一致ゲート（sysid-gate）
`sf sil sysid-gate`（`lib/sfcli/commands/sil.py` `run_sysid_gate`）が `sysid_gate.scn` を400Hzレート記録付きで実行し、実機と同一の同定パイプライン（`sf sysid rate-fit`）で(b,L,T)を抽出、実機基準値と比較。
- 合格基準: 立ち上がり時定数 ±20%、gyro RMS ±50%（`docs/architecture/simulation-policy.md` §4）
- 実測結果: 初回計測(2026-07-22)は全軸FAIL（SIL一次遅れ支配 vs 実機むだ時間支配、構造が逆）。第2回計測(2026-07-26, モータODE化後)でroll/pitch PASS、yawは反トルク零点を3パラフィットで表現できずFAIL
- SILプラント改修バックログ（simulation-policy.md §6）は14項目、うち実装済みは#0/#1/#2/#3の4件、残り10件（不感帯、空気抵抗、フロー品質、バッテリサグRint実測、N1振動係数再同定、実機ログリプレイ、ヨー4パラ化、ヨートルク権限、姿勢減衰余裕等）は「未着手」

### 2.7 Web GUI（`sf sil gui`）
`simulator/sil/gui/`: `server.py`（stdlibのみ、静的配信＋JSON API）、`scn.py`（.scn⇔イベント配列変換）、`params_meta.py`（`params.cpp`のtable[]を正規表現パース）、`static/{index.html,app.js,style.css}`（Plotlyグラフ＋three.js 3Dビュー、CDN読込）。
機能: シナリオ作成・54個のパラメータ検索編集（`SIL_EMU_PARAMS_FILE`経由、再ビルド不要）・実行・3Dフライトアニメ・グラフ・合否ゲート表示。出典: `simulator/sil/gui/README.md`

---

## 3. 教育資産

### 3.1 workshopレッスン
- レッスンディレクトリ実数 **15**（`firmware/workshop/lessons/`実測: lesson_00〜lesson_13 + lesson_90_dxh_workshop）
- 順序SSOTは `firmware/workshop/lessons/lesson_manifest.yaml`。Day1〜構成で0:環境構築、1:モータ制御、2:コントローラ入力、3:LED制御、4:IMU、5:レートP制御+初飛行、6:システムモデリング、7:sysid、8:PID、9:推定、10:API概要、12:Python SDK、13:競技、90:DXH版
- Beamerスライド `.tex` は3ファイルのみ実装確認（`docs/workshop/slides/beamer/{preamble,stampfly_workshop,dxh_workshop}.tex`）— stampfly_workshop.texが全レッスンを1ファイルに集約している可能性が高く、レッスン単位の個別.texファイルは見当たらない（`lesson01.tex`等は存在しない。ビルド成果物`.aux`/`.log`/`.snm`はlesson_04〜13分が`docs/workshop/slides/beamer/`に残存＝ビルド実績はある）
- pptx: `docs/workshop/slides/pptx/generate_slides.py`のみ（生成スクリプト、静的pptx資産は`__pycache__`のみで実体ファイル未確認）

### 3.2 examples
- `examples/education/` 配下に8サブディレクトリ、各1〜2本のPythonスクリプト実在: `noise_analysis/allan_variance.py`, `hello_flight/{fly_and_move,hello_stampfly}.py`, `rate_step_test/analyze_step.py`, `pid_1d/pid_first_order.py`, `cascade_sim/cascade_demo.py`, `custom_pid/external_pid.py`, `waypoint_mission/waypoint_flight.py`, `square_path/square_path.py`
- `examples/README.md` は `protocol_roundtrip/`（仕様→エンコード/デコード最小例）と `pid_tuning/`（設計→パラメータ→実機反映）を案内しているが、両ディレクトリの中身は `.gitkeep` のみ — **文書のみ（未実装）**

### 3.3 Blockly Web UI
`sf blocks`実装は実在（`lib/sfcli/commands/blocks.py` 783行）。フロントエンドも実在: `lib/sfcli/assets/blocks.html`、Blockly本体を同梱 `lib/sfcli/assets/vendor/blockly/blockly.min.js`（v13.1.1、memoryインデックス記載と一致）。UDP:8889テキストAPI・UDP:8890状態文字列を仲介。教育ガイド `docs/guides/block_programming.md` あり。デモE2Eは実施済みだが実機E2Eは未実施（memory記載、本調査ではログ実測はしていない＝**未確認**）

### 3.4 スライド教材（一般）
`docs/assets/tikz/` にTikZ図資産、`docs/hikoki64/`（飛行機シンポジウム原稿）、`docs/sci26/`（学会原稿、LaTeX、`WRITING_POLICY.md`あり）、`docs/juida2026/`, `docs/sci_tutorial/` 等、学会・講座向け資料ディレクトリが多数存在（詳細な内容の逐一確認は本調査の範囲外／**未確認**）

---

## 4. 配布基盤

### 4.1 GUIインストーラ（StampFly Setup）
- 実装: `tools/installer_gui/stampfly_installer.py`
- 設計原則（docstring実測）: 自前のインストールロジックを持たず、(1)リポジトリclone、(2)clone直後の`scripts/installer.py`をプロセス内importしてInstallerクラスを呼ぶのみ。単一実体原則によりCLIインストーラ(`install.sh`/`install.bat`)と機能差なし
- ガイド: `docs/guides/gui-installer.md`。Windows/macOS(arm64/x64)/Linuxの4アセットをv2026.07.2以降のリリースから提供
- 付随: `tools/terminal_launcher/`（"StampFly Terminal"ランチャー、setup_env読込済み端末を開く）

### 4.2 フラッシャ（StampFly Flasher）
- 実装: `tools/flasher_gui/stampfly_flasher.py`（Python+Tkinter、クロスプラットフォーム）
- GitHub Releasesの最新`full.bin`を自動DL（SHA256検証）、esptoolをインプロセス呼び出し
- `sf flasher install/uninstall/status/update` でネイティブアプリ化。Linux版はv2026.07.2以降で提供
- macOS向けWeb Flasher(`/flash/`)のChromium Web Serialクラッシュ既知問題の回避策として案内

### 4.3 リリース体制
- タグ実績（`git tag`実測）: v2026.07.0〜v2026.07.6（7回のリリース）
- `.github/workflows/release.yml`: `v*`タグpushでvehicle/controller両ターゲットをESP-IDF v5.5.2 (esp32s3)でビルドし、`esptool.py write_flash 0x0`で直接書ける単一マージ済みイメージをGitHub Releaseへ添付。`workflow_dispatch`はビルド確認のみでRelease作成なし
- `.github/workflows/sil-regression.yml`: main push時にSILシナリオ退行を自動実行
- `.github/workflows/deploy-pages.yml`: 存在確認のみ（内容未精査、**未確認**）
- `sf upgrade`（`upgrade.py`、v2026.07.2で追加）: 非エキスパート向けの単一更新コマンド。stdlibのみで動作する契約があり、壊れた/中途半端なインストールからの復旧経路として設計

---

## 5. protocol/ SSOT の仕組み

- `protocol/spec/`: `messages.yaml`(464行)・`espnow_tdma.yaml`(217行)・`websocket.yaml`(197行)の3ファイル、機械可読仕様が実在
- `protocol/generated/`・`protocol/tools/`: **中身は`.gitkeep`のみ（空）** — READMEの「ディレクトリ構成」節では「仕様から生成されたコード」「仕様検証・コード生成ツール」と説明されているが、**自動コード生成は実装されていない（文書のみ）**
- 実際のプロトコル構造体実装は手書き: `firmware/common/protocol/include/espnow_protocol.hpp`、`udp_protocol.hpp`（CLAUDE.md記載の通り、vehicle/vehicle_old/controllerで共有）
- ControlPacket(14B)・TelemetryPacket(22B)・TelemetryWSPacket(116B, Legacy)・TelemetryExtendedBatchPacket(552B, 現行400Hz)のバイトレイアウトは`protocol/README.md`にテーブルで文書化されているが、これがコードから自動生成されている証跡はなく、**SSOTは「仕様書＋手書き実装の共有」であり、コード生成パイプラインは未実装**と判断される

---

## 6. analysis/・tools/ の解析・同定ツール群

### 6.1 tools/sysid（システム同定コアライブラリ）
`__init__.py`, `_generated_params.py`（`sf params generate`生成物、§6.3参照）, `defaults.py`, `drag.py`, `inertia.py`, `motor.py`, `noise.py`, `params.py`, `plant_fit.py`, `steady_state.py`, `validation.py`, `visualizer.py` の12モジュール実在。`sf sysid`の各サブコマンド（noise/inertia/motor/drag/params/validate/fit/plan/rate-fit/rate-tune/rate-excite、計11種、`sysid.py`内`add_parser`呼び出し15箇所で確認）のバックエンド

### 6.2 tools/log_analyzer
FFT解析(`analyze_fft.py`, `analyze_fft_detailed.py`)、飛行解析(`flight_analysis.py`)、モータ健全性(`motor_health.py`)、時系列プロット(`plot_timeseries.py`)、レートsysid(`rate_sysid.py`)、ESKF/姿勢3D可視化(`visualize_eskf.py`, `visualize_pose_3d.py`, `visualize_attitude_3d.py`等9種)、UDP/WiFiキャプチャ(`udp_capture.py`, `wifi_capture.py`)など多数実在。過去のFFT実行結果CSV・PNGも残存（実測ログとの紐付き実績あり）

### 6.3 tools/params_audit
`check_params.py`・`generate.py`・`params_manifest.py`。`sf params check`（Phase 0監査、稼働中）と`sf params generate`（Phase 1コード生成、2026-07-26に一部着手）の2系統。生成対象は`tools/sysid/_generated_params.py`・`simulator/sil/plant/generated_params.hpp`・`docs/architecture/stampfly-parameters.md`の3箇所のみで、`simulator/genesis/motor_model.py`・`simulator/vpython/core/motors.py`・firmware側`actuator.cpp`等10箇所以上は依然手書き複製のまま（README実測記載）

### 6.4 tools/log_capture, calibration, ci
- `log_capture.py`: USBシリアル経由バイナリログ取得
- `calibration/plot_mag_xy.py`: 磁力計プロット
- `ci/`: `check_flasher_install.py`, `check_installer_gui.py`, `check_upgrade.py`, `render_sil_summary.py`（CI検証スクリプト群）

### 6.5 analysis/
- `analysis/scripts/` に個別研究ディレクトリ9件（`ct_switch_study_20260727`, `alt_dob_design`, `verify_hikoki64`, `thermal_ident_study_20260729`, `roll_tuning_20260717`, `yaw_nt_kanazawa`, `vt_ident_study_20260729` 等）
- `analysis/reports/` に5件のレポートディレクトリ（`yaw_nt_kanazawa_20260627`, `altlog_20260614T201629`, `rate_sysid_reference`, `altlog_20260614T214537` 等）
- 層2（実ログ駆動オフライン再生）の実施記録として`simulation-policy.md`から参照されている実績値（ヨーκ修正リプレイ一致0.0〜0.7%、ALT_HOLD再生誤差約8%、高度DOB設計シム予測−37〜−56%→実機−67%）と対応

### 6.6 tools/stampfly_py
Tello風Python SDK。`stampfly.py`本体＋djitellopy互換サンプル(`example_djitellopy.py`, `example_djitellopy2.py`)、`example_square.py`。`sf blocks`は意図的にこれを再利用せず独自クライアントを実装（ブロッキング設計のため優先stop経路が組めないと`blocks.py`docstringに明記）

---

## 7. Genesis シミュレータ連携の状態

- `simulator/genesis/`: `motor_model.py`, `control_allocation.py`（アクティブ）、`scripts/run_genesis_sim.py`・`run_genesis_headless.py`（メインスクリプト）
- `scripts/archive/` に開発履歴・デバッグスクリプト24本超（`01_hello_genesis.py`〜`24_pid_rate_control.py`、`debug_*.py`群）— 現行運用対象外の過去資産として明示的にarchive化されている
- 連携状態: 物理量ベース制御（PID出力=トルク[Nm]）、2000Hz物理演算・400Hz制御ループ、RK4モータ/プロペラダイナミクス。venv環境（`requirements.txt`）で`genesis-world`+`torch`導入が前提
- **SILとの関係が判明**: `simulation-policy.md`のSILバックログ#2（モータODE化、2026-07-26実装済み）は`simulator/genesis/motor_model.py`の電気機械ODEをSILへ移植したものと明記されている — Genesisは独立シムに留まらず、実測モータパラメータ（$J_{mp}$, $C_Q$, $K_m$, $R_m$等）の供給源としてSILプラント改良に実際に寄与した実績がある
- ドキュメント: `simulator/genesis/docs/urdf_mesh_normals.md`、`docs/architecture/genesis-integration.md`（本調査では内容精査せず、**未確認**）

---

## 8. ドキュメント体系

### 8.1 firmware/vehicle 設計6文書（CLAUDE.md必読指定）
`firmware/vehicle/docs/` 実測行数: `requirements.md`(500行), `architecture.md`(825行), `detailed_design.md`(814行), `coding_and_education.md`(418行), `development_roadmap.md`(444行), `hardware_init.md`(344行) — 合計3,345行、全て実在確認
- 同ディレクトリには他に18本の派生・調査系ドキュメント（`chi2_latchup_*`, `poshold_journey.md`, `yaw_axis_model.md`, `noise_and_vibration_model.md`, `control_theory_overview.md`, `topic_reference.md`, `workshop_migration.md`, `wobble_minimization_study.md`, `implementation_log.md`, `feature_status.md`, `operation_manual.md`, `pairing_plan.md`, `init_stuck_debug.md`, `code_review_2026-06-13.md`, `design_tag_verification.md`, `takeoff_overshoot_findings.md`, `alt_hold_takeoff_findings.md`, `figures/`）が実在

### 8.2 docs/architecture/
11ファイル実在: `ros2-udp-debug.md`, `genesis-integration.md`, `tello-api-reference.md`, `coordinate-systems.md`, `control-system.md`, `stampfly-parameters.md`, `simulation-policy.md`（シミュレーション方針SSOT、2026-07-22制定）, `tdma-usage.md`, `control-allocation-migration.md`

### 8.3 docs/guides/, docs/commands/, docs/setup/
- `docs/guides/`: 9本（`gui-installer.md`, `motor_spin_quickstart.md`, `troubleshooting.md`, `glossary.md`, `safety.md`, `block_programming.md`, `flight-log-viz.md`, `upgrading.md`, `tools.md`）
- `docs/commands/`: sf CLI各コマンドのリファレンス18本＋README（`sf-upgrade.md`等、`lib/sfcli/commands/`の主要コマンドと1対1対応）
- `docs/setup/`: OS別セットアップ（windows/macos/linux）＋wifi-sta/education/README

### 8.4 プロトコル・SIL固有文書
`simulator/sil/docs/` に6本（`coordinate_frames.md`, `hover_resume.md`, `p5_noise_resume.md`, `plant_timebase_bug.md`, `vl53_dynamic_validity_resume.md`, `vl53_m2_resume.md`）。`simulator/sil/RESET_PLAN.md`がSIL設計の正、`simulator/sil/scenarios/TEST_MATRIX.md`がシナリオ一覧の正

### 8.5 バイリンガル構成の遵守
確認した主要文書（`README.md`各種、`simulation-policy.md`, `RESET_PLAN.md`, `TEST_MATRIX.md`, `gui-installer.md`等）は全てCLAUDE.md規定の「日本語→`<a id="english">`区切り→英語」構成に従っていることを実測確認

---

## 総括所見（棚卸しから見える構造）

1. **文書のみ（実装未確認）の代表例**:
   - `protocol/generated/`・`protocol/tools/` — READMEが謳う自動コード生成は未実装。実体は手書き共有ヘッダ（`firmware/common/protocol/`）
   - `examples/protocol_roundtrip/`・`examples/pid_tuning/` — READMEに案内があるが中身は`.gitkeep`のみ
   - SILノイズN3（フロー品質モデル）— simulation-policy.md自身が「未着手」と明記
   - SILプラント改修バックログ14項目中10項目「未着手」（不感帯、空気抵抗、Rint実測、実機ログリプレイ等）

2. **数値が計画とわずかに食い違う箇所**: `.scn`/`.expect`実測（40本/33本）と`sil-regression.yml`コメント記載（32本）に差異（ワークフロー内で「グロブが正、本数は増えてよい」と自己申告済みなので矛盾ではなく更新遅延）

3. **相互連携の実例**: Genesis（`motor_model.py`の電気機械ODE）が実測モータパラメータの供給源としてSILプラント改修バックログ#2に実際に反映された、という文書横断の裏取りができた数少ない事例。
