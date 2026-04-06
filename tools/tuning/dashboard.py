"""
StampFly Tuning Dashboard — Interactive GUI
インタラクティブ GUI チューニングダッシュボード

Launch: sf tune gui  (or: streamlit run tools/tuning/dashboard.py)

Features:
- パラメータスライダーでリアルタイムシミュレーション
- ログ vs シミュレーションの重ね描き
- NIS 評価指標ダッシュボード
- config.hpp への反映ボタン
- Man-in-the-loop オーケストレーション
"""

import sys
import os
from pathlib import Path

# Setup paths
_tools_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_repo_root = os.path.dirname(_tools_dir)
if _tools_dir not in sys.path:
    sys.path.insert(0, _tools_dir)

import streamlit as st
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from common.config_parser import load_config, find_config_hpp
from sim.closed_loop import ClosedLoopSim
from sim.drone_plant import DroneParams

# Page config
st.set_page_config(
    page_title="StampFly Tuning",
    page_icon="🚁",
    layout="wide",
)

st.title("🚁 StampFly Tuning Dashboard")


# =============================================================================
# Load current config
# =============================================================================
@st.cache_data
def get_config():
    return load_config()

config = get_config()


# =============================================================================
# Sidebar: Parameter controls
# =============================================================================
st.sidebar.header("Parameters")

tab_names = ["ESKF", "Position", "Altitude", "Attitude", "Rate"]
selected_tab = st.sidebar.radio("Control Loop", tab_names)

param_overrides = {}

if selected_tab == "ESKF":
    st.sidebar.subheader("ESKF Q/R Parameters")
    eskf = config.get('eskf', {})

    accel_n = st.sidebar.slider("ACCEL_NOISE", 0.05, 2.0,
                                float(eskf.get('ACCEL_NOISE', 0.3)), 0.05,
                                help="Process noise [m/s²/√Hz]")
    param_overrides['eskf.ACCEL_NOISE'] = accel_n

    flow_n = st.sidebar.slider("FLOW_NOISE", 0.05, 1.0,
                               float(eskf.get('FLOW_NOISE', 0.3)), 0.05,
                               help="Flow observation noise [m/s]")
    param_overrides['eskf.FLOW_NOISE'] = flow_n

    innov_clamp = st.sidebar.slider("FLOW_INNOV_CLAMP", 0.0, 1.0,
                                    float(eskf.get('FLOW_INNOV_CLAMP', 0.3)), 0.05,
                                    help="Innovation clamp [m/s]")
    param_overrides['eskf.FLOW_INNOV_CLAMP'] = innov_clamp

    tof_n = st.sidebar.slider("TOF_NOISE", 0.005, 0.1,
                              float(eskf.get('TOF_NOISE', 0.03)), 0.005,
                              help="ToF observation noise [m]")
    param_overrides['eskf.TOF_NOISE'] = tof_n

    accel_att_n = st.sidebar.slider("ACCEL_ATT_NOISE", 0.01, 0.5,
                                    float(eskf.get('ACCEL_ATT_NOISE', 0.06)), 0.01,
                                    help="Accel attitude noise [m/s²]")
    param_overrides['eskf.ACCEL_ATT_NOISE'] = accel_att_n

    # Bandwidth estimate
    dt_flow = 0.01
    dt_imu = 0.0025
    Q_vel = accel_n**2 * dt_imu * (dt_flow / dt_imu)
    R = flow_n**2
    P_ss = (Q_vel + np.sqrt(Q_vel**2 + 4*Q_vel*R)) / 2
    K_ss = P_ss / (P_ss + R)
    bw = K_ss * 100 / (2*np.pi)
    st.sidebar.metric("Velocity BW", f"{bw:.1f} Hz", help="Effective velocity estimation bandwidth")

elif selected_tab == "Position":
    st.sidebar.subheader("Position Control PID")
    pc = config.get('position_control', {})

    pos_kp = st.sidebar.slider("POS_KP", 0.1, 5.0,
                               float(pc.get('POS_KP', 1.0)), 0.1)
    param_overrides['position_control.POS_KP'] = pos_kp

    pos_ti = st.sidebar.slider("POS_TI", 0.5, 20.0,
                               float(pc.get('POS_TI', 5.0)), 0.5)
    param_overrides['position_control.POS_TI'] = pos_ti

    pos_td = st.sidebar.slider("POS_TD", 0.0, 0.5,
                               float(pc.get('POS_TD', 0.1)), 0.01)
    param_overrides['position_control.POS_TD'] = pos_td

    vel_kp = st.sidebar.slider("VEL_KP", 0.05, 2.0,
                               float(pc.get('VEL_KP', 0.3)), 0.05)
    param_overrides['position_control.VEL_KP'] = vel_kp

    vel_ti = st.sidebar.slider("VEL_TI", 0.5, 10.0,
                               float(pc.get('VEL_TI', 2.0)), 0.5)
    param_overrides['position_control.VEL_TI'] = vel_ti

    vel_td = st.sidebar.slider("VEL_TD", 0.0, 0.1,
                               float(pc.get('VEL_TD', 0.02)), 0.005)
    param_overrides['position_control.VEL_TD'] = vel_td

    max_tilt = st.sidebar.slider("MAX_TILT [deg]", 1.0, 30.0,
                                 float(pc.get('MAX_TILT_ANGLE', 0.1745)) * 180/np.pi, 1.0)
    param_overrides['position_control.MAX_TILT_ANGLE'] = max_tilt * np.pi / 180

elif selected_tab == "Altitude":
    st.sidebar.subheader("Altitude Control PID")
    ac = config.get('altitude_control', {})

    alt_kp = st.sidebar.slider("ALT_KP", 0.1, 3.0,
                               float(ac.get('ALT_KP', 0.6)), 0.1)
    param_overrides['altitude_control.ALT_KP'] = alt_kp

    alt_ti = st.sidebar.slider("ALT_TI", 1.0, 20.0,
                               float(ac.get('ALT_TI', 7.0)), 0.5)
    param_overrides['altitude_control.ALT_TI'] = alt_ti

    alt_vel_kp = st.sidebar.slider("VEL_KP (alt)", 0.01, 0.5,
                                   float(ac.get('VEL_KP', 0.1)), 0.01)
    param_overrides['altitude_control.VEL_KP'] = alt_vel_kp

    alt_vel_ti = st.sidebar.slider("VEL_TI (alt)", 0.5, 10.0,
                                   float(ac.get('VEL_TI', 2.5)), 0.5)
    param_overrides['altitude_control.VEL_TI'] = alt_vel_ti

elif selected_tab == "Attitude":
    st.sidebar.subheader("Attitude Control PID")
    atc = config.get('attitude_control', {})

    roll_kp = st.sidebar.slider("ROLL_ANGLE_KP", 1.0, 15.0,
                                float(atc.get('ROLL_ANGLE_KP', 5.0)), 0.5)
    param_overrides['attitude_control.ROLL_ANGLE_KP'] = roll_kp

    pitch_kp = st.sidebar.slider("PITCH_ANGLE_KP", 1.0, 15.0,
                                 float(atc.get('PITCH_ANGLE_KP', 5.0)), 0.5)
    param_overrides['attitude_control.PITCH_ANGLE_KP'] = pitch_kp

    att_ti = st.sidebar.slider("ANGLE_TI", 0.5, 10.0,
                               float(atc.get('ROLL_ANGLE_TI', 4.0)), 0.5)
    param_overrides['attitude_control.ROLL_ANGLE_TI'] = att_ti
    param_overrides['attitude_control.PITCH_ANGLE_TI'] = att_ti

elif selected_tab == "Rate":
    st.sidebar.subheader("Rate Control PID")
    rc = config.get('rate_control', {})

    roll_rate_kp = st.sidebar.slider("ROLL_RATE_KP", 0.1, 3.0,
                                     float(rc.get('ROLL_RATE_KP', 0.65)), 0.05)
    param_overrides['rate_control.ROLL_RATE_KP'] = roll_rate_kp

    pitch_rate_kp = st.sidebar.slider("PITCH_RATE_KP", 0.1, 3.0,
                                      float(rc.get('PITCH_RATE_KP', 0.95)), 0.05)
    param_overrides['rate_control.PITCH_RATE_KP'] = pitch_rate_kp

    yaw_rate_kp = st.sidebar.slider("YAW_RATE_KP", 0.5, 10.0,
                                    float(rc.get('YAW_RATE_KP', 3.0)), 0.5)
    param_overrides['rate_control.YAW_RATE_KP'] = yaw_rate_kp


# =============================================================================
# Simulation
# =============================================================================
st.sidebar.markdown("---")
disturbance = st.sidebar.slider("Disturbance [m]", 0.05, 1.0, 0.3, 0.05)
sim_duration = st.sidebar.slider("Duration [s]", 2.0, 30.0, 10.0, 1.0)

# Run simulation
sim = ClosedLoopSim(param_overrides=param_overrides)
mode = 'position' if selected_tab in ['Position', 'ESKF'] else (
    'altitude' if selected_tab == 'Altitude' else 'stabilize')

result = sim.run(
    duration=sim_duration,
    disturbance_pos=np.array([disturbance, 0.0]),
    mode=mode,
)
metrics = result.metrics()


# =============================================================================
# Main display
# =============================================================================
col1, col2, col3, col4 = st.columns(4)
col1.metric("Pos X max", f"{metrics['pos_x_max']*100:.1f} cm")
col2.metric("Settle time", f"{metrics['settle_time']:.1f} s")
col3.metric("Pitch max", f"{metrics['pitch_max_deg']:.1f}°")
col4.metric("Pos X RMS", f"{metrics['pos_x_rms']*100:.1f} cm")

# Plots
fig = make_subplots(rows=3, cols=1,
                    subplot_titles=("Position X", "Velocity X", "Pitch Angle"),
                    shared_xaxes=True,
                    vertical_spacing=0.08)

# Position
fig.add_trace(go.Scatter(x=result.t, y=[p*100 for p in result.pos_x],
                         name="pos_x [cm]", line=dict(color='blue')), row=1, col=1)
fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)

# Velocity
fig.add_trace(go.Scatter(x=result.t, y=[v*100 for v in result.vel_x],
                         name="vel_x [cm/s]", line=dict(color='green')), row=2, col=1)
fig.add_hline(y=0, line_dash="dash", line_color="gray", row=2, col=1)

# Pitch angle
fig.add_trace(go.Scatter(x=result.t, y=[p*180/np.pi for p in result.pitch],
                         name="pitch [°]", line=dict(color='red')), row=3, col=1)
fig.add_trace(go.Scatter(x=result.t, y=[p*180/np.pi for p in result.angle_ref_pitch],
                         name="pitch ref [°]", line=dict(color='orange', dash='dot')), row=3, col=1)
fig.add_hline(y=0, line_dash="dash", line_color="gray", row=3, col=1)

fig.update_layout(height=700, showlegend=True)
fig.update_xaxes(title_text="Time [s]", row=3, col=1)
fig.update_yaxes(title_text="[cm]", row=1, col=1)
fig.update_yaxes(title_text="[cm/s]", row=2, col=1)
fig.update_yaxes(title_text="[°]", row=3, col=1)

st.plotly_chart(fig, use_container_width=True)


# =============================================================================
# Log file loading (optional)
# =============================================================================
st.markdown("---")
st.subheader("📂 Flight Log Analysis")

log_dir = Path(_repo_root) / "logs"
log_files = sorted(log_dir.glob("*.jsonl"), reverse=True) if log_dir.exists() else []

if log_files:
    selected_log = st.selectbox("Select log file",
                                [f.name for f in log_files[:20]])
    if st.button("Load & Analyze"):
        from eskf_sim.loader import load_log
        log = load_log(str(log_dir / selected_log))
        st.success(f"Loaded: {len(log)} samples, {log.duration_s:.1f}s, {log.sample_rate_hz:.0f}Hz")

        # Plot position from log
        if log.has_eskf():
            log_t = log.timestamps - log.timestamps[0]
            # Filter samples with position data
            pos_samples = [(t, s) for t, s in zip(log_t, log.samples)
                          if s.eskf_position is not None]
            if pos_samples:
                lt = [p[0] for p in pos_samples]
                lx = [p[1].eskf_position[0] for p in pos_samples]
                ly = [p[1].eskf_position[1] for p in pos_samples]

                fig_log = make_subplots(rows=2, cols=1,
                                       subplot_titles=("Position X (log)", "Position Y (log)"))
                fig_log.add_trace(go.Scatter(x=lt, y=[x*100 for x in lx],
                                            name="pos_x [cm]"), row=1, col=1)
                fig_log.add_trace(go.Scatter(x=lt, y=[y*100 for y in ly],
                                            name="pos_y [cm]"), row=2, col=1)
                fig_log.update_layout(height=400)
                st.plotly_chart(fig_log, use_container_width=True)
else:
    st.info("No log files found in logs/")


# =============================================================================
# Apply to config.hpp
# =============================================================================
st.markdown("---")
st.subheader("⚡ Apply Parameters")

changed_params = {k: v for k, v in param_overrides.items()
                  if True}  # Show all for now

if changed_params:
    st.code("\n".join(f"{k} = {v}" for k, v in changed_params.items()))

    if st.button("Apply to config.hpp", type="primary"):
        st.warning("config.hpp modification not yet implemented. "
                  "Copy values above and edit manually, or use sf tune apply.")
