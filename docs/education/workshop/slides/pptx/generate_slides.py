#!/usr/bin/env python3
"""Generate StampFly Workshop slides (Lesson 0-8) as PowerPoint files.

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

    add_title_slide(prs, "Lesson 6: PID 制御", "PID Control")

    add_content_slide(prs, "今日のゴール / Today's Goal", [
        "I 項・D 項を追加し、定常偏差除去とオーバーシュート低減を実現する",
        "",
        "• P 制御の限界（定常偏差が残る）",
        "• I 項: 偏差の積分で定常偏差を除去",
        "• D 項: 偏差の微分でオーバーシュートを低減",
    ])

    add_content_slide(
        prs, "PID 制御器 / PID Controller",
        [
            "P（比例）: 現在の誤差に比例した出力",
            "I（積分）: 誤差の蓄積を補正",
            "D（微分）: 誤差の変化率で振動を抑制",
        ],
        image_path=IMAGES_DIR / "pid_block.png",
    )

    add_table_slide(prs, "推奨ゲイン / Recommended Gains", [
        "軸", "Kp", "Ki", "Kd",
    ], [
        ["Roll", "0.5", "0.3", "0.005"],
        ["Pitch", "0.5", "0.3", "0.005"],
        ["Yaw", "2.0", "0.5", "0.01"],
    ])

    add_content_slide(prs, "チューニングの順序 / Tuning Procedure", [
        "1. Ki = Kd = 0 にして Kp を調整（振動しない最大値）",
        "2. Ki を少しずつ追加（定常偏差が消えるまで）",
        "3. Kd を少しずつ追加（振動が収まるまで）",
    ])

    add_code_slide(prs, "実習: ロール軸 PID", """
#include "workshop_api.hpp"
float Kp=0.5f, Ki=0.3f, Kd=0.005f;
float integral=0, prev_err=0;
void setup() { ws::print("Lesson 6: PID"); }
void loop_400Hz(float dt) {
    if (!ws::is_armed()) {
        ws::motor_stop_all();
        integral = 0; prev_err = 0;  // Reset
        return;
    }
    float target = ws::rc_roll() * 1.0f;
    float error  = target - ws::gyro_x();
    float P = Kp * error;
    integral += error * dt;
    if (integral >  0.5f) integral =  0.5f;
    if (integral < -0.5f) integral = -0.5f;
    float I = Ki * integral;
    float D = Kd * (error - prev_err) / dt;
    prev_err = error;
    float roll_out = P + I + D;
    // Repeat for pitch and yaw axes
    ws::motor_mixer(ws::rc_throttle(), roll_out,
                    pitch_out, yaw_out);
}
""")

    add_checkpoint_slide(prs, [
        "定常偏差がなくなった（P のみと比較）",
        "振動なく安定してホバリング",
        "ゲインを変更して応答の変化を確認",
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
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate StampFly workshop PPTX")
    parser.add_argument("--lesson", type=int, help="Lesson number (0-8)")
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
