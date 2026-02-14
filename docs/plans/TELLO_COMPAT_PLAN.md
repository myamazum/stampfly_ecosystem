# Tello 互換レイヤー実装プラン
# Tello Compatibility Layer Implementation Plan

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 実装ステータス

| Phase | ステータス | 説明 |
|-------|----------|------|
| Phase 0: 仕様調査・ドキュメント | ✅ 完了 | Tello SDK 仕様整理、StampFly マッピング |
| Phase 1: ファームウェア移動コマンド | 🔜 未着手 | `up`/`down`/`left`/`right`/`forward`/`back`/`cw`/`ccw` |
| Phase 2: sf CLI 拡張 | 🔜 未着手 | sf コマンドに Tello 互換コマンドを追加 |
| Phase 3: テレメトリ・読み取り | 🔜 未着手 | `battery?`/`height?` 等のクエリ対応 |
| Phase 4: RC 制御 | 🔜 未着手 | `rc a b c d` リアルタイム制御 |
| Phase 5: Python SDK | 🔜 未着手 | djitellopy 互換 `StampFly` クラス |
| Phase 6: UDP 互換（任意） | 💤 保留 | djitellopy 直接利用が必要な場合のみ |

## 1. 背景と目的

### 目的

StampFly を Tello の代替として教育現場で使えるようにする。既存の Tello 教材やコードの概念をそのまま活用し、導入障壁を下げる。

### 設計方針（改訂）

当初は Tello の UDP プロトコルをファームウェアに実装する計画だったが、以下の理由で方針を変更する。

| 当初の方針 | 改訂後の方針 | 理由 |
|-----------|------------|------|
| UDP 8889 コマンドサーバー追加 | 既存 TCP CLI を活用 | ファームウェア変更を最小化 |
| UDP 8890 テレメトリ送信追加 | 既存 WebSocket を活用 | 400Hz バイナリ > 10Hz テキスト |
| IP を 192.168.10.1 に変更 | 192.168.4.1 を維持 | 既存ワークフロー維持 |
| djitellopy をそのまま使う | StampFly Python SDK を作成 | StampFly の優位性を活かす |
| プロトコル互換を優先 | API 互換を優先 | 教育的にはメソッド名が同じなら十分 |

### アーキテクチャ

```
教育用 Python スクリプト
  │  from stampfly import StampFly
  │  drone = StampFly()
  │  drone.takeoff()
  │  drone.move_up(100)
  │
  ├─── StampFly Python SDK (lib/stampfly/)
  │      djitellopy 互換メソッド名
  │      │
  │      └─── VehicleConnection (lib/sfcli/utils/)
  │             ├─ VehicleCLI       TCP 23 (コマンド送受信)
  │             └─ VehicleTelemetry  WebSocket 80 (テレメトリ)
  │
  ├─── sf CLI (lib/sfcli/)
  │      sf takeoff / sf up 100 / sf battery
  │      │
  │      └─── VehicleConnection (同上、共有)
  │
  └─── StampFly ファームウェア
         WiFi CLI サーバー (TCP 23)
         WebSocket テレメトリ (WS 80)
         FlightCommandService (コマンド実行)
```

**ポイント:**
- Python SDK と sf CLI は `VehicleConnection` を共有（サブプロセス呼び出しではない）
- ファームウェアの通信プロトコルは変更しない
- ファームウェア側の変更は移動コマンドのハンドラ追加のみ

## 2. Phase 1: ファームウェア移動コマンド

### 前提条件

- POSITION_HOLD モード（位置制御）の実装が必要
- オプティカルフロー (PMW3901) + ToF による水平位置推定
- 現状は高度制御（スロットル直接制御）のみ

### 実装タスク

| タスク | ファイル | 説明 |
|--------|---------|------|
| `up x` / `down x` ハンドラ | `cmd_flight.cpp` | 高度目標を ±x cm 変更、到達まで待機 |
| `left x` / `right x` ハンドラ | `cmd_flight.cpp` | 水平位置目標を ±x cm 変更 |
| `forward x` / `back x` ハンドラ | `cmd_flight.cpp` | 前後位置目標を ±x cm 変更 |
| `cw x` / `ccw x` ハンドラ | `cmd_flight.cpp` | ヨー角目標を ±x 度変更 |
| `go x y z speed` ハンドラ | `cmd_flight.cpp` | 3D 座標移動 |
| `emergency` ハンドラ | `cmd_flight.cpp` | 全モーター即時停止 |
| 位置制御ループ | `flight_command.cpp` | `updateMoveCommand()` 追加 |
| `FlightCommandType` 拡張 | `flight_command.hpp` | `MOVE_UP`, `MOVE_DOWN`, `MOVE_LEFT` 等追加 |

### パラメータ範囲

| パラメータ | Tello 範囲 | StampFly 範囲（暫定） | 備考 |
|-----------|-----------|---------------------|------|
| 移動距離 | 20-500 cm | 20-200 cm | 機体サイズ・推力の制約 |
| 移動速度 | 10-100 cm/s | 10-50 cm/s | 最大速度 ≈ 2 m/s |
| 回転角度 | 1-360 度 | 1-360 度 | 同等 |
| go 座標 | -500~500 cm | -200~200 cm | 飛行可能範囲の制約 |

### 依存関係

```
位置制御ループ (POSITION_HOLD)
  ├─ オプティカルフロー位置推定 (PMW3901)
  ├─ ToF 高度推定 (VL53L3CX)
  └─ ESKF 状態推定（既存）
```

**注意:** 位置制御の精度はオプティカルフローの品質に依存する。床面のテクスチャが少ない環境では誤差が大きくなる。

## 3. Phase 2: sf CLI 拡張

### 新規 sf コマンド

| コマンド | 構文 | 説明 | 対応する Tello コマンド |
|---------|------|------|----------------------|
| `sf up` | `sf up <cm>` | 指定距離上昇 | `up x` |
| `sf down` | `sf down <cm>` | 指定距離下降 | `down x` |
| `sf left` | `sf left <cm>` | 指定距離左移動 | `left x` |
| `sf right` | `sf right <cm>` | 指定距離右移動 | `right x` |
| `sf forward` | `sf forward <cm>` | 指定距離前進 | `forward x` |
| `sf back` | `sf back <cm>` | 指定距離後退 | `back x` |
| `sf cw` | `sf cw <deg>` | 時計回り回転 | `cw x` |
| `sf ccw` | `sf ccw <deg>` | 反時計回り回転 | `ccw x` |
| `sf go` | `sf go <x> <y> <z> <speed>` | 3D 座標移動 | `go x y z speed` |
| `sf emergency` | `sf emergency` | 緊急停止 | `emergency` |
| `sf stop` | `sf stop` | ホバリング | `stop` |
| `sf battery` | `sf battery` | バッテリー残量表示 | `battery?` |
| `sf height` | `sf height` | 高度表示 | `height?` |

### 実装方針

- `lib/sfcli/commands/flight.py` に追加（既存の takeoff/land/hover/jump と同じパターン）
- `VehicleConnection` を使用して TCP CLI にコマンド送信
- テレメトリ監視で移動完了を検出

## 4. Phase 3: テレメトリ・読み取りコマンド

### ファームウェア側

| タスク | 説明 |
|--------|------|
| `battery` CLI コマンド | INA3221 から電圧読み取り → % 換算して返答 |
| `height` CLI コマンド | ToF/ESKF から高度を cm で返答 |
| `attitude` CLI コマンド | クォータニオン → pitch/roll/yaw 度で返答 |
| `speed` CLI コマンド | 設定された移動速度を返答 |
| `tof` CLI コマンド | ToF 生値を cm で返答 |
| `baro` CLI コマンド | 気圧高度を cm で返答 |
| `acceleration` CLI コマンド | 加速度を cm/s² で返答 |

### sf CLI 側

| コマンド | 構文 | 説明 |
|---------|------|------|
| `sf sensor battery` | `sf sensor battery` | バッテリー % 表示 |
| `sf sensor height` | `sf sensor height` | 高度 cm 表示 |
| `sf sensor attitude` | `sf sensor attitude` | 姿勢角表示 |
| `sf sensor tof` | `sf sensor tof` | ToF 距離表示 |

## 5. Phase 4: RC 制御

### ファームウェア側

| タスク | 説明 |
|--------|------|
| `rc a b c d` CLI コマンド | 4 値を受信して ControlArbiter に送信 |
| 入力正規化 | -100~100 → -1.0~1.0 |
| タイムアウト | 1 秒以上入力がなければホバリング復帰 |

### sf CLI / Python SDK 側

| タスク | 説明 |
|--------|------|
| `sf rc` コマンド | インタラクティブ RC モード（キーボード入力） |
| `send_rc_control()` API | TCP 接続を維持して高速送信（≥20Hz） |

## 6. Phase 5: Python SDK

### パッケージ構成

```
lib/stampfly/
  ├─ __init__.py          # from stampfly import StampFly
  ├─ stampfly.py          # StampFly クラス（djitellopy 互換 API）
  └─ exceptions.py        # エラー定義
```

### StampFly クラス設計

```python
from stampfly import StampFly

drone = StampFly(host='192.168.4.1')  # デフォルト IP は StampFly のまま

# --- djitellopy 互換メソッド ---
drone.connect()                       # TCP CLI + WebSocket 接続
drone.takeoff()                       # 離陸
drone.land()                          # 着陸
drone.emergency()                     # 緊急停止

drone.move_up(100)                    # 100cm 上昇
drone.move_down(50)                   # 50cm 下降
drone.move_forward(100)               # 100cm 前進
drone.move_back(50)                   # 50cm 後退
drone.move_left(30)                   # 30cm 左
drone.move_right(30)                  # 30cm 右

drone.rotate_clockwise(90)            # 時計回り 90 度
drone.rotate_counter_clockwise(45)    # 反時計回り 45 度

drone.send_rc_control(0, 50, 0, 0)    # RC 制御

drone.get_battery()                   # バッテリー %
drone.get_height()                    # 高度 cm
drone.get_distance_tof()              # ToF cm

drone.end()                           # 切断

# --- StampFly 拡張 API（Tello にないもの） ---
drone.get_telemetry_raw()             # 400Hz バイナリテレメトリ直接アクセス
drone.get_optical_flow()              # オプティカルフロー生値
drone.get_imu_raw()                   # 400Hz IMU データ
drone.hover(altitude=0.5, duration=5) # 指定高度でホバリング
drone.jump(altitude=0.15)             # ジャンプ
```

### 内部実装

```python
class StampFly:
    def __init__(self, host='192.168.4.1'):
        self._conn = VehicleConnection()  # lib/sfcli/utils/ を再利用
        self._host = host

    def connect(self):
        asyncio.run(self._conn.connect(self._host))

    def takeoff(self):
        resp = asyncio.run(self._conn.send_flight_command('takeoff'))
        # 完了まで監視
        ...

    def move_up(self, x: int):
        # x: cm (20-200)
        resp = asyncio.run(self._conn.send_flight_command(f'up {x}'))
        ...

    def get_battery(self) -> int:
        resp = asyncio.run(self._conn.cli.send_command('battery'))
        return int(resp.strip())
```

## 7. Phase 6: UDP 互換（任意）

**このフェーズは djitellopy をそのまま使いたいという具体的な要望が出た場合のみ実装する。**

| タスク | 説明 |
|--------|------|
| UDP 8889 リスナー | ファームウェアに UDP コマンドサーバー追加 |
| UDP 8890 テレメトリ | 10Hz テキスト形式の互換テレメトリ送信 |
| IP 切替設定 | 192.168.4.1 / 192.168.10.1 を設定で切替 |
| djitellopy 動作検証 | `from djitellopy import Tello` がそのまま動くことを確認 |

## 8. ハードウェア制約による非対応機能

以下は StampFly のハード構成上、実装不可能な Tello SDK 機能。

| 機能 | コマンド | 理由 |
|------|---------|------|
| ビデオストリーム | `streamon`/`streamoff`/`setfps`/`setresolution`/`setbitrate` | カメラ非搭載 |
| カメラ切替 | `downvision` | カメラ非搭載 |
| フリップ | `flip l/r/f/b` | 推力重量比不足（≈1.7:1、要 >2:1） |
| ミッションパッド | `mon`/`moff`/`mdirection`/`go...mid`/`curve...mid`/`jump...mid` | ダウンワードカメラなし |
| スロー・トゥ・フライ | `throwfly` | 軽量すぎて投げ検出困難（35g） |
| モーター温度 | `templ`/`temph` テレメトリ | モーター温度センサーなし |

**合計 47 コマンド中 16 コマンド（34%）がハード制約で不可。**

## 9. 実装優先順位

```
Phase 0 ✅ 仕様調査・ドキュメント
  │
Phase 1 ── ファームウェア移動コマンド ──── 位置制御が全ての基盤
  │         up/down/left/right/forward/back/cw/ccw
  │         ※ POSITION_HOLD モード実装が最大のタスク
  │
Phase 2 ── sf CLI 拡張 ──────────────── sf up 100 / sf cw 90 が動く
  │
Phase 3 ── テレメトリ・読み取り ────────── sf battery / sf height が動く
  │
Phase 4 ── RC 制御 ──────────────────── sf rc でリアルタイム操縦
  │
Phase 5 ── Python SDK ──────────────── from stampfly import StampFly
  │
Phase 6 ── UDP 互換（任意）──────────── djitellopy 直接利用（必要な場合のみ）
```

## 10. 参考資料

| リソース | 説明 |
|---------|------|
| `docs/tello_api_reference.md` | Tello SDK 全コマンド仕様 + StampFly マッピング |
| `lib/sfcli/commands/flight.py` | 既存 sf フライトコマンド実装 |
| `lib/sfcli/utils/vehicle_connection.py` | TCP CLI + WebSocket 接続クラス |
| `firmware/vehicle/components/sf_svc_flight_command/` | フライトコマンドサービス |
| `firmware/vehicle/components/sf_svc_console/commands/cmd_flight.cpp` | CLI ハンドラ |

---

<a id="english"></a>

# Tello Compatibility Layer Implementation Plan

## Implementation Status

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 0: Research & Documentation | ✅ Done | Tello SDK spec documentation, StampFly mapping |
| Phase 1: Firmware Movement Commands | 🔜 Not started | `up`/`down`/`left`/`right`/`forward`/`back`/`cw`/`ccw` |
| Phase 2: sf CLI Extension | 🔜 Not started | Add Tello-compatible commands to sf CLI |
| Phase 3: Telemetry & Read Commands | 🔜 Not started | `battery?`/`height?` query support |
| Phase 4: RC Control | 🔜 Not started | `rc a b c d` real-time control |
| Phase 5: Python SDK | 🔜 Not started | djitellopy-compatible `StampFly` class |
| Phase 6: UDP Compatibility (Optional) | 💤 Deferred | Only if direct djitellopy usage is required |

## 1. Background and Purpose

### Design Philosophy (Revised)

The original plan was to implement Tello's UDP protocol in firmware. This has been revised:

| Original Approach | Revised Approach | Reason |
|-------------------|-----------------|--------|
| Add UDP 8889 command server | Use existing TCP CLI | Minimize firmware changes |
| Add UDP 8890 telemetry | Use existing WebSocket | 400Hz binary > 10Hz text |
| Change IP to 192.168.10.1 | Keep 192.168.4.1 | Preserve existing workflows |
| Use djitellopy directly | Create StampFly Python SDK | Leverage StampFly advantages |
| Protocol compatibility first | API compatibility first | Same method names suffice for education |

### Architecture

```
Educational Python Scripts
  │  from stampfly import StampFly
  │
  ├─── StampFly Python SDK (lib/stampfly/)
  │      djitellopy-compatible method names
  │      │
  │      └─── VehicleConnection (lib/sfcli/utils/)
  │             ├─ VehicleCLI       TCP 23 (commands)
  │             └─ VehicleTelemetry  WebSocket 80 (telemetry)
  │
  ├─── sf CLI (lib/sfcli/)
  │      sf takeoff / sf up 100 / sf battery
  │      │
  │      └─── VehicleConnection (shared)
  │
  └─── StampFly Firmware (minimal changes)
         WiFi CLI Server (TCP 23)
         WebSocket Telemetry (WS 80)
         FlightCommandService (command execution)
```

**Key Points:**
- Python SDK and sf CLI share `VehicleConnection` (no subprocess calls)
- No firmware protocol changes required
- Firmware changes limited to adding movement command handlers

## 2. Phase Summary

### Phase 1: Firmware Movement Commands

Add position-hold flight commands to firmware. Requires POSITION_HOLD mode using optical flow + ToF.

### Phase 2: sf CLI Extension

Add `sf up`/`sf down`/`sf forward`/`sf back`/`sf left`/`sf right`/`sf cw`/`sf ccw` commands.

### Phase 3: Telemetry & Read Commands

Add `battery`/`height`/`attitude`/`tof` CLI commands to firmware and corresponding sf commands.

### Phase 4: RC Control

Add `rc a b c d` command for real-time stick input control.

### Phase 5: Python SDK

Create `StampFly` class with djitellopy-compatible API, internally using `VehicleConnection`.

### Phase 6: UDP Compatibility (Optional)

Only implement if there's a concrete need for direct djitellopy wire-level compatibility.

## 3. Hardware Limitations

16 out of 47 Tello SDK commands (34%) cannot be implemented due to hardware constraints:
- No camera (7 video commands)
- Insufficient thrust-to-weight ratio for flips (1 command)
- No downward camera for Mission Pads (6 commands)
- Too light for throw-to-fly (1 command)
- No motor temperature sensor (1 telemetry field)

## 4. References

| Resource | Description |
|---------|-------------|
| `docs/tello_api_reference.md` | Full Tello SDK command specs + StampFly mapping |
| `lib/sfcli/commands/flight.py` | Existing sf flight command implementation |
| `lib/sfcli/utils/vehicle_connection.py` | TCP CLI + WebSocket connection class |
