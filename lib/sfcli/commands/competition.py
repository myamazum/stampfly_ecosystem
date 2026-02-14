"""
sf competition - Workshop competition tools

Tools for the StampFly workshop competition day (Day 5).
StampFly 勉強会 競技会（Day 5）のためのツール。

Subcommands:
    timer  - Time trial stopwatch
    hover  - Hovering stability test (altitude sigma measurement)
    score  - Display competition scores
"""

import argparse
import asyncio
import json
import math
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..utils import console, paths

COMMAND_NAME = "competition"
COMMAND_HELP = "Workshop competition tools"

# Score storage
SCORES_FILE = ".sf/competition_scores.json"


def _scores_path() -> Path:
    """Get scores file path"""
    return paths.root() / SCORES_FILE


def _load_scores() -> dict:
    """Load competition scores from file"""
    path = _scores_path()
    if path.exists():
        return json.loads(path.read_text())
    return {"teams": {}}


def _save_scores(scores: dict) -> None:
    """Save competition scores to file"""
    path = _scores_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(scores, indent=2, ensure_ascii=False))


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register command with CLI"""
    parser = subparsers.add_parser(
        COMMAND_NAME,
        help=COMMAND_HELP,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    comp_subparsers = parser.add_subparsers(
        dest="comp_command",
        title="subcommands",
        metavar="<subcommand>",
    )

    # --- timer ---
    timer_parser = comp_subparsers.add_parser(
        "timer",
        help="Time trial stopwatch",
        description="Stopwatch for time trial competition. Press Enter to record laps.",
    )
    timer_parser.add_argument(
        "--team",
        default=None,
        help="Team name for score recording",
    )
    timer_parser.add_argument(
        "--gates",
        type=int,
        default=4,
        help="Number of gates (default: 4)",
    )
    timer_parser.set_defaults(func=run_timer)

    # --- hover ---
    hover_parser = comp_subparsers.add_parser(
        "hover",
        help="Hovering stability test",
        description="Measure altitude stability during hover (10-second window).",
    )
    hover_parser.add_argument(
        "--team",
        default=None,
        help="Team name for score recording",
    )
    hover_parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Test duration in seconds (default: 10.0)",
    )
    hover_parser.add_argument(
        "--target",
        type=float,
        default=0.3,
        help="Target altitude in meters (default: 0.3)",
    )
    hover_parser.add_argument(
        "--ip",
        default="192.168.4.1",
        help="StampFly WiFi IP (default: 192.168.4.1)",
    )
    hover_parser.set_defaults(func=run_hover)

    # --- score ---
    score_parser = comp_subparsers.add_parser(
        "score",
        help="Display competition scores",
        description="Show competition scores and rankings.",
    )
    score_parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all scores",
    )
    score_parser.set_defaults(func=run_score)

    # Default: show help
    parser.set_defaults(func=lambda args: (parser.print_help(), 0)[1])


def run_timer(args: argparse.Namespace) -> int:
    """Time trial stopwatch"""
    console.header("Time Trial Timer")
    console.print()
    console.print("  Controls:")
    console.print("    Enter  - Record lap / Start timer")
    console.print("    q      - Stop and save")
    console.print()

    if args.team:
        console.info(f"Team: {args.team}")

    console.print(f"  Gates: {args.gates}")
    console.print()
    console.info("Press Enter to START...")

    try:
        input()
    except (EOFError, KeyboardInterrupt):
        return 0

    start_time = time.monotonic()
    laps: List[float] = []

    console.success("STARTED!")
    console.print()

    for gate in range(1, args.gates + 1):
        prompt = f"  Gate {gate}/{args.gates} - Press Enter..."
        try:
            console.print(prompt, end="")
            line = input()
            if line.strip().lower() == "q":
                break
        except (EOFError, KeyboardInterrupt):
            break

        lap_time = time.monotonic() - start_time
        laps.append(lap_time)
        console.print(f"    Lap {gate}: {lap_time:.3f}s")

    total_time = time.monotonic() - start_time

    console.print()
    console.header("Results")
    console.print()
    console.print(f"  Total time: {total_time:.3f}s")
    console.print(f"  Gates cleared: {len(laps)}/{args.gates}")

    if len(laps) > 1:
        for i, lap in enumerate(laps):
            if i == 0:
                console.print(f"    Gate {i+1}: {lap:.3f}s")
            else:
                console.print(f"    Gate {i+1}: {lap:.3f}s (+{lap - laps[i-1]:.3f}s)")

    # Save score if team specified
    if args.team:
        scores = _load_scores()
        if args.team not in scores["teams"]:
            scores["teams"][args.team] = {}
        scores["teams"][args.team]["timer"] = {
            "total_time": round(total_time, 3),
            "gates_cleared": len(laps),
            "gates_total": args.gates,
            "laps": [round(t, 3) for t in laps],
            "timestamp": datetime.now().isoformat(),
        }
        _save_scores(scores)
        console.success(f"Score saved for team: {args.team}")

    return 0


def run_hover(args: argparse.Namespace) -> int:
    """Hovering stability test via WiFi telemetry"""
    try:
        import websockets
    except ImportError:
        console.error("websockets package required: pip install websockets")
        return 1

    console.header("Hovering Stability Test")
    console.print()
    console.print(f"  Target altitude: {args.target:.2f} m")
    console.print(f"  Test duration:   {args.duration:.1f} s")
    console.print(f"  StampFly IP:     {args.ip}")
    console.print()

    async def _collect_altitude():
        """Collect altitude data via WebSocket"""
        uri = f"ws://{args.ip}/ws"
        altitudes: List[float] = []

        console.info(f"Connecting to {uri}...")

        try:
            async with websockets.connect(uri, open_timeout=5) as ws:
                console.success("Connected! Collecting altitude data...")
                console.print()

                start = time.monotonic()
                while time.monotonic() - start < args.duration:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(msg)

                        # Extract altitude from telemetry
                        # Support multiple field names
                        alt = None
                        for key in ("alt", "altitude", "pos_z", "z"):
                            if key in data:
                                alt = float(data[key])
                                break

                        if alt is not None:
                            altitudes.append(alt)
                            elapsed = time.monotonic() - start
                            console.print(
                                f"\r  [{elapsed:5.1f}s] alt={alt:6.3f}m  "
                                f"samples={len(altitudes)}",
                                end="",
                            )

                    except asyncio.TimeoutError:
                        continue
                    except json.JSONDecodeError:
                        continue

                console.print()

        except (ConnectionRefusedError, OSError) as e:
            console.error(f"Connection failed: {e}")
            console.print("  Make sure StampFly WiFi AP is connected")
            return None

        return altitudes

    # Run async collection
    altitudes = asyncio.run(_collect_altitude())

    if altitudes is None:
        return 1

    if len(altitudes) < 10:
        console.error(f"Not enough data points ({len(altitudes)}). Need at least 10.")
        return 1

    # Calculate statistics
    mean_alt = sum(altitudes) / len(altitudes)
    variance = sum((a - mean_alt) ** 2 for a in altitudes) / len(altitudes)
    sigma = math.sqrt(variance)
    min_alt = min(altitudes)
    max_alt = max(altitudes)
    error_from_target = abs(mean_alt - args.target)

    console.print()
    console.header("Hover Test Results")
    console.print()
    console.print(f"  Samples:          {len(altitudes)}")
    console.print(f"  Target altitude:  {args.target:.3f} m")
    console.print(f"  Mean altitude:    {mean_alt:.3f} m")
    console.print(f"  Altitude sigma:   {sigma:.4f} m ({sigma*100:.2f} cm)")
    console.print(f"  Min / Max:        {min_alt:.3f} / {max_alt:.3f} m")
    console.print(f"  Range:            {(max_alt - min_alt)*100:.2f} cm")
    console.print(f"  Error from target: {error_from_target*100:.2f} cm")
    console.print()

    # Rating
    if sigma < 0.01:
        rating = "Excellent"
    elif sigma < 0.02:
        rating = "Good"
    elif sigma < 0.05:
        rating = "Fair"
    else:
        rating = "Needs improvement"
    console.info(f"Rating: {rating} (sigma={sigma*100:.2f} cm)")

    # Save score if team specified
    if args.team:
        scores = _load_scores()
        if args.team not in scores["teams"]:
            scores["teams"][args.team] = {}
        scores["teams"][args.team]["hover"] = {
            "mean_altitude": round(mean_alt, 4),
            "sigma": round(sigma, 4),
            "target": args.target,
            "error": round(error_from_target, 4),
            "min": round(min_alt, 4),
            "max": round(max_alt, 4),
            "samples": len(altitudes),
            "duration": args.duration,
            "rating": rating,
            "timestamp": datetime.now().isoformat(),
        }
        _save_scores(scores)
        console.success(f"Score saved for team: {args.team}")

    return 0


def run_score(args: argparse.Namespace) -> int:
    """Display competition scores"""
    if args.clear:
        path = _scores_path()
        if path.exists():
            path.unlink()
            console.success("Scores cleared")
        else:
            console.info("No scores to clear")
        return 0

    scores = _load_scores()

    if not scores["teams"]:
        console.info("No competition scores recorded yet")
        console.print("  Use 'sf competition timer --team <name>' to start")
        return 0

    console.header("Competition Scores")
    console.print()

    # Timer rankings
    timer_teams = []
    for team, data in scores["teams"].items():
        if "timer" in data:
            timer_teams.append((team, data["timer"]))

    if timer_teams:
        # Sort by total time (lower is better)
        timer_teams.sort(key=lambda x: x[1]["total_time"])

        console.info("Time Trial Rankings:")
        console.print()
        for rank, (team, t) in enumerate(timer_teams, 1):
            gates = f"{t['gates_cleared']}/{t['gates_total']}"
            console.print(f"  {rank}. {team:20s}  {t['total_time']:8.3f}s  gates: {gates}")
        console.print()

    # Hover rankings
    hover_teams = []
    for team, data in scores["teams"].items():
        if "hover" in data:
            hover_teams.append((team, data["hover"]))

    if hover_teams:
        # Sort by sigma (lower is better)
        hover_teams.sort(key=lambda x: x[1]["sigma"])

        console.info("Hover Stability Rankings:")
        console.print()
        for rank, (team, h) in enumerate(hover_teams, 1):
            sigma_cm = h["sigma"] * 100
            console.print(
                f"  {rank}. {team:20s}  sigma={sigma_cm:5.2f}cm  "
                f"mean={h['mean_altitude']:.3f}m  [{h['rating']}]"
            )
        console.print()

    return 0
