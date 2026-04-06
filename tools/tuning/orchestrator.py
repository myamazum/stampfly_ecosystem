"""
Man-in-the-Loop Tuning Orchestrator
マンインザループ チューニングオーケストレータ

Automates the tuning cycle:
  Analyze → Propose → Approve → Build → Flash → Fly → Log → Evaluate → Repeat

The tool drives the process; the human only flies.
ツールがプロセスを主導し、人間は飛行のみ行う。
"""

import sys
import os
import subprocess
import json
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path

_tools_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)


@dataclass
class FlightPlan:
    """Flight test instruction for the pilot.
    パイロットへの飛行テスト指示。
    """
    mode: str                    # 'STABILIZE', 'ALT_HOLD', 'POS_HOLD'
    duration_s: int = 30         # Flight duration [s]
    instructions: List[str] = field(default_factory=list)
    log_duration_s: int = 30     # WiFi log capture duration [s]


@dataclass
class TuningPhase:
    """Single tuning phase configuration.
    単一チューニングフェーズの設定。
    """
    name: str
    target: str                  # 'eskf', 'rate', 'attitude', 'altitude', 'position'
    flight_plan: FlightPlan
    convergence_criteria: Dict[str, float]
    max_iterations: int = 5
    params_to_tune: List[str] = field(default_factory=list)


@dataclass
class TuningIteration:
    """Result of a single tuning iteration.
    単一チューニングイテレーションの結果。
    """
    iteration: int
    params_proposed: Dict[str, float]
    params_applied: Dict[str, float]
    log_path: Optional[str] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    converged: bool = False
    notes: str = ""


# =============================================================================
# Standard flight plans
# 標準飛行プラン
# =============================================================================

FLIGHT_PLANS = {
    'eskf': FlightPlan(
        mode='ALT_HOLD',
        duration_s=30,
        instructions=[
            "ALT_HOLD モードで ARM",
            "離陸して約 50cm の高度を維持",
            "スティック中立のまま 30 秒間ホバリング",
            "できるだけ位置を保持（±30cm 以内）",
            "着陸して DISARM",
        ],
        log_duration_s=30,
    ),
    'rate': FlightPlan(
        mode='STABILIZE',
        duration_s=20,
        instructions=[
            "STABILIZE モードで ARM",
            "離陸して約 50cm の高度を維持",
            "右スティックを右に 0.5 秒倒して戻す",
            "3 秒待つ",
            "右スティックを前に 0.5 秒倒して戻す",
            "3 秒待つ",
            "左スティックを左に 0.5 秒倒して戻す（ヨー）",
            "5 秒ホバリング",
            "着陸して DISARM",
        ],
        log_duration_s=20,
    ),
    'attitude': FlightPlan(
        mode='STABILIZE',
        duration_s=20,
        instructions=[
            "STABILIZE モードで ARM",
            "離陸して約 50cm の高度を維持",
            "右スティックをゆっくり右に傾けて戻す（2 秒）",
            "3 秒待つ",
            "右スティックをゆっくり前に傾けて戻す（2 秒）",
            "5 秒ホバリング",
            "着陸して DISARM",
        ],
        log_duration_s=20,
    ),
    'altitude': FlightPlan(
        mode='ALT_HOLD',
        duration_s=30,
        instructions=[
            "ALT_HOLD モードで ARM",
            "離陸して約 50cm の高度を維持（5 秒）",
            "左スティックを上に 1 秒倒して戻す（高度変更）",
            "5 秒待つ",
            "左スティックを下に 1 秒倒して戻す（元に戻す）",
            "10 秒ホバリング",
            "着陸して DISARM",
        ],
        log_duration_s=30,
    ),
    'position': FlightPlan(
        mode='POS_HOLD',
        duration_s=30,
        instructions=[
            "ALT_HOLD で ARM → 離陸 → 安定したら POS_HOLD に切替",
            "スティック中立で 10 秒間静止",
            "機体を手で 20cm ほど押して離す（位置復帰テスト）",
            "10 秒待つ",
            "着陸して DISARM",
        ],
        log_duration_s=30,
    ),
}


# =============================================================================
# Standard tuning phases
# 標準チューニングフェーズ
# =============================================================================

STANDARD_PHASES = [
    TuningPhase(
        name="ESKF Q/R Balance",
        target="eskf",
        flight_plan=FLIGHT_PLANS['eskf'],
        convergence_criteria={
            'flow_nis_mean': 2.0,       # target ± 1.0
            'accel_bias_drift_rate': 0.01,  # max
        },
        max_iterations=5,
        params_to_tune=['eskf.ACCEL_NOISE', 'eskf.FLOW_NOISE'],
    ),
    TuningPhase(
        name="Altitude Control",
        target="altitude",
        flight_plan=FLIGHT_PLANS['altitude'],
        convergence_criteria={
            'altitude_std': 0.05,  # [m]
        },
        max_iterations=3,
        params_to_tune=['altitude_control.ALT_KP', 'altitude_control.VEL_KP'],
    ),
    TuningPhase(
        name="Position Control",
        target="position",
        flight_plan=FLIGHT_PLANS['position'],
        convergence_criteria={
            'position_std': 0.15,  # [m]
        },
        max_iterations=5,
        params_to_tune=[
            'position_control.POS_KP', 'position_control.VEL_KP',
        ],
    ),
]


class TuningOrchestrator:
    """Orchestrates the tuning workflow.
    チューニングワークフローをオーケストレーション。
    """

    def __init__(self, phases: Optional[List[TuningPhase]] = None,
                 repo_root: Optional[str] = None):
        self.phases = phases or STANDARD_PHASES
        self.repo_root = Path(repo_root) if repo_root else Path(_tools_dir).parent
        self.history: List[TuningIteration] = []

    def run_cli(self, phase_filter: Optional[str] = None):
        """Run tuning session in CLI mode.
        CLI モードでチューニングセッションを実行。
        """
        phases = self.phases
        if phase_filter:
            phases = [p for p in phases if p.target == phase_filter]

        print("=" * 60)
        print("🔧 StampFly Auto-Tuning Session")
        print("=" * 60)

        for pi, phase in enumerate(phases):
            print(f"\n{'='*60}")
            print(f"Phase {pi+1}/{len(phases)}: {phase.name}")
            print(f"{'='*60}")

            for iteration in range(phase.max_iterations):
                print(f"\n--- Iteration {iteration+1}/{phase.max_iterations} ---")

                # 1. Propose parameters
                proposal = self._propose_params(phase, iteration)
                print("\n📝 Parameter proposal:")
                for k, v in proposal.items():
                    print(f"  {k}: {v}")

                # 2. Wait for approval
                response = input("\n[Enter] to apply, [s]kip, [q]uit: ").strip().lower()
                if response == 'q':
                    print("Session ended by user.")
                    return
                if response == 's':
                    print("Phase skipped.")
                    break

                # 3. Apply, build, flash
                print("\n⚡ Applying parameters...")
                # TODO: apply_to_config_hpp(proposal)
                print("  (Manual: edit config.hpp with values above)")

                print("\n⚡ Building...")
                # TODO: subprocess.run(['sf', 'build', 'vehicle'])

                print("\n⚡ Flashing...")
                # TODO: subprocess.run(['sf', 'flash', 'vehicle'])

                # 4. Flight instructions
                fp = phase.flight_plan
                print(f"\n✈️  Flight Instructions ({fp.mode}, {fp.duration_s}s):")
                print("┌" + "─" * 50 + "┐")
                for inst in fp.instructions:
                    print(f"│ {inst:<48} │")
                print("└" + "─" * 50 + "┘")

                input("\n[Enter] when ready to capture log...")

                # 5. Capture log
                print(f"\n📡 Capturing WiFi log ({fp.log_duration_s}s)...")
                # TODO: subprocess.run(['sf', 'log', 'wifi', '-d', str(fp.log_duration_s)])
                print("  (Manual: run 'sf log wifi' in another terminal)")

                input("\n[Enter] when log capture is complete...")

                # 6. Find latest log
                log_dir = self.repo_root / "logs"
                logs = sorted(log_dir.glob("*.jsonl"), reverse=True) if log_dir.exists() else []
                if logs:
                    latest_log = logs[0]
                    print(f"\n📊 Analyzing: {latest_log.name}")

                    # 7. Evaluate
                    result = self._evaluate(phase, str(latest_log))
                    print("\n📊 Results:")
                    for k, v in result.items():
                        print(f"  {k}: {v}")

                    # 8. Check convergence
                    converged = self._check_convergence(phase, result)
                    if converged:
                        print("\n✅ Phase converged! Moving to next phase.")
                        break
                    else:
                        print("\n⚠️ Not yet converged. Continuing...")
                else:
                    print("⚠️ No log files found.")

            print(f"\nPhase '{phase.name}' complete.")

        print("\n" + "=" * 60)
        print("✅ Tuning session complete!")
        print("=" * 60)

    def _propose_params(self, phase: TuningPhase, iteration: int) -> Dict[str, float]:
        """Propose parameters for next iteration.
        次のイテレーション用パラメータを提案。
        """
        from common.config_parser import load_config

        config = load_config()
        proposal = {}
        for param_key in phase.params_to_tune:
            ns, name = param_key.split('.')
            current = config.get(ns, {}).get(name, 0)
            proposal[param_key] = current  # Start with current

        return proposal

    def _evaluate(self, phase: TuningPhase, log_path: str) -> Dict[str, float]:
        """Evaluate flight log against phase criteria.
        フライトログをフェーズ基準で評価。
        """
        from eskf_sim.loader import load_log

        log = load_log(log_path)
        results = {}
        results['samples'] = len(log)
        results['duration'] = log.duration_s

        # Position statistics
        pos_samples = [s for s in log.samples if s.eskf_position is not None]
        if pos_samples:
            px = [s.eskf_position[0] for s in pos_samples]
            py = [s.eskf_position[1] for s in pos_samples]
            results['pos_x_std'] = float(np.std(px))
            results['pos_y_std'] = float(np.std(py))
            results['pos_x_max'] = float(max(abs(min(px)), abs(max(px))))
            results['pos_y_max'] = float(max(abs(min(py)), abs(max(py))))

        return results

    def _check_convergence(self, phase: TuningPhase, result: Dict) -> bool:
        """Check if phase convergence criteria are met.
        フェーズの収束条件を確認。
        """
        for key, target in phase.convergence_criteria.items():
            if key in result:
                if result[key] > target:
                    return False
        return True


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='StampFly Auto-Tuning Orchestrator')
    parser.add_argument('--phase', choices=['eskf', 'rate', 'attitude', 'altitude', 'position'],
                       help='Run only this phase')
    args = parser.parse_args()

    import numpy as np
    orch = TuningOrchestrator()
    orch.run_cli(phase_filter=args.phase)
