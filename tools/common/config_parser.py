#!/usr/bin/env python3
"""
config_parser.py - Parse config.hpp as Single Source of Truth

config.hpp をパースし、全パラメータを Python dict として提供する。
ESKFConfig や PID パラメータのハードコードを廃止し、ここから読み込む。

Usage:
    from tools.common.config_parser import load_config

    params = load_config()  # auto-detect config.hpp
    accel_noise = params['eskf']['ACCEL_NOISE']
    pos_kp = params['position_control']['POS_KP']
"""

import re
import os
from pathlib import Path
from typing import Dict, Any, Optional


# Default config.hpp location (relative to repository root)
# デフォルトの config.hpp パス（リポジトリルートからの相対パス）
DEFAULT_CONFIG_PATH = "firmware/vehicle/main/config.hpp"


def find_repo_root(start_path: Optional[str] = None) -> Path:
    """Find repository root by looking for CLAUDE.md or .git
    リポジトリルートを CLAUDE.md または .git で検索
    """
    path = Path(start_path) if start_path else Path.cwd()
    for parent in [path] + list(path.parents):
        if (parent / "CLAUDE.md").exists() or (parent / ".git").exists():
            return parent
    raise FileNotFoundError(
        f"Cannot find repository root from {path}. "
        "Ensure you are in the stampfly_ecosystem directory."
    )


def find_config_hpp(config_path: Optional[str] = None) -> Path:
    """Find config.hpp, auto-detecting repository root if needed
    config.hpp を検索、必要に応じてリポジトリルートを自動検出
    """
    if config_path:
        p = Path(config_path)
        if p.exists():
            return p
        raise FileNotFoundError(f"Config file not found: {config_path}")

    root = find_repo_root()
    p = root / DEFAULT_CONFIG_PATH
    if p.exists():
        return p
    raise FileNotFoundError(f"Config file not found: {p}")


def parse_config_hpp(filepath: str | Path) -> Dict[str, Dict[str, Any]]:
    """Parse config.hpp and extract all constexpr parameters.

    config.hpp をパースし、namespace 階層付きの dict を返す。

    Returns:
        {
            'eskf': {'ACCEL_NOISE': 0.3, 'FLOW_NOISE': 0.30, ...},
            'rate_control': {'ROLL_RATE_KP': 0.65, ...},
            'position_control': {'POS_KP': 1.0, ...},
            ...
        }

    Top-level constants (outside nested namespaces) are in the '_root' key.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    with open(filepath, 'r') as f:
        content = f.read()

    result: Dict[str, Dict[str, Any]] = {}
    namespace_stack: list[str] = []

    # Patterns
    # パターン定義
    ns_open = re.compile(r'^\s*namespace\s+(\w+)\s*\{')
    ns_close = re.compile(r'^\s*\}\s*//\s*namespace')
    brace_close = re.compile(r'^\s*\}')

    # Match: inline constexpr <type> NAME = VALUE;
    constexpr_pattern = re.compile(
        r'inline\s+constexpr\s+'
        r'(?:float|double|int|uint8_t|uint16_t|uint32_t|int8_t|int16_t|int32_t|bool|UBaseType_t)\s+'
        r'(\w+)\s*=\s*'
        r'([^;]+);'
    )

    for line in content.splitlines():
        # Track namespace nesting
        # namespace のネストを追跡
        m = ns_open.match(line)
        if m:
            namespace_stack.append(m.group(1))
            continue

        if ns_close.match(line) or (brace_close.match(line) and namespace_stack):
            if namespace_stack:
                namespace_stack.pop()
            continue

        # Extract constexpr values
        # constexpr 値を抽出
        m = constexpr_pattern.search(line)
        if m:
            name = m.group(1)
            raw_value = m.group(2).strip()

            # Parse value
            # 値をパース
            value = _parse_value(raw_value)
            if value is None:
                continue  # Skip unparseable values (arrays, complex expressions)

            # Determine namespace key
            # namespace キーを決定
            if namespace_stack:
                # Skip outermost 'config' namespace
                # 最外の 'config' namespace はスキップ
                ns_parts = [n for n in namespace_stack if n != 'config']
                ns_key = '.'.join(ns_parts) if ns_parts else '_root'
            else:
                ns_key = '_root'

            if ns_key not in result:
                result[ns_key] = {}
            result[ns_key][name] = value

    return result


def _parse_value(raw: str) -> Any:
    """Parse a C++ constexpr value to Python type
    C++ の constexpr 値を Python 型に変換
    """
    # Remove trailing 'f' for float literals
    # float リテラルの末尾 'f' を除去
    raw = raw.strip()

    # Remove comments
    # コメントを除去
    if '//' in raw:
        raw = raw[:raw.index('//')].strip()

    # Remove trailing f/F
    if raw.endswith('f') or raw.endswith('F'):
        raw = raw[:-1]

    # Boolean
    if raw == 'true':
        return True
    if raw == 'false':
        return False

    # Try numeric
    try:
        # Try int first
        if raw.startswith('0x') or raw.startswith('0X'):
            return int(raw, 16)
        if '.' in raw or 'e' in raw.lower():
            return float(raw)
        return int(raw)
    except ValueError:
        pass

    # Complex expressions (e.g., (1 << 2)) - skip
    return None


def load_config(config_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
    """Load config.hpp parameters. Main entry point.

    config.hpp パラメータを読み込む。メインエントリポイント。

    Args:
        config_path: Optional explicit path to config.hpp.
                     If None, auto-detects from repository root.

    Returns:
        Nested dict: {namespace: {param_name: value}}
    """
    path = find_config_hpp(config_path)
    return parse_config_hpp(path)


def get_eskf_params(config: Optional[Dict] = None, config_path: Optional[str] = None) -> Dict[str, Any]:
    """Get ESKF-specific parameters with convenient names.

    ESKF 固有のパラメータを取得（便利な名前付き）。

    Returns dict compatible with ESKFConfig field names.
    """
    if config is None:
        config = load_config(config_path)

    eskf = config.get('eskf', {})

    # Map config.hpp names → ESKFConfig field names
    # config.hpp の名前 → ESKFConfig フィールド名にマッピング
    mapping = {
        'gyro_noise': 'GYRO_NOISE',
        'accel_noise': 'ACCEL_NOISE',
        'gyro_bias_noise': 'GYRO_BIAS_NOISE',
        'accel_bias_noise': 'ACCEL_BIAS_NOISE',
        'baro_noise': 'BARO_NOISE',
        'tof_noise': 'TOF_NOISE',
        'mag_noise': 'MAG_NOISE',
        'flow_noise': 'FLOW_NOISE',
        'accel_att_noise': 'ACCEL_ATT_NOISE',
        'mag_chi2_gate': 'MAG_CHI2_GATE',
        'flow_chi2_gate': 'FLOW_CHI2_GATE',
        'flow_innov_clamp': 'FLOW_INNOV_CLAMP',
        'accel_att_chi2_gate': 'ACCEL_ATT_CHI2_GATE',
        'use_optical_flow': 'USE_OPTICAL_FLOW',
        'use_barometer': 'USE_BAROMETER',
        'use_tof': 'USE_TOF',
        'use_magnetometer': 'USE_MAGNETOMETER',
        'enable_yaw_estimation': 'ENABLE_YAW_ESTIMATION',
        'baro_innov_gate': 'BARO_INNOV_GATE',
        'tof_innov_gate': 'TOF_INNOV_GATE',
        'flow_rad_per_pixel': 'FLOW_RAD_PER_PIXEL',
        'flow_gyro_scale': 'FLOW_GYRO_SCALE',
        'flow_min_height': 'FLOW_MIN_HEIGHT',
        'flow_max_height': 'FLOW_MAX_HEIGHT',
        'flow_tilt_cos_threshold': 'FLOW_TILT_COS_THRESHOLD',
        'flow_offset_x': 'FLOW_OFFSET_X',
        'flow_offset_y': 'FLOW_OFFSET_Y',
        'flow_cam_to_body_xx': 'FLOW_CAM_TO_BODY_XX',
        'flow_cam_to_body_xy': 'FLOW_CAM_TO_BODY_XY',
        'flow_cam_to_body_yx': 'FLOW_CAM_TO_BODY_YX',
        'flow_cam_to_body_yy': 'FLOW_CAM_TO_BODY_YY',
    }

    result = {}
    for py_name, cpp_name in mapping.items():
        if cpp_name in eskf:
            result[py_name] = eskf[cpp_name]

    return result


def get_pid_params(namespace: str, config: Optional[Dict] = None,
                   config_path: Optional[str] = None) -> Dict[str, Any]:
    """Get PID parameters for a specific control loop.

    特定の制御ループの PID パラメータを取得。

    Args:
        namespace: One of 'rate_control', 'attitude_control',
                   'altitude_control', 'position_control'
    """
    if config is None:
        config = load_config(config_path)
    return config.get(namespace, {})


def print_config(config: Optional[Dict] = None, config_path: Optional[str] = None):
    """Print all parsed parameters for debugging.
    デバッグ用に全パラメータを表示。
    """
    if config is None:
        config = load_config(config_path)

    for ns, params in sorted(config.items()):
        print(f"\n[{ns}]")
        for name, value in sorted(params.items()):
            print(f"  {name} = {value}")


# =============================================================================
# Standalone execution
# スタンドアロン実行
# =============================================================================

if __name__ == '__main__':
    import sys

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        config = load_config(config_path)
        print_config(config)
        print(f"\nTotal: {sum(len(v) for v in config.values())} parameters "
              f"in {len(config)} namespaces")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
