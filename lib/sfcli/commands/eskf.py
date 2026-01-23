"""
sf eskf - ESKF simulation and parameter tuning commands
sf eskf - ESKFシミュレーション・パラメータチューニングコマンド

Unix philosophy: Small tools that do one thing well and work together via pipes.

Subcommands:
    replay    - Replay ESKF from sensor log (CSV input -> state output)
    compare   - Compare estimated vs reference states (error metrics)
    params    - Parameter management (show, convert, diff)
    tune      - Parameter optimization (SA, GD, Grid)
    plot      - Visualization (matplotlib)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, List

import yaml

from ..utils import console, paths

COMMAND_NAME = "eskf"
COMMAND_HELP = "ESKF simulation and parameter tuning"


def register(subparsers: argparse._SubParsersAction) -> None:
    """Register command with CLI"""
    parser = subparsers.add_parser(
        COMMAND_NAME,
        help=COMMAND_HELP,
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Create sub-subparsers for eskf subcommands
    eskf_subparsers = parser.add_subparsers(
        dest="eskf_command",
        title="subcommands",
        metavar="<subcommand>",
    )

    # --- replay ---
    replay_parser = eskf_subparsers.add_parser(
        "replay",
        help="Replay ESKF from sensor log",
        description="Replay ESKF filter from logged sensor data. Output estimated states.",
    )
    replay_parser.add_argument(
        "input",
        nargs="?",
        help="Input CSV file (default: stdin)",
    )
    replay_parser.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)",
    )
    replay_parser.add_argument(
        "-p", "--params",
        help="Parameter file (YAML/JSON)",
    )
    replay_parser.add_argument(
        "-f", "--format",
        choices=["csv", "jsonl"],
        default="csv",
        help="Output format (default: csv)",
    )
    replay_parser.add_argument(
        "--time-range",
        nargs=2,
        type=float,
        metavar=("START", "END"),
        help="Time range to process (seconds)",
    )
    replay_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    replay_parser.set_defaults(func=run_replay)

    # --- compare ---
    compare_parser = eskf_subparsers.add_parser(
        "compare",
        help="Compare estimated vs reference states",
        description="Compare two state files and compute error metrics.",
    )
    compare_parser.add_argument(
        "input",
        nargs="?",
        help="Estimated states file (default: stdin)",
    )
    compare_parser.add_argument(
        "-r", "--ref",
        required=True,
        help="Reference file (required)",
    )
    compare_parser.add_argument(
        "--detail",
        action="store_true",
        help="Output detailed time-series errors",
    )
    compare_parser.add_argument(
        "--format",
        choices=["json", "csv", "text"],
        default="text",
        help="Output format (default: text)",
    )
    compare_parser.set_defaults(func=run_compare)

    # --- params ---
    params_parser = eskf_subparsers.add_parser(
        "params",
        help="Parameter management",
        description="Show, convert, or diff ESKF parameters.",
    )
    params_subparsers = params_parser.add_subparsers(
        dest="params_command",
        title="params subcommands",
        metavar="<action>",
    )

    # params show
    params_show = params_subparsers.add_parser(
        "show",
        help="Show default or loaded parameters",
    )
    params_show.add_argument(
        "file",
        nargs="?",
        help="Parameter file to show (default: show defaults)",
    )
    params_show.add_argument(
        "--format",
        choices=["yaml", "json"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    params_show.set_defaults(func=run_params_show)

    # params convert
    params_convert = params_subparsers.add_parser(
        "convert",
        help="Convert parameter file format",
    )
    params_convert.add_argument(
        "input",
        help="Input parameter file",
    )
    params_convert.add_argument(
        "-o", "--output",
        help="Output file (default: stdout)",
    )
    params_convert.set_defaults(func=run_params_convert)

    # params diff
    params_diff = params_subparsers.add_parser(
        "diff",
        help="Compare two parameter files",
    )
    params_diff.add_argument(
        "file1",
        help="First parameter file",
    )
    params_diff.add_argument(
        "file2",
        help="Second parameter file",
    )
    params_diff.set_defaults(func=run_params_diff)

    params_parser.set_defaults(func=run_params_help)

    # --- tune ---
    tune_parser = eskf_subparsers.add_parser(
        "tune",
        help="Optimize ESKF parameters",
        description="Optimize Q/R parameters from flight logs using various methods.",
    )
    tune_parser.add_argument(
        "inputs",
        nargs="+",
        help="Input log files (.csv)",
    )
    tune_parser.add_argument(
        "-o", "--output",
        help="Output parameter file (default: stdout)",
    )
    tune_parser.add_argument(
        "-m", "--method",
        choices=["sa", "gd", "grid"],
        default="sa",
        help="Optimization method: sa (Simulated Annealing), gd (Gradient Descent), grid (Grid Search)",
    )
    tune_parser.add_argument(
        "--iter",
        type=int,
        help="Maximum iterations (default: 500 for SA, 80 for GD)",
    )
    tune_parser.add_argument(
        "--cost",
        choices=["rmse", "mae", "position"],
        default="rmse",
        help="Cost function (default: rmse)",
    )
    tune_parser.add_argument(
        "--range",
        help="Parameter search range file (YAML)",
    )
    tune_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output",
    )
    tune_parser.set_defaults(func=run_tune)

    # --- plot ---
    plot_parser = eskf_subparsers.add_parser(
        "plot",
        help="Visualize ESKF states",
        description="Visualize estimated states with optional overlay.",
    )
    plot_parser.add_argument(
        "input",
        nargs="?",
        help="Input file (default: stdin)",
    )
    plot_parser.add_argument(
        "-o", "--output",
        help="Output image file (default: show interactive)",
    )
    plot_parser.add_argument(
        "--overlay",
        help="Overlay reference file",
    )
    plot_parser.add_argument(
        "--mode",
        choices=["all", "position", "velocity", "attitude"],
        default="all",
        help="Display mode (default: all)",
    )
    plot_parser.set_defaults(func=run_plot)

    parser.set_defaults(func=run_help)


def run_help(args: argparse.Namespace) -> int:
    """Show help when no subcommand specified"""
    console.print("Usage: sf eskf <subcommand> [options]")
    console.print()
    console.print("Subcommands:")
    console.print("  replay    Replay ESKF from sensor log")
    console.print("  compare   Compare estimated vs reference states")
    console.print("  params    Parameter management")
    console.print("  tune      Parameter optimization")
    console.print("  plot      Visualization")
    console.print()
    console.print("Run 'sf eskf <subcommand> --help' for details.")
    console.print()
    console.print("Pipeline examples:")
    console.print("  sf eskf replay flight.csv --params tuned.yaml | sf eskf compare --ref flight.csv")
    console.print("  sf eskf tune flight.csv -o optimized.yaml")
    console.print("  sf eskf replay flight.csv | sf eskf plot --overlay flight.csv -o result.png")
    return 0


def run_replay(args: argparse.Namespace) -> int:
    """Run ESKF replay"""
    try:
        # Add eskf_sim to path
        sys.path.insert(0, str(paths.root() / "tools"))
        from eskf_sim import ESKF, ESKFConfig, load_csv
        from eskf_sim.loader import STATE_OUTPUT_COLUMNS, state_to_row, write_csv_header, write_csv_row
    except ImportError as e:
        console.error(f"Failed to import eskf_sim: {e}")
        return 1
    finally:
        sys.path.pop(0)

    # Load parameters
    config = ESKFConfig()
    if args.params:
        config = _load_params(args.params, ESKFConfig)
        if config is None:
            return 1

    # Load input
    if args.input:
        if not Path(args.input).exists():
            console.error(f"Input file not found: {args.input}")
            return 1
        if not args.quiet:
            console.info(f"Loading: {args.input}")
        log_data = load_csv(args.input)
    else:
        console.error("stdin input not yet supported. Please specify input file.")
        return 1

    if not args.quiet:
        console.info(f"Format: {log_data.format}")
        console.info(f"Samples: {len(log_data)}, Duration: {log_data.duration_s:.2f}s")

    # Initialize ESKF
    eskf = ESKF(config)
    eskf.init()

    # Determine output
    out_file = sys.stdout
    if args.output:
        out_file = open(args.output, 'w')

    # Write header
    if args.format == 'csv':
        write_csv_header(out_file, STATE_OUTPUT_COLUMNS)

    # Process samples
    import numpy as np
    prev_timestamp_us = None

    for i, sample in enumerate(log_data.samples):
        # Apply time range filter
        if args.time_range:
            t_s = (sample.timestamp_us - log_data.samples[0].timestamp_us) / 1e6
            if t_s < args.time_range[0] or t_s > args.time_range[1]:
                continue

        # Compute dt
        if prev_timestamp_us is None:
            dt = 0.0025  # Default 400Hz
        else:
            dt = (sample.timestamp_us - prev_timestamp_us) / 1e6
        prev_timestamp_us = sample.timestamp_us

        # Skip if dt is invalid
        if dt <= 0 or dt > 0.1:
            continue

        # ESKF prediction
        eskf.predict(sample.accel, sample.gyro, dt)

        # Measurement updates
        if sample.tof_distance is not None and sample.tof_distance > 0.02:
            eskf.update_tof(sample.tof_distance)

        if sample.baro_altitude is not None:
            eskf.update_baro(sample.baro_altitude)

        if sample.flow_dx is not None and sample.tof_distance is not None:
            eskf.update_flow_raw(
                sample.flow_dx,
                sample.flow_dy or 0,
                sample.tof_distance,
                dt,
                sample.gyro[0],
                sample.gyro[1],
            )

        # Attitude correction from accelerometer
        eskf.update_accel_attitude(sample.accel)

        # Output state
        state = eskf.get_state()
        row = state_to_row(sample.timestamp_us, state)

        if args.format == 'csv':
            write_csv_row(out_file, row, STATE_OUTPUT_COLUMNS)
        else:  # jsonl
            out_file.write(json.dumps(row) + '\n')

    if args.output:
        out_file.close()
        if not args.quiet:
            console.success(f"Output written to: {args.output}")

    return 0


def run_compare(args: argparse.Namespace) -> int:
    """Compare estimated vs reference states"""
    try:
        sys.path.insert(0, str(paths.root() / "tools"))
        from eskf_sim import load_csv, compute_metrics
    except ImportError as e:
        console.error(f"Failed to import eskf_sim: {e}")
        return 1
    finally:
        sys.path.pop(0)

    # Load reference
    if not Path(args.ref).exists():
        console.error(f"Reference file not found: {args.ref}")
        return 1

    ref_data = load_csv(args.ref)

    # Load estimated
    if args.input:
        if not Path(args.input).exists():
            console.error(f"Input file not found: {args.input}")
            return 1
        est_data = load_csv(args.input)
    else:
        console.error("stdin input not yet supported. Please specify input file.")
        return 1

    # Build state dictionaries
    est_states = []
    ref_states = []
    timestamps = []

    for sample in est_data.samples:
        if sample.eskf_position is not None:
            est_states.append({
                'position': sample.eskf_position.tolist(),
                'velocity': sample.eskf_velocity.tolist() if sample.eskf_velocity is not None else [0, 0, 0],
                'euler_deg': _quat_to_euler_deg(sample.eskf_quat) if sample.eskf_quat is not None else [0, 0, 0],
            })
        else:
            # Try to parse from CSV columns (for replay output)
            continue
        timestamps.append(sample.timestamp_us)

    for sample in ref_data.samples:
        if sample.eskf_position is not None:
            ref_states.append({
                'position': sample.eskf_position.tolist(),
                'velocity': sample.eskf_velocity.tolist() if sample.eskf_velocity is not None else [0, 0, 0],
                'euler_deg': _quat_to_euler_deg(sample.eskf_quat) if sample.eskf_quat is not None else [0, 0, 0],
            })

    # Compute metrics
    result, ts_error = compute_metrics(est_states, ref_states, timestamps)

    # Output
    if args.format == 'json':
        print(result.to_json())
    elif args.format == 'csv' and args.detail and ts_error:
        # CSV detail output
        import csv
        writer = csv.DictWriter(sys.stdout, fieldnames=ts_error.to_csv_rows()[0].keys())
        writer.writeheader()
        for row in ts_error.to_csv_rows():
            writer.writerow(row)
    else:
        result.print_summary()

    return 0


def run_params_help(args: argparse.Namespace) -> int:
    """Show params help"""
    console.print("Usage: sf eskf params <action> [options]")
    console.print()
    console.print("Actions:")
    console.print("  show      Show default or loaded parameters")
    console.print("  convert   Convert parameter file format")
    console.print("  diff      Compare two parameter files")
    return 0


def run_params_show(args: argparse.Namespace) -> int:
    """Show parameters"""
    try:
        sys.path.insert(0, str(paths.root() / "tools"))
        from eskf_sim import ESKFConfig
    except ImportError as e:
        console.error(f"Failed to import eskf_sim: {e}")
        return 1
    finally:
        sys.path.pop(0)

    if args.file:
        config = _load_params(args.file, ESKFConfig)
        if config is None:
            return 1
    else:
        config = ESKFConfig()

    params_dict = config.to_dict()

    if args.format == 'yaml':
        print(yaml.dump(params_dict, default_flow_style=False, sort_keys=False))
    else:
        print(json.dumps(params_dict, indent=2))

    return 0


def run_params_convert(args: argparse.Namespace) -> int:
    """Convert parameter file format"""
    if not Path(args.input).exists():
        console.error(f"File not found: {args.input}")
        return 1

    # Load
    with open(args.input, 'r') as f:
        if args.input.endswith('.json'):
            data = json.load(f)
        else:
            data = yaml.safe_load(f)

    # Output
    out_format = 'yaml'
    if args.output and args.output.endswith('.json'):
        out_format = 'json'

    if args.output:
        with open(args.output, 'w') as f:
            if out_format == 'json':
                json.dump(data, f, indent=2)
            else:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        console.success(f"Converted to: {args.output}")
    else:
        if out_format == 'json':
            print(json.dumps(data, indent=2))
        else:
            print(yaml.dump(data, default_flow_style=False, sort_keys=False))

    return 0


def run_params_diff(args: argparse.Namespace) -> int:
    """Compare two parameter files"""
    for f in [args.file1, args.file2]:
        if not Path(f).exists():
            console.error(f"File not found: {f}")
            return 1

    # Load both files
    def load_file(filepath):
        with open(filepath, 'r') as f:
            if filepath.endswith('.json'):
                return json.load(f)
            return yaml.safe_load(f)

    data1 = load_file(args.file1)
    data2 = load_file(args.file2)

    # Flatten and compare
    flat1 = _flatten_dict(data1)
    flat2 = _flatten_dict(data2)

    all_keys = set(flat1.keys()) | set(flat2.keys())
    has_diff = False

    console.print(f"Comparing: {args.file1} vs {args.file2}")
    console.print()

    for key in sorted(all_keys):
        v1 = flat1.get(key)
        v2 = flat2.get(key)

        if v1 != v2:
            has_diff = True
            if v1 is None:
                console.print(f"  + {key}: {v2}")
            elif v2 is None:
                console.print(f"  - {key}: {v1}")
            else:
                console.print(f"  ~ {key}: {v1} -> {v2}")

    if not has_diff:
        console.print("  No differences found.")

    return 0


def run_tune(args: argparse.Namespace) -> int:
    """Run parameter optimization"""
    try:
        sys.path.insert(0, str(paths.root() / "tools"))
        from eskf_sim.optimizer import ESKFOptimizer
    except ImportError as e:
        console.error(f"Failed to import optimizer: {e}")
        console.print("Note: scipy is required for optimization.")
        return 1
    finally:
        sys.path.pop(0)

    # Validate inputs
    for f in args.inputs:
        if not Path(f).exists():
            console.error(f"File not found: {f}")
            return 1

    # Default iterations
    max_iter = args.iter
    if max_iter is None:
        max_iter = 500 if args.method == 'sa' else 80

    # Create optimizer
    optimizer = ESKFOptimizer(args.inputs, quiet=args.quiet)

    # Run optimization
    if args.method == 'sa':
        best_params = optimizer.optimize_sa(max_iter)
    elif args.method == 'gd':
        best_params = optimizer.optimize_gd(max_iter)
    else:
        console.error("Grid search not yet implemented")
        return 1

    if best_params is None:
        console.error("Optimization failed")
        return 1

    # Output results
    if not args.quiet:
        optimizer.print_results()

    if args.output:
        with open(args.output, 'w') as f:
            yaml.dump(best_params, f, default_flow_style=False, sort_keys=False)
        console.success(f"Parameters saved to: {args.output}")
    else:
        print(yaml.dump(best_params, default_flow_style=False, sort_keys=False))

    return 0


def run_plot(args: argparse.Namespace) -> int:
    """Visualize ESKF states"""
    try:
        sys.path.insert(0, str(paths.root() / "tools"))
        from eskf_sim.visualizer import plot_states
        from eskf_sim import load_csv
    except ImportError as e:
        console.error(f"Failed to import visualizer: {e}")
        console.print("Note: matplotlib is required for visualization.")
        return 1
    finally:
        sys.path.pop(0)

    # Load input
    if args.input:
        if not Path(args.input).exists():
            console.error(f"File not found: {args.input}")
            return 1
        data = load_csv(args.input)
    else:
        console.error("stdin input not yet supported. Please specify input file.")
        return 1

    # Load overlay
    overlay_data = None
    if args.overlay:
        if not Path(args.overlay).exists():
            console.error(f"Overlay file not found: {args.overlay}")
            return 1
        overlay_data = load_csv(args.overlay)

    # Plot
    plot_states(
        data,
        overlay=overlay_data,
        output_file=args.output,
        mode=args.mode,
    )

    return 0


# --- Helper functions ---

def _load_params(filepath: str, config_class):
    """Load parameters from YAML/JSON file"""
    path = Path(filepath)
    if not path.exists():
        console.error(f"Parameter file not found: {filepath}")
        return None

    try:
        with open(path, 'r') as f:
            if path.suffix == '.json':
                data = json.load(f)
            else:
                data = yaml.safe_load(f)
        return config_class.from_dict(data)
    except Exception as e:
        console.error(f"Failed to load parameters: {e}")
        return None


def _flatten_dict(d: dict, parent_key: str = '', sep: str = '.') -> dict:
    """Flatten nested dictionary"""
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _quat_to_euler_deg(quat) -> list:
    """Convert quaternion to euler angles in degrees"""
    import numpy as np
    w, x, y, z = quat

    # Roll
    sinr_cosp = 2.0 * (w * x + y * z)
    cosr_cosp = 1.0 - 2.0 * (x * x + y * y)
    roll = np.arctan2(sinr_cosp, cosr_cosp)

    # Pitch
    sinp = 2.0 * (w * y - z * x)
    if np.abs(sinp) >= 1:
        pitch = np.sign(sinp) * np.pi / 2
    else:
        pitch = np.arcsin(sinp)

    # Yaw
    siny_cosp = 2.0 * (w * z + x * y)
    cosy_cosp = 1.0 - 2.0 * (y * y + z * z)
    yaw = np.arctan2(siny_cosp, cosy_cosp)

    return [np.rad2deg(roll), np.rad2deg(pitch), np.rad2deg(yaw)]
