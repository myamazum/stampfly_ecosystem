# Serial CLI 再構築プラン

**ステータス: ✅ 完了**

---

## 完了サマリー

### 実施内容

| Phase | 内容 | 状態 |
|-------|------|------|
| Phase 1 | 既存 Serial CLI の削除 | ✅ 完了 |
| Phase 2 | ESP-IDF 標準コンソールで再構築 | ✅ 完了 |
| Phase 3 | 動作確認 | ✅ 完了 |

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `sf_svc_serial_cli/` | ディレクトリ全体を削除 |
| `main/tasks/cli_task.cpp` | ESP-IDF 標準コンソール使用に変更 |
| `main/CMakeLists.txt` | sf_svc_serial_cli 依存削除 |
| `main/config.hpp` | STACK_SIZE_CLI を 4096 に復元 |

### 実装上の注意点

1. **マクロ名**: `ESP_CONSOLE_DEV_CDC_CONFIG_DEFAULT()` を使用（`USB_CDC` ではない）
2. **コマンド登録順序**: REPL 作成後にコマンドを登録することでデフォルト help を上書き
3. **タスク終了**: REPL は独自タスクで動作するため CLITask は `vTaskDelete()` で終了

### 動作確認結果

- ✅ プロンプト表示
- ✅ 文字エコー
- ✅ コマンド実行（help, status, version 等）
- ✅ 履歴（上下矢印）
- ✅ Tab 補完
- ✅ WiFi CLI と同じ help 形式

---

## 1. 現状分析

### WiFi CLI 仕様（動作確認済み）

| 項目 | 内容 |
|------|------|
| コンポーネント | `sf_svc_wifi_cli` |
| I/O 方式 | TCP ソケット (`recv`/`send`) |
| 行編集 | `sf_lib_line_editor` (LineEditor クラス) |
| 補完 | Tab キーで登録コマンドを補完 |
| 履歴 | 上下矢印キーでコマンド履歴をナビゲート |
| Telnet 対応 | IAC ネゴシエーションでエコー・文字モードを設定 |
| コマンド実行 | `Console::getInstance().run(line)` |
| 出力リダイレクト | `console.setOutput(callback, ctx)` |

### WiFi CLI の I/O コールバック

```cpp
// 読み取り: ソケットから1バイト取得
static int socket_read_byte(void* ctx) {
    int fd = *static_cast<int*>(ctx);
    char c;
    int ret = recv(fd, &c, 1, 0);  // ブロッキング
    if (ret <= 0) return -1;
    return static_cast<unsigned char>(c);
}

// 書き込み: ソケットにデータ送信
static int socket_write_data(void* ctx, const void* data, size_t len) {
    int fd = *static_cast<int*>(ctx);
    return send(fd, data, len, 0);
}
```

### 現在の問題点

Serial CLI が動作しない原因として考えられる点：

1. **USB CDC VFS の設定不足**
   - ESP-IDF の USB CDC は TinyUSB ベースで、適切なドライバ初期化が必要
   - 手動設定が複雑で不整合が発生

2. **stdio バッファリング**
   - `getchar()`/`putchar()` は stdio レイヤーを経由
   - USB CDC ドライバとの組み合わせで予期しない動作

3. **古いコードの残骸**
   - 複数回の修正で不整合が発生した可能性

## 2. 再構築方針

### アプローチ選択肢

| 方法 | メリット | デメリット |
|------|----------|------------|
| A. ESP-IDF 標準コンソール使用 | 確実に動作、セットアップ簡単 | linenoise 固定、カスタム不可 |
| B. TinyUSB CDC 直接使用 | 完全な制御、LineEditor 使用可能 | 実装が複雑 |
| C. VFS 経由で raw read/write | 中間的アプローチ | VFS 設定が複雑 |

**推奨: 方法 A を採用**

理由：
- Serial CLI は USB 経由の標準コンソールとして十分
- ESP-IDF 標準は linenoise 組み込み済みで履歴・補完対応
- WiFi CLI で LineEditor が使えるため、高度な機能はそちらで提供
- シンプルで保守しやすい

### 役割分担

| CLI | 用途 | 実装 |
|-----|------|------|
| Serial CLI | デバッグ・開発用の基本コンソール | ESP-IDF 標準コンソール |
| WiFi CLI | 飛行中のリモートアクセス、高度な機能 | カスタム LineEditor |

## 3. 実装計画

### Phase 1: 既存 Serial CLI の削除

1. `sf_svc_serial_cli` コンポーネントを削除
2. `cli_task.cpp` を更新して SerialCLI 参照を削除
3. `main/CMakeLists.txt` から依存関係を削除
4. ビルド確認

### Phase 2: 新 Serial CLI の作成

ESP-IDF 標準コンソールを使用したシンプルな実装：

```cpp
// cli_task.cpp
#include "esp_console.h"
#include "console.hpp"

void CLITask(void* pvParameters) {
    // コマンド登録
    auto& console = Console::getInstance();
    console.registerAllCommands();

    // USB CDC コンソール設定
    esp_console_repl_config_t repl_config = ESP_CONSOLE_REPL_CONFIG_DEFAULT();
    repl_config.prompt = "stampfly> ";
    repl_config.max_cmdline_length = 256;

    esp_console_dev_usb_cdc_config_t cdc_config =
        ESP_CONSOLE_DEV_USB_CDC_CONFIG_DEFAULT();

    esp_console_repl_t* repl = nullptr;
    ESP_ERROR_CHECK(esp_console_new_repl_usb_cdc(&cdc_config, &repl_config, &repl));
    ESP_ERROR_CHECK(esp_console_start_repl(repl));

    // コンソールは別タスクで動作するため、このタスクは削除可能
    vTaskDelete(nullptr);
}
```

### Phase 3: 動作確認

1. ビルド・書き込み
2. `idf.py monitor` で接続
3. 以下を確認：
   - プロンプト表示
   - 文字エコー
   - コマンド実行（help, status, version）
   - 履歴（上下矢印）
   - Tab 補完

## 4. ファイル変更一覧

### 削除

- `firmware/vehicle/components/sf_svc_serial_cli/` (ディレクトリ全体)

### 変更

- `firmware/vehicle/main/CMakeLists.txt` - sf_svc_serial_cli 依存削除
- `firmware/vehicle/main/tasks/cli_task.cpp` - ESP-IDF 標準コンソール使用に変更
- `firmware/vehicle/main/config.hpp` - `STACK_SIZE_CLI` を元に戻す（4096）

## 5. 確認事項

ユーザーへの質問：

1. **Serial CLI の機能要件**
   - ESP-IDF 標準コンソールで十分か？
   - WiFi CLI と同じカスタム LineEditor が必要か？

2. **CLI タスクの扱い**
   - コンソールは別タスクで動作するため、CLITask を維持するか削除するか？
