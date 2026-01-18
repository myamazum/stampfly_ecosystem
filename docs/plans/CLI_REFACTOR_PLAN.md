# CLI Refactor Plan - ESP-IDF Console + linenoise 統合

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### 目的

Serial CLI と WiFi CLI を統合し、以下を実現する：

1. **共通コマンド基盤**: ESP-IDF Console によるコマンド登録・実行
2. **高機能行編集**: linenoise による履歴・補完・カーソル移動
3. **マルチ入出力**: Serial/WiFi 両方から同じコマンドを実行可能

### ステータス

| 項目 | 状態 |
|------|------|
| 計画策定 | ✅ 完了 |
| Phase 1: esp_console 統合 | ✅ 完了 |
| Phase 2: linenoise 統合 | ✅ 完了 |
| Phase 3: WiFi CLI 統合 | ✅ 完了 |
| Phase 4: 旧CLI削除 | ⏳ 未着手 |

### 現状の問題

```
┌─────────────────────────────────────────────────────────────────┐
│                        現状: 分離したCLI                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────┐      ┌─────────────────────┐          │
│  │    Serial CLI       │      │     WiFi CLI        │          │
│  │    (cli.cpp)        │      │   (wifi_cli.cpp)    │          │
│  ├─────────────────────┤      ├─────────────────────┤          │
│  │ - 独自コマンド登録   │      │ - 独自コマンド処理   │          │
│  │ - 独自入力処理       │      │ - 独自入力処理       │          │
│  │ - printf出力        │      │ - send()出力        │          │
│  │ - 25+コマンド        │      │ - 3コマンドのみ      │          │
│  │ - 履歴なし          │      │ - 履歴なし          │          │
│  └─────────────────────┘      └─────────────────────┘          │
│                                                                 │
│  問題点:                                                        │
│  - コマンド実装の重複                                            │
│  - WiFi CLIでSerialのコマンドが使えない                          │
│  - 行編集機能が貧弱（履歴・補完なし）                             │
│  - 新コマンド追加時に複数箇所を修正                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 2. 目標アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                   目標: 統合CLIアーキテクチャ                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ┌─────────────────────┐                      │
│                    │   esp_console       │                      │
│                    │  (コマンド基盤)      │                      │
│                    ├─────────────────────┤                      │
│                    │ - コマンド登録       │                      │
│                    │ - 引数パース         │                      │
│                    │ - ヘルプ生成         │                      │
│                    │ - esp_console_run() │                      │
│                    └──────────┬──────────┘                      │
│                               │                                 │
│              ┌────────────────┼────────────────┐                │
│              │                │                │                │
│              ▼                ▼                ▼                │
│  ┌───────────────────┐ ┌───────────────┐ ┌───────────────┐     │
│  │   Serial REPL     │ │  WiFi REPL    │ │ (将来)        │     │
│  │   + linenoise     │ │  + LineEditor │ │ WebSocket等   │     │
│  ├───────────────────┤ ├───────────────┤ ├───────────────┤     │
│  │ - stdin/stdout    │ │ - TCP Socket  │ │ - ...         │     │
│  │ - 履歴 ↑↓        │ │ - 履歴 ↑↓    │ │               │     │
│  │ - Tab補完         │ │ - Tab補完     │ │               │     │
│  │ - カーソル移動    │ │ - カーソル移動 │ │               │     │
│  └───────────────────┘ └───────────────┘ └───────────────┘     │
│                                                                 │
│  メリット:                                                       │
│  - コマンド定義は1箇所                                           │
│  - Serial/WiFi両方で全コマンド利用可能                           │
│  - 高機能行編集（履歴、補完、カーソル）                           │
│  - 新しいI/Oバックエンドを簡単に追加可能                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3. ESP-IDF Console 概要

### esp_console コンポーネント

ESP-IDFに標準搭載されているCLIフレームワーク：

```cpp
#include "esp_console.h"

// コマンド登録
esp_console_cmd_t cmd = {
    .command = "status",
    .help = "Show system status",
    .hint = NULL,
    .func = &cmd_status,
    .argtable = NULL  // または argtable3 による引数定義
};
esp_console_cmd_register(&cmd);

// コマンド実行
esp_console_run("status", &ret);
```

### linenoise

BSD/MITライセンスの軽量 readline 代替：

```cpp
#include "linenoise/linenoise.h"

// 履歴設定
linenoiseHistorySetMaxLen(20);

// 補完設定
linenoiseSetCompletionCallback(&completion_callback);

// 行入力（履歴・補完・カーソル移動対応）
char* line = linenoise("stampfly> ");
if (line) {
    linenoiseHistoryAdd(line);
    esp_console_run(line, &ret);
    linenoiseFree(line);
}
```

### linenoise の機能

| 機能 | キー | 動作 |
|------|------|------|
| 履歴（前） | ↑ / Ctrl+P | 前のコマンド |
| 履歴（次） | ↓ / Ctrl+N | 次のコマンド |
| カーソル左 | ← / Ctrl+B | 1文字左 |
| カーソル右 | → / Ctrl+F | 1文字右 |
| 行頭 | Home / Ctrl+A | 行の先頭へ |
| 行末 | End / Ctrl+E | 行の末尾へ |
| 削除（前） | Backspace | 前の文字削除 |
| 削除（後） | Delete / Ctrl+D | 次の文字削除 |
| 単語削除 | Ctrl+W | 前の単語削除 |
| 行削除 | Ctrl+U | 行全体削除 |
| 補完 | Tab | コマンド補完 |

## 4. 実装フェーズ

### Phase 1: esp_console によるコマンド基盤

**目標**: 既存コマンドを esp_console に移行

```
firmware/vehicle/components/sf_svc_console/
├── CMakeLists.txt
├── include/
│   └── console.hpp
├── console.cpp              # esp_console 初期化・管理
└── commands/
    ├── cmd_system.cpp       # help, status, reboot
    ├── cmd_sensor.cpp       # sensor, teleplot, log
    ├── cmd_motor.cpp        # motor
    ├── cmd_control.cpp      # trim, pid
    ├── cmd_comm.cpp         # comm, pair
    └── cmd_calib.cpp        # magcal
```

**console.hpp:**

```cpp
#pragma once

#include "esp_console.h"
#include "esp_err.h"

namespace stampfly {

class Console {
public:
    static Console& getInstance();

    // 初期化
    esp_err_t init();

    // 全コマンド登録
    void registerAllCommands();

    // コマンド実行（任意のソースから呼び出し可能）
    int run(const char* cmdline);

    // 出力リダイレクト用コールバック
    using OutputFunc = void (*)(const char* str, void* ctx);
    void setOutput(OutputFunc func, void* ctx);

    // printf互換出力（リダイレクト対応）
    void print(const char* fmt, ...);

private:
    Console() = default;
    OutputFunc output_func_ = nullptr;
    void* output_ctx_ = nullptr;
};

}  // namespace stampfly
```

**コマンド移行例（cmd_system.cpp）:**

```cpp
#include "console.hpp"
#include "esp_console.h"
#include "argtable3/argtable3.h"

// status コマンド
static int cmd_status(int argc, char** argv)
{
    auto& console = stampfly::Console::getInstance();
    auto& state = stampfly::StampFlyState::getInstance();

    console.print("=== StampFly Status ===\r\n");
    console.print("Flight State: %s\r\n",
                  flightStateToString(state.getFlightState()));
    console.print("Battery: %.2fV\r\n", state.getBatteryVoltage());
    // ...

    return 0;
}

// コマンド登録
void register_system_commands()
{
    // status
    esp_console_cmd_t status_cmd = {
        .command = "status",
        .help = "Show system status",
        .hint = NULL,
        .func = &cmd_status,
    };
    esp_console_cmd_register(&status_cmd);

    // help (esp_console built-in)
    esp_console_register_help_command();

    // reboot
    esp_console_cmd_t reboot_cmd = {
        .command = "reboot",
        .help = "Reboot the system",
        .hint = NULL,
        .func = &cmd_reboot,
    };
    esp_console_cmd_register(&reboot_cmd);
}
```

### Phase 2: Serial REPL + linenoise

**目標**: Serial CLI に linenoise を統合

```
firmware/vehicle/components/sf_svc_serial_repl/
├── CMakeLists.txt
├── include/
│   └── serial_repl.hpp
└── serial_repl.cpp
```

**serial_repl.cpp:**

```cpp
#include "serial_repl.hpp"
#include "console.hpp"
#include "linenoise/linenoise.h"
#include "esp_vfs_dev.h"
#include "driver/usb_serial_jtag.h"

namespace stampfly {

esp_err_t SerialREPL::init()
{
    // USB Serial 設定
    usb_serial_jtag_driver_config_t config = {
        .tx_buffer_size = 256,
        .rx_buffer_size = 256,
    };
    usb_serial_jtag_driver_install(&config);

    // VFS経由でstdin/stdoutをUSB Serialに接続
    esp_vfs_usb_serial_jtag_use_driver();

    // linenoise 設定
    linenoiseSetMultiLine(1);
    linenoiseHistorySetMaxLen(20);
    linenoiseSetCompletionCallback(&completionCallback);
    linenoiseSetHintsCallback(&hintsCallback);

    return ESP_OK;
}

void SerialREPL::run()
{
    auto& console = Console::getInstance();

    // 出力を stdout にリダイレクト
    console.setOutput([](const char* str, void*) {
        printf("%s", str);
        fflush(stdout);
    }, nullptr);

    printf("\r\n=== StampFly CLI ===\r\n");
    printf("Type 'help' for available commands.\r\n\r\n");

    while (true) {
        char* line = linenoise("stampfly> ");

        if (line == nullptr) {
            // EOF or error
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }

        if (strlen(line) > 0) {
            linenoiseHistoryAdd(line);
            int ret = console.run(line);
            if (ret != 0) {
                printf("Error: %d\r\n", ret);
            }
        }

        linenoiseFree(line);
    }
}

// Tab補完コールバック
void SerialREPL::completionCallback(const char* buf, linenoiseCompletions* lc)
{
    // esp_console から登録コマンドを取得して補完候補に追加
    // （実装詳細は省略）
}

}  // namespace stampfly
```

### Phase 3: WiFi REPL 統合

**目標**: WiFi CLI を共通コマンド基盤に接続

```
firmware/vehicle/components/sf_svc_wifi_repl/
├── CMakeLists.txt
├── include/
│   ├── wifi_repl.hpp
│   └── socket_line_editor.hpp  # ソケット用行編集
└── wifi_repl.cpp
```

**課題**: linenoise は stdin/stdout 前提。ソケットには直接使えない。

**解決策**: linenoise のロジックを参考にした SocketLineEditor を実装

```cpp
// socket_line_editor.hpp

class SocketLineEditor {
public:
    SocketLineEditor(int fd);

    // 1行入力を取得（ブロッキング）
    // エスケープシーケンス処理、履歴、補完対応
    char* getLine(const char* prompt);
    void freeLine(char* line);

    // 履歴
    void addHistory(const char* line);
    void setHistoryMaxLen(int len);

    // 補完
    using CompletionCallback = void (*)(const char*, Completions*);
    void setCompletionCallback(CompletionCallback cb);

private:
    int fd_;
    char buffer_[256];
    size_t pos_ = 0;
    size_t len_ = 0;

    // 履歴
    std::vector<std::string> history_;
    int history_index_ = -1;

    // エスケープシーケンス処理
    void processEscape();
    void handleArrowUp();
    void handleArrowDown();
    void handleArrowLeft();
    void handleArrowRight();

    // 画面更新
    void refreshLine();
    void write(const char* data, size_t len);
};
```

**wifi_repl.cpp:**

```cpp
#include "wifi_repl.hpp"
#include "console.hpp"
#include "socket_line_editor.hpp"

namespace stampfly {

void WiFiREPL::handleClient(int client_fd)
{
    auto& console = Console::getInstance();
    SocketLineEditor editor(client_fd);

    editor.setHistoryMaxLen(10);
    editor.setCompletionCallback(&completionCallback);

    // 出力をソケットにリダイレクト
    console.setOutput([](const char* str, void* ctx) {
        int fd = *static_cast<int*>(ctx);
        send(fd, str, strlen(str), 0);
    }, &client_fd);

    // ウェルカムメッセージ
    const char* welcome =
        "\r\n=== StampFly WiFi CLI ===\r\n"
        "Type 'help' for available commands.\r\n\r\n";
    send(client_fd, welcome, strlen(welcome), 0);

    while (true) {
        char* line = editor.getLine("stampfly> ");

        if (line == nullptr) {
            break;  // 切断
        }

        if (strlen(line) > 0) {
            editor.addHistory(line);

            // exit/quit は特別処理
            if (strcmp(line, "exit") == 0 || strcmp(line, "quit") == 0) {
                send(client_fd, "Goodbye.\r\n", 10, 0);
                editor.freeLine(line);
                break;
            }

            int ret = console.run(line);
            if (ret != 0) {
                char buf[32];
                snprintf(buf, sizeof(buf), "Error: %d\r\n", ret);
                send(client_fd, buf, strlen(buf), 0);
            }
        }

        editor.freeLine(line);
    }
}

}  // namespace stampfly
```

## 5. ディレクトリ構成（最終形）

```
firmware/vehicle/components/
├── sf_svc_console/          # 共通コマンド基盤（NEW）
│   ├── CMakeLists.txt
│   ├── include/
│   │   └── console.hpp
│   ├── console.cpp
│   └── commands/
│       ├── cmd_system.cpp
│       ├── cmd_sensor.cpp
│       ├── cmd_motor.cpp
│       ├── cmd_control.cpp
│       ├── cmd_comm.cpp
│       └── cmd_calib.cpp
│
├── sf_svc_serial_repl/      # Serial REPL + linenoise（NEW）
│   ├── CMakeLists.txt
│   ├── include/
│   │   └── serial_repl.hpp
│   └── serial_repl.cpp
│
├── sf_svc_wifi_repl/        # WiFi REPL（REFACTOR from sf_svc_wifi_cli）
│   ├── CMakeLists.txt
│   ├── include/
│   │   ├── wifi_repl.hpp
│   │   └── socket_line_editor.hpp
│   ├── wifi_repl.cpp
│   └── socket_line_editor.cpp
│
├── sf_svc_cli/              # DEPRECATED → 削除予定
└── sf_svc_wifi_cli/         # DEPRECATED → 削除予定
```

## 6. 実装スケジュール

### Phase 1: esp_console 統合

| Step | 内容 | ファイル |
|------|------|----------|
| 1.1 | sf_svc_console コンポーネント作成 | `console.hpp/cpp` |
| 1.2 | 出力リダイレクト機構実装 | `console.cpp` |
| 1.3 | 既存コマンドを esp_console 形式に移行 | `commands/*.cpp` |
| 1.4 | 動作確認（Serial経由） | - |

### Phase 2: Serial REPL + linenoise

| Step | 内容 | ファイル |
|------|------|----------|
| 2.1 | sf_svc_serial_repl コンポーネント作成 | `serial_repl.hpp/cpp` |
| 2.2 | linenoise 統合 | `serial_repl.cpp` |
| 2.3 | Tab補完実装 | `serial_repl.cpp` |
| 2.4 | 動作確認（履歴、補完、カーソル） | - |

### Phase 3: WiFi REPL 統合

| Step | 内容 | ファイル |
|------|------|----------|
| 3.1 | SocketLineEditor 実装 | `socket_line_editor.hpp/cpp` |
| 3.2 | sf_svc_wifi_repl 作成 | `wifi_repl.hpp/cpp` |
| 3.3 | 共通コマンド接続 | `wifi_repl.cpp` |
| 3.4 | 動作確認（Telnet経由で全コマンド） | - |

### Phase 4: クリーンアップ

| Step | 内容 |
|------|------|
| 4.1 | 旧 sf_svc_cli 削除 |
| 4.2 | 旧 sf_svc_wifi_cli 削除 |
| 4.3 | ドキュメント更新 |

## 7. 出力リダイレクトの詳細設計

### 問題

- コマンドは `printf()` で出力している
- WiFi CLI では `send()` で出力する必要がある
- 同時に複数クライアントがいる場合も考慮

### 解決策: Thread-Local Output Context

```cpp
// console.cpp

// スレッドローカルな出力コンテキスト
static __thread OutputFunc t_output_func = nullptr;
static __thread void* t_output_ctx = nullptr;

void Console::setOutput(OutputFunc func, void* ctx)
{
    t_output_func = func;
    t_output_ctx = ctx;
}

void Console::print(const char* fmt, ...)
{
    char buf[512];
    va_list args;
    va_start(args, fmt);
    vsnprintf(buf, sizeof(buf), fmt, args);
    va_end(args);

    if (t_output_func) {
        t_output_func(buf, t_output_ctx);
    } else {
        // デフォルト: stdout
        printf("%s", buf);
        fflush(stdout);
    }
}
```

### 使用パターン

```cpp
// Serial REPL
void serial_task(void* arg) {
    Console::getInstance().setOutput(serial_output, nullptr);
    // ... REPL loop
}

// WiFi REPL (各クライアント)
void client_task(void* arg) {
    int fd = ...;
    Console::getInstance().setOutput(socket_output, &fd);
    // ... REPL loop
}
```

## 8. メモリ・リソース見積もり

| コンポーネント | ROM増加 | RAM増加 |
|---------------|---------|---------|
| esp_console | ~8KB | ~1KB |
| linenoise | ~8KB | ~2KB (履歴含む) |
| SocketLineEditor | ~4KB | ~1KB/クライアント |
| **合計** | ~20KB | ~4KB + 1KB/WiFiクライアント |

現在の実装から削除されるもの：
- 旧cli.cpp のコマンド処理部分: -10KB (ROM)
- 旧wifi_cli.cpp の重複部分: -3KB (ROM)

**差し引き: ROM約+7KB、RAM約+2KB**

## 9. リスクと対策

| リスク | 対策 |
|--------|------|
| linenoise がブロッキング | Serial REPL は専用タスクで実行 |
| WiFi でエスケープシーケンス解析が複雑 | 段階的実装（まず基本機能、後で履歴追加） |
| 出力リダイレクト時の競合 | Thread-Local Storage 使用 |
| 移行中の機能退行 | Phase毎に動作確認、旧実装は最後まで残す |

## 10. 飛行制御への影響分析

### 結論

**CLI処理は飛行制御に影響しない。** 現在のタスク設計（コア分離 + 優先度分離）により安全性が確保されている。

### タスク優先度とコア配置

```
Core 1 (飛行制御専用)              Core 0 (その他)
───────────────────────            ───────────────────────
IMU Task      : 24 (最高)          Mag Task      : 18
Control Task  : 23                 Baro Task     : 16
OptFlow Task  : 20                 Comm Task     : 15
                                   ToF Task      : 14
                                   Telemetry Task: 13
                                   Power Task    : 12
                                   Button Task   : 10
                                   LED Task      : 8
                                   CLI Task      : 5 (最低)
                                   WiFi CLI      : 5 (予定)
```

### 安全性の根拠

#### 1. 物理的コア分離
- **飛行制御（IMU/Control/OptFlow）は Core 1 で動作**
- **CLI/WiFi CLI は Core 0 で動作**
- ESP32-S3 のデュアルコアにより物理的に独立
- Core 0 での処理がどれだけ重くても Core 1 には影響しない

#### 2. 優先度による保護
- CLI Task は優先度 5（システム内最低）
- Control Task は優先度 23（CLI の 4.6 倍）
- FreeRTOS のプリエンプティブスケジューリングにより、高優先度タスクは即座に実行される

#### 3. 処理フロー図

```
                    ┌─────────────────────────────────────┐
                    │           ESP32-S3                  │
                    ├──────────────────┬──────────────────┤
                    │      Core 1      │      Core 0      │
                    │   (Flight Ctrl)  │   (Auxiliary)    │
                    ├──────────────────┼──────────────────┤
                    │                  │                  │
                    │  IMU Task (24)   │  CLI Task (5)    │
                    │      ↓           │      ↓           │
                    │  400Hz 確実実行  │  低優先度で実行   │
                    │      ↓           │      ↓           │
                    │  Control Task    │  linenoise       │
                    │  (23)            │  ブロッキングI/O  │
                    │      ↓           │      ↓           │
                    │  Motor Output    │  コマンド実行    │
                    │                  │                  │
                    │  ← 相互に独立 →  │                  │
                    └──────────────────┴──────────────────┘
```

### linenoise 追加時の懸念と評価

| 懸念事項 | リスク評価 | 理由 |
|----------|-----------|------|
| ブロッキング I/O | **低** | CLI Task のみ影響、Core 1 は無関係 |
| malloc 使用 | **低** | ESP-IDF の heap_caps は高速、履歴サイズ制限で対応 |
| 文字列処理 | **低** | Core 0、最低優先度で実行 |
| 共有リソース競合 | **中** | NVS/センサ状態アクセス時にミューテックス使用（既存設計） |

### 追加の安全策（オプション）

飛行中の CLI 応答を制限することで、さらに安全性を高めることが可能：

```cpp
void CLITask(void* arg) {
    while (true) {
        auto& state = StampFlyState::getInstance();

        if (state.getFlightState() == FlightState::FLYING) {
            // 飛行中は入力処理を間引く（10Hz）
            vTaskDelay(pdMS_TO_TICKS(100));
        } else {
            // 地上では通常処理
            processInput();
        }
    }
}
```

### 実装後の確認事項

1. **制御ループジッタ測定**: 飛行中に CLI 操作を行い、制御周期の乱れがないか確認
2. **CPU 使用率モニタリング**: `vTaskGetRunTimeStats()` で各タスクの CPU 時間を確認
3. **実飛行テスト**: CLI 操作しながらのホバリング安定性確認

## 11. 代替案

### 案A: linenoise を WiFi にも使用（難易度高）

linenoise を改造してソケットFDでも動作するようにする。
- メリット: 完全に同じ挙動
- デメリット: linenoise への深い理解が必要、メンテナンス性低下

### 案B: microrl 使用

別の軽量 CLI ライブラリ microrl を使用。
- メリット: I/O抽象化が組み込まれている
- デメリット: ESP-IDFとの統合が必要、esp_console の機能が使えない

### 案C: 現状維持 + 最小限の共通化（採用しない）

コマンド実行部分のみ共通化し、行編集は各自実装。
- メリット: 変更量が少ない
- デメリット: 行編集の重複が残る

**推奨: 本計画のアプローチ（esp_console + 独自 SocketLineEditor）**

---

<a id="english"></a>

# CLI Refactor Plan - ESP-IDF Console + linenoise Integration

## 1. Overview

### Purpose

Integrate Serial CLI and WiFi CLI with:

1. **Common command base**: ESP-IDF Console for command registration/execution
2. **Advanced line editing**: linenoise for history/completion/cursor movement
3. **Multi I/O**: Execute same commands from both Serial and WiFi

### Status

| Item | Status |
|------|--------|
| Planning | ✅ Done |
| Phase 1: esp_console integration | ✅ Done |
| Phase 2: linenoise integration | ✅ Done |
| Phase 3: WiFi CLI integration | ✅ Done |
| Phase 4: Remove old CLI | ⏳ Not started |

## 2. Target Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Target: Unified CLI Architecture              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│                    ┌─────────────────────┐                      │
│                    │   esp_console       │                      │
│                    │  (Command Engine)   │                      │
│                    ├─────────────────────┤                      │
│                    │ - Command registry  │                      │
│                    │ - Argument parsing  │                      │
│                    │ - Help generation   │                      │
│                    │ - esp_console_run() │                      │
│                    └──────────┬──────────┘                      │
│                               │                                 │
│              ┌────────────────┼────────────────┐                │
│              │                │                │                │
│              ▼                ▼                ▼                │
│  ┌───────────────────┐ ┌───────────────┐ ┌───────────────┐     │
│  │   Serial REPL     │ │  WiFi REPL    │ │ (Future)      │     │
│  │   + linenoise     │ │  + LineEditor │ │ WebSocket etc │     │
│  └───────────────────┘ └───────────────┘ └───────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 3. Implementation Phases

### Phase 1: esp_console Command Base
- Create sf_svc_console component
- Migrate existing commands to esp_console format
- Implement output redirection mechanism

### Phase 2: Serial REPL + linenoise
- Create sf_svc_serial_repl component
- Integrate linenoise for history/completion
- Tab completion with registered commands

### Phase 3: WiFi REPL Integration
- Implement SocketLineEditor (linenoise-inspired)
- Create sf_svc_wifi_repl component
- Connect to common command base

### Phase 4: Cleanup
- Remove deprecated sf_svc_cli
- Remove deprecated sf_svc_wifi_cli
- Update documentation

## 4. Key Design Decisions

### Output Redirection
- Thread-local output context
- Each REPL sets its own output function
- Commands use `Console::print()` instead of `printf()`

### WiFi Line Editing
- Custom SocketLineEditor (not linenoise directly)
- Handles escape sequences for arrow keys
- History support per-client

## 5. Resource Estimate

| Component | ROM | RAM |
|-----------|-----|-----|
| esp_console | ~8KB | ~1KB |
| linenoise | ~8KB | ~2KB |
| SocketLineEditor | ~4KB | ~1KB/client |
| **Total** | ~20KB | ~4KB base |

Net change: +7KB ROM, +2KB RAM (after removing old implementations)
