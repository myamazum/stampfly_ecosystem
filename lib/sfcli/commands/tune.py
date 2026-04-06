"""
sf tune - Drone tuning commands
ドローンチューニングコマンド

Subcommands:
    gui       - Launch interactive tuning dashboard
    auto      - Run man-in-the-loop auto-tuning
    eskf      - ESKF parameter sweep (log replay)
    position  - Position PID parameter sweep (simulation)
    params    - Show current parameters from config.hpp
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ..utils import console, paths

COMMAND_NAME = "tune"
COMMAND_HELP = "Drone parameter tuning"


def register(subparsers) -> None:
    parser = subparsers.add_parser(COMMAND_NAME, help=COMMAND_HELP)
    sub = parser.add_subparsers(dest="tune_cmd")

    # gui
    gui_parser = sub.add_parser("gui", help="Launch tuning dashboard (Streamlit)")
    gui_parser.add_argument("--port", type=int, default=8501, help="Port (default: 8501)")

    # auto
    auto_parser = sub.add_parser("auto", help="Man-in-the-loop auto-tuning")
    auto_parser.add_argument("--phase", choices=['eskf', 'rate', 'attitude', 'altitude', 'position'],
                            help="Run only this phase")

    # eskf
    eskf_parser = sub.add_parser("eskf", help="ESKF parameter sweep")
    eskf_parser.add_argument("--log", required=True, help="Log file path")
    eskf_parser.add_argument("--top", type=int, default=10, help="Show top N results")

    # position
    pos_parser = sub.add_parser("position", help="Position PID parameter sweep")
    pos_parser.add_argument("--disturbance", type=float, default=0.3, help="Step disturbance [m]")
    pos_parser.add_argument("--top", type=int, default=10, help="Show top N results")

    # params
    sub.add_parser("params", help="Show current config.hpp parameters")

    parser.set_defaults(func=run)


def run(args) -> int:
    repo_root = paths.root()
    tools_dir = repo_root / "tools"

    if args.tune_cmd == "gui":
        return _run_gui(repo_root, args.port)
    elif args.tune_cmd == "auto":
        return _run_auto(repo_root, args.phase if hasattr(args, 'phase') else None)
    elif args.tune_cmd == "eskf":
        return _run_eskf_sweep(repo_root, args.log, args.top)
    elif args.tune_cmd == "position":
        return _run_position_sweep(repo_root, args.disturbance, args.top)
    elif args.tune_cmd == "params":
        return _run_params(repo_root)
    else:
        # Show help when no subcommand given
        # サブコマンド未指定時はヘルプを表示
        print("sf tune - Drone parameter tuning")
        print()
        print("Subcommands:")
        print("  gui        Launch interactive tuning dashboard (Streamlit)")
        print("  auto       Man-in-the-loop auto-tuning session")
        print("  eskf       ESKF parameter sweep (log replay)")
        print("  position   Position PID parameter sweep (simulation)")
        print("  params     Show current config.hpp parameters")
        print()
        print("Examples:")
        print("  sf tune gui")
        print("  sf tune auto --phase eskf")
        print("  sf tune eskf --log logs/latest.jsonl")
        print("  sf tune position --disturbance 0.3")
        print("  sf tune params")
        return 0


def _run_gui(repo_root: Path, port: int) -> int:
    """Launch Streamlit dashboard."""
    dashboard = repo_root / "tools" / "tuning" / "dashboard.py"
    if not dashboard.exists():
        console.error(f"Dashboard not found: {dashboard}")
        return 1

    console.info(f"Launching tuning dashboard on port {port}...")
    console.info(f"Open http://localhost:{port} in browser")

    try:
        result = subprocess.run(
            [sys.executable, "-m", "streamlit", "run", str(dashboard),
             "--server.port", str(port),
             "--server.headless", "true"],
            cwd=str(repo_root),
        )
        return result.returncode
    except KeyboardInterrupt:
        console.info("Dashboard stopped.")
        return 0


def _run_auto(repo_root: Path, phase: Optional[str]) -> int:
    """Run auto-tuning orchestrator."""
    sys.path.insert(0, str(repo_root / "tools"))
    from tuning.orchestrator import TuningOrchestrator
    import numpy as np

    orch = TuningOrchestrator(repo_root=str(repo_root))
    orch.run_cli(phase_filter=phase)
    return 0


def _run_eskf_sweep(repo_root: Path, log_path: str, top_n: int) -> int:
    """Run ESKF parameter sweep."""
    sys.path.insert(0, str(repo_root / "tools"))
    from tuning.sweep import sweep_eskf, print_results

    # Resolve log path
    log = Path(log_path)
    if not log.exists():
        log = repo_root / "logs" / log_path
    if not log.exists():
        console.error(f"Log file not found: {log_path}")
        return 1

    console.info(f"ESKF sweep with: {log}")
    results = sweep_eskf(str(log))
    print_results(results, top_n)
    return 0


def _run_position_sweep(repo_root: Path, disturbance: float, top_n: int) -> int:
    """Run position PID sweep."""
    sys.path.insert(0, str(repo_root / "tools"))
    from tuning.sweep import sweep_position, print_results

    console.info(f"Position PID sweep (disturbance={disturbance}m)")
    results = sweep_position(disturbance=disturbance)
    print_results(results, top_n)
    return 0


def _run_params(repo_root: Path) -> int:
    """Show current parameters."""
    sys.path.insert(0, str(repo_root / "tools"))
    from common.config_parser import load_config, print_config

    config = load_config()
    print_config(config)
    return 0
