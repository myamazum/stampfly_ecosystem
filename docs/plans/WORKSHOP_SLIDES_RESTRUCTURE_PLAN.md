# Workshop スライド統合リストラクチャ計画

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 背景と動機

### 現状の問題

- **番号ベースのファイル名** (`lesson_02.tex`) では内容が推測できない。レッスン追加・並べ替え時に全ファイルのリネームが必要
- **14個の独立PDF** として配布していたが、Workshop完了により全レッスンを1冊のPDFに統合したい
- **スライド内のコードスニペット** が `solution.cpp` / `student.cpp` とハードコピーで重複しており、ファームウェア更新時にスライドとの乖離が発生する
- **`sf lesson` コマンド** がレッスン番号のみで動作し、内容が分からない。番号が変わるとユーザーが混乱する

### ゴール

1. 全レッスンを1つのBeamer PDFに統合（レッスン間にディバイダ）
2. ファイル名を内容ベースに変更（番号→トピック名）
3. コードスニペットをファームウェアソースから自動抽出する仕組みを構築
4. `sf lesson list` で番号・タイトル・概要を表示、番号変更に強い設計

---

## 2. 設計

### ファイル構成（変更後）

```
docs/education/workshop/slides/
├── beamer/
│   ├── main.tex                    # 統合メインファイル（\input で各章を読み込む）
│   ├── stampfly_slides.sty         # 共通スタイル（既存）
│   ├── preamble.tex                # 共通プリアンブル（新規、main.tex から分離）
│   │
│   ├── chapters/                   # レッスン別ファイル（内容ベース命名）
│   │   ├── environment_setup.tex      # 旧 lesson_00
│   │   ├── motor_control.tex          # 旧 lesson_01
│   │   ├── controller_input.tex       # 旧 lesson_02
│   │   ├── led_control.tex            # 旧 lesson_03
│   │   ├── imu_sensor.tex             # 旧 lesson_04
│   │   ├── rate_p_control.tex         # 旧 lesson_05
│   │   ├── system_modeling.tex        # 旧 lesson_06
│   │   ├── system_identification.tex  # 旧 lesson_07
│   │   ├── pid_control.tex            # 旧 lesson_08
│   │   ├── attitude_estimation.tex    # 旧 lesson_09
│   │   ├── api_reference.tex          # 旧 lesson_10
│   │   ├── custom_firmware.tex        # 旧 lesson_11
│   │   ├── python_sdk.tex             # 旧 lesson_12
│   │   └── precision_landing.tex      # 旧 lesson_13
│   │
│   └── main.pdf                    # 統合PDF出力
│
├── tikz/                           # TikZ図（既存、変更なし）
├── images/                         # PNG画像（既存、変更なし）
├── Makefile                        # 更新
└── .gitignore                      # 更新
```

### main.tex の構造

```latex
\documentclass[aspectratio=169, 14pt]{beamer}
\usepackage{stampfly_slides}

\title{StampFly Workshop}
\subtitle{ドローン制御工学ワークショップ}
\author{StampFly Workshop}
\date{}

\begin{document}

\begin{frame}
  \titlepage
\end{frame}

% --- Day 1 ---
\lessondivider{0}{環境セットアップ}{Environment Setup}
\input{chapters/environment_setup}

\lessondivider{1}{モータ制御}{Motor Control}
\input{chapters/motor_control}

\lessondivider{2}{コントローラ入力}{Controller Input}
\input{chapters/controller_input}

% --- Day 2 ---
\lessondivider{3}{LED制御}{LED Control}
\input{chapters/led_control}

% ... 以下同様 ...

\end{document}
```

各 `chapters/*.tex` ファイルには `\documentclass` や `\begin{document}` を含めず、フレーム定義のみを記述する。

### レッスン番号の管理

**番号はメインファイルの `\input` 順序で決まる。** 個別ファイルは番号を持たない。

- `\lessondivider{N}{JP}{EN}` のNだけがレッスン番号を定義
- ファイルを並べ替えたら `\lessondivider` の番号を書き換えるだけ
- 新レッスン挿入時も他ファイルの編集は不要

### レッスンメタデータ（lesson_manifest.yaml）

レッスンの番号・タイトル・ファイルの対応を1箇所で管理する:

```
firmware/workshop/lessons/lesson_manifest.yaml
```

```yaml
# Lesson Manifest — Single Source of Truth for lesson ordering
# レッスンマニフェスト — レッスン順序の唯一の情報源

lessons:
  - number: 0
    id: environment_setup
    title_ja: 環境セットアップ
    title_en: Environment Setup
    description_ja: ESP-IDF環境構築、ビルド・書き込み・モニタの基本
    description_en: ESP-IDF setup, build/flash/monitor basics
    firmware_dir: lesson_00_setup    # firmware/workshop/lessons/ 配下
    slide_file: environment_setup    # chapters/ 配下（.tex省略）

  - number: 1
    id: motor_control
    title_ja: モータ制御
    title_en: Motor Control
    description_ja: PWMデューティ比によるモータ制御、ARM/DISARM
    description_en: Motor control via PWM duty cycle, arm/disarm
    firmware_dir: lesson_01_motor
    slide_file: motor_control

  # ... 以下同様 ...
```

**利点:**
- `sf lesson list` がこのファイルを読んで番号・タイトル・概要を表示
- Makefile / スクリプトがこのファイルを参照してビルド順を決定
- レッスン追加・並べ替えはこのファイルの編集だけで完結
- PPTXジェネレータもこのファイルからレッスン情報を取得可能

---

## 3. コードスニペット自動抽出

### 方針

ファームウェアのソースコードにマーカーコメントを埋め込み、スライドビルド時に自動抽出する。

### ソースコード側（solution.cpp / student.cpp）

```cpp
// @@snippet: setup
void setup() {
    ws::print("Lesson 3: LED Control");
    ws::disable_led_task();
}
// @@end-snippet: setup

// @@snippet: loop
void loop_400Hz(float dt) {
    if (ws::is_armed()) {
        ws::led_color(0, 255, 0);    // Green
    } else {
        float v = ws::battery_voltage();
        float level = (v - 3.3f) / (4.2f - 3.3f);
        if (level < 0) level = 0;
        if (level > 1) level = 1;
        uint8_t r = 255 * (1.0f - level);
        uint8_t g = 255 * level;
        ws::led_color(r, g, 0);
    }
}
// @@end-snippet: loop
```

### スライド側（chapters/led_control.tex）

```latex
% Auto-extracted from firmware/workshop/lessons/lesson_03_led/solution.cpp
% @@include-snippet: lesson_03_led/solution.cpp:setup+loop
\begin{lstlisting}[style=sfcpp, title={user\_code.cpp}]
%%SNIPPET:lesson_03_led/solution.cpp:setup%%
%%SNIPPET:lesson_03_led/solution.cpp:loop%%
\end{lstlisting}
```

### 抽出スクリプト（tools/extract_snippets.py）

- `%%SNIPPET:path:name%%` プレースホルダを検出
- 対応するソースから `@@snippet` ～ `@@end-snippet` 間を抽出
- `.tex` ファイルを一時コピーに展開（ソース `.tex` 自体は書き換えない）
- Makefileで `lualatex` 前に実行

### ビルドフロー

```
extract_snippets.py → chapters/*.tex (展開済み一時ファイル) → lualatex → main.pdf
```

---

## 4. sf lesson コマンドの改善

### 変更点

| 機能 | 現在 | 変更後 |
|------|------|--------|
| `sf lesson list` | ディレクトリ名のみ | manifest から番号・タイトル・概要を表示 |
| `sf lesson switch` | 番号のみ | 番号またはID（`sf lesson switch motor_control`）|
| `sf lesson info <N>` | なし | 新規: 該当レッスンの詳細（API一覧、前提知識等）|
| レッスン発見 | ディレクトリ走査 | manifest.yaml 優先、フォールバックでディレクトリ走査 |

### `sf lesson list` 出力イメージ

```
Workshop Lessons
================

  Day 1:
    Lesson  0: 環境セットアップ / Environment Setup
                ESP-IDF環境構築、ビルド・書き込み・モニタの基本
    Lesson  1: モータ制御 / Motor Control
                PWMデューティ比によるモータ制御、ARM/DISARM
    Lesson  2: コントローラ入力 / Controller Input
                ESP-NOW無線通信、RCスティック値、オープンループ制御

  Day 2:
    Lesson  3: LED制御 / LED Control
                ...
    ...

  Total: 14 lessons
  Switch: sf lesson switch <N or id>
```

---

## 5. 実装ステップ

### Phase 1: ファイル構造の変更（破壊的変更なし）

1. `beamer/chapters/` ディレクトリを作成
2. 既存 `lesson_XX.tex` を `chapters/` に内容ベース名でコピー
3. 各ファイルから `\documentclass` / `\begin{document}` / `\end{document}` を除去
4. `\lesson{N}{JP}{EN}` マクロ呼び出しも除去（`\lessondivider` に移行）
5. `main.tex` を作成し、全章を `\input` で統合
6. `preamble.tex` を分離（`stampfly_slides.sty` のカスタマイズ等）
7. Makefileに `main.pdf` ビルドターゲットを追加
8. ビルド確認（`make main` で統合PDF生成）

### Phase 2: レッスンマニフェスト

1. `lesson_manifest.yaml` を作成
2. `sf lesson list` を manifest 対応に改修
3. `sf lesson switch` にID指定を追加
4. `sf lesson info` サブコマンドを追加

### Phase 3: コードスニペット連携

1. `tools/extract_snippets.py` を作成
2. 全 `solution.cpp` / `student.cpp` にスニペットマーカーを追加
3. `chapters/*.tex` のハードコードされたコードブロックをスニペット参照に置換
4. Makefileのビルドフローにスニペット抽出ステップを追加
5. ビルド確認（コードが正しく展開されることを検証）

### Phase 4: クリーンアップ

1. 旧 `lesson_XX.tex` ファイルを削除
2. `.gitignore` 更新（一時展開ファイルの除外）
3. ドキュメント更新（DOCUMENT_INDEX.md、README等）
4. PPTXジェネレータは現状維持（必要が生じた場合にのみ対応）

---

## 6. リスクと対策

| リスク | 影響 | 対策 |
|--------|------|------|
| 統合PDFのページ数増大（コンパイル時間） | ビルド時間増加 | 個別ビルドモードも残す（Makefile `make chapter NAME=led_control`）|
| スニペットマーカーのメンテナンスコスト | マーカー忘れでビルド失敗 | `make check-snippets` で未解決プレースホルダを検出 |
| lesson_manifest.yaml とディレクトリの不整合 | sf lesson が動作しない | `sf doctor` にmanifest検証を追加 |
| 既存Beamer PDFのgit履歴との断絶 | git blameが効かない | `git mv` を活用、Phase 1完了時にコミット |

---

## 7. 最終成果物

| 成果物 | 説明 |
|--------|------|
| `main.pdf` | 全14レッスン統合PDF（配布用） |
| `chapters/*.tex` | 内容ベース命名の個別レッスンファイル |
| `lesson_manifest.yaml` | レッスンメタデータの唯一の情報源 |
| `tools/extract_snippets.py` | コードスニペット自動抽出ツール |
| 改修済み `sf lesson` | manifest対応、ID指定、info表示 |

---

---

<a id="english"></a>

# Workshop Slides Restructure Plan

## 1. Background and Motivation

### Current Problems

- **Number-based file names** (`lesson_02.tex`) don't convey content. Renumbering is required when adding/reordering lessons
- **14 separate PDFs** were distributed, but with the workshop complete, all lessons should be merged into a single PDF
- **Code snippets in slides** are hard-copied from `solution.cpp` / `student.cpp`, causing drift when firmware is updated
- **`sf lesson` command** only works with lesson numbers, making it unclear what each lesson covers. Number changes confuse users

### Goals

1. Merge all lessons into a single Beamer PDF with lesson dividers
2. Rename files from numbers to topic-based names
3. Build a mechanism to auto-extract code snippets from firmware source
4. `sf lesson list` shows number, title, and description; resilient to number changes

---

## 2. Design

### File Structure (After)

```
docs/education/workshop/slides/
├── beamer/
│   ├── main.tex                    # Master file (\input each chapter)
│   ├── stampfly_slides.sty         # Common style (existing)
│   ├── preamble.tex                # Common preamble (new, extracted from main)
│   │
│   ├── chapters/                   # Per-lesson files (topic-based names)
│   │   ├── environment_setup.tex      # was lesson_00
│   │   ├── motor_control.tex          # was lesson_01
│   │   ├── controller_input.tex       # was lesson_02
│   │   ├── led_control.tex            # was lesson_03
│   │   ├── imu_sensor.tex             # was lesson_04
│   │   ├── rate_p_control.tex         # was lesson_05
│   │   ├── system_modeling.tex        # was lesson_06
│   │   ├── system_identification.tex  # was lesson_07
│   │   ├── pid_control.tex            # was lesson_08
│   │   ├── attitude_estimation.tex    # was lesson_09
│   │   ├── api_reference.tex          # was lesson_10
│   │   ├── custom_firmware.tex        # was lesson_11
│   │   ├── python_sdk.tex             # was lesson_12
│   │   └── precision_landing.tex      # was lesson_13
│   │
│   └── main.pdf                    # Combined PDF output
│
├── tikz/                           # TikZ diagrams (unchanged)
├── images/                         # PNG images (unchanged)
├── Makefile                        # Updated
└── .gitignore                      # Updated
```

### main.tex Structure

Each `chapters/*.tex` contains only frame definitions (no `\documentclass` or `\begin{document}`). Lesson numbers are defined solely by the `\lessondivider{N}{JP}{EN}` calls in `main.tex`.

### Lesson Manifest (lesson_manifest.yaml)

A single YAML file at `firmware/workshop/lessons/lesson_manifest.yaml` defines the mapping between lesson numbers, topic IDs, titles, firmware directories, and slide files. This is the Single Source of Truth for lesson ordering.

---

## 3. Code Snippet Auto-Extraction

Firmware source files are annotated with `@@snippet` / `@@end-snippet` markers. A build-time script (`tools/extract_snippets.py`) resolves `%%SNIPPET:path:name%%` placeholders in `.tex` files before LaTeX compilation.

---

## 4. sf lesson Command Improvements

- `sf lesson list`: Reads manifest, shows number + title + description
- `sf lesson switch`: Accepts number or topic ID
- `sf lesson info <N>`: New subcommand showing lesson details

---

## 5. Implementation Phases

| Phase | Description | Scope |
|-------|-------------|-------|
| 1 | File restructure | Create `chapters/`, `main.tex`, rename files, update Makefile |
| 2 | Lesson manifest | Create YAML, update `sf lesson` command |
| 3 | Code snippet sync | Create extractor, add markers, update slides |
| 4 | Cleanup | Remove old files, update docs. PPTX generator left as-is (update only when needed) |

---

## 6. Risks and Mitigations

| Risk | Mitigation |
|------|-----------|
| Long compile time for combined PDF | Keep per-chapter build mode in Makefile |
| Snippet marker maintenance | `make check-snippets` detects unresolved placeholders |
| Manifest/directory mismatch | `sf doctor` validates manifest |
| Git history disruption | Use `git mv` where possible |
