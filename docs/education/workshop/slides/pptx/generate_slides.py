#!/usr/bin/env python3
"""Generate StampFly Workshop slides (Lesson 0-9) as PowerPoint files.

Usage:
    python generate_slides.py              # Generate all lessons
    python generate_slides.py --lesson 0   # Generate specific lesson

Requires: python-pptx, Pillow
"""

from __future__ import annotations

import argparse
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SLIDE_WIDTH = Inches(13.333)   # 16:9
SLIDE_HEIGHT = Inches(7.5)

# StampFly brand colors
SF_BLUE = RGBColor(0, 120, 200)
SF_DARK = RGBColor(0, 60, 100)
SF_LIGHT = RGBColor(220, 240, 255)
SF_RED = RGBColor(220, 50, 30)
SF_GREEN = RGBColor(40, 160, 40)
SF_GRAY = RGBColor(80, 80, 80)
WHITE = RGBColor(255, 255, 255)
BLACK = RGBColor(0, 0, 0)

# Fonts — Meiryo for Japanese, Consolas for code
FONT_JP = "Meiryo"
FONT_CODE = "Consolas"

# Directories
SCRIPT_DIR = Path(__file__).resolve().parent
IMAGES_DIR = SCRIPT_DIR.parent / "images"
OUTPUT_DIR = SCRIPT_DIR / "output"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def new_presentation() -> Presentation:
    """Create a blank 16:9 presentation."""
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    return prs


def add_title_slide(prs: Presentation, title: str, subtitle: str) -> None:
    """Add a title slide with blue background."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank layout

    # Blue background
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = SF_BLUE

    # Title text
    left, top = Inches(1), Inches(2.5)
    txBox = slide.shapes.add_textbox(left, top, Inches(11), Inches(1.5))
    tf = txBox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_JP
    p.alignment = PP_ALIGN.CENTER

    # Subtitle
    txBox2 = slide.shapes.add_textbox(left, Inches(4.2), Inches(11), Inches(1))
    tf2 = txBox2.text_frame
    tf2.word_wrap = True
    p2 = tf2.paragraphs[0]
    p2.text = subtitle
    p2.font.size = Pt(24)
    p2.font.color.rgb = RGBColor(200, 230, 255)
    p2.font.name = FONT_JP
    p2.alignment = PP_ALIGN.CENTER


def add_content_slide(
    prs: Presentation,
    title: str,
    bullets: list[str],
    *,
    image_path: Path | None = None,
) -> None:
    """Add a content slide with title, bullet points, and optional image."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank

    # Title bar
    title_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
        SLIDE_WIDTH, Inches(1.1),
    )
    title_shape.fill.solid()
    title_shape.fill.fore_color.rgb = SF_BLUE
    title_shape.line.fill.background()
    tf = title_shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = f"  {title}"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_JP

    # Content area
    if image_path and image_path.exists():
        text_width = Inches(6.5)
        img_left = Inches(7.5)
    else:
        text_width = Inches(11)
        img_left = None

    # Bullet text
    txBox = slide.shapes.add_textbox(
        Inches(0.8), Inches(1.5), text_width, Inches(5.5),
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = bullet
        p.font.size = Pt(20)
        p.font.name = FONT_JP
        p.font.color.rgb = SF_GRAY
        p.space_after = Pt(8)
        p.level = 0

    # Image
    if img_left and image_path and image_path.exists():
        slide.shapes.add_picture(
            str(image_path), img_left, Inches(1.5),
            width=Inches(5),
        )


def add_code_slide(
    prs: Presentation,
    title: str,
    code: str,
    *,
    filename: str = "student.cpp",
) -> None:
    """Add a slide with code listing."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title bar
    title_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
        SLIDE_WIDTH, Inches(1.1),
    )
    title_shape.fill.solid()
    title_shape.fill.fore_color.rgb = SF_BLUE
    title_shape.line.fill.background()
    tf = title_shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = f"  {title}"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_JP

    # Filename label
    lbl = slide.shapes.add_textbox(
        Inches(0.8), Inches(1.3), Inches(3), Inches(0.5),
    )
    lp = lbl.text_frame.paragraphs[0]
    lp.text = filename
    lp.font.size = Pt(14)
    lp.font.bold = True
    lp.font.color.rgb = SF_BLUE
    lp.font.name = FONT_CODE

    # Code box background
    code_bg = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE,
        Inches(0.6), Inches(1.8),
        Inches(12), Inches(5.2),
    )
    code_bg.fill.solid()
    code_bg.fill.fore_color.rgb = SF_LIGHT
    code_bg.line.color.rgb = RGBColor(180, 210, 240)
    code_bg.line.width = Pt(1)

    # Code text
    txBox = slide.shapes.add_textbox(
        Inches(0.8), Inches(1.9), Inches(11.6), Inches(5.0),
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    lines = code.strip().split("\n")
    for i, line in enumerate(lines):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = line
        p.font.size = Pt(15)
        p.font.name = FONT_CODE
        p.font.color.rgb = SF_GRAY
        p.space_after = Pt(2)


def add_table_slide(
    prs: Presentation,
    title: str,
    headers: list[str],
    rows: list[list[str]],
) -> None:
    """Add a slide with a table."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title bar
    title_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
        SLIDE_WIDTH, Inches(1.1),
    )
    title_shape.fill.solid()
    title_shape.fill.fore_color.rgb = SF_BLUE
    title_shape.line.fill.background()
    tf = title_shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = f"  {title}"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_JP

    # Table
    n_rows = len(rows) + 1
    n_cols = len(headers)
    table_shape = slide.shapes.add_table(
        n_rows, n_cols,
        Inches(0.8), Inches(1.6),
        Inches(11.5), Inches(0.6 * n_rows),
    )
    table = table_shape.table

    # Header row
    for j, h in enumerate(headers):
        cell = table.cell(0, j)
        cell.text = h
        cell.fill.solid()
        cell.fill.fore_color.rgb = SF_BLUE
        for paragraph in cell.text_frame.paragraphs:
            paragraph.font.size = Pt(16)
            paragraph.font.bold = True
            paragraph.font.color.rgb = WHITE
            paragraph.font.name = FONT_JP

    # Data rows
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.cell(i + 1, j)
            cell.text = val
            if i % 2 == 0:
                cell.fill.solid()
                cell.fill.fore_color.rgb = SF_LIGHT
            for paragraph in cell.text_frame.paragraphs:
                paragraph.font.size = Pt(14)
                paragraph.font.name = FONT_JP
                paragraph.font.color.rgb = SF_GRAY


def add_checkpoint_slide(
    prs: Presentation,
    checks: list[str],
    next_lesson: str,
) -> None:
    """Add a checkpoint / summary slide."""
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    # Title bar
    title_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
        SLIDE_WIDTH, Inches(1.1),
    )
    title_shape.fill.solid()
    title_shape.fill.fore_color.rgb = SF_BLUE
    title_shape.line.fill.background()
    tf = title_shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = "  チェックポイント / Checkpoint"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_JP

    # Checks
    txBox = slide.shapes.add_textbox(
        Inches(0.8), Inches(1.6), Inches(11), Inches(3.5),
    )
    tf = txBox.text_frame
    tf.word_wrap = True
    for i, check in enumerate(checks):
        if i == 0:
            p = tf.paragraphs[0]
        else:
            p = tf.add_paragraph()
        p.text = f"\u2610  {check}"
        p.font.size = Pt(20)
        p.font.name = FONT_JP
        p.font.color.rgb = SF_GRAY
        p.space_after = Pt(6)

    # Next lesson box
    box = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE,
        Inches(0.8), Inches(5.5),
        Inches(11.5), Inches(1.2),
    )
    box.fill.solid()
    box.fill.fore_color.rgb = SF_LIGHT
    box.line.color.rgb = SF_BLUE
    box.line.width = Pt(2)
    btf = box.text_frame
    btf.vertical_anchor = MSO_ANCHOR.MIDDLE
    bp = btf.paragraphs[0]
    bp.text = f"次のレッスン: {next_lesson}"
    bp.font.size = Pt(22)
    bp.font.bold = True
    bp.font.color.rgb = SF_BLUE
    bp.font.name = FONT_JP
    bp.alignment = PP_ALIGN.CENTER


# ---------------------------------------------------------------------------
# Lesson builders
# ---------------------------------------------------------------------------

def build_lesson_00() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 0: 環境セットアップ", "Environment Setup")

    # P2: Workshop curriculum
    add_table_slide(prs, "ワークショップカリキュラム / Workshop Curriculum", [
        "Day", "Lesson", "テーマ",
    ], [
        ["Day 1", "0 - 2", "環境セットアップ + モータ + コントローラ"],
        ["Day 2", "3 - 5", "LED + IMU + 初フライト"],
        ["Day 3", "6 - 8", "PID制御 + テレメトリ + モデリング"],
        ["Day 4", "9 - 11", "姿勢推定 + Python SDK + 競技会準備"],
        ["Day 5 AM", "", "ホバリングタイム競技会"],
    ])

    # P3: StampFly hardware specs
    add_table_slide(prs, "StampFly ハードウェア / Hardware", [
        "項目", "仕様",
    ], [
        ["MCU", "ESP32-S3 (M5Stamp S3)"],
        ["IMU", "BMI270 (6軸 400Hz)"],
        ["気圧", "BMP280"],
        ["ToF", "VL53L3CX"],
        ["質量", "37g（バッテリ含む）"],
        ["通信", "ESP-NOW + WiFi"],
        ["バッテリ", "LiPo 1S 3.7V"],
    ])

    # P4: Ecosystem overview
    add_content_slide(prs, "エコシステム全体像 / Ecosystem Overview", [
        "StampFly Ecosystem の6層構造:",
        "",
        "• firmware/ --- 機体・送信機の組込みコード",
        "• control/ --- 制御設計（PID, MPC）",
        "• simulator/ --- 3D 物理シミュレータ",
        "• analysis/ --- データ解析（Jupyter）",
        "• tools/ --- 開発ツール（sf CLI）",
        "• protocol/ --- 通信仕様（SSOT）",
    ])

    # P5: sf CLI development tool
    add_table_slide(prs, "開発ツール sf CLI / Development Tool", [
        "カテゴリ", "コマンド例", "説明",
    ], [
        ["ビルド", "sf build / sf flash", "ファームウェア開発"],
        ["診断", "sf doctor / sf monitor", "デバッグ"],
        ["ログ", "sf log wifi / sf log viz", "テレメトリ取得・可視化"],
        ["シミュレータ", "sf sim run", "仮想環境で練習"],
        ["キャリブレーション", "sf cal gyro/accel/mag", "センサ校正"],
    ])

    # P6: Windows setup (1/2) — Prerequisites & install
    add_content_slide(prs, "Windows 環境構築 (1/2) / Windows Setup", [
        "【前提条件の確認】（CMD で実行）",
        "  git --version → git version 2.x（なければ winget install Git.Git）",
        "  python --version → Python 3.10 以上（なければ winget install Python.Python.3.12）",
        "",
        "【インストール手順】（CMD で実行）",
        "  1. リポジトリをクローン",
        "  2. install.bat を実行（ESP-IDF + sfcli 自動インストール）",
        "  3. setup_env.bat で開発環境をアクティベート",
        "",
        "  git clone https://github.com/.../stampfly-ecosystem.git",
        "  cd stampfly-ecosystem && install.bat && setup_env.bat",
    ])

    # P7: Windows setup (2/2) — Driver & verification
    add_content_slide(prs, "Windows 環境構築 (2/2) / Driver & Verification", [
        "【USB シリアルドライバ】",
        "• CH9102F ドライバをインストール（M5Stack 製品用）",
        "• https://docs.m5stack.com/en/download",
        "",
        "【動作確認】",
        "• sf doctor で環境診断 — すべて OK になれば完了",
        "",
        "【macOS / Linux ユーザー】",
        "• install.sh + setup_env.sh を使用してください",
    ])

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "ワークショップファームウェアをビルド・書き込み・動作確認する",
        "",
        "1. sf lesson build でビルド",
        "2. sf lesson flash で書き込み",
        "3. シリアルモニタで \"Hello StampFly!\" を確認",
    ])

    add_content_slide(
        prs, "開発フロー / Development Flow",
        ["sf CLI でビルド → フラッシュ → モニタの流れ"],
        image_path=IMAGES_DIR / "build_flash_flow.png",
    )

    add_table_slide(prs, "sf CLI コマンド一覧", [
        "コマンド", "説明",
    ], [
        ["sf doctor", "環境診断"],
        ["sf lesson build", "ワークショップビルド"],
        ["sf lesson flash", "書き込み＋モニタ"],
        ["sf lesson switch N", "レッスン切り替え"],
        ["sf monitor", "シリアルモニタ"],
    ])

    add_content_slide(prs, "ワークショップの構造 / Workshop Structure", [
        "学生が実装する関数は2つだけ！",
        "",
        "• setup() --- 起動時に1回呼ばれる",
        "• loop_400Hz(dt) --- 400Hz（2.5ms毎）で呼ばれる",
        "",
        "ハードウェアの複雑さは ws:: 名前空間で隠蔽",
        "FreeRTOS, SPI/I2C, センサーフュージョンを意識する必要なし",
    ])

    # P12: Firmware architecture
    add_content_slide(
        prs, "ファームウェアの全体像 / Firmware Architecture",
        [
            "5層構造（下から上へ）:",
            "",
            "  5. student.cpp ← 皆さんのコードはここ！",
            "  4. ws:: API（gyro_x(), motor_set_duty() 等）",
            "  3. Vehicle Components（IMU, baro, motor driver）",
            "  2. ESP-IDF / FreeRTOS（tasks, timers, queues）",
            "  1. Hardware（ESP32-S3, BMI270, BMP280）",
            "",
            "ws::gyro_x() と書くだけで SPI通信→フィルタ→バイアス補正を全部やってくれる",
            "下のレイヤーはワークショップ中意識する必要なし",
        ],
        image_path=IMAGES_DIR / "firmware_layers.png",
    )

    # P13: Behind the 400Hz loop
    add_content_slide(
        prs, "400Hz ループの裏側 / Behind the 400Hz Loop",
        [
            "loop_400Hz() が呼ばれるまでの流れ:",
            "",
            "  1. ESP Timer（2500μs）→ ハードウェアタイマ割り込み",
            "  2. IMU Task（Read BMI270）→ SPI読み取り + バイアス補正",
            "  3. Go!（data ready）→ データ準備完了",
            "  4. loop_400Hz (Your Code) → student.cpp が実行される",
            "",
            "→ 2.5ms ごとに繰り返し = 400Hz",
            "",
            "【ポイント】loop_400Hz(dt) は常にIMUデータ更新後に呼ばれる",
            "学生はタイマー管理不要、ただ関数を書くだけ！",
        ],
        image_path=IMAGES_DIR / "loop_400hz_timeline.png",
    )

    add_code_slide(prs, "実習: Hello StampFly", """
#include "workshop_api.hpp"

void setup()
{
    ws::print("Hello StampFly!");
}

void loop_400Hz(float dt)
{
    // Nothing to do in Lesson 0
}
""")

    # P15: Workflow
    add_content_slide(prs, "作業の進め方 / Workflow", [
        "【ファイル構造】",
        "  firmware/workshop/",
        "    ├── lessons/",
        "    │   ├── lesson_00/student.cpp  ← テンプレート",
        "    │   ├── lesson_01/student.cpp",
        "    │   └── ...",
        "    └── main/",
        "        └── user_code.cpp  ← ここを編集！",
        "",
        "【手順】",
        "  1. sf lesson switch N → テンプレートを user_code.cpp にコピー",
        "  2. user_code.cpp を編集",
        "  3. sf lesson build",
        "  4. sf lesson flash",
        "",
        "⚠ student.cpp はテンプレート — 直接編集しない！ switch で何度でもリセット可能",
    ])

    # P16: Controller setup
    add_content_slide(prs, "コントローラのセットアップ / Controller Setup", [
        "【コントローラのビルドと書き込み】",
        "  1. コントローラを USB 接続",
        "  2. sf build controller",
        "  3. sf flash controller",
        "",
        "【確認】",
        "  LCD に起動画面が表示されれば OK",
        "  Lesson 2 でペアリングして使用する",
    ])

    # P17: Simulator
    add_content_slide(prs, "シミュレータで遊ぶ / Try the Simulator", [
        "【USB HID モードに切替】",
        "  1. 画面タッチでメニューを開く",
        "  2. Comm: を選択",
        "  3. USB HID に切替 → 自動再起動",
        "",
        "【コマンド】",
        "  sf sim run                  ← デフォルト（VPython + ボクセルワールド）",
        "  sf sim run -w ringworld     ← 軽量ワールド",
        "",
        "【操作】スロットル → 上昇 / ロール・ピッチ → 傾き / ヨー → 回転",
        "",
        "アクロモード（角速度制御）で飛行 → まずは感覚をつかもう",
        "⚠ 終了後は Comm: を ESP-NOW に戻すこと（実機飛行用）",
    ])

    add_checkpoint_slide(prs, [
        "sf doctor がエラーなしで通る",
        "ビルドが成功し \"Hello StampFly!\" が表示される",
        "コントローラのビルド・書き込みが完了した",
        "シミュレータが起動し操縦を試した",
    ], "Lesson 1: モータ制御")

    return prs


def build_lesson_01() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 1: モータ制御", "Motor Control")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "モータの番号と配置を理解し、PWM で個別制御する",
        "",
        "• モータ番号 M1-M4 の位置を覚える",
        "• PWM デューティ比でモータ回転数を制御",
        "• 安全な地上テストの方法を学ぶ",
    ])

    add_content_slide(
        prs, "モータ配置 / Motor Layout",
        [
            "対角のモータが同じ方向に回転（トルクバランス）",
            "M1(FR), M3(RL) = CW（時計回り）",
            "M2(RR), M4(FL) = CCW（反時計回り）",
        ],
        image_path=IMAGES_DIR / "motor_layout.png",
    )

    add_content_slide(
        prs, "PWM とは / What is PWM?",
        [
            "Pulse Width Modulation（パルス幅変調）",
            "Duty 0% = 停止 / 100% = 最大回転",
            "StampFly API: motor_set_duty(id, 0.0~1.0)",
        ],
        image_path=IMAGES_DIR / "pwm_waveform.png",
    )

    add_table_slide(prs, "モータ制御 API", [
        "関数", "説明", "引数",
    ], [
        ["motor_set_duty(id, duty)", "個別モータ設定", "id=1-4, duty=0.0-1.0"],
        ["motor_set_all(duty)", "全モータ一括", "duty=0.0-1.0"],
        ["motor_stop_all()", "全モータ停止", "---"],
    ])

    add_code_slide(prs, "実習: モータを順番に回す", """
#include "workshop_api.hpp"

static uint32_t timer = 0;

void setup() {
    ws::print("Lesson 1: Motor Control");
}

void loop_400Hz(float dt) {
    timer++;
    // 800 ticks = 2 seconds at 400Hz
    int motor_id = (timer / 800) % 4 + 1;

    ws::motor_stop_all();
    ws::motor_set_duty(motor_id, 0.1f);  // 10% duty
}
""")

    add_checkpoint_slide(prs, [
        "M1 が FR（右前）のプロペラを回す",
        "M1→M2→M3→M4 の順に回転する",
        "各モータ 2 秒ごとに切り替わる",
    ], "Lesson 2: コントローラ入力")

    return prs


def build_lesson_02() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 2: コントローラ入力", "Controller Input")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "スティック値を変数に読み取り、演算でモータを個別制御する",
        "",
        "• ESP-NOW 無線通信の仕組みを理解",
        "• 変数と四則演算でスティック → モータ Duty を計算",
        "• オープンループ手動操縦の限界を体感",
    ])

    add_content_slide(
        prs, "ESP-NOW 通信フロー / Communication Flow",
        [
            "コントローラ → 2.4GHz 無線 → StampFly",
            "スティック値は ws:: API で取得可能",
        ],
        image_path=IMAGES_DIR / "espnow_dataflow.png",
    )

    add_table_slide(prs, "コントローラ API", [
        "関数", "説明", "値域",
    ], [
        ["rc_throttle()", "スロットル", "0.0 -- 1.0"],
        ["rc_roll()", "ロール", "-1.0 -- +1.0"],
        ["rc_pitch()", "ピッチ", "-1.0 -- +1.0"],
        ["rc_yaw()", "ヨー", "-1.0 -- +1.0"],
        ["is_armed()", "ARM状態", "true / false"],
        ["motor_set_duty(id, v)", "モータ個別制御", "id=1-4, v=0.0-1.0"],
    ])

    add_content_slide(prs, "ペアリング手順 / Pairing", [
        "Step 1: コントローラの M5ボタンを押しながら電源ON → LCD に \"Pairing mode...\" 表示",
        "Step 2: StampFly のボタンを 3秒長押し → 青LED高速点滅 + ビープ音",
        "Step 3: ペアリング完了 → ビープ音が鳴り、次回から自動接続",
        "",
        "⚠ 教室では一組ずつペアリングする（ブロードキャスト通信のため近くの機体と干渉する可能性）",
        "⚠ うまくいかない場合: 両方を再起動して Step 1 からやり直す",
    ])

    # Motor layout + mixing sign table
    add_table_slide(prs, "モータ配置とミキシング / Motor Layout & Mixing", [
        "Motor", "T", "Roll", "Pitch", "Yaw",
    ], [
        ["M1 FR", "+", "+", "-", "-"],
        ["M2 RR", "+", "+", "+", "+"],
        ["M3 RL", "+", "-", "+", "-"],
        ["M4 FL", "+", "-", "-", "+"],
    ])

    add_content_slide(
        prs, "オープンループ制御 / Open-Loop Control",
        [
            "フィードバックなしの直接制御",
            "問題: 外乱（風・重心ずれ）に対応できない",
            "→ Lesson 5-6 で PID 制御を導入して解決",
        ],
        image_path=IMAGES_DIR / "open_loop.png",
    )

    add_code_slide(prs, "実習: 手動ミキシング", """
#include "workshop_api.hpp"
static uint32_t tick = 0;
void setup() { ws::print("L2: Open-Loop Control"); }
void loop_400Hz(float dt) {
    tick++;
    float t = ws::rc_throttle();
    float r = ws::rc_roll()  * 0.3f;
    float p = ws::rc_pitch() * 0.3f;
    float y = ws::rc_yaw()   * 0.3f;
    ws::motor_set_duty(1, t + r - p - y); // FR
    ws::motor_set_duty(2, t + r + p + y); // RR
    ws::motor_set_duty(3, t - r + p - y); // RL
    ws::motor_set_duty(4, t - r - p + y); // FL
    if (tick % 80 == 0)
        ws::print("T=%.2f R=%.2f P=%.2f Y=%.2f",
            t, r, p, y);
}
""")

    add_checkpoint_slide(prs, [
        "コントローラとペアリングできた",
        "スロットルで全モータが均等に回る",
        "ピッチスティックで前後モータの回転差が出る",
        "ゲイン(0.3f)を変えて挙動の違いを確認した",
    ], "Lesson 3: LED 制御")

    return prs


def build_lesson_03() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 3: LED 制御", "LED Control")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "LED でシステムの状態を可視化する",
        "",
        "• WS2812 アドレサブル LED の制御",
        "• 状態遷移の考え方（ステートマシン）",
        "• バッテリー電圧のモニタリング",
    ])

    add_content_slide(
        prs, "LED 状態遷移 / LED State Machine",
        [
            "DISARM → 赤、ARM → 緑、低バッテリー → 橙",
            "is_armed() と battery_voltage() で状態判定",
        ],
        image_path=IMAGES_DIR / "led_state_machine.png",
    )

    add_table_slide(prs, "LED 制御 API", [
        "関数", "説明", "引数",
    ], [
        ["led_color(r, g, b)", "LED 色設定", "各 0-255"],
        ["is_armed()", "ARM 状態確認", "true / false"],
        ["battery_voltage()", "バッテリー電圧", "3.0-4.2 V"],
    ])

    add_content_slide(prs, "バッテリー電圧と色 / Battery & Color", [
        "LiPo バッテリー: 3.3V（空）〜 4.2V（満充電）",
        "",
        "電圧 → 色のマッピング:",
        "  3.3V = 赤（危険！）",
        "  3.75V = 黄",
        "  4.2V = 緑（満充電）",
        "",
        "⚠ 3.3V 以下で使用禁止！バッテリーが損傷します",
    ])

    add_code_slide(prs, "実習: ARM 状態で LED 色を変える", """
#include "workshop_api.hpp"

void setup() {
    ws::print("Lesson 3: LED Control");
}

void loop_400Hz(float dt) {
    if (ws::is_armed()) {
        ws::led_color(0, 255, 0);    // Green
    } else {
        // Battery level as color gradient
        float v = ws::battery_voltage();
        float level = (v - 3.3f) / (4.2f - 3.3f);
        if (level < 0) level = 0;
        if (level > 1) level = 1;
        uint8_t r = 255 * (1.0f - level);
        uint8_t g = 255 * level;
        ws::led_color(r, g, 0);
    }
}
""")

    add_checkpoint_slide(prs, [
        "DISARM 時に赤〜緑のグラデーション表示",
        "ARM すると緑に変わる",
        "バッテリー残量に応じて色が変化する",
    ], "Lesson 4: IMU センサー")

    return prs


def build_lesson_04() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 4: IMU センサ", "IMU Sensor")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "IMU（ジャイロ+加速度）データを読み取り、テレメトリで可視化する",
        "",
        "• NED 座標系（北-東-下）の理解",
        "• ジャイロスコープで角速度を取得",
        "• 加速度センサで並進加速度を取得",
        "• WiFi テレメトリでリアルタイム表示",
    ])

    add_content_slide(
        prs, "NED 座標系 / NED Coordinate System",
        [
            "X = 前方 (Forward)",
            "Y = 右方 (Right)",
            "Z = 下方 (Down)",
            "",
            "BMI270: 6軸 IMU（3軸ジャイロ + 3軸加速度）400Hz",
        ],
        image_path=IMAGES_DIR / "imu_axes.png",
    )

    add_table_slide(prs, "IMU API", [
        "関数", "説明", "単位",
    ], [
        ["gyro_x/y/z()", "角速度 (Roll/Pitch/Yaw)", "rad/s"],
        ["accel_x/y/z()", "加速度 (X/Y/Z)", "m/s²"],
        ["telemetry_send(name, val)", "WiFi テレメトリ送信", "---"],
    ])

    add_code_slide(prs, "実習: 6軸読み取り + テレメトリ", """
#include "workshop_api.hpp"
static uint32_t tick = 0;
void setup() {
    ws::print("Lesson 4: IMU Sensor");
}
void loop_400Hz(float dt) {
    tick++;
    float gx = ws::gyro_x();
    float gy = ws::gyro_y();
    float gz = ws::gyro_z();
    // Send via WiFi telemetry
    ws::telemetry_send("gyro_x", gx);
    ws::telemetry_send("gyro_y", gy);
    ws::telemetry_send("gyro_z", gz);
    // Print every 200ms (80 ticks)
    if (tick % 80 == 0) {
        ws::print("gx=%.2f gy=%.2f gz=%.2f", gx, gy, gz);
    }
}
""")

    add_checkpoint_slide(prs, [
        "手で傾けるとジャイロ値が変化する",
        "静止時に accel_z ≈ 9.81 を確認",
        "sf log wifi でテレメトリデータを受信できる",
    ], "Lesson 5: レート P 制御 + 初フライト")

    return prs


def build_lesson_05() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 5: レート P 制御 + 初フライト", "Rate P-Control + First Flight")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "比例フィードバック制御を実装し、初の制御飛行を行う",
        "",
        "• 閉ループ制御の考え方",
        "• P 制御で角速度を安定化",
        "• ARM/DISARM による安全管理",
    ])

    add_content_slide(
        prs, "閉ループ制御 / Closed-Loop Control",
        [
            "目標値とセンサ値の差（誤差）を計算",
            "誤差に比例ゲイン Kp を掛けて制御出力",
            "ジャイロセンサが帰還（フィードバック）を提供",
        ],
        image_path=IMAGES_DIR / "feedback_block.png",
    )

    add_table_slide(prs, "制御 API", [
        "関数", "説明", "値域",
    ], [
        ["gyro_x/y/z()", "ジャイロ角速度", "rad/s"],
        ["rc_roll/pitch/yaw()", "スティック入力", "-1.0 -- +1.0"],
        ["rc_throttle()", "スロットル", "0.0 -- 1.0"],
        ["motor_mixer(T,R,P,Y)", "モーターミキサー", "---"],
        ["is_armed()", "ARM 状態確認", "true / false"],
    ])

    add_code_slide(prs, "実習: 3軸 P 制御", """
#include "workshop_api.hpp"
void setup() { ws::print("Lesson 5: Rate P-Control"); }
void loop_400Hz(float dt) {
    if (!ws::is_armed()) {
        ws::motor_stop_all();
        ws::led_color(50, 0, 0);  // Red = DISARM
        return;
    }
    ws::led_color(0, 50, 0);  // Green = ARM
    float Kp_rp = 0.5f, Kp_yaw = 2.0f;
    float rate_max = 1.0f, yaw_max = 5.0f;
    float roll_e  = ws::rc_roll()*rate_max  - ws::gyro_x();
    float pitch_e = ws::rc_pitch()*rate_max - ws::gyro_y();
    float yaw_e   = ws::rc_yaw()*yaw_max   - ws::gyro_z();
    ws::motor_mixer(ws::rc_throttle(),
        Kp_rp*roll_e, Kp_rp*pitch_e, Kp_yaw*yaw_e);
}
""")

    add_content_slide(prs, "安全注意 / Safety", [
        "⚠ フライト前チェック:",
        "",
        "☐ 保護メガネを着用",
        "☐ 低スロットルから徐々に上げる（最初は 30% 以下）",
        "☐ プロペラの回転方向を確認（M1=CW, M2=CCW, M3=CW, M4=CCW）",
        "☐ 異常時はすぐにスロットルを下げて DISARM",
    ])

    add_checkpoint_slide(prs, [
        "ARM 後スロットルを上げて安定ホバリング",
        "スティック操作で機体が応答する",
        "DISARM で即座にモーターが停止する",
    ], "Lesson 6: PID 制御")

    return prs


def build_lesson_06() -> Presentation:
    prs = new_presentation()

    # Slide 1: Title
    add_title_slide(prs, "Lesson 6: PID 制御", "PID Control")

    # Slide 2: Goal (updated)
    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "工学形式 PID を実装し、不完全微分でノイズに強い制御を実現する",
        "",
        "• P 制御の限界（定常偏差、振動）",
        "• 工学形式 Kp / Ti / Td とは",
        "• 不完全微分: ノイズに強い微分項",
        "• ログから調整する方法",
    ])

    # Slide 3: PID Block Diagram
    add_content_slide(
        prs, "PID 制御器 / PID Controller",
        [
            "P（比例）: 現在の誤差に比例した出力",
            "I（積分）: Kp/Ti で偏差の蓄積を補正",
            "D（不完全微分）: Td·s/(η·Td·s+1) で高周波をカット",
            "",
            "C(s) = Kp(1 + 1/(Ti·s) + Td·s/(η·Td·s+1))",
        ],
        image_path=IMAGES_DIR / "pid_block.png",
    )

    # Slide 4: Why Incomplete Derivative? (new)
    add_content_slide(prs, "なぜ不完全微分か / Why Incomplete Derivative?", [
        "【問題】",
        "• ジャイロセンサにはノイズがある",
        "• 理想微分 de/dt はノイズを増幅",
        "• 高周波振動 → モータに悪影響",
        "",
        "【解決策】",
        "• 不完全微分フィルタ η で高周波をカット",
        "• η = 0.1〜0.2（小→フィルタ弱い、大→フィルタ強い）",
        "• 微分の効きとノイズ除去のトレードオフ",
    ])

    # Slide 5: Engineering Form Parameters (new)
    add_table_slide(prs, "工学形式パラメータ / Engineering Form", [
        "パラメータ", "意味", "効果",
    ], [
        ["Kp", "比例ゲイン", "大→応答速い、大きすぎ→振動"],
        ["Ti", "積分時間 [s]", "小→積分強い、小さすぎ→ワインドアップ"],
        ["Td", "微分時間 [s]", "大→微分強い、大きすぎ→ノイズ増幅"],
        ["η", "フィルタ係数", "0.1〜0.2、大→ノイズに強い"],
    ])

    # Slide 6: Log-Based Tuning Guide (new)
    add_table_slide(prs, "ログから調整する / Log-Based Tuning", [
        "ログで見える症状", "原因", "調整",
    ], [
        ["振動が収まらない", "Kp 過大", "Kp↓"],
        ["応答が遅い", "Kp 過小", "Kp↑"],
        ["定常偏差が残る", "I項不足", "Ti↓（積分強化）"],
        ["オーバーシュート大", "D項不足", "Td↑（微分強化）"],
        ["高周波ノイズ", "η 過小", "η↑（0.1→0.2）"],
        ["ゆっくり発散", "ワインドアップ", "Ti↑"],
    ])

    # Slide 7: Recommended Gains (Ti/Td form)
    add_table_slide(prs, "推奨ゲイン / Recommended Gains", [
        "軸", "Kp", "Ti [s]", "Td [s]", "η",
    ], [
        ["Roll", "0.5", "1.67", "0.01", "0.125"],
        ["Pitch", "0.5", "1.67", "0.01", "0.125"],
        ["Yaw", "2.0", "4.0", "0.005", "0.125"],
    ])

    # Slide 8: Hands-on Step 1 -- Ideal PID
    add_code_slide(prs, "実習 Step 1: 理想 PID", """
float Kp=0.5f, Ti=1.67f, Td=0.01f;
float integral=0, prev_err=0;
// inside loop_400Hz(dt)
float error = target - ws::gyro_x();
float P = Kp * error;
if (Ti > 0)  // I term (trapezoidal)
    integral += (dt/(2*Ti)) * (error + prev_err);
float I = Kp * integral;
float D = Kp*Td*(error - prev_err)/dt; // ideal D
prev_err = error;
float roll_out = P + I + D;
""")

    # Slide 9: Hands-on Step 2 -- Incomplete Derivative
    add_code_slide(prs, "実習 Step 2: 不完全微分", """
// Replace ideal D with incomplete derivative filter
float eta = 0.125f;
float d_filt = 0;  // persistent state
// inside loop_400Hz(dt)
float alpha = 2*eta*Td / dt;
float a = (alpha - 1) / (alpha + 1);
float b = 2*Td / ((alpha + 1) * dt);
d_filt = a * d_filt + b * (error - prev_err);
float D = Kp * d_filt;  // Filtered!
""")

    # Slide 10: Checkpoint (updated)
    add_checkpoint_slide(prs, [
        "理想微分 vs 不完全微分で高周波振動の違いを確認",
        "定常偏差がなくなった（P のみと比較）",
        "ゲイン調整表を使って応答を改善できた",
    ], "Lesson 7: テレメトリ + ステップ応答")

    return prs


def build_lesson_07() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 7: テレメトリ + ステップ応答",
                    "Telemetry + Step Response")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "WiFi テレメトリでステップ応答データを取得し、制御性能を分析する",
        "",
        "• ステップ応答とは何か",
        "• 立ち上がり時間・オーバーシュート・整定時間",
        "• sf log wifi でデータ取得",
    ])

    add_content_slide(
        prs, "ステップ応答 / Step Response",
        [
            "Rise Time: 目標値の 10%→90% に到達する時間",
            "Overshoot: 目標値を超える量",
            "Settling Time: ±5% 以内に収まる時間",
        ],
        image_path=IMAGES_DIR / "step_response.png",
    )

    add_table_slide(prs, "テレメトリ API", [
        "関数", "説明", "引数",
    ], [
        ["telemetry_send(name, val)", "テレメトリ送信", "名前, float 値"],
        ["led_color(r, g, b)", "LED 色設定", "各 0-255"],
    ])

    add_content_slide(prs, "実験手順 / Experiment Procedure", [
        "1. ホバリング状態でステップ入力を自動付加",
        "2. sf log wifi でリアルタイム記録",
        "3. CSV を分析して性能指標を計測",
    ])

    add_code_slide(prs, "実習: ステップ応答実験", """
// Step response experiment (excerpt)
float step_rate = 0.5f;    // Step amplitude [rad/s]
uint32_t delay  = 800;     // 2s wait at 400Hz
uint32_t dur    = 400;     // 1s step

float roll_step = 0.0f;
if (elapsed >= delay && elapsed < delay + dur)
    roll_step = step_rate;  // Step ON!

// Override roll target with step input
float roll_target = roll_step;

// Send telemetry at 400Hz
ws::telemetry_send("step_target", roll_step);
ws::telemetry_send("step_actual", ws::gyro_x());

// LED: red during step, green otherwise
if (roll_step > 0) ws::led_color(50, 0, 0);
else               ws::led_color(0, 50, 0);
""")

    add_checkpoint_slide(prs, [
        "sf log wifi でデータを取得できた",
        "波形でオーバーシュートを確認",
        "整定時間を計測（目安: 0.3s 以内）",
    ], "Lesson 8: モデリング")

    return prs


def build_lesson_08() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 8: モデリング", "Quadrotor Dynamics")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "運動方程式から第一原理でモーターミキサーを自力導出する",
        "",
        "• クアッドロータの力学モデル",
        "• 推力 T、ロール/ピッチ/ヨー トルク",
        "• motor_mixer() を使わず個別モータ制御",
    ])

    # Motor layout + Mixer matrix side by side (matching Beamer columns layout)
    slide = prs.slides.add_slide(prs.slide_layouts[6])  # blank
    title_shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(0), Inches(0),
        SLIDE_WIDTH, Inches(1.1),
    )
    title_shape.fill.solid()
    title_shape.fill.fore_color.rgb = SF_BLUE
    title_shape.line.fill.background()
    tf = title_shape.text_frame
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]
    p.text = "  ミキサー行列 / Motor Mixer Matrix"
    p.font.size = Pt(28)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = FONT_JP
    motor_img = IMAGES_DIR / "motor_layout.png"
    mixer_img = IMAGES_DIR / "mixer_matrix.png"
    if motor_img.exists():
        slide.shapes.add_picture(
            str(motor_img), Inches(0.3), Inches(1.3), width=Inches(4.5),
        )
    if mixer_img.exists():
        slide.shapes.add_picture(
            str(mixer_img), Inches(5.5), Inches(1.3), width=Inches(7.3),
        )

    add_table_slide(prs, "物理パラメータ / Physical Parameters", [
        "パラメータ", "値", "説明",
    ], [
        ["L", "0.023 m", "アーム長（中心→モータ）"],
        ["kq", "0.01", "トルク対推力比"],
    ])

    add_code_slide(prs, "実習: カスタムミキサー", """
// Custom mixer from first principles
float L = 0.023f, kq = 0.01f;
float T = throttle;
float R = roll_cmd, P = pitch_cmd, Y = yaw_cmd;

float m1 = T/4 + R/(4*L) - P/(4*L) - Y/(4*kq);
float m2 = T/4 + R/(4*L) + P/(4*L) + Y/(4*kq);
float m3 = T/4 - R/(4*L) + P/(4*L) - Y/(4*kq);
float m4 = T/4 - R/(4*L) - P/(4*L) + Y/(4*kq);

// Clamp [0.0, 1.0]
if (m1 < 0) m1 = 0; if (m1 > 1) m1 = 1;
if (m2 < 0) m2 = 0; if (m2 > 1) m2 = 1;
if (m3 < 0) m3 = 0; if (m3 > 1) m3 = 1;
if (m4 < 0) m4 = 0; if (m4 > 1) m4 = 1;

ws::motor_set_duty(1, m1); ws::motor_set_duty(2, m2);
ws::motor_set_duty(3, m3); ws::motor_set_duty(4, m4);
""")

    add_checkpoint_slide(prs, [
        "motor_mixer() なしで飛行できた",
        "motor_mixer() 使用時と同等の飛行性能",
        "L や kq を変えて挙動の変化を確認",
    ], "Lesson 9: 姿勢推定")

    return prs


def build_lesson_09() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 9: 姿勢推定", "Attitude Estimation")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "相補フィルタを実装し、ESKFの推定値と比較する",
        "",
        "• ジャイロ積分のドリフト問題を理解",
        "• 相補フィルタで加速度センサとジャイロを融合",
        "• テレメトリで CF vs ESKF をリアルタイム比較",
    ])

    add_content_slide(
        prs, "ジャイロドリフト問題 / Gyro Drift Problem",
        [
            "ジャイロは角速度 ω を測定 → 角度 = ∫ω dt",
            "微小なバイアスが時間と共に蓄積（ドリフト）",
            "ジャイロ単体では長時間の姿勢推定は不可能",
            "",
            "→ 加速度センサと組み合わせて解決",
        ],
        image_path=IMAGES_DIR / "gyro_drift.png",
    )

    add_content_slide(
        prs, "相補フィルタ / Complementary Filter",
        [
            "θ̂ = α·(θ̂_prev + ω·dt) + (1−α)·θ_accel",
            "",
            "α = 0.98（ジャイロ 98% + 加速度 2%）",
            "",
            "ジャイロ: 短期精度◎ / 長期ドリフト✕",
            "加速度: 長期安定◎ / 振動ノイズ✕",
            "→ 両者の長所を融合",
        ],
        image_path=IMAGES_DIR / "comp_filter.png",
    )

    add_code_slide(prs, "実習: 相補フィルタ実装", """
#include "workshop_api.hpp"
#include <cmath>
static float cf_roll = 0.0f, cf_pitch = 0.0f;

void setup() { ws::print("Lesson 9: Attitude Estimation"); }

void loop_400Hz(float dt) {
    float gx = ws::gyro_x(), gy = ws::gyro_y();
    float ax = ws::accel_x(), ay = ws::accel_y(),
          az = ws::accel_z();
    float accel_roll  = atan2f(ay, az);
    float accel_pitch = atan2f(-ax, az);

    constexpr float alpha = 0.98f;
    cf_roll  = alpha*(cf_roll  + gx*dt)
             + (1-alpha)*accel_roll;
    cf_pitch = alpha*(cf_pitch + gy*dt)
             + (1-alpha)*accel_pitch;

    ws::telemetry_send("cf_roll",  cf_roll*57.3f);
    ws::telemetry_send("eskf_roll",
                       ws::estimated_roll()*57.3f);
}
""")

    add_checkpoint_slide(prs, [
        "手で傾けると CF のロール・ピッチが変化する",
        "CF と ESKF の値が概ね一致する",
        "α を変えて応答の違いを観察した",
    ], "TBD")

    return prs


def build_lesson_10() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 10: Python SDK プログラム飛行", "Python SDK Flight")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "Python SDK でプログラム飛行を実現する",
        "",
        "• WiFi 経由で PC から StampFly を制御",
        "• SDK API で離陸・移動・着陸をプログラム化",
        "• RC 制御値の送信とテレメトリの取得",
    ])

    add_content_slide(
        prs, "SDK アーキテクチャ / SDK Architecture",
        [
            "PC (Python SDK) ↔ WiFi AP ↔ StampFly ESP32-S3",
            "",
            "TCP CLI (port 23): コマンド送受信（takeoff, land, move...）",
            "WebSocket (port 81): テレメトリ受信（400 Hz リアルタイム）",
            "",
            "WiFi AP アドレス: 192.168.4.1",
        ],
        image_path=IMAGES_DIR / "python_sdk_arch.png",
    )

    add_table_slide(prs, "Python SDK API", ["関数", "説明", "備考"], [
        ["StampFly(host)", "インスタンス生成", "デフォルト 192.168.4.1"],
        ["connect()", "WiFi 接続", "TCP CLI + WS"],
        ["takeoff()", "離陸", "ブロッキング"],
        ["land()", "着陸", "ブロッキング"],
        ["move_forward(cm)", "前進", "20-200 cm"],
        ["rotate_clockwise(deg)", "時計回り回転", "1-360°"],
        ["send_rc_control(lr,fb,ud,yaw)", "RC 制御値送信", "-100〜+100"],
        ["get_telemetry()", "テレメトリ取得", "400 Hz dict"],
        ["end()", "切断", "リソース解放"],
    ])

    add_code_slide(prs, "実習1: 基本プログラム飛行", """
from stampfly import StampFly

drone = StampFly()
drone.connect()

drone.takeoff()
drone.move_forward(50)    # 50 cm forward
drone.rotate_clockwise(90)
drone.move_forward(50)
drone.land()

drone.end()
""", filename="flight_basic.py")

    add_code_slide(prs, "実習2: RC制御 + テレメトリ", """
import time
from stampfly import StampFly

drone = StampFly()
drone.connect()
drone.takeoff()

# Hover + read telemetry for 5 seconds
for _ in range(50):
    drone.send_rc_control(0, 0, 0, 0)
    t = drone.get_telemetry()
    print(f"alt={t.get('alt',0):.1f}")
    time.sleep(0.1)

drone.land()
drone.end()
""", filename="flight_rc.py")

    add_checkpoint_slide(prs, [
        "WiFi AP に接続し connect() が成功する",
        "takeoff() → move_forward() → land() が動作する",
        "get_telemetry() で高度データを取得できる",
    ], "Lesson 11: ホバリングタイム競技会 ルール説明")

    return prs


def build_lesson_11() -> Presentation:
    prs = new_presentation()

    add_title_slide(prs, "Lesson 11: ホバリングタイム競技会", "Hover Time Competition")

    add_content_slide(prs, "競技会概要 / Competition Overview", [
        "ホバリングタイム競技",
        "PID 制御で安定ホバリングし、滞空時間を競う",
        "",
        "• 種目: ホバリングタイム（角速度フィードバック制御）",
        "• 目標: 最長 60 秒の安定ホバリング",
        "• 評価: 滞空時間（ベストタイム採用）",
        "• ツール: sf competition hover-time",
    ])

    add_table_slide(prs, "競技ルール詳細 / Competition Rules",
        ["項目", "内容"],
        [
            ["種目", "ホバリングタイム（角速度フィードバック制御）"],
            ["制限時間", "最長 60 秒"],
            ["試行回数", "3 回（ベストタイム採用）"],
            ["判定", "離陸〜接地までの滞空時間"],
            ["失格条件", "安全エリア外への飛行、手による介入"],
        ],
    )

    add_table_slide(prs, "タイムスケジュール / Schedule",
        ["時間", "内容"],
        [
            ["Day 4: 13:00-13:30", "ルール説明（このスライド）"],
            ["Day 4: 13:30-16:00", "準備・自由練習・予選"],
            ["Day 5: 9:00-9:15", "ルール確認・機体チェック"],
            ["Day 5: 9:15-9:45", "最終チューニング"],
            ["Day 5: 9:45-10:45", "競技本番"],
            ["Day 5: 10:45-11:30", "結果発表・表彰・振り返り"],
        ],
    )

    add_content_slide(prs, "攻略のヒント / Tips for Success", [
        "【PID ゲイン調整】",
        "• まず P ゲインだけで安定させる",
        "• 振動が出たら D ゲインを追加",
        "• 定常偏差があれば I ゲインを微調整",
        "",
        "【バッテリ & 安全】",
        "• フル充電で本番に臨む",
        "• プロペラの取付を再確認",
        "• 異常振動はすぐに着陸",
        "",
        "テレメトリ活用: sf log wifi でリアルタイムデータを確認",
    ])

    add_checkpoint_slide(prs, [
        "競技ルールと失格条件を理解した",
        "バッテリがフル充電されている",
        "PID ゲインの調整方法を把握している",
        "安全チェックリストを確認した",
    ], "さあ、練習を始めよう！ 13:30 から自由練習")

    return prs


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

BUILDERS = {
    0: build_lesson_00,
    1: build_lesson_01,
    2: build_lesson_02,
    3: build_lesson_03,
    4: build_lesson_04,
    5: build_lesson_05,
    6: build_lesson_06,
    7: build_lesson_07,
    8: build_lesson_08,
    9: build_lesson_09,
    10: build_lesson_10,
    11: build_lesson_11,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate StampFly workshop PPTX")
    parser.add_argument("--lesson", type=int, help="Lesson number (0-11)")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.lesson is not None:
        lessons = [args.lesson]
    else:
        lessons = sorted(BUILDERS.keys())

    for n in lessons:
        builder = BUILDERS.get(n)
        if builder is None:
            print(f"Unknown lesson: {n}")
            continue
        prs = builder()
        out_path = OUTPUT_DIR / f"lesson_{n:02d}.pptx"
        prs.save(str(out_path))
        print(f"Generated: {out_path}")


if __name__ == "__main__":
    main()
