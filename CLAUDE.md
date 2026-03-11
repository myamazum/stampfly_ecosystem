# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Session Rules

- **セッション開始時またはコンテキスト圧縮後に以下を読むこと:**
  - `PROJECT_PLAN.md`
  - `.claude/settings.local.json`
  - 前回のコミットログ（Next stepsから作業を再開）
- **応答は日本語で行うこと**
- **コードを変更したら必ずコミットすること** - 変更をローカルに残さず、適切な単位でコミットする
  - **必ず `/commit` スキルを使用する** - `docs/contributing/commit-guidelines.md` に基づいたコミットメッセージを自動作成
  - **Next steps セクションを必ず含める** - 次回セッション開始時のタスクを明記
  - 作業終了時、ファイル変更後、重要な節目で自動実行
- **sf CLI を積極的に使用すること** - ビルド、書き込み、診断などは `idf.py` を直接呼ぶのではなく `sf` コマンドを優先する

## Build Environment

### ESP-IDF
ESP-IDFの初期化:
```bash
source ~/esp/esp-idf/export.sh
```

ファームウェアのビルド:
```bash
cd firmware/vehicle  # or firmware/controller
idf.py build
idf.py flash monitor
```

### sf CLI（推奨）
sf CLI は ESP-IDF 環境に統合された開発ツール。`idf.py` を直接使う代わりにこちらを優先する：
```bash
source ~/esp/esp-idf/export.sh  # ESP-IDF環境をアクティブ化（sfを使うため）

sf doctor              # 環境診断（問題があればまずこれを実行）
sf build vehicle       # vehicleファームウェアをビルド
sf build controller    # controllerファームウェアをビルド
sf flash vehicle       # vehicleに書き込み
sf monitor             # シリアルモニタを開く
sf flash vehicle -m    # 書き込み後にモニタを開く
```

**sf CLI の開発・改善:**
- コマンド実装: `lib/sfcli/commands/`
- ユーティリティ: `lib/sfcli/utils/`
- 新コマンド追加時は既存コマンドのパターンに従う
- 問題発見時は積極的に修正してフレームワークを改善する

**ツール統合方針:**
- **全てのツールは sf CLI 経由で使用する** - スタンドアロンの Python スクリプトを直接実行しない
- `tools/` 配下のスクリプトは sf CLI のバックエンド実装として扱う
- 新しいツールを作成する場合は、必ず対応する sf コマンドも追加する
- ラッパースクリプト（viz_*.py 等）は非推奨、sf コマンドのオプションで対応する

**sf CLI コマンド一覧:**
| コマンド | 説明 |
|---------|------|
| `sf doctor` | 環境診断 |
| `sf build [target]` | ファームウェアビルド |
| `sf flash [target]` | 書き込み（-m でモニタ付き）|
| `sf monitor` | シリアルモニタ |
| `sf log list` | ログファイル一覧 |
| `sf log capture` | USB経由バイナリログ取得 |
| `sf log wifi` | WiFi経由400Hzテレメトリ取得 |
| `sf log convert` | バイナリ→CSV変換 |
| `sf log info` | ログファイル情報表示 |
| `sf log analyze` | フライトログ解析 |
| `sf log viz` | ログ可視化 |
| `sf cal list` | キャリブレーション一覧 |
| `sf cal gyro/accel/mag` | 各種キャリブレーション |
| `sf sim list/run` | シミュレータ操作 |

### Genesis Simulator
Genesis物理シミュレータはvenv仮想環境にインストールされている:
```bash
cd simulator/sandbox/genesis_sim
source venv/bin/activate
cd scripts
python <script_name>.py
```

## Writing Conventions

### Code Comments
コメントは英語と日本語を併記する：
```c
// Initialize the motor driver
// モータドライバを初期化
motor_init();
```

### Documentation

ドキュメントは以下のルールに従う：

#### 1. バイリンガル構成（Bilingual Structure）

- 日本語を先に、英語を後に記述
- 冒頭に英語版の存在を示す注記を入れる（`#english` へのリンク付き）
- 英語セクションは `---` で区切り、直前に `<a id="english"></a>` を設置

```markdown
# Document Title

> **Note:** [English version follows after the Japanese section.](#english) / 日本語の後に英語版があります。

## 1. 概要

### このドキュメントについて
...

### 対象読者
...

## 2. 詳細

### 仕様
...

---

<a id="english"></a>

## 1. Overview

### About This Document
...

### Target Audience
...

## 2. Details

### Specifications
...
```

#### 2. 見出しフォーマット（Heading Format）

| レベル | 形式 | 例 |
|--------|------|-----|
| ドキュメントタイトル | `# Title` | `# StampFly Vehicle Firmware` |
| 章 | `## N. 章タイトル` | `## 1. 概要` / `## 1. Overview` |
| 節 | `### 節タイトル` | `### このプロジェクトについて` |
| 項 | `#### 項タイトル` | `#### パラメータ一覧` |

**注意:**
- 章には番号を付ける（`## 1.`, `## 2.`, ...）
- 節・項には番号を付けない（`## 1.1` ではなく `###`）
- 日本語と英語で同じ番号体系を使う

#### 3. 構造化情報（Structured Information）

リスト形式よりもテーブルを優先する：

```markdown
| 機能 | 説明 |
|------|------|
| IMU | BMI270（加速度・ジャイロ）400Hz |
| 気圧センサー | BMP280 50Hz |
```

#### 4. コードブロック（Code Blocks）

言語を明示する：

````markdown
```cpp
// Initialize motor
motor_init();
```

```bash
idf.py build flash monitor
```
````

#### 5. 図表（Diagrams）

ASCII アートを活用する：

```markdown
```
               Front
          FL (M4)   FR (M1)
             ╲   ▲   ╱
              ╲  │  ╱
               ╲ │ ╱
                ╲│╱
                 ╳         ← Center
                ╱│╲
               ╱ │ ╲
              ╱  │  ╲
             ╱   │   ╲
          RL (M3)    RR (M2)
                Rear
```
```

#### 6. 参考資料（References）

外部リンクはテーブル形式で整理：

```markdown
| リポジトリ | 説明 |
|-----------|------|
| [StampFly技術仕様](https://github.com/...) | ハードウェア仕様書 |
```

## Slide Rules（スライドルール）

### 自動レビュー必須

**CRITICAL: スライド（Beamer / TikZ）の `.tex` ファイルを変更したら、必ず PDF リビルドとレビューを実行すること。ユーザーへの確認は不要 — 変更したら自動的に行う。**

- スライド `.tex` を編集 → PDF リビルド → サブエージェントで目視確認 → 問題があれば修正、の一連を1サイクルとして完結させる
- 「レビューしますか？」とユーザーに聞かない。変更したら必ずやる
- 作成だけして fix を次回に回さない

### 画像確認はサブエージェント限定

**CRITICAL: スライド PDF の画像をメインコンテキストで Read してはならない。必ずサブエージェント内で完結させること。**

このルールは以下の全てに適用される：
- フルレビュー（チェックリスト適用）
- 簡易確認（1〜2ページの目視チェック）
- ユーザーから「確認して」と依頼された場合

理由: 画像の Read はコンテキストを大きく消費し、rate limit に抵触する原因になる。サブエージェント内で画像確認を完結させ、メインコンテキストにはテキストの指摘事項だけを返す。

## Slide Review Checklist

上記「Slide Rules」に従い、スライド変更後は以下のチェックリストでレビューし、問題があれば同一セッション内で修正すること。

### レビュー手順

1. **Beamer の `.tex` を1ページずつ読み、チェックリストを適用する**
2. **TikZ の `.tex` を1ファイルずつ読み、チェックリストを適用する**
3. **PDF を画像化してサブエージェントで目視確認する**（テキストレビューだけでは検出できないレイアウト崩れを発見するため。**Slide Image Rule 参照**）
4. 問題を発見したら修正し、修正ごとに fix コミットする

### 画像化による目視確認手順

テキストベースのレビューでは検出できない問題（はみ出し、重なり、切れ）を発見するため、**必ず PDF を画像化して目視確認する**。

#### サブエージェントによる目視確認（必須）

Agent ツールで以下のようなプロンプトのサブエージェントを起動する:

```
スライドの目視確認を行ってください。

1. TikZ をコンパイル・画像化して Read で確認:
   cd docs/education/workshop/slides/tikz
   lualatex -interaction=nonstopmode <file>.tex
   magick -density 150 <file>.pdf -quality 85 /tmp/tikz_<file>.png

2. Beamer をコンパイル・画像化して各ページを Read で確認:
   cd docs/education/workshop/slides/beamer
   lualatex -interaction=nonstopmode stampfly_workshop.tex
   magick -density 150 "stampfly_workshop.pdf[<page>]" -quality 85 /tmp/beamer_p<N>.png

3. 以下のチェックリストで各ページを確認し、問題があれば報告:
   - 図・テキストがスライド端で切れていないか
   - ノード・ラベルが重なっていないか
   - resizebox のスケーリングで横幅・縦幅が収まっているか
   - フッターにコンテンツが被っていないか

問題がなければ「問題なし」、問題があれば該当ページ番号・チェック項目ID・具体的な内容を報告してください。
コードの修正は行わず、レビュー結果の報告のみ行ってください。
```

**ポイント:**
- 解像度は 150dpi、品質 85 で十分（200dpi より軽量）
- 変更したページ付近のみ確認すればよい（全156ページを毎回確認しない）
- サブエージェントの結果を受けて、メイン側で修正→再度サブエージェントで確認のサイクルを回す

### チェック項目

#### L: レイアウト（Beamer スライド）

| ID | チェック内容 | 過去の発生例 |
|----|------------|-------------|
| L1 | テキストがスライド下端・フッターにはみ出していないか（vbox overflow） | L0 P4/P10, L7 caption |
| L2 | `block` / `alertblock` 内のテキストが長すぎて折り返しが不自然でないか | L2 goal text |
| L3 | テーブルのカラム幅が適切か（`p{Nmm}` で不要な折り返しが発生していないか） | L0 P2 テーマ column |
| L4 | コードリスティングがスライド1枚に収まるか（行数・フォントサイズ） | L7 code listing 20→14行 |
| L5 | `\resizebox` や `columns` で図とテキストが重ならないか | L9 P4 top-bottom→side-by-side |
| L6 | `\vspace` で要素間の余白が適切か（詰まりすぎ・空きすぎ） | L0 P10 exampleblock |

#### T: TikZ 図

| ID | チェック内容 | 過去の発生例 |
|----|------------|-------------|
| T1 | **タイトル重複:** TikZ 図内にタイトルを持たないこと（Beamer の frame title が担当） | feedback\_block, mixer\_matrix, imu\_axes, pid\_block |
| T2 | **ラベル重なり:** ラベル同士、ラベルと線・ノード・矢印が重なっていないか | gyro\_drift "True angle" vs curve, pid\_block labels vs sum node |
| T3 | **矢印の接続:** 矢印の始点がブロック・加算点・分岐点のいずれかに接続し、空白から発生していないか。矢印の終点がブロック・加算点に接続し、空白に消えていないか。図の入出力信号線には必ずラベル（`r(t)`, `y(t)` 等）があるか | — |
| T4 | **矢印の交差:** 矢印が不自然に交差していないか（交差が必要な場合は `line to` でオフセット） | — |
| T5 | **信号フローの正しさ:** ブロック図のフィードバック分岐点・加算点が制御工学の慣例に従っているか | feedback\_block tap point |
| T6 | **アノテーション位置:** 矢印・ラベルが指す先が実際のデータ点と一致しているか | step\_response overshoot arrow |
| T7 | **図のサイズ:** Beamer に `\resizebox` で埋め込んだときスライド領域に収まるか | gyro\_drift 12x6→8x5 |
| T8 | **数式・物理量の正確性:** 伝達関数・単位・パラメータが技術的に正しいか。**特に、同一スライド内のブロック図と数式が一致しているか**（共通ゲインの欠落、符号の不整合等）。各パスの伝達関数を加算して数式と照合すること | step\_response 2nd-order TF, pid\_block D項に $K_p$ 欠落 |
| T9 | **色定義:** `\definecolor` は `\begin{document}` の後に記述（standalone パッケージの互換性） | 全 TikZ ファイル |
| T10 | **フィードバック矢印の経路:** フィードバックループの矢印がノード下の説明テキスト（`desc` ノード等）を貫通していないか。矢印の終点はボックスの角（`south west` 等）ではなく辺の中点（`west`, `south` 等）に接続し、経路は説明テキストの外側を通すこと | build\_flash\_flow feedback → s1.south west |
| T11 | **分岐点のジャンクションドット:** 信号線が分岐する箇所に `\fill circle` で黒丸を配置しているか。ドットがないと信号の分岐元が不明瞭になる | sysid\_concept output tap |
| T12 | **矢印経路の微小セグメント:** `\|-` や `-\|` で生成される直角経路に、微小な水平/垂直セグメント（接続先ノードのすぐ隣で折れ曲がる等）が含まれていないか。タップ点を接続先の真上/真横に配置し直線化するか、経路を見直して解消する | sysid\_concept `\|-` で y(t) 側に微小左ジョグ発生 |

#### S: スライド構造

| ID | チェック内容 |
|----|------------|
| S1 | 各レッスンが標準構造に従っているか: タイトル → ゴール → 図/概念 → API → 実習コード → チェックポイント |
| S2 | 「次のレッスン」ブロックが正しいレッスン番号・タイトルを参照しているか |
| S3 | `\lesson{N}{日本語タイトル}{英語タイトル}` のフォーマットが正しいか |

### 修正方針

1. **レイアウト溢れ:** テキスト短縮 → フォントサイズ縮小（`\footnotesize`, `\scriptsize`）→ `columns` レイアウト変更の順で対応
2. **TikZ タイトル重複:** TikZ 側のタイトルを削除（Beamer frame title に委ねる）
3. **ラベル重なり:** `above`/`below`/`left`/`right` の位置変更、または `xshift`/`yshift` で微調整
4. **ブロック図の信号フロー:** フィードバック分岐は出力信号線上に junction dot を置く
5. **フィードバック矢印の経路:** 終点を `.west` や `.south` に変更し、説明テキストの外側を迂回させる（例: `-| ($(node.west)+(-8mm,0)$) -- (node.west)`）
6. **分岐点のドット欠落:** `\fill[color] (tap) circle (2.5pt);` でジャンクションドットを追加
7. **矢印の微小セグメント:** タップ点の座標を接続先ノードの真上/真横に合わせ（例: `\coordinate (tap) at (est.east |- plant.east);`）、`|-` を直線 `--` に置き換えて微小折れ曲がりを解消

## Project Overview

StampFly Ecosystem is an educational/research platform for drone control engineering. It covers the complete workflow: **design → implementation → experimentation → analysis → education**.

**Current Status:** Vehicle firmware (ACRO mode skeleton) and controller firmware are implemented and buildable.

## Architecture

The project uses a **responsibility-based directory structure**:

```
stampfly-ecosystem/
├── docs/              # Human-readable documentation
├── firmware/
│   ├── vehicle/       # Vehicle firmware
│   ├── controller/    # Transmitter firmware
│   └── common/        # Shared embedded code (protocol impl, math, utils)
├── protocol/          # Communication spec - Single Source of Truth (SSOT)
│   ├── spec/          # Machine-readable protocol definition (YAML/proto)
│   ├── generated/     # Auto-generated code from spec
│   └── tools/         # Validation and code generation
├── control/           # Control systems design (models, PID, MPC, SIL)
├── analysis/          # Data analysis (notebooks, scripts, datasets)
├── tools/             # Utilities (flashing, calibration, log capture, CI)
├── simulator/         # SIL/HIL testing environments
├── examples/          # Minimal working examples for learning
└── third_party/       # External dependencies
```

### Key Design Principles

1. **Protocol as Foundation**: All communication implementations derive from `protocol/spec/`. This is the Single Source of Truth.
2. **Responsibility Separation**: Each directory has a clear role. Don't mix concerns across boundaries.
3. **Educational Focus**: Code quality and documentation matter as much as functionality. This is built for students and researchers.

### Firmware Structure (ESP-IDF)

The `firmware/vehicle/` follows ESP-IDF component structure:
- `components/sensors/` - IMU, barometric, ToF, optical flow
- `components/estimation/` - AHRS, EKF, sensor fusion
- `components/control/` - Attitude, angular rate, position control loops
- `components/actuators/` - Motor mixing, saturation, failsafe
- `components/comms/` - Telemetry using protocol spec
- `components/system/` - State management, parameters, diagnostics, CLI
- `main/` - Task initialization and dependency management

## Build System

ESP-IDF for embedded firmware (ESP32 target)。**sf CLI を優先して使用する:**
```bash
# 推奨: sf CLI を使用
source ~/esp/esp-idf/export.sh
sf build vehicle
sf flash vehicle -m

# 代替: idf.py を直接使用（sf で問題がある場合のみ）
cd firmware/vehicle
idf.py build
idf.py flash monitor
```

## Implementation Priority

When developing this codebase, follow this order:
1. **protocol/spec/** - Define communication specification first
2. **firmware/common/protocol/** - Implement protocol encode/decode
3. **firmware/vehicle/** - Basic task structure and sensor integration
4. **examples/** - Minimal working demonstrations
5. **tools/** - Development utilities
6. **control/** and **analysis/** - Design and analysis tooling

## Language Notes

- **Firmware**: C/C++ (ESP-IDF framework)
- **Analysis/Tools**: Python (Jupyter notebooks, scripts)
- **Protocol Spec**: YAML or Protocol Buffers

## Reference

All architectural decisions are documented in `PROJECT_PLAN.md`. Consult this document before making structural changes.
