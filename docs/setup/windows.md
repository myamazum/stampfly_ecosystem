# Windows セットアップ

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

WindowsでのStampFly開発環境セットアップ手順です。ESP-IDF公式のWindows Installerを使ったネイティブセットアップを推奨します。

## 2. 推奨構成

| 方法 | 推奨度 | 説明 |
|------|--------|------|
| ネイティブ Windows | ★★★ | ESP-IDF公式インストーラで簡単セットアップ |
| WSL2 + Ubuntu | ★★☆ | Linux環境に慣れている場合の代替 |

## 3. ネイティブWindowsセットアップ（推奨）

### ESP-IDF Windows Installerを使用

1. https://dl.espressif.com/dl/esp-idf/ からインストーラをダウンロード
2. ESP-IDF v5.5.2を選択してインストール
3. ESP-IDF Command Promptを使用

### シリアルポートドライバ

CH9102F（M5Stack製品）用ドライバ:
- https://www.wch.cn/downloads/CH343SER_EXE.html

### 動作確認

ESP-IDF Command Promptを開いて実行:

```cmd
# プロジェクトディレクトリに移動
cd C:\path\to\stampfly_ecosystem

# 環境診断
sf doctor

# ビルド
sf build vehicle
```

### 注意事項

- sf CLIの一部機能はWindows未対応の場合があります（随時対応中）
- シミュレータ（Genesis）はLinux環境が必要です

## 4. WSL2セットアップ（代替）

Linux環境に慣れている場合やシミュレータを使用する場合はWSL2も利用できます。

### WSL2のインストール

PowerShell（管理者）で実行:

```powershell
wsl --install -d Ubuntu-22.04
```

再起動後、Ubuntuを起動してユーザー設定を完了します。

### Ubuntu内でのセットアップ

WSL2 Ubuntuターミナルで、[Linuxガイド](linux.md)の手順に従ってください。

### USBデバイスの接続（WSL2）

WSL2でUSBデバイスを使用するには、usbipd-winが必要です:

1. Windows側でusbipd-winをインストール:
   - https://github.com/dorssel/usbipd-win/releases からダウンロード

2. PowerShell（管理者）でデバイスを接続:

```powershell
# デバイス一覧を表示
usbipd list

# デバイスをWSL2に接続（BUSIDは上記で確認）
usbipd bind --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

3. WSL2側で確認:

```bash
ls /dev/ttyUSB*
```

## 5. トラブルシューティング

### USBデバイスがWSL2で認識されない

```powershell
# Windows側で再度接続
usbipd detach --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

### WSL2のパフォーマンスが遅い

WSL2のLinuxファイルシステム内（`/home/user/`）で作業することを推奨します。`/mnt/c/`はパフォーマンスが低下します。

---

<a id="english"></a>

## 1. Overview

Setup instructions for StampFly development environment on Windows. Native Windows setup using the official ESP-IDF installer is recommended.

## 2. Recommended Configuration

| Method | Rating | Description |
|--------|--------|-------------|
| Native Windows | ★★★ | Easy setup with official ESP-IDF installer |
| WSL2 + Ubuntu | ★★☆ | Alternative for those familiar with Linux |

## 3. Native Windows Setup (Recommended)

### Using ESP-IDF Windows Installer

1. Download installer from https://dl.espressif.com/dl/esp-idf/
2. Select ESP-IDF v5.5.2 and install
3. Use ESP-IDF Command Prompt

### Serial Port Driver

CH9102F (M5Stack products) driver:
- https://www.wch.cn/downloads/CH343SER_EXE.html

### Verify Installation

Open ESP-IDF Command Prompt and run:

```cmd
# Navigate to project
cd C:\path\to\stampfly_ecosystem

# Run diagnostics
sf doctor

# Build
sf build vehicle
```

### Notes

- Some sf CLI features may not yet support Windows (being addressed)
- Simulator (Genesis) requires a Linux environment

## 4. WSL2 Setup (Alternative)

WSL2 is available as an alternative for those familiar with Linux or who need the simulator.

### Install WSL2

Run in PowerShell (Administrator):

```powershell
wsl --install -d Ubuntu-22.04
```

After restart, launch Ubuntu and complete user setup.

### Setup in Ubuntu

In WSL2 Ubuntu terminal, follow the [Linux guide](linux.md).

### USB Device Connection (WSL2)

To use USB devices in WSL2, you need usbipd-win:

1. Install usbipd-win on Windows:
   - Download from https://github.com/dorssel/usbipd-win/releases

2. Connect device in PowerShell (Administrator):

```powershell
# List devices
usbipd list

# Connect to WSL2 (use BUSID from above)
usbipd bind --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

3. Verify in WSL2:

```bash
ls /dev/ttyUSB*
```

## 5. Troubleshooting

### USB Device Not Recognized in WSL2

```powershell
# Reconnect on Windows side
usbipd detach --busid <BUSID>
usbipd attach --wsl --busid <BUSID>
```

### Slow WSL2 Performance

Working within the WSL2 Linux filesystem (`/home/user/`) is recommended. `/mnt/c/` has slower performance.
