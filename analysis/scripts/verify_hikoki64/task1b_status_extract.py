#!/usr/bin/env python3
"""
Task 1b — recover as-flown settings from the status telemetry records only.
No source-code or documentation values used to fill in anything absent from
the log itself.

Field-identity note (from reading firmware/vehicle_old, allowed as firmware
source code per task instructions): in tools/log_analyzer/udp_capture.py the
JSONL "status".pid_roll/pid_pitch/pid_yaw are packed from vehicle_old's
StatusPacket.pid_*_kp/ti/td, which telemetry_task.cpp populates from
g_rate_controller_ptr->{roll,pitch,yaw}_pid with the comment "PID gains from
rate controller" -- i.e. these are RATE-loop gains, not position- or
attitude-loop gains. No position-loop (pos.kp/vel.kp) or attitude-loop gain
fields exist anywhere in this log's schema (checked: the only ids present are
mag, tof_b, imu, posvel, rate_ref, flow, baro, ctrl, ctrl_ref, status; none of
their fields besides status.pid_roll/pitch/yaw carry gain values).
"""
import json

LOG = "/Users/kouhei/tmp/github/stampfly_ecosystem/logs/stampfly_udp_20260622T161055.jsonl"
OUT = "/private/tmp/claude-501/-Users-kouhei-tmp-github-stampfly-ecosystem/5e87008a-97a4-42d5-9e0e-02387c2a8022/scratchpad/verify_A"

STATE_NAME = {0: "INIT", 1: "IDLE_GROUND", 2: "IDLE_HELD", 3: "ARMED_GROUND",
              4: "TAKEOFF", 5: "FLYING", 6: "LANDING"}  # from poshold_analysis.py MODE/STATE dict (allowed script)

status = []
with open(LOG) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("id") == "status":
            status.append(d)

t0 = status[0]["ts"]
roll_sets = sorted(set(tuple(s["pid_roll"]) for s in status))
pitch_sets = sorted(set(tuple(s["pid_pitch"]) for s in status))
yaw_sets = sorted(set(tuple(s["pid_yaw"]) for s in status))

flying_idx = [i for i, s in enumerate(status) if s["flight_state"] == 5]
volts_flying = [status[i]["voltage"] for i in flying_idx]

result = {
    "n_status_records": len(status),
    "status_period_s_approx": 1.0,
    "rate_loop_gains_pid_roll_kp_ti_td": list(roll_sets[0]) if len(roll_sets) == 1 else roll_sets,
    "rate_loop_gains_pid_pitch_kp_ti_td": list(pitch_sets[0]) if len(pitch_sets) == 1 else pitch_sets,
    "rate_loop_gains_pid_yaw_kp_ti_td": list(yaw_sets[0]) if len(yaw_sets) == 1 else yaw_sets,
    "gains_changed_during_log": (len(roll_sets) > 1 or len(pitch_sets) > 1 or len(yaw_sets) > 1),
    "position_loop_gains_in_log": "NOT PRESENT (no pos.kp/vel.kp-type field exists anywhere in this log schema)",
    "attitude_loop_gains_in_log": "NOT PRESENT (status only carries pid_roll/pitch/yaw, identified as RATE-loop gains; no separate attitude/angle-loop gain field exists)",
    "voltage_full_sequence": [s["voltage"] for s in status],
    "voltage_min_max_overall": [min(s["voltage"] for s in status), max(s["voltage"] for s in status)],
    "voltage_min_max_during_flight_state_FLYING(5)": [min(volts_flying), max(volts_flying)] if volts_flying else None,
    "flight_state_sequence": [s["flight_state"] for s in status],
    "flight_state_name_sequence": [STATE_NAME.get(s["flight_state"], s["flight_state"]) for s in status],
    "flight_state_5_FLYING_first_status_t_s": None,
    "flight_state_5_FLYING_last_status_t_s": None,
}
if flying_idx:
    result["flight_state_5_FLYING_first_status_t_s"] = (status[flying_idx[0]]["ts"] - t0) / 1e6
    result["flight_state_5_FLYING_last_status_t_s"] = (status[flying_idx[-1]]["ts"] - t0) / 1e6

print(json.dumps(result, indent=2))
with open(f"{OUT}/task1b_results.json", "w") as f:
    json.dump(result, f, indent=2)
print(f"\nsaved: {OUT}/task1b_results.json")
