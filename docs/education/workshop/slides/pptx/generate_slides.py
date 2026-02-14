#!/usr/bin/env python3
"""Generate StampFly Workshop slides (Lesson 0-3) as PowerPoint files.

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

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "ワークショップファームウェアをビルド・書き込み・動作確認する",
        "",
        "1. sf build workshop でビルド",
        "2. sf flash workshop -m で書き込み",
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
        ["sf build workshop", "ワークショップビルド"],
        ["sf flash workshop -m", "書き込み＋モニタ"],
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

    add_checkpoint_slide(prs, [
        "sf doctor がエラーなしで通る",
        "ビルドが成功する",
        "シリアルモニタに \"Hello StampFly!\" が表示される",
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
        "コントローラのスティック値を読み取り、モータを操作する",
        "",
        "• ESP-NOW 無線通信の仕組みを理解",
        "• スティック値の正規化（ADC → 浮動小数点）",
        "• オープンループ制御の限界を体感",
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

    add_code_slide(prs, "実習: スロットル → モータ", """
#include "workshop_api.hpp"

static uint32_t tick = 0;

void setup() {
    ws::print("Lesson 2: Controller Input");
}

void loop_400Hz(float dt) {
    tick++;
    float throttle = ws::rc_throttle();

    // Direct throttle-to-motor (open loop)
    ws::motor_set_all(throttle);

    // Print every 200ms
    if (tick % 80 == 0) {
        ws::print("T=%.2f R=%.2f P=%.2f Y=%.2f",
            throttle, ws::rc_roll(),
            ws::rc_pitch(), ws::rc_yaw());
    }
}
""")

    add_checkpoint_slide(prs, [
        "コントローラとペアリングできた",
        "ARM 後、スロットルでモータが回る",
        "シリアルモニタに T/R/P/Y 値が表示される",
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


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

BUILDERS = {
    0: build_lesson_00,
    1: build_lesson_01,
    2: build_lesson_02,
    3: build_lesson_03,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate StampFly workshop PPTX")
    parser.add_argument("--lesson", type=int, help="Lesson number (0-3)")
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
