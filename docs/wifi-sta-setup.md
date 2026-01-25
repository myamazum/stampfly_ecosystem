# WiFi STA Mode Setup Guide

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このドキュメントについて

StampFly VehicleのWiFi STAモード機能のセットアップと使用方法を説明します。

### 対象読者

- StampFlyドローンの開発者
- ROS2連携やインターネット接続を必要とする研究者
- 複数環境（研究室、自宅）で開発を行うユーザー

### WiFi STAモードとは

WiFi STAモードは、StampFlyがWiFiルーター（アクセスポイント）に接続するモードです。これにより、以下が可能になります：

| 機能 | 説明 |
|------|------|
| **ROS2連携** | 外部PCのROS2ノードと通信（STA IP経由） |
| **インターネットアクセス** | OTA更新、クラウドロギング、NTP時刻同期 |
| **複数環境対応** | 研究室と自宅など、複数のWiFi環境を保存 |
| **群制御準備** | 複数ドローンを同じルーターに接続（将来） |
| **APモード併用** | デバッグ用APモード（192.168.4.1）も維持 |

### 重要な仕様

| 項目 | 仕様 |
|------|------|
| WiFiモード | APSTA（AP + STA 同時動作） |
| 保存可能AP数 | 最大5個 |
| 優先順位 | 保存順（最初に追加したAPが最優先） |
| 自動接続 | デフォルトON（起動時に自動接続） |
| フェイルオーバー | 接続失敗時、次のAPに自動切り替え |
| チャンネル制約 | STAとAPは同じチャンネル（STA優先） |

## 2. 初回セットアップ

### 2.1 ファームウェアの書き込み

WiFi STA機能を含むファームウェアを書き込みます：

```bash
# ESP-IDF環境をアクティブ化
source ~/esp/esp-idf/export.sh

# ビルドと書き込み
sf build vehicle
sf flash vehicle -m
```

### 2.2 シリアルCLIへの接続

USB経由でシリアルコンソールに接続：

```bash
sf monitor
```

または、ファームウェア書き込み直後なら `-m` オプションで自動的にモニタが起動します。

### 2.3 WiFi STA設定の追加

#### 単一APの追加（最も一般的）

```bash
# 研究室のWiFiを追加
wifi sta add "Lab-WiFi" "your-lab-password"
```

#### 複数APの追加（研究室と自宅）

```bash
# 優先順位1: 研究室
wifi sta add "Lab-WiFi" "lab-password"

# 優先順位2: 自宅
wifi sta add "Home-WiFi" "home-password"
```

**注意:**
- SSIDにスペースが含まれる場合は引用符で囲む
- パスワードは平文でNVSに保存される（セキュリティ考慮が必要な場合はNVS暗号化を有効化）
- 追加順が優先順位（最初に追加したAPから接続試行）

### 2.4 AP一覧の確認

```bash
wifi sta list
```

出力例:
```
Saved APs (priority order):
  [0] Lab-WiFi
  [1] Home-WiFi
```

### 2.5 手動接続テスト

```bash
# 優先順位順に自動接続
wifi sta connect

# または、特定のインデックスを指定
wifi sta connect 0
```

接続成功時のログ:
```
I (12345) controller_comm: Connecting to SSID 'Lab-WiFi' (priority 1/2)...
I (15678) controller_comm: STA got IP: 192.168.1.123 (connected to 'Lab-WiFi')
```

### 2.6 接続状態の確認

```bash
wifi status
```

出力例:
```
WiFi Configuration:
  Mode: AP+STA
  Channel: 6
  AP SSID: StampFly
  AP IP: 192.168.4.1
  STA Status: Connected
  STA IP: 192.168.1.123
  Connected to: Lab-WiFi
  Saved APs: 2
```

### 2.7 自動接続の有効化

起動時に自動的にWiFiルーターに接続するよう設定：

```bash
wifi sta auto on
```

これで、次回の起動時から自動的にWiFiに接続されます。

## 3. CLIコマンドリファレンス

### wifi sta list

保存されたAP一覧を優先順位順に表示します。

```bash
wifi sta list
```

**出力例:**
```
Saved APs (priority order):
  [0] Lab-WiFi (connected)
  [1] Home-WiFi
  [2] Cafe-WiFi
```

### wifi sta add <ssid> <password>

新しいAP設定を追加します（最大5個）。

```bash
wifi sta add "Office-WiFi" "office123"
```

**パラメータ:**
- `ssid`: WiFiのSSID（スペース含む場合は引用符で囲む）
- `password`: WiFiパスワード

**エラー:**
- `AP list full (max 5)`: すでに5個のAP登録済み
- `AP already exists`: 同じSSIDが既に登録済み

**注意:**
- 設定は自動的にNVSに保存される
- 再起動後も保持される

### wifi sta remove <index>

指定インデックスのAP設定を削除します。

```bash
# インデックス1（2番目のAP）を削除
wifi sta remove 1
```

**パラメータ:**
- `index`: 削除するAPのインデックス（0から始まる）

**注意:**
- 削除後、後続のAPが詰められる（index 2がindex 1になる）
- 現在接続中のAPを削除すると自動的に切断される
- 設定は自動的にNVSに保存される

### wifi sta connect [index]

WiFiルーターに接続します。

```bash
# 優先順位順に自動接続
wifi sta connect

# インデックス0のAPに接続
wifi sta connect 0
```

**パラメータ:**
- `index`: (オプション) 接続するAPのインデックス。省略時は優先順位順に試行

**動作:**
- インデックス指定なし: 保存順に接続を試行、最初に成功したAPに接続
- インデックス指定あり: 指定APへの接続を試行

### wifi sta disconnect

現在のWiFiルーターから切断します。

```bash
wifi sta disconnect
```

**注意:**
- 自動接続が有効な場合、切断後に自動的に再接続される
- 一時的な切断が必要な場合は `wifi sta auto off` を先に実行

### wifi sta auto [on|off]

起動時の自動接続を設定します。

```bash
# 現在の設定を確認
wifi sta auto

# 自動接続を有効化
wifi sta auto on

# 自動接続を無効化
wifi sta auto off
```

**パラメータ:**
- `on`: 起動時に自動接続を有効化
- `off`: 起動時に自動接続を無効化
- (省略): 現在の設定を表示

**デフォルト:** ON（有効）

**用途:**
- フィールドでの飛行時は `off` にして起動を高速化
- 開発時は `on` にして自動的にルーターに接続

### wifi status

WiFi全体の状態を表示します（AP + STA）。

```bash
wifi status
```

**出力例:**
```
WiFi Configuration:
  Mode: AP+STA
  Channel: 6
  AP SSID: StampFly
  AP IP: 192.168.4.1
  STA Status: Connected
  STA IP: 192.168.1.123
  Connected to: Lab-WiFi
  Saved APs: 2
```

## 4. 運用シナリオ

### シナリオA: 研究室と自宅を行き来する開発者

**初回設定:**
```bash
wifi sta add "Lab-WiFi" "lab-password"
wifi sta add "Home-WiFi" "home-password"
wifi sta auto on
```

**運用:**
- 研究室で起動: 自動的にLab-WiFiに接続
- 自宅で起動: Lab-WiFiが不在のため、自動的にHome-WiFiに接続
- 両環境でROS2開発が可能
- APモード（192.168.4.1）も併用可能

### シナリオB: フィールドでの飛行（STA不要）

**設定:**
```bash
wifi sta auto off
reboot
```

**運用:**
- STA接続試行なし、起動高速化
- APモード専用（ESP-NOW通信用）
- ログ記録のみ

### シナリオC: ROS2開発

**設定:**
```bash
wifi sta add "Lab-WiFi" "lab-password"
wifi sta auto on
reboot
```

**PC側（ROS2ノード）:**
```bash
# StampFlyのSTA IPを確認（例: 192.168.1.123）
ping 192.168.1.123

# ROS2ブリッジ経由で制御
ros2 topic echo /stampfly/telemetry
ros2 topic pub /stampfly/control ...
```

### シナリオD: APとSTAの併用

**同時アクセス:**
- PC-A: StampFly APに接続（192.168.4.1）→ デバッグ用
- PC-B: 同じルーターに接続（192.168.1.123）→ ROS2連携

**用途:**
- デバッグ用のローカルアクセス（WebSocket, Telnet）
- 本番用の外部PC連携（ROS2, UDP）

## 5. トラブルシューティング

### 接続できない

**症状:** `wifi sta connect` しても接続できない

**確認事項:**
1. SSIDが正しいか確認
   ```bash
   wifi sta list
   ```

2. パスワードが正しいか確認
   - 削除して再追加:
   ```bash
   wifi sta remove 0
   wifi sta add "Lab-WiFi" "correct-password"
   ```

3. ルーターが稼働しているか確認
   - ルーターの電源、WiFi機能を確認

4. ログでエラー原因を確認
   ```
   E (xxxxx) controller_comm: STA disconnected from 'Lab-WiFi' (reason:15)
   ```
   - reason:15 = AUTH_FAIL（パスワード誤り）
   - reason:201 = NO_AP_FOUND（SSIDが見つからない）

### 接続が不安定

**症状:** 接続と切断を繰り返す

**対策:**
1. WiFiチャンネルの混雑を確認
   - ルーター側でチャンネルを変更

2. 電波強度を確認
   - ルーターに近づける

3. 他のデバイスとの干渉を確認
   - ESP-NOWコントローラーとの干渉（同じチャンネル）

### チャンネルが変わってしまう

**症状:** WiFiチャンネルが意図しない値に変わる

**原因:** ESP32のAPSTA制約により、STAが接続したAPのチャンネルにAPも追従します。

**対策:**
- これは仕様です（STAが優先）
- ESP-NOWペアリング時は、ルーターのチャンネルに合わせてコントローラー側も調整

**ログ例:**
```
W (xxxxx) controller_comm: Channel changed: 1 -> 6 (AP follows STA)
```

### 自動接続が動作しない

**症状:** 起動時にWiFiに接続しない

**確認事項:**
1. 自動接続が有効か確認
   ```bash
   wifi sta auto
   ```

2. AP設定が保存されているか確認
   ```bash
   wifi sta list
   ```

3. NVS消去後は再設定が必要
   ```bash
   wifi sta add "Lab-WiFi" "password"
   wifi sta auto on
   ```

### シリアルCLIが応答しない

**症状:** WiFi接続中にシリアルCLIが固まる

**対策:**
1. リセットボタンを押す
2. USBケーブルを抜き差し
3. シリアルモニタを再接続
   ```bash
   sf monitor
   ```

**原因調査:**
- 起動ログで "Guru Meditation Error" を確認
- WiFi接続タイムアウト中の場合は30秒待つ

## 6. Telnet CLI接続

WiFi STA経由でTelnet CLIに接続できます。

### 接続方法

**APモード経由（StampFlyのAPに直接接続）:**
```bash
telnet 192.168.4.1 23
```

**STAモード経由（同じWiFiルーターに接続）:**
```bash
# StampFlyのSTA IPを確認（例: 192.168.1.123）
telnet 192.168.1.123 23
```

**ポート番号省略:**
```bash
# 23番はTelnetデフォルトなので省略可能
telnet 192.168.4.1
telnet 192.168.1.123
```

### macOS/Linuxの場合

```bash
telnet 192.168.4.1
```

### Windowsの場合

Telnetクライアントを有効化：
1. コントロールパネル → プログラム → Windowsの機能
2. 「Telnetクライアント」にチェック

または、PuTTYを使用：
- Host: 192.168.4.1
- Port: 23
- Connection type: Telnet

### 切断方法

**macOS/Linux:**
```
Ctrl + ]
telnet> quit
```

**Windows:**
```
Ctrl + ]
Microsoft Telnet> quit
```

## 7. 次のステップ

WiFi STA機能のセットアップが完了したら、以下に進んでください：

### ROS2統合

STA IP経由でROS2ブリッジと通信：
- [ROS2_INTEGRATION_PLAN.md](plans/ROS2_INTEGRATION_PLAN.md) を参照

### 群制御準備

複数ドローンを同じルーターに接続：
- [WIFI_COMM_PLAN.md](plans/WIFI_COMM_PLAN.md) の将来構想を参照

### セキュリティ強化

NVS Flash Encryptionを有効化してパスワードを保護：
- ESP-IDF公式ドキュメントを参照

---

<a id="english"></a>

## 1. Overview

### About This Document

This guide explains how to set up and use the WiFi STA mode feature on StampFly Vehicle.

### Target Audience

- StampFly drone developers
- Researchers requiring ROS2 integration or internet connectivity
- Users developing across multiple environments (lab, home)

### What is WiFi STA Mode?

WiFi STA mode allows StampFly to connect to a WiFi router (access point). This enables:

| Feature | Description |
|---------|-------------|
| **ROS2 Integration** | Communicate with ROS2 nodes on external PC (via STA IP) |
| **Internet Access** | OTA updates, cloud logging, NTP time sync |
| **Multi-Environment Support** | Save multiple WiFi configs (lab, home, etc.) |
| **Swarm Control Preparation** | Connect multiple drones to same router (future) |
| **AP Mode Coexistence** | Debug AP mode (192.168.4.1) maintained |

### Key Specifications

| Item | Specification |
|------|---------------|
| WiFi Mode | APSTA (AP + STA simultaneous) |
| Max Saved APs | 5 |
| Priority | Save order (first added = highest priority) |
| Auto-Connect | Default ON (auto-connect on boot) |
| Failover | Auto-switch to next AP on connection failure |
| Channel Constraint | STA and AP share channel (STA priority) |

## 2. Initial Setup

### 2.1 Flash Firmware

Flash firmware with WiFi STA feature:

```bash
# Activate ESP-IDF environment
source ~/esp/esp-idf/export.sh

# Build and flash
sf build vehicle
sf flash vehicle -m
```

### 2.2 Connect to Serial CLI

Connect via USB:

```bash
sf monitor
```

Or, use `-m` flag during flash for automatic monitor.

### 2.3 Add WiFi STA Configuration

#### Add Single AP (Most Common)

```bash
# Add lab WiFi
wifi sta add "Lab-WiFi" "your-lab-password"
```

#### Add Multiple APs (Lab and Home)

```bash
# Priority 1: Lab
wifi sta add "Lab-WiFi" "lab-password"

# Priority 2: Home
wifi sta add "Home-WiFi" "home-password"
```

**Notes:**
- Use quotes for SSIDs with spaces
- Passwords stored in plaintext in NVS (enable NVS encryption for security)
- Add order = priority order (first added = highest priority)

### 2.4 Verify AP List

```bash
wifi sta list
```

Example output:
```
Saved APs (priority order):
  [0] Lab-WiFi
  [1] Home-WiFi
```

### 2.5 Manual Connection Test

```bash
# Auto-connect in priority order
wifi sta connect

# Or, connect to specific index
wifi sta connect 0
```

Connection success log:
```
I (12345) controller_comm: Connecting to SSID 'Lab-WiFi' (priority 1/2)...
I (15678) controller_comm: STA got IP: 192.168.1.123 (connected to 'Lab-WiFi')
```

### 2.6 Check Connection Status

```bash
wifi status
```

Example output:
```
WiFi Configuration:
  Mode: AP+STA
  Channel: 6
  AP SSID: StampFly
  AP IP: 192.168.4.1
  STA Status: Connected
  STA IP: 192.168.1.123
  Connected to: Lab-WiFi
  Saved APs: 2
```

### 2.7 Enable Auto-Connect

Configure auto-connect on boot:

```bash
wifi sta auto on
```

Now WiFi will connect automatically on next boot.

## 3. CLI Command Reference

See Japanese section for detailed command descriptions:
- `wifi sta list` - List saved APs
- `wifi sta add <ssid> <password>` - Add AP config
- `wifi sta remove <index>` - Remove AP config
- `wifi sta connect [index]` - Connect to AP
- `wifi sta disconnect` - Disconnect from AP
- `wifi sta auto [on|off]` - Configure auto-connect
- `wifi status` - Show WiFi status (AP + STA)

## 4. Operational Scenarios

### Scenario A: Developer Between Lab and Home

**Initial Setup:**
```bash
wifi sta add "Lab-WiFi" "lab-password"
wifi sta add "Home-WiFi" "home-password"
wifi sta auto on
```

**Operation:**
- Boot at lab: Auto-connect to Lab-WiFi
- Boot at home: Auto-connect to Home-WiFi (Lab-WiFi unavailable)
- ROS2 development in both environments
- AP mode (192.168.4.1) also available

### Scenario B: Field Flight (STA Not Needed)

**Configuration:**
```bash
wifi sta auto off
reboot
```

**Operation:**
- No STA connection attempts, faster boot
- AP mode only (for ESP-NOW)
- Logging only

### Scenario C: ROS2 Development

**Configuration:**
```bash
wifi sta add "Lab-WiFi" "lab-password"
wifi sta auto on
reboot
```

**PC Side (ROS2 Node):**
```bash
# Check StampFly STA IP (e.g., 192.168.1.123)
ping 192.168.1.123

# Control via ROS2 bridge
ros2 topic echo /stampfly/telemetry
ros2 topic pub /stampfly/control ...
```

## 5. Troubleshooting

See Japanese section for detailed troubleshooting:
- Cannot connect
- Unstable connection
- Channel changes unexpectedly
- Auto-connect not working
- Serial CLI not responding

## 6. Telnet CLI Connection

Connect to Telnet CLI via WiFi STA:

**Via AP Mode:**
```bash
telnet 192.168.4.1 23
```

**Via STA Mode:**
```bash
# Check StampFly STA IP (e.g., 192.168.1.123)
telnet 192.168.1.123 23
```

Port 23 is default for Telnet and can be omitted:
```bash
telnet 192.168.4.1
telnet 192.168.1.123
```

## 7. Next Steps

After completing WiFi STA setup:

### ROS2 Integration

Communicate with ROS2 bridge via STA IP:
- See [ROS2_INTEGRATION_PLAN.md](plans/ROS2_INTEGRATION_PLAN.md)

### Swarm Control Preparation

Connect multiple drones to same router:
- See [WIFI_COMM_PLAN.md](plans/WIFI_COMM_PLAN.md) future plans

### Security Enhancement

Enable NVS Flash Encryption to protect passwords:
- See ESP-IDF official documentation
