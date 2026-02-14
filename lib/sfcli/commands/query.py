"""
sf battery / height / tof / baro / attitude / acceleration / speed
Telemetry query commands

Send Tello-compatible query commands to StampFly via WiFi CLI and display results.
WiFi CLI経由でTello互換クエリコマンドを送信し、結果を表示します。

Commands:
    battery       - Query battery level (%)
    height        - Query ESKF estimated height (cm)
    tof           - Query ToF bottom distance (cm)
    baro          - Query barometric altitude (cm)
    attitude      - Query attitude angles (pitch, roll, yaw in deg)
    acceleration  - Query acceleration (x, y, z in cm/s²)
    speed         - Query configured speed (cm/s)
"""

import argparse
import asyncio

from ..utils import console
from ..utils.vehicle_connection import VehicleCLI, DEFAULT_HOST


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register query commands with CLI

    クエリコマンドをCLIに登録する
    """
    # Define query commands: (name, help, cli_cmd, format_func)
    queries = [
        ("battery", "Query battery level (%)", "battery?", _fmt_battery),
        ("height", "Query ESKF estimated height (cm)", "height?", _fmt_height),
        ("tof", "Query ToF bottom distance (cm)", "tof?", _fmt_tof),
        ("baro", "Query barometric altitude (cm)", "baro?", _fmt_baro),
        ("attitude", "Query attitude angles (deg)", "attitude?", _fmt_attitude),
        ("acceleration", "Query acceleration (cm/s²)", "acceleration?", _fmt_acceleration),
        ("speed", "Query configured speed (cm/s)", "speed?", _fmt_speed),
    ]

    for name, help_text, cli_cmd, fmt_func in queries:
        parser = subparsers.add_parser(
            name,
            help=help_text,
            description=f"{help_text}. WiFi CLI経由でクエリ送信。",
        )
        parser.add_argument(
            "--ip",
            default=DEFAULT_HOST,
            help=f"Vehicle IP address (default: {DEFAULT_HOST})",
        )
        parser.set_defaults(
            func=lambda args, c=cli_cmd, f=fmt_func: _run_query(args, c, f)
        )


# =============================================================================
# Format Functions
# =============================================================================

def _fmt_battery(raw: str) -> str:
    return f"Battery: {raw.strip()}%"


def _fmt_height(raw: str) -> str:
    return f"Height: {raw.strip()} cm"


def _fmt_tof(raw: str) -> str:
    return f"ToF: {raw.strip()} cm"


def _fmt_baro(raw: str) -> str:
    return f"Baro: {raw.strip()} cm"


def _fmt_attitude(raw: str) -> str:
    parts = raw.strip().split()
    if len(parts) == 3:
        return f"Attitude: P={parts[0]} R={parts[1]} Y={parts[2]} deg"
    return f"Attitude: {raw.strip()}"


def _fmt_acceleration(raw: str) -> str:
    parts = raw.strip().split()
    if len(parts) == 3:
        return f"Acceleration: X={parts[0]} Y={parts[1]} Z={parts[2]} cm/s²"
    return f"Acceleration: {raw.strip()}"


def _fmt_speed(raw: str) -> str:
    return f"Speed: {raw.strip()} cm/s"


# =============================================================================
# Query Execution
# =============================================================================

def _run_query(args: argparse.Namespace, cli_cmd: str, fmt_func) -> int:
    """Execute a query command via WiFi CLI.

    WiFi CLI経由でクエリコマンドを実行する
    """
    try:
        return asyncio.run(_async_query(args, cli_cmd, fmt_func))
    except KeyboardInterrupt:
        return 130


async def _async_query(args: argparse.Namespace, cli_cmd: str, fmt_func) -> int:
    """Async query execution: connect → send → display → disconnect.

    非同期クエリ実行: 接続 → 送信 → 表示 → 切断
    """
    cli = VehicleCLI()

    try:
        # Connect to vehicle CLI
        # 機体CLIに接続
        try:
            await cli.connect(args.ip, timeout=5.0)
        except OSError:
            console.error("Vehicle not reachable. Connect to StampFly WiFi AP first.")
            return 1

        # Send query command
        # クエリコマンドを送信
        response = await cli.send_command(cli_cmd, timeout=3.0)

        # Format and display
        # フォーマットして表示
        console.success(fmt_func(response))

        await cli.disconnect()
        return 0

    except ConnectionError as e:
        console.error(f"Connection lost: {e}")
        return 1
    except Exception as e:
        console.error(f"Query failed: {e}")
        try:
            await cli.disconnect()
        except Exception:
            pass
        return 1
