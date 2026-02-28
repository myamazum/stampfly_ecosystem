"""
sf rc - RC (Remote Control) command

Send real-time RC control inputs to StampFly.
リアルタイムRC制御入力をStampFlyに送信する。

Modes:
    sf rc <a> <b> <c> <d>   - One-shot: send single RC command
    sf rc                   - Interactive: keyboard control mode

Parameters (Tello SDK compatible):
    a: left/right   (-100~100) → roll
    b: forward/back  (-100~100) → pitch
    c: up/down       (-100~100) → throttle
    d: yaw           (-100~100) → yaw
"""

import argparse
import asyncio
import os
import sys
import time

# Terminal raw mode modules (Unix only)
# ターミナル生入力モジュール（Unix専用）
try:
    import select
    import termios
    import tty
    _HAS_TERMIOS = True
except ImportError:
    _HAS_TERMIOS = False

from ..utils import console
from ..utils.vehicle_connection import VehicleConnection, DEFAULT_HOST


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register rc command with CLI

    rcコマンドをCLIに登録する
    """
    parser = subparsers.add_parser(
        "rc",
        help="RC control (one-shot or interactive keyboard)",
        description=(
            "Send RC control inputs to StampFly.\n"
            "  sf rc <a> <b> <c> <d>  — One-shot mode (single command)\n"
            "  sf rc                  — Interactive keyboard control mode\n\n"
            "Parameters: a=roll, b=pitch, c=throttle, d=yaw (-100~100)"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "values",
        nargs="*",
        type=int,
        help="RC values: <a> <b> <c> <d> (-100~100). Omit for interactive mode.",
    )
    parser.add_argument(
        "--ip",
        default=DEFAULT_HOST,
        help=f"Vehicle IP address (default: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--rate",
        type=int,
        default=20,
        help="Send rate in Hz for interactive mode (default: 20)",
    )
    parser.set_defaults(func=run_rc)


def run_rc(args: argparse.Namespace) -> int:
    """Execute RC command (one-shot or interactive)"""
    if args.values:
        if len(args.values) != 4:
            console.error("Expected 4 values: sf rc <a> <b> <c> <d>")
            return 1
        for v in args.values:
            if v < -100 or v > 100:
                console.error("Values must be -100~100")
                return 1
        return _run_oneshot(args)
    else:
        return _run_interactive(args)


# =============================================================================
# One-shot mode
# =============================================================================

def _run_oneshot(args: argparse.Namespace) -> int:
    """Send a single rc command and disconnect."""
    a, b, c, d = args.values
    console.info(f"RC one-shot: a={a} b={b} c={c} d={d}", prefix="RC")
    try:
        return asyncio.run(_async_oneshot(a, b, c, d, args.ip))
    except KeyboardInterrupt:
        return 130


async def _async_oneshot(a: int, b: int, c: int, d: int, host: str) -> int:
    """Async one-shot RC command."""
    conn = VehicleConnection()

    try:
        console.print(f"  Connecting to {host}...")
        try:
            await conn.connect(host, timeout=5.0)
        except OSError:
            console.error("Vehicle not reachable. Connect to StampFly WiFi AP first.")
            return 1
        except ImportError as e:
            console.error(str(e))
            return 1

        console.success("Connected")

        response = await conn.cli.send_command(f"rc {a} {b} {c} {d}")
        if response:
            console.print(f"  {response}")

        await conn.disconnect()
        return 0

    except Exception as e:
        console.error(f"RC command failed: {e}")
        try:
            await conn.disconnect()
        except Exception:
            pass
        return 1


# =============================================================================
# Interactive mode
# =============================================================================

# Key mappings for interactive control
# インタラクティブ制御のキーマッピング
KEY_HELP = """
  [RC Interactive Mode / インタラクティブモード]

  W/S     Forward / Backward (pitch)
  A/D     Left / Right (roll)
  Q/E     Yaw left / Yaw right
  Space   Up (throttle)
  Z       Down (throttle)
  +/-     Speed adjust (10-100)
  L       Land
  X       Emergency stop
  Ctrl+C  Quit (sends rc 0 0 0 0)
"""


def _run_interactive(args: argparse.Namespace) -> int:
    """Run interactive keyboard RC control mode."""
    # termios is required for raw keyboard input (Unix only)
    # termiosはキーボード生入力に必要（Unix専用）
    if not _HAS_TERMIOS:
        console.error("Interactive RC mode is not supported on Windows")
        console.error("Use one-shot mode: sf rc <a> <b> <c> <d>")
        return 1

    # Check if stdin is a terminal
    # 標準入力がターミナルかチェック
    if not sys.stdin.isatty():
        console.error("Interactive mode requires a terminal")
        return 1

    console.info("Starting interactive RC mode", prefix="RC")
    console.print(KEY_HELP)

    try:
        return asyncio.run(_async_interactive(args.ip, args.rate))
    except KeyboardInterrupt:
        return 0


async def _async_interactive(host: str, rate: int) -> int:
    """Async interactive RC control loop."""
    conn = VehicleConnection()

    console.print(f"  Connecting to {host}...")
    try:
        await conn.connect(host, timeout=5.0)
    except OSError:
        console.error("Vehicle not reachable. Connect to StampFly WiFi AP first.")
        return 1
    except ImportError as e:
        console.error(str(e))
        return 1

    console.success("Connected (CLI + WebSocket)")
    console.print("  Press keys to control. Ctrl+C to quit.\n")

    # State for RC values
    # RC値の状態
    rc_state = {
        "a": 0,   # roll (left/right)
        "b": 0,   # pitch (forward/back)
        "c": 0,   # throttle (up/down)
        "d": 0,   # yaw
        "speed": 50,
        "running": True,
        "last_line_len": 0,
    }

    # Track which keys are pressed (for key release detection)
    # 押されているキーの追跡（キーリリース検出用）
    key_timers = {}

    # Save terminal settings
    # ターミナル設定を保存
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    interval = 1.0 / rate
    start_time = time.monotonic()
    last_telemetry = None

    try:
        # Set raw mode for character-by-character input
        # 1文字ずつ入力するためにrawモードに設定
        tty.setraw(fd)

        while rc_state["running"]:
            loop_start = time.monotonic()

            # Read all available keys (non-blocking)
            # 利用可能な全キーを読み取り（ノンブロッキング）
            while select.select([sys.stdin], [], [], 0)[0]:
                ch = sys.stdin.read(1)
                _handle_key(ch, rc_state, key_timers, loop_start)

            # Key release detection: zero out axes if key not pressed recently
            # キーリリース検出: 最近押されていない軸をゼロにする
            _update_key_release(rc_state, key_timers, loop_start, timeout=0.08)

            # Handle special commands (land / emergency)
            # 特殊コマンドの処理（着陸 / 緊急停止）
            if rc_state.pop("_land", False):
                try:
                    await conn.cli.send_command("land", timeout=2.0)
                except Exception:
                    pass
                rc_state["running"] = False
                break
            if rc_state.pop("_emergency", False):
                try:
                    await conn.cli.send_command("emergency", timeout=2.0)
                except Exception:
                    pass
                rc_state["running"] = False
                break

            # Send RC command via CLI
            # CLI経由でRCコマンドを送信
            a, b, c, d = rc_state["a"], rc_state["b"], rc_state["c"], rc_state["d"]
            try:
                await conn.cli.send_command(f"rc {a} {b} {c} {d}", timeout=1.0)
            except Exception:
                pass

            # Receive telemetry (non-blocking)
            # テレメトリ受信（ノンブロッキング）
            try:
                telem = await conn.telemetry.receive(timeout=0.05)
                if telem:
                    last_telemetry = telem
            except Exception:
                pass

            # Display status line
            # ステータス行を表示
            _display_status(rc_state, last_telemetry, start_time)

            # Rate limiting
            # レート制限
            elapsed = time.monotonic() - loop_start
            if elapsed < interval:
                await asyncio.sleep(interval - elapsed)

    except KeyboardInterrupt:
        pass
    finally:
        # Restore terminal settings
        # ターミナル設定を復元
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        # Send neutral RC to stop
        # ニュートラルRCを送信して停止
        console.print("\n")
        console.info("Sending rc 0 0 0 0...", prefix="RC")
        try:
            await conn.cli.send_command("rc 0 0 0 0", timeout=2.0)
        except Exception:
            pass

        await conn.disconnect()
        console.success("Disconnected")

    return 0


def _handle_key(ch: str, state: dict, timers: dict, now: float) -> None:
    """Handle a single keypress.

    キー入力を処理する
    """
    spd = state["speed"]

    if ch in ('\x03',):  # Ctrl+C
        state["running"] = False
    elif ch == 'w':
        state["b"] = spd
        timers["b+"] = now
    elif ch == 's':
        state["b"] = -spd
        timers["b-"] = now
    elif ch == 'a':
        state["a"] = -spd
        timers["a-"] = now
    elif ch == 'd':
        state["a"] = spd
        timers["a+"] = now
    elif ch == 'q':
        state["d"] = -spd
        timers["d-"] = now
    elif ch == 'e':
        state["d"] = spd
        timers["d+"] = now
    elif ch == ' ':
        state["c"] = spd
        timers["c+"] = now
    elif ch == 'z':
        state["c"] = -spd
        timers["c-"] = now
    elif ch in ('+', '='):
        state["speed"] = min(100, spd + 10)
    elif ch in ('-', '_'):
        state["speed"] = max(10, spd - 10)
    elif ch == 'l':
        state["a"] = 0
        state["b"] = 0
        state["c"] = 0
        state["d"] = 0
        state["_land"] = True
    elif ch == 'x':
        state["a"] = 0
        state["b"] = 0
        state["c"] = 0
        state["d"] = 0
        state["_emergency"] = True


def _update_key_release(state: dict, timers: dict, now: float, timeout: float) -> None:
    """Zero out axes whose keys haven't been pressed recently.

    最近キーが押されていない軸をゼロにする
    """
    # Check roll (a axis)
    a_plus = timers.get("a+", 0)
    a_minus = timers.get("a-", 0)
    if now - max(a_plus, a_minus) > timeout:
        state["a"] = 0

    # Check pitch (b axis)
    b_plus = timers.get("b+", 0)
    b_minus = timers.get("b-", 0)
    if now - max(b_plus, b_minus) > timeout:
        state["b"] = 0

    # Check throttle (c axis)
    c_plus = timers.get("c+", 0)
    c_minus = timers.get("c-", 0)
    if now - max(c_plus, c_minus) > timeout:
        state["c"] = 0

    # Check yaw (d axis)
    d_plus = timers.get("d+", 0)
    d_minus = timers.get("d-", 0)
    if now - max(d_plus, d_minus) > timeout:
        state["d"] = 0


def _display_status(state: dict, telemetry: dict, start_time: float) -> None:
    """Display real-time status line (overwrites with \\r).

    リアルタイムステータス行を表示（\\rで上書き）
    """
    a, b, c, d = state["a"], state["b"], state["c"], state["d"]
    spd = state["speed"]
    elapsed = time.monotonic() - start_time

    # Telemetry values
    # テレメトリ値
    alt = 0.0
    tof = 0.0
    if telemetry:
        alt = telemetry.get("pos_z", 0.0)
        tof = telemetry.get("tof_bottom", 0.0)

    line = (
        f"  [RC] R={a:+4d} P={b:+4d} T={c:+4d} Y={d:+4d} "
        f"spd={spd:3d} | Alt: {alt:.2f}m | ToF: {tof:.2f}m | {elapsed:.1f}s"
    )

    # Pad to clear previous line
    # 前の行を消すためにパディング
    pad = max(0, state["last_line_len"] - len(line))
    sys.stdout.write(f"\r{line}{' ' * pad}")
    sys.stdout.flush()
    state["last_line_len"] = len(line)
