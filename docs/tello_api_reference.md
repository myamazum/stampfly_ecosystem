# Tello SDK API リファレンス — StampFly 互換レイヤー設計

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このドキュメントについて

DJI Tello SDK は教育用ドローンのデファクトスタンダードであり、djitellopy をはじめとする Python SDK が世界中の教育現場で使われている。本ドキュメントは Tello SDK の仕様を網羅的に整理し、StampFly への移植に必要な差分を明確にする。

### Tello SDK バージョン

| バージョン | 対象デバイス | 主な追加機能 |
|-----------|------------|-------------|
| SDK 1.3 | Tello（通常版） | 基本飛行、移動、回転、フリップ、ビデオ |
| SDK 2.0 | Tello EDU | `stop`、ミッションパッド、`sdk?`/`sn?`/`wifi?`、`ap` |
| SDK 3.0 | Tello EDU (v02.05.01.17+) / RoboMaster TT | `motoron`/`motoroff`、`throwfly`、ビデオ設定、ポート再設定 |

### 本ドキュメントの対象範囲

StampFly 互換レイヤーは **SDK 2.0** を基準とする。SDK 2.0 は最も広く使われており、djitellopy のデフォルト対象バージョンである。SDK 3.0 固有のコマンド（`motoron` 等）は Phase 5 以降で検討する。

## 2. 通信アーキテクチャ

### Tello の通信構成

```
PC / スマートフォン  <-- WiFi -->  Tello (192.168.10.1)
      │                                  │
      │  UDP 8889 (コマンド送受信)         │
      │  ─────────────────────────────>   │
      │  <─────────────────────────────   │
      │                                  │
      │  UDP 8890 (テレメトリ受信)         │
      │  <─────────────────────────────   │
      │                                  │
      │  UDP 11111 (H.264 ビデオ受信)     │
      │  <─────────────────────────────   │
```

### StampFly の通信構成（現状）

```
PC / スマートフォン  <-- WiFi -->  StampFly (192.168.4.1)
      │                                  │
      │  TCP 23 (Telnet CLI)              │
      │  ─────────────────────────────>   │
      │  <─────────────────────────────   │
      │                                  │
      │  WebSocket 80 (バイナリテレメトリ)  │
      │  <─────────────────────────────   │
```

### 通信プロトコル比較

| 項目 | Tello | StampFly（現状） | 互換レイヤー（計画） |
|------|-------|-----------------|-------------------|
| コマンド送受信 | UDP 8889（テキスト） | TCP 23（Telnet CLI） | UDP 8889（テキスト） |
| テレメトリ | UDP 8890（テキスト、10Hz） | WebSocket 80（バイナリ、400Hz） | UDP 8890（テキスト、10Hz） |
| ビデオ | UDP 11111（H.264） | なし | 非対応 |
| ドローン IP | 192.168.10.1 | 192.168.4.1 | 192.168.10.1 に変更 |
| 初期化 | `command` 送信で SDK モード開始 | Telnet 接続 | `command` 送信で SDK モード開始 |
| 自動着陸 | 15秒間コマンドなしで自動着陸 | なし | 15秒タイムアウト実装 |

### Tello 初期化シーケンス

1. WiFi で Tello AP に接続（SSID: `TELLO-XXXXXX`）
2. UDP ソケットを `0.0.0.0:8889` にバインド
3. テレメトリ受信用ソケットを `0.0.0.0:8890` にバインド
4. `"command"` を `192.168.10.1:8889` に送信
5. `"ok"` レスポンスを受信 → SDK モード有効化完了

## 3. コマンド一覧（Tello → StampFly マッピング）

### コマンドカテゴリ概要

| カテゴリ | コマンド数 | StampFly 対応状況 |
|---------|----------|------------------|
| 初期化 (`command`) | 1 | 未対応 → Phase 1 |
| 基本飛行 (`takeoff`/`land`/`emergency`/`stop`) | 4 | 部分対応（`takeoff`/`land` 実装済） |
| 移動 (`up`/`down`/`left`/`right`/`forward`/`back`) | 6 | 未対応 → Phase 2 |
| 回転 (`cw`/`ccw`) | 2 | 未対応 → Phase 2 |
| 複合飛行 (`go`/`curve`) | 2 | 未対応 → Phase 2 |
| RC 制御 (`rc`) | 1 | 未対応 → Phase 4 |
| フリップ (`flip`) | 1 | 非対応（ハード制約） |
| 読み取り (`battery?`/`speed?` 等) | 12 | 未対応 → Phase 3 |
| 設定 (`speed`/`wifi`/`ap`) | 3 | 未対応 → Phase 3 |
| ビデオ (`streamon`/`streamoff`) | 2 | 非対応（カメラなし） |
| ミッションパッド (`mon`/`moff` 等) | 6 | 非対応 |
| モーター (`motoron`/`motoroff`, SDK 3.0) | 2 | 未対応 → Phase 5 |
| その他 (SDK 3.0) | 5 | 非対応 |

### コントロールコマンド

| コマンド | 構文 | 説明 | レスポンス | StampFly 対応 |
|---------|------|------|-----------|--------------|
| `command` | `command` | SDK モード開始 | `ok` / `error` | **Phase 1** |
| `takeoff` | `takeoff` | 自動離陸 | `ok` / `error` | **実装済** ※ |
| `land` | `land` | 自動着陸 | `ok` / `error` | **実装済** ※ |
| `emergency` | `emergency` | 全モーター緊急停止 | `ok` / `error` | **Phase 1** |
| `stop` | `stop` | その場でホバリング | `ok` / `error` | **Phase 1**（`hover` で代用可） |

※ 現状の StampFly `takeoff`/`land` は TCP CLI 経由。Tello 互換にするには UDP 8889 でのテキストコマンド受付が必要。

### 移動コマンド

| コマンド | 構文 | パラメータ範囲 | 単位 | StampFly 対応 |
|---------|------|--------------|------|--------------|
| `up` | `up x` | x: 20-500 | cm | **Phase 2** |
| `down` | `down x` | x: 20-500 | cm | **Phase 2** |
| `left` | `left x` | x: 20-500 | cm | **Phase 2** |
| `right` | `right x` | x: 20-500 | cm | **Phase 2** |
| `forward` | `forward x` | x: 20-500 | cm | **Phase 2** |
| `back` | `back x` | x: 20-500 | cm | **Phase 2** |

### 回転コマンド

| コマンド | 構文 | パラメータ範囲 | 単位 | StampFly 対応 |
|---------|------|--------------|------|--------------|
| `cw` | `cw x` | x: 1-360 | 度 | **Phase 2** |
| `ccw` | `ccw x` | x: 1-360 | 度 | **Phase 2** |

### 複合移動コマンド

| コマンド | 構文 | パラメータ | StampFly 対応 |
|---------|------|----------|--------------|
| `go` | `go x y z speed` | xyz: -500~500 cm, speed: 10-100 cm/s | **Phase 2** |
| `curve` | `curve x1 y1 z1 x2 y2 z2 speed` | xyz: -500~500 cm, speed: 10-60 cm/s, 弧半径: 0.5-10m | 未定 |

### RC コントロール

| コマンド | 構文 | パラメータ | 説明 | StampFly 対応 |
|---------|------|----------|------|--------------|
| `rc` | `rc a b c d` | 各値: -100~100 | a=左右, b=前後, c=上下, d=ヨー | **Phase 4** |

RC パラメータ詳細：

| パラメータ | 範囲 | 説明 |
|-----------|------|------|
| `a` (left_right) | -100（左）~ 100（右） | ロール入力 |
| `b` (forward_backward) | -100（後）~ 100（前） | ピッチ入力 |
| `c` (up_down) | -100（下）~ 100（上） | スロットル入力 |
| `d` (yaw) | -100（反時計回り）~ 100（時計回り） | ヨー入力 |

### フリップコマンド

| コマンド | 構文 | パラメータ | StampFly 対応 |
|---------|------|----------|--------------|
| `flip` | `flip x` | l（左）/ r（右）/ f（前）/ b（後） | **非対応**（ハード制約：機体重量・推力比の制約でフリップ不可） |

### 読み取りコマンド

| コマンド | 構文 | レスポンス例 | 単位 | StampFly 対応 |
|---------|------|------------|------|--------------|
| `speed?` | `speed?` | `"10"` | cm/s | **Phase 3** |
| `battery?` | `battery?` | `"87"` | % | **Phase 3** |
| `time?` | `time?` | `"15"` | 秒 | **Phase 3** |
| `wifi?` | `wifi?` | `"90"` | SNR | 未定 |
| `sdk?` | `sdk?` | `"20"` | - | **Phase 3** |
| `sn?` | `sn?` | `"0TQDF6GEBMB5HF"` | - | **Phase 3** |
| `height?` | `height?` | `"50"` | cm | **Phase 3** |
| `temp?` | `temp?` | `"62~65"` | °C | 未定 |
| `attitude?` | `attitude?` | `"pitch:0;roll:0;yaw:0;"` | 度 | **Phase 3** |
| `baro?` | `baro?` | `"170.07"` | cm | **Phase 3** |
| `acceleration?` | `acceleration?` | `"agx:-13.00;agy:-5.00;agz:-998.00;"` | cm/s² | **Phase 3** |
| `tof?` | `tof?` | `"10"` | cm | **Phase 3** |

### 設定コマンド

| コマンド | 構文 | パラメータ | StampFly 対応 |
|---------|------|----------|--------------|
| `speed` | `speed x` | x: 10-100 cm/s | **Phase 3** |
| `wifi` | `wifi ssid pass` | SSID とパスワード | 未定 |
| `ap` | `ap ssid pass` | ステーションモード接続（EDU のみ） | 未定 |

### ビデオコマンド

| コマンド | 構文 | StampFly 対応 |
|---------|------|--------------|
| `streamon` | `streamon` | **非対応**（カメラなし） |
| `streamoff` | `streamoff` | **非対応**（カメラなし） |

### ミッションパッドコマンド（EDU 専用）

| コマンド | 構文 | 説明 | StampFly 対応 |
|---------|------|------|--------------|
| `mon` | `mon` | ミッションパッド検出有効 | **非対応** |
| `moff` | `moff` | ミッションパッド検出無効 | **非対応** |
| `mdirection` | `mdirection x` | 検出方向: 0=下方, 1=前方, 2=両方 | **非対応** |
| `go` (with mid) | `go x y z speed mid` | パッド基準座標移動 | **非対応** |
| `curve` (with mid) | `curve ... speed mid` | パッド基準カーブ移動 | **非対応** |
| `jump` | `jump x y z speed yaw mid1 mid2` | パッド間移動 | **非対応** |

### SDK 3.0 追加コマンド

| コマンド | 構文 | 説明 | StampFly 対応 |
|---------|------|------|--------------|
| `motoron` | `motoron` | モーター低速回転開始 | **Phase 5** |
| `motoroff` | `motoroff` | モーター低速回転停止 | **Phase 5** |
| `throwfly` | `throwfly` | スロー・トゥ・フライ | 非対応 |
| `reboot` | `reboot` | ドローン再起動 | **Phase 5** |
| `setbitrate` | `setbitrate x` | ビデオビットレート設定 | 非対応 |
| `setfps` | `setfps x` | ビデオ FPS 設定 | 非対応 |
| `setresolution` | `setresolution x` | ビデオ解像度設定 | 非対応 |

## 4. テレメトリ仕様

### Tello テレメトリフォーマット

Tello は UDP 8890 でセミコロン区切りのテキストデータを約 10Hz で送信する。

```
pitch:0;roll:0;yaw:0;vgx:0;vgy:0;vgz:0;templ:62;temph:65;tof:10;h:0;bat:87;baro:170.07;time:0;agx:-13.00;agy:-5.00;agz:-998.00;\r\n
```

### Tello テレメトリフィールド

| フィールド | 型 | 単位 | 説明 |
|-----------|-----|------|------|
| `pitch` | int | 度 | ピッチ角 |
| `roll` | int | 度 | ロール角 |
| `yaw` | int | 度 | ヨー角 |
| `vgx` | int | dm/s | X 軸速度 |
| `vgy` | int | dm/s | Y 軸速度 |
| `vgz` | int | dm/s | Z 軸速度 |
| `templ` | int | °C | 最低温度 |
| `temph` | int | °C | 最高温度 |
| `tof` | int | cm | ToF センサー距離 |
| `h` | int | cm | 高度（相対） |
| `bat` | int | % | バッテリー残量 |
| `baro` | float | cm | 気圧計高度 |
| `time` | int | 秒 | モーター使用時間 |
| `agx` | float | cm/s² | X 軸加速度 |
| `agy` | float | cm/s² | Y 軸加速度 |
| `agz` | float | cm/s² | Z 軸加速度（静止時 ≈ -998） |

### StampFly テレメトリとの対応

StampFly は WebSocket でバイナリパケットを 400Hz（4サンプル × 100フレーム/秒）で送信する。1サンプルは 136 バイトの `ExtendedSample` 構造体。

| Tello フィールド | StampFly フィールド | 変換 |
|-----------------|-------------------|------|
| `pitch` | `quat_w/x/y/z` → オイラー角 | クォータニオンからピッチ角を算出 |
| `roll` | `quat_w/x/y/z` → オイラー角 | クォータニオンからロール角を算出 |
| `yaw` | `quat_w/x/y/z` → オイラー角 | クォータニオンからヨー角を算出 |
| `vgx` | `vel_x` | m/s → dm/s に変換 |
| `vgy` | `vel_y` | m/s → dm/s に変換 |
| `vgz` | `vel_z` | m/s → dm/s に変換（NED→Tello座標系変換） |
| `templ` | なし | ダミー値（ESP32 チップ温度で代用可能） |
| `temph` | なし | ダミー値（ESP32 チップ温度で代用可能） |
| `tof` | `tof_bottom` | m → cm に変換 |
| `h` | `pos_z` | NED の Z（下方正）→ cm に変換（符号反転） |
| `bat` | なし | バッテリー電圧から % 換算（要実装） |
| `baro` | `baro_altitude` | m → cm に変換 |
| `time` | `timestamp_us` | μs → 秒に変換（起動時からの経過時間） |
| `agx` | `accel_x` | m/s² → cm/s² に変換 |
| `agy` | `accel_y` | m/s² → cm/s² に変換 |
| `agz` | `accel_z` | m/s² → cm/s² に変換 |

### StampFly 固有テレメトリ（Tello にないもの）

| フィールド | 単位 | 説明 |
|-----------|------|------|
| `gyro_x/y/z` | rad/s | 生ジャイロデータ（LPF 済） |
| `gyro_corrected_x/y/z` | rad/s | バイアス補正済ジャイロ |
| `ctrl_throttle/roll/pitch/yaw` | 0-1 / -1~1 | 制御入力値 |
| `gyro_bias_x/y/z` | 0.0001 rad/s | ジャイロバイアス推定値 |
| `accel_bias_x/y/z` | 0.0001 m/s² | 加速度バイアス推定値 |
| `eskf_status` | - | ESKF 収束フラグ |
| `tof_front` | m | 前方 ToF 距離 |
| `flow_x/y` | pixel/frame | オプティカルフロー |
| `flow_quality` | 0-255 | フロー品質 |

## 5. レスポンス仕様

### コマンドレスポンス

| 結果 | レスポンス | 例 |
|------|-----------|-----|
| 成功 | `"ok"` | コマンド正常実行 |
| 失敗 | `"error"` またはエラーメッセージ | `"error Not joystick"`, `"error Motor stop"` |
| 数値 | 数値文字列 | `"87"` (`battery?` の場合) |

### タイムアウト

| 状況 | タイムアウト |
|------|------------|
| 通常コマンドのレスポンス待ち | 7 秒 |
| `takeoff` のレスポンス待ち | 20 秒（離陸完了まで待機） |
| コマンドなしでの自動着陸 | 15 秒 |

### 通信ルール

| ルール | 説明 |
|--------|------|
| 逐次実行 | 前のコマンドのレスポンスを受信してから次を送信 |
| RC 例外 | `rc` コマンドは連続送信可能（最小間隔 ≈ 1ms） |
| 最小間隔 | 通常コマンド間は約 100ms |

## 6. Python SDK (djitellopy) API

### 基本的な使用例

```python
from djitellopy import Tello

tello = Tello()
tello.connect()              # SDK モード開始
tello.takeoff()              # 離陸

tello.move_up(100)           # 100cm 上昇
tello.move_forward(100)      # 100cm 前進
tello.rotate_clockwise(90)   # 時計回り 90 度
tello.land()                 # 着陸
tello.end()                  # 切断
```

### StampFly 互換 SDK の使用例（目標）

```python
from stampfly import StampFly   # djitellopy 互換 API

drone = StampFly()              # Tello() と同じインターフェース
drone.connect()                 # UDP 8889 で "command" 送信
drone.takeoff()                 # 離陸

drone.move_up(100)              # 100cm 上昇
drone.move_forward(100)         # 100cm 前進
drone.rotate_clockwise(90)      # 時計回り 90 度
drone.land()                    # 着陸
drone.end()                     # 切断
```

### djitellopy 主要メソッド — StampFly マッピング

#### 接続

| メソッド | SDK コマンド | StampFly 対応 |
|---------|-------------|--------------|
| `Tello(host='192.168.10.1')` | - | Phase 1（IP 変更） |
| `connect(wait_for_state=True)` | `command` | Phase 1 |
| `end()` | - | Phase 1 |

#### 飛行制御

| メソッド | SDK コマンド | StampFly 対応 |
|---------|-------------|--------------|
| `takeoff()` | `takeoff` | **実装済**（要 UDP 化） |
| `land()` | `land` | **実装済**（要 UDP 化） |
| `emergency()` | `emergency` | Phase 1 |
| `send_rc_control(lr, fb, ud, yaw)` | `rc a b c d` | Phase 4 |

#### 移動（距離: 20-500 cm）

| メソッド | SDK コマンド | StampFly 対応 |
|---------|-------------|--------------|
| `move_up(x)` | `up x` | Phase 2 |
| `move_down(x)` | `down x` | Phase 2 |
| `move_left(x)` | `left x` | Phase 2 |
| `move_right(x)` | `right x` | Phase 2 |
| `move_forward(x)` | `forward x` | Phase 2 |
| `move_back(x)` | `back x` | Phase 2 |

#### 回転

| メソッド | SDK コマンド | StampFly 対応 |
|---------|-------------|--------------|
| `rotate_clockwise(x)` | `cw x` | Phase 2 |
| `rotate_counter_clockwise(x)` | `ccw x` | Phase 2 |

#### 座標移動

| メソッド | SDK コマンド | StampFly 対応 |
|---------|-------------|--------------|
| `go_xyz_speed(x, y, z, speed)` | `go x y z speed` | Phase 2 |
| `curve_xyz_speed(...)` | `curve ...` | 未定 |

#### フリップ

| メソッド | SDK コマンド | StampFly 対応 |
|---------|-------------|--------------|
| `flip_left()` | `flip l` | 非対応 |
| `flip_right()` | `flip r` | 非対応 |
| `flip_forward()` | `flip f` | 非対応 |
| `flip_back()` | `flip b` | 非対応 |

#### ステート取得（テレメトリから取得）

| メソッド | Tello フィールド | StampFly 対応 |
|---------|-----------------|--------------|
| `get_battery()` | `bat` | Phase 3 |
| `get_height()` | `h` | Phase 3（`pos_z` から変換） |
| `get_distance_tof()` | `tof` | Phase 3（`tof_bottom` から変換） |
| `get_barometer()` | `baro` | Phase 3（`baro_altitude` から変換） |
| `get_pitch()` | `pitch` | Phase 3（クォータニオンから変換） |
| `get_roll()` | `roll` | Phase 3（クォータニオンから変換） |
| `get_yaw()` | `yaw` | Phase 3（クォータニオンから変換） |
| `get_speed_x()` | `vgx` | Phase 3（`vel_x` から変換） |
| `get_speed_y()` | `vgy` | Phase 3（`vel_y` から変換） |
| `get_speed_z()` | `vgz` | Phase 3（`vel_z` から変換） |
| `get_acceleration_x()` | `agx` | Phase 3（`accel_x` から変換） |
| `get_acceleration_y()` | `agy` | Phase 3（`accel_y` から変換） |
| `get_acceleration_z()` | `agz` | Phase 3（`accel_z` から変換） |
| `get_flight_time()` | `time` | Phase 3 |
| `get_temperature()` | `(templ+temph)/2` | 未定 |

#### クエリ（コマンド問い合わせ）

| メソッド | SDK コマンド | StampFly 対応 |
|---------|-------------|--------------|
| `query_battery()` | `battery?` | Phase 3 |
| `query_speed()` | `speed?` | Phase 3 |
| `query_height()` | `height?` | Phase 3 |
| `query_attitude()` | `attitude?` | Phase 3 |
| `query_barometer()` | `baro?` | Phase 3 |
| `query_distance_tof()` | `tof?` | Phase 3 |
| `query_sdk_version()` | `sdk?` | Phase 3 |
| `query_serial_number()` | `sn?` | Phase 3 |
| `query_flight_time()` | `time?` | Phase 3 |
| `query_wifi_signal_noise_ratio()` | `wifi?` | 未定 |

#### ビデオ

| メソッド | StampFly 対応 |
|---------|--------------|
| `streamon()` | 非対応（カメラなし） |
| `streamoff()` | 非対応（カメラなし） |
| `get_frame_read()` | 非対応（カメラなし） |

#### ミッションパッド

| メソッド | StampFly 対応 |
|---------|--------------|
| `enable_mission_pads()` | 非対応 |
| `disable_mission_pads()` | 非対応 |
| `get_mission_pad_id()` | 非対応 |

## 7. 移植戦略（ロードマップ）

### Phase 1: UDP コマンドインターフェース

**目標:** djitellopy の `connect()` / `takeoff()` / `land()` が動作する最小実装

| タスク | 実装箇所 | 説明 |
|--------|---------|------|
| UDP 8889 リスナー追加 | ファームウェア新コンポーネント | テキストコマンドを受信しパースする UDP サーバー |
| `command` コマンド | UDP ハンドラ | SDK モード開始。`ok` レスポンスを返す |
| `takeoff` コマンド | 既存 `FlightCommandService` に委譲 | 離陸完了後に `ok` を返す |
| `land` コマンド | 既存 `FlightCommandService` に委譲 | 着陸完了後に `ok` を返す |
| `emergency` コマンド | 全モーター即時停止 | 即座に `ok` を返す |
| `stop` コマンド | `hover` で代用 | ホバリング後 `ok` を返す |
| `ok` / `error` レスポンス | UDP 送信 | コマンド送信元にレスポンスを返送 |
| WiFi AP の IP 変更 | `192.168.4.1` → `192.168.10.1` | Tello 互換 IP（設定で切替可能に） |
| 15秒タイムアウト | SDK モード中の安全機構 | コマンド途絶時の自動着陸 |

**既存実装との関係:**

```
[djitellopy]                    [StampFly ファームウェア]
    │                                   │
    │  UDP "takeoff"                    │
    │  ────────────────────────────>    │
    │                           ┌──────┴──────┐
    │                           │ UDP 8889    │
    │                           │ リスナー     │
    │                           │ (新規実装)   │
    │                           └──────┬──────┘
    │                                  │
    │                           ┌──────┴──────┐
    │                           │ FlightCmd   │
    │                           │ Service     │
    │                           │ (既存)       │
    │                           └──────┬──────┘
    │                                  │
    │  UDP "ok"                        │
    │  <────────────────────────────   │
```

### Phase 2: 移動コマンド

**目標:** 距離指定移動と回転が動作する

**前提:** POSITION_HOLD モード（位置制御）の実装が必要。現状の StampFly はスロットル直接制御のみ。

| タスク | 説明 |
|--------|------|
| POSITION_HOLD モード実装 | オプティカルフロー + ToF による位置制御ループ |
| `up x` / `down x` | 高度目標値を ±x cm 変更、目標到達で `ok` |
| `left x` / `right x` | 左右目標位置を ±x cm 変更、目標到達で `ok` |
| `forward x` / `back x` | 前後目標位置を ±x cm 変更、目標到達で `ok` |
| `cw x` / `ccw x` | ヨー角目標を ±x 度変更、目標到達で `ok` |
| `go x y z speed` | 3D 座標移動、速度指定 |
| `speed x` | 移動速度のデフォルト値設定 |

### Phase 3: テレメトリ互換

**目標:** Tello フォーマットのテレメトリを UDP 8890 で送信

| タスク | 説明 |
|--------|------|
| UDP 8890 テレメトリ送信タスク | 10Hz でクライアントにテレメトリを送信 |
| テレメトリフォーマット変換 | StampFly バイナリ → Tello テキスト形式 |
| クォータニオン → オイラー角変換 | pitch/roll/yaw を度単位で出力 |
| 単位変換 | m → cm, m/s → dm/s 等 |
| バッテリー残量計算 | 電圧 → % 換算ロジック |
| 読み取りコマンド実装 | `battery?`, `height?`, `tof?` 等 |

**テレメトリ出力テンプレート:**

```c
snprintf(buf, sizeof(buf),
    "pitch:%d;roll:%d;yaw:%d;"
    "vgx:%d;vgy:%d;vgz:%d;"
    "templ:%d;temph:%d;"
    "tof:%d;h:%d;bat:%d;"
    "baro:%.2f;time:%d;"
    "agx:%.2f;agy:%.2f;agz:%.2f;\r\n",
    pitch_deg, roll_deg, yaw_deg,
    vgx_dms, vgy_dms, vgz_dms,
    temp_low, temp_high,
    tof_cm, height_cm, battery_pct,
    baro_cm, flight_time_s,
    agx_cmss, agy_cmss, agz_cmss);
```

### Phase 4: RC 制御

**目標:** リアルタイムスティック入力による飛行制御

| タスク | 説明 |
|--------|------|
| `rc a b c d` パーサー | -100~100 の 4 値を受信 |
| RC → ControlArbiter 変換 | -100~100 → -1.0~1.0 に正規化して ControlArbiter に送信 |
| 入力レート制限 | 最低 50ms 間隔（20Hz）で制御ループに反映 |
| フェイルセーフ | RC 入力が 1 秒以上途絶した場合のホバリング復帰 |

### Phase 5: Python SDK 互換ライブラリ

**目標:** `from stampfly import StampFly` で djitellopy 互換 API を提供

| タスク | 説明 |
|--------|------|
| `StampFly` クラス作成 | djitellopy の `Tello` と同じメソッドシグネチャ |
| UDP 通信レイヤー | djitellopy と同じ UDP ソケット通信 |
| テレメトリパーサー | Tello テキスト形式をパース |
| StampFly 拡張 API | Tello にない StampFly 固有機能（400Hz テレメトリ、WebSocket 等） |
| djitellopy 互換テスト | djitellopy のサンプルコードがそのまま動作することを検証 |
| PyPI パッケージ化 | `pip install stampfly` でインストール可能に |

### ロードマップタイムライン

```
Phase 1 ─── UDP コマンド基盤 ──────── connect/takeoff/land が動く
  │
Phase 2 ─── 移動コマンド ──────────── up/down/left/right/forward/back/cw/ccw
  │
Phase 3 ─── テレメトリ互換 ────────── get_battery()/get_height() 等が動く
  │
Phase 4 ─── RC 制御 ──────────────── send_rc_control() が動く
  │
Phase 5 ─── Python SDK ──────────── from stampfly import StampFly
```

## 8. 参考資料

| リソース | 説明 |
|---------|------|
| [Tello SDK 2.0 User Guide](https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf) | SDK 2.0 公式仕様書 |
| [Tello SDK 3.0 User Guide](https://dl.djicdn.com/downloads/RoboMaster+TT/Tello_SDK_3.0_User_Guide_en.pdf) | SDK 3.0 公式仕様書 |
| [djitellopy GitHub](https://github.com/damiafuentes/DJITelloPy) | Python SDK ソースコード |
| [djitellopy API Reference](https://djitellopy.readthedocs.io/en/latest/tello/) | Python SDK ドキュメント |

---

<a id="english"></a>

# Tello SDK API Reference — StampFly Compatibility Layer Design

## 1. Overview

### About This Document

The DJI Tello SDK is the de facto standard for educational drones, with Python SDKs like djitellopy widely used in educational settings worldwide. This document comprehensively documents the Tello SDK specifications and identifies the gaps for porting to StampFly.

### Tello SDK Versions

| Version | Target Device | Key Additions |
|---------|--------------|---------------|
| SDK 1.3 | Tello (standard) | Basic flight, movement, rotation, flip, video |
| SDK 2.0 | Tello EDU | `stop`, Mission Pads, `sdk?`/`sn?`/`wifi?`, `ap` |
| SDK 3.0 | Tello EDU (v02.05.01.17+) / RoboMaster TT | `motoron`/`motoroff`, `throwfly`, video settings, port config |

### Scope

The StampFly compatibility layer targets **SDK 2.0** as the baseline. SDK 2.0 is the most widely used version and the default target of djitellopy. SDK 3.0-specific commands (`motoron`, etc.) will be considered in Phase 5+.

## 2. Communication Architecture

### Tello Communication Setup

```
PC / Smartphone  <-- WiFi -->  Tello (192.168.10.1)
      |                               |
      |  UDP 8889 (Command TX/RX)      |
      |  ─────────────────────────>    |
      |  <─────────────────────────    |
      |                               |
      |  UDP 8890 (Telemetry RX)       |
      |  <─────────────────────────    |
      |                               |
      |  UDP 11111 (H.264 Video RX)    |
      |  <─────────────────────────    |
```

### StampFly Communication Setup (Current)

```
PC / Smartphone  <-- WiFi -->  StampFly (192.168.4.1)
      |                               |
      |  TCP 23 (Telnet CLI)           |
      |  ─────────────────────────>    |
      |  <─────────────────────────    |
      |                               |
      |  WebSocket 80 (Binary Telem)   |
      |  <─────────────────────────    |
```

### Protocol Comparison

| Item | Tello | StampFly (Current) | Compatibility Layer (Planned) |
|------|-------|-------------------|-------------------------------|
| Commands | UDP 8889 (text) | TCP 23 (Telnet CLI) | UDP 8889 (text) |
| Telemetry | UDP 8890 (text, 10Hz) | WebSocket 80 (binary, 400Hz) | UDP 8890 (text, 10Hz) |
| Video | UDP 11111 (H.264) | None | Not supported |
| Drone IP | 192.168.10.1 | 192.168.4.1 | 192.168.10.1 (configurable) |
| Init | Send `command` for SDK mode | Telnet connection | Send `command` for SDK mode |
| Auto-land | 15s timeout without commands | None | 15s timeout |

## 3. Command List (Tello → StampFly Mapping)

### Category Summary

| Category | Commands | StampFly Status |
|----------|----------|-----------------|
| Init (`command`) | 1 | Not impl → Phase 1 |
| Basic flight (`takeoff`/`land`/`emergency`/`stop`) | 4 | Partial (`takeoff`/`land` done) |
| Movement (`up`/`down`/`left`/`right`/`forward`/`back`) | 6 | Not impl → Phase 2 |
| Rotation (`cw`/`ccw`) | 2 | Not impl → Phase 2 |
| Complex (`go`/`curve`) | 2 | Not impl → Phase 2 |
| RC control (`rc`) | 1 | Not impl → Phase 4 |
| Flip (`flip`) | 1 | Not supported (HW limitation) |
| Read (`battery?`/`speed?` etc.) | 12 | Not impl → Phase 3 |
| Set (`speed`/`wifi`/`ap`) | 3 | Not impl → Phase 3 |
| Video (`streamon`/`streamoff`) | 2 | Not supported (no camera) |
| Mission Pads (`mon`/`moff` etc.) | 6 | Not supported |
| Motor (SDK 3.0) | 2 | Not impl → Phase 5 |

### Control Commands

| Command | Syntax | Description | Response | StampFly |
|---------|--------|-------------|----------|----------|
| `command` | `command` | Enter SDK mode | `ok` / `error` | **Phase 1** |
| `takeoff` | `takeoff` | Auto takeoff | `ok` / `error` | **Done** ※ |
| `land` | `land` | Auto land | `ok` / `error` | **Done** ※ |
| `emergency` | `emergency` | Kill all motors | `ok` / `error` | **Phase 1** |
| `stop` | `stop` | Hover in place | `ok` / `error` | **Phase 1** |

※ Current StampFly `takeoff`/`land` uses TCP CLI. Tello compatibility requires UDP 8889 text command interface.

### Movement Commands

| Command | Syntax | Range | Unit | StampFly |
|---------|--------|-------|------|----------|
| `up` | `up x` | x: 20-500 | cm | **Phase 2** |
| `down` | `down x` | x: 20-500 | cm | **Phase 2** |
| `left` | `left x` | x: 20-500 | cm | **Phase 2** |
| `right` | `right x` | x: 20-500 | cm | **Phase 2** |
| `forward` | `forward x` | x: 20-500 | cm | **Phase 2** |
| `back` | `back x` | x: 20-500 | cm | **Phase 2** |

### Rotation Commands

| Command | Syntax | Range | Unit | StampFly |
|---------|--------|-------|------|----------|
| `cw` | `cw x` | x: 1-360 | degrees | **Phase 2** |
| `ccw` | `ccw x` | x: 1-360 | degrees | **Phase 2** |

### Complex Movement

| Command | Syntax | Parameters | StampFly |
|---------|--------|-----------|----------|
| `go` | `go x y z speed` | xyz: -500~500 cm, speed: 10-100 cm/s | **Phase 2** |
| `curve` | `curve x1 y1 z1 x2 y2 z2 speed` | xyz: -500~500 cm, speed: 10-60 cm/s | TBD |

### RC Control

| Command | Syntax | Parameters | Description | StampFly |
|---------|--------|-----------|-------------|----------|
| `rc` | `rc a b c d` | each: -100~100 | a=LR, b=FB, c=UD, d=yaw | **Phase 4** |

### Flip

| Command | Syntax | StampFly |
|---------|--------|----------|
| `flip` | `flip l/r/f/b` | **Not supported** (thrust-to-weight ratio limitation) |

### Read Commands

| Command | Syntax | Response | Unit | StampFly |
|---------|--------|----------|------|----------|
| `speed?` | `speed?` | `"10"` | cm/s | **Phase 3** |
| `battery?` | `battery?` | `"87"` | % | **Phase 3** |
| `time?` | `time?` | `"15"` | sec | **Phase 3** |
| `height?` | `height?` | `"50"` | cm | **Phase 3** |
| `attitude?` | `attitude?` | `"pitch:0;roll:0;yaw:0;"` | degrees | **Phase 3** |
| `baro?` | `baro?` | `"170.07"` | cm | **Phase 3** |
| `tof?` | `tof?` | `"10"` | cm | **Phase 3** |
| `sdk?` | `sdk?` | `"20"` | - | **Phase 3** |
| `sn?` | `sn?` | `"0TQDF6GEBMB5HF"` | - | **Phase 3** |

## 4. Telemetry Specification

### Tello Telemetry Format

Tello sends semicolon-separated text data at ~10Hz via UDP 8890:

```
pitch:0;roll:0;yaw:0;vgx:0;vgy:0;vgz:0;templ:62;temph:65;tof:10;h:0;bat:87;baro:170.07;time:0;agx:-13.00;agy:-5.00;agz:-998.00;\r\n
```

### Tello Telemetry Fields

| Field | Type | Unit | Description |
|-------|------|------|-------------|
| `pitch` | int | degrees | Pitch angle |
| `roll` | int | degrees | Roll angle |
| `yaw` | int | degrees | Yaw angle |
| `vgx` | int | dm/s | X velocity |
| `vgy` | int | dm/s | Y velocity |
| `vgz` | int | dm/s | Z velocity |
| `templ` | int | °C | Lowest temperature |
| `temph` | int | °C | Highest temperature |
| `tof` | int | cm | ToF sensor distance |
| `h` | int | cm | Height (relative) |
| `bat` | int | % | Battery percentage |
| `baro` | float | cm | Barometric altitude |
| `time` | int | sec | Motor run time |
| `agx` | float | cm/s² | X acceleration |
| `agy` | float | cm/s² | Y acceleration |
| `agz` | float | cm/s² | Z acceleration (≈ -998 at rest) |

### StampFly Telemetry Mapping

| Tello Field | StampFly Field | Conversion |
|-------------|---------------|------------|
| `pitch` | `quat_w/x/y/z` → Euler | Quaternion to pitch angle |
| `roll` | `quat_w/x/y/z` → Euler | Quaternion to roll angle |
| `yaw` | `quat_w/x/y/z` → Euler | Quaternion to yaw angle |
| `vgx` | `vel_x` | m/s → dm/s |
| `vgy` | `vel_y` | m/s → dm/s |
| `vgz` | `vel_z` | m/s → dm/s (NED→Tello frame) |
| `tof` | `tof_bottom` | m → cm |
| `h` | `pos_z` | NED Z (down-positive) → cm (negate) |
| `bat` | N/A | Voltage → % conversion (to be impl) |
| `baro` | `baro_altitude` | m → cm |
| `agx/y/z` | `accel_x/y/z` | m/s² → cm/s² |

## 5. Response Specification

### Command Responses

| Result | Response | Example |
|--------|----------|---------|
| Success | `"ok"` | Command executed |
| Failure | `"error"` or message | `"error Not joystick"` |
| Numeric | Numeric string | `"87"` (for `battery?`) |

### Timeouts

| Situation | Timeout |
|-----------|---------|
| Normal command response | 7 seconds |
| `takeoff` response | 20 seconds |
| Auto-land (no commands) | 15 seconds |

## 6. Python SDK (djitellopy) API

### Basic Usage

```python
from djitellopy import Tello

tello = Tello()
tello.connect()
tello.takeoff()
tello.move_up(100)
tello.move_forward(100)
tello.rotate_clockwise(90)
tello.land()
tello.end()
```

### StampFly Compatible SDK (Goal)

```python
from stampfly import StampFly

drone = StampFly()       # Same interface as Tello()
drone.connect()
drone.takeoff()
drone.move_up(100)
drone.land()
drone.end()
```

See the Japanese section above for the complete method mapping table.

## 7. Migration Roadmap

### Phase 1: UDP Command Interface

Minimum implementation for `connect()` / `takeoff()` / `land()` to work with djitellopy.

| Task | Description |
|------|-------------|
| UDP 8889 listener | Text command UDP server in firmware |
| `command` handler | Enter SDK mode, return `ok` |
| `takeoff` / `land` | Delegate to existing `FlightCommandService` |
| `emergency` | Immediate motor kill |
| `ok` / `error` response | UDP response to command sender |
| IP change | `192.168.4.1` → `192.168.10.1` (configurable) |
| 15s timeout | Auto-land safety on command loss |

### Phase 2: Movement Commands

Requires POSITION_HOLD mode (position control with optical flow + ToF).

| Task | Description |
|------|-------------|
| POSITION_HOLD mode | Position control loop |
| `up`/`down`/`left`/`right`/`forward`/`back` | Distance-based movement |
| `cw`/`ccw` | Yaw rotation |
| `go x y z speed` | 3D coordinate movement |

### Phase 3: Telemetry Compatibility

| Task | Description |
|------|-------------|
| UDP 8890 telemetry | Text format at 10Hz |
| Format conversion | StampFly binary → Tello text |
| Quaternion → Euler | Attitude conversion |
| Unit conversion | m → cm, m/s → dm/s |
| Read commands | `battery?`, `height?`, `tof?`, etc. |

### Phase 4: RC Control

| Task | Description |
|------|-------------|
| `rc a b c d` parser | Parse 4 values (-100~100) |
| RC → ControlArbiter | Normalize and send to control loop |
| Failsafe | Hover on RC input loss (>1s) |

### Phase 5: Python SDK

| Task | Description |
|------|-------------|
| `StampFly` class | djitellopy-compatible API |
| StampFly extensions | 400Hz telemetry, WebSocket access |
| PyPI package | `pip install stampfly` |

## 8. References

| Resource | Description |
|---------|-------------|
| [Tello SDK 2.0 User Guide](https://dl-cdn.ryzerobotics.com/downloads/Tello/Tello%20SDK%202.0%20User%20Guide.pdf) | Official SDK 2.0 spec |
| [Tello SDK 3.0 User Guide](https://dl.djicdn.com/downloads/RoboMaster+TT/Tello_SDK_3.0_User_Guide_en.pdf) | Official SDK 3.0 spec |
| [djitellopy GitHub](https://github.com/damiafuentes/DJITelloPy) | Python SDK source |
| [djitellopy API Reference](https://djitellopy.readthedocs.io/en/latest/tello/) | Python SDK docs |
