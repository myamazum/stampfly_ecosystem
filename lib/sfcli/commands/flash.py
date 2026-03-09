"""
sf flash - Flash firmware to device

Flashes vehicle or controller firmware to connected device.
接続されたデバイスにファームウェアを書き込みます。
"""

import argparse
import subprocess
from pathlib import Path
from ..utils import console, paths, platform, espidf

COMMAND_NAME = "flash"
COMMAND_HELP = "Flash firmware to device"


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register command with CLI"""
    parser = subparsers.add_parser(
        COMMAND_NAME,
        help=COMMAND_HELP,
        description=__doc__,
    )
    parser.add_argument(
        "target",
        nargs="?",
        default="vehicle",
        help="Target to flash (default: vehicle). Use 'sf app list' to see available targets.",
    )
    parser.add_argument(
        "-p", "--port",
        default=None,
        help="Serial port (auto-detect if not specified)",
    )
    parser.add_argument(
        "-b", "--baud",
        type=int,
        default=460800,
        help="Baud rate (default: 460800)",
    )
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Flash factory legacy firmware (PlatformIO merged binary)",
    )
    parser.add_argument(
        "--build",
        action="store_true",
        help="Build before flashing",
    )
    parser.add_argument(
        "-m", "--monitor",
        action="store_true",
        help="Start monitor after flashing",
    )
    parser.set_defaults(func=run)


def _flash_legacy(args: argparse.Namespace) -> int:
    """Flash legacy factory firmware (PlatformIO merged binary)
    レガシーファクトリーファームウェアを書き込む"""
    legacy_bin = paths.firmware() / "legacy" / "merged.bin"
    if not legacy_bin.exists():
        console.error(f"Legacy binary not found: {legacy_bin}")
        return 1

    # Detect or use specified port
    # シリアルポートの検出または指定ポートの使用
    port = args.port
    if not port:
        port = platform.default_serial_port()
        if not port:
            console.error("No serial port detected. Please specify with -p/--port")
            available = platform.serial_ports()
            if available:
                console.print("Available ports:")
                for p in available:
                    console.print(f"  {p}")
            return 1
        console.info(f"Auto-detected port: {port}")

    # Check ESP-IDF for esptool
    idf_path = platform.esp_idf_path()
    if not idf_path:
        console.error("ESP-IDF not found. esptool.py is required.")
        return 1

    env = espidf.prepare_idf_env(idf_path)

    # Use esptool.py to write merged binary at offset 0x0
    # esptool.py でマージ済みバイナリをオフセット0x0に書き込む
    cmd = [
        "python", "-m", "esptool",
        "--chip", "esp32s3",
        "--port", port,
        "--baud", str(args.baud),
        "write_flash", "0x0", str(legacy_bin),
    ]

    console.info("Flashing legacy factory firmware...")
    console.print(f"  Binary: {legacy_bin}")
    console.print(f"  Port:   {port}")
    console.print(f"  Baud:   {args.baud}")
    console.print()

    result = subprocess.run(cmd, env=env)

    if result.returncode == 0:
        console.print()
        console.success("Legacy firmware flashed successfully")
        return 0
    else:
        console.print()
        console.error("Legacy firmware flash failed")
        return result.returncode


def run(args: argparse.Namespace) -> int:
    """Execute flash command"""
    # Legacy firmware shortcut
    # レガシーファームウェアの書き込み
    if args.legacy:
        return _flash_legacy(args)

    # Determine target directory
    # 動的ターゲット検出: firmware/ 配下の CMakeLists.txt を持つディレクトリ
    target_dir = paths.firmware_target_dir(args.target)

    if not target_dir.exists():
        console.error(f"Target directory not found: {target_dir}")
        return 1

    # Check ESP-IDF
    idf_path = platform.esp_idf_path()
    if not idf_path:
        console.error("ESP-IDF not found. Please install ESP-IDF first.")
        return 1

    # Detect or use specified port
    port = args.port
    if not port:
        port = platform.default_serial_port()
        if not port:
            console.error("No serial port detected. Please specify with -p/--port")
            available = platform.serial_ports()
            if available:
                console.print("Available ports:")
                for p in available:
                    console.print(f"  {p}")
            return 1
        console.info(f"Auto-detected port: {port}")

    # Build if requested
    if args.build:
        console.info("Building before flash...")
        from . import build as build_cmd
        build_args = argparse.Namespace(
            target=args.target,
            clean=False,
            jobs=None,
            verbose=False,
        )
        result = build_cmd.run(build_args)
        if result != 0:
            console.error("Build failed, aborting flash")
            return result
        console.print()

    # Prepare environment (uses ESP-IDF's Python, not our venv)
    env = espidf.prepare_idf_env(idf_path)

    # Flash command
    cmd = espidf.idf_command(["-p", port, "-b", str(args.baud)])

    if args.monitor:
        cmd.append("flash")
        cmd.append("monitor")
    else:
        cmd.append("flash")

    console.info(f"Flashing {args.target} firmware...")
    console.print(f"  Port: {port}")
    console.print(f"  Baud: {args.baud}")
    console.print()

    # Execute flash
    result = subprocess.run(cmd, cwd=target_dir, env=env)

    if result.returncode == 0:
        if not args.monitor:
            console.print()
            console.success(f"Flash successful: {args.target}")
        return 0
    else:
        console.print()
        console.error(f"Flash failed: {args.target}")
        return result.returncode
