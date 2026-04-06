#!/usr/bin/env python3
"""
ESKF parameter sweep using flight log replay.
Finds optimal ACCEL_BIAS_NOISE and FLOW_NOISE to prevent bias drift.

Uses simplified ESKF: predict (IMU) + updateFlow + updateToF + updateAccelAtt
"""
import json
import math
import numpy as np
import sys

# State indices
POS_X, POS_Y, POS_Z = 0, 1, 2
VEL_X, VEL_Y, VEL_Z = 3, 4, 5
ATT_X, ATT_Y, ATT_Z = 6, 7, 8
BG_X, BG_Y, BG_Z = 9, 10, 11
BA_X, BA_Y, BA_Z = 12, 13, 14
N = 15

GRAVITY = 9.81

# Fixed config from firmware
FLOW_RAD_PER_PIXEL = 0.00222
FLOW_CAM_TO_BODY = np.array([[0.943, 0.0], [0.0, 1.015]])
FLOW_GYRO_SCALE = 1.0
FLOW_MIN_HEIGHT = 0.02
GYRO_NOISE = 0.009655
GYRO_BIAS_NOISE = 0.000013
TOF_NOISE = 0.00254
ACCEL_ATT_NOISE = 0.06
ATT_CORRECTION_CLAMP = 0.05


def quat_to_dcm(q):
    """Quaternion [x,y,z,w] to DCM (3x3)"""
    x, y, z, w = q
    return np.array([
        [1-2*(y*y+z*z), 2*(x*y-w*z),   2*(x*z+w*y)],
        [2*(x*y+w*z),   1-2*(x*x+z*z), 2*(y*z-w*x)],
        [2*(x*z-w*y),   2*(y*z+w*x),   1-2*(x*x+y*y)]
    ])


def quat_multiply(q1, q2):
    """Quaternion multiplication [x,y,z,w]"""
    x1,y1,z1,w1 = q1
    x2,y2,z2,w2 = q2
    return np.array([
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
        w1*w2 - x1*x2 - y1*y2 - z1*z2
    ])


def rot_vec_to_quat(rv):
    """Rotation vector to quaternion [x,y,z,w]"""
    angle = np.linalg.norm(rv)
    if angle < 1e-10:
        return np.array([0, 0, 0, 1.0])
    axis = rv / angle
    ha = angle / 2
    return np.array([axis[0]*math.sin(ha), axis[1]*math.sin(ha),
                     axis[2]*math.sin(ha), math.cos(ha)])


class ESKF:
    def __init__(self, accel_noise, accel_bias_noise, flow_noise):
        self.x = np.zeros(N)
        self.q = np.array([0, 0, 0, 1.0])  # [x,y,z,w]
        self.P = np.diag([
            1.0, 1.0, 1.0,       # pos
            0.25, 0.25, 0.25,    # vel
            0.01, 0.01, 0.01,    # att
            1e-4, 1e-4, 1e-4,    # bg
            0.01, 0.01, 0.01     # ba
        ])
        self.accel_noise = accel_noise
        self.accel_bias_noise = accel_bias_noise
        self.flow_noise = flow_noise
        # Active mask: all enabled for flow+tof config
        # flow=1, baro=0, tof=1, mag=0
        # MASK_FLOW = POS_X|POS_Y|VEL_X|VEL_Y|BA_X|BA_Y
        # MASK_TOF = POS_Z|VEL_Z|BA_Z
        self.active_mask = 0x7FFF  # all active initially
        # Disable mag & baro bits
        MASK_MAG = (1<<ATT_Z) | (1<<BG_Z)
        MASK_BARO = (1<<POS_Z) | (1<<VEL_Z) | (1<<BA_Z)
        # mag off
        self.active_mask &= ~MASK_MAG
        # baro off but tof on (same bits), so keep them
        # Final: 0x7FFF & ~MASK_MAG = 0x7FFF & ~0x0900 = 0x76FF
        # But TOF restores POS_Z|VEL_Z|BA_Z
        self.active_mask = 0x76FF | MASK_BARO  # = 0x76FF | 0x4024 = 0x76FF
        # Actually just use all except ATT_Z and BG_Z
        self.active_mask = 0x7FFF & ~((1<<ATT_Z) | (1<<BG_Z))  # 0x76FF

        self.init_P_diag = np.diag(self.P).copy()

    def predict(self, accel, gyro, dt):
        bg = self.x[BG_X:BG_Z+1]
        ba = self.x[BA_X:BA_Z+1]
        gyro_c = gyro - bg
        gyro_c[2] = 0  # no yaw from gyro (yaw estimation via gyro integration disabled here for simplicity, but we keep it)
        # Actually yaw estimation IS enabled, let's keep gyro_c[2]
        gyro_c = gyro - bg
        accel_c = accel - ba

        R = quat_to_dcm(self.q)
        a_ned = R @ accel_c + np.array([0, 0, GRAVITY])

        # Update nominal state
        for i in range(3):
            if (self.active_mask >> i) & 1:
                self.x[i] += self.x[3+i] * dt + 0.5 * a_ned[i] * dt**2
            if (self.active_mask >> (3+i)) & 1:
                self.x[3+i] += a_ned[i] * dt

        # Quaternion update
        dq = rot_vec_to_quat(gyro_c * dt)
        self.q = quat_multiply(self.q, dq)
        self.q /= np.linalg.norm(self.q)

        # Covariance prediction (simplified but capturing key dynamics)
        F = np.eye(N)
        # dp/dv
        for i in range(3):
            F[i, 3+i] = dt
        # dv/datt (cross product with accel)
        skew_a = np.array([
            [0, -accel_c[2], accel_c[1]],
            [accel_c[2], 0, -accel_c[0]],
            [-accel_c[1], accel_c[0], 0]
        ])
        F[3:6, 6:9] = -R @ skew_a * dt
        # dv/dba
        F[3:6, 12:15] = -R * dt
        # datt/dbg
        F[6:9, 9:12] = -np.eye(3) * dt

        Q = np.zeros(N)
        Q[3:6] = self.accel_noise**2 * dt
        Q[6:9] = GYRO_NOISE**2 * dt
        Q[9:12] = GYRO_BIAS_NOISE**2 * dt
        Q[12:15] = self.accel_bias_noise**2 * dt

        # Mask Q
        for i in range(N):
            if not ((self.active_mask >> i) & 1):
                Q[i] = 0

        self.P = F @ self.P @ F.T + np.diag(Q)
        self._enforce_constraints()

    def update_flow(self, flow_dx, flow_dy, distance, dt_flow, gyro_x, gyro_y):
        if distance < FLOW_MIN_HEIGHT or dt_flow <= 0:
            return

        bg = self.x[BG_X:BG_Z+1]
        # Pixel -> angular rate
        fx = flow_dx * FLOW_RAD_PER_PIXEL / dt_flow
        fy = flow_dy * FLOW_RAD_PER_PIXEL / dt_flow
        # Rotation compensation
        gx_c = gyro_x - bg[0]
        gy_c = gyro_y - bg[1]
        rot_x = FLOW_GYRO_SCALE * gy_c
        rot_y = -FLOW_GYRO_SCALE * gx_c
        trans_x_cam = fx - rot_x
        trans_y_cam = fy - rot_y
        # Camera -> body
        trans = FLOW_CAM_TO_BODY @ np.array([trans_x_cam, trans_y_cam])
        # Velocity
        vx_body = trans[0] * distance
        vy_body = trans[1] * distance
        # Body -> NED
        yaw = math.atan2(2*(self.q[3]*self.q[2]+self.q[0]*self.q[1]),
                         1-2*(self.q[1]**2+self.q[2]**2))
        cy, sy = math.cos(yaw), math.sin(yaw)
        vx_ned = cy*vx_body - sy*vy_body
        vy_ned = sy*vx_body + cy*vy_body

        # Innovation
        y = np.array([vx_ned - self.x[VEL_X], vy_ned - self.x[VEL_Y]])
        R_val = self.flow_noise**2
        S = np.array([[self.P[3,3]+R_val, self.P[3,4]],
                       [self.P[4,3], self.P[4,4]+R_val]])
        det = S[0,0]*S[1,1] - S[0,1]*S[1,0]
        if abs(det) < 1e-10:
            return
        Si = np.array([[S[1,1], -S[0,1]], [-S[1,0], S[0,0]]]) / det

        K = np.zeros((N, 2))
        for i in range(N):
            K[i,0] = self.P[i,3]*Si[0,0] + self.P[i,4]*Si[0,1]
            K[i,1] = self.P[i,3]*Si[1,0] + self.P[i,4]*Si[1,1]

        dx = K @ y
        dx[ATT_Z] = 0
        self._apply_masked(dx)

        # Joseph form P update
        I_KH = np.eye(N)
        H = np.zeros((2, N))
        H[0, VEL_X] = 1
        H[1, VEL_Y] = 1
        I_KH -= K @ H
        R_mat = np.eye(2) * R_val
        self.P = I_KH @ self.P @ I_KH.T + K @ R_mat @ K.T
        self._enforce_constraints()

    def update_tof(self, distance):
        # Tilt correction
        roll = math.atan2(2*(self.q[3]*self.q[0]+self.q[1]*self.q[2]),
                          1-2*(self.q[0]**2+self.q[1]**2))
        pitch = math.asin(max(-1, min(1, 2*(self.q[3]*self.q[1]-self.q[2]*self.q[0]))))
        if abs(roll) > 0.7 or abs(pitch) > 0.7:
            return
        height = distance * math.cos(roll) * math.cos(pitch)

        y_val = -height - self.x[POS_Z]

        # Innovation gate
        if abs(y_val) > 0.5:
            return

        R_val = TOF_NOISE**2
        S = self.P[2,2] + R_val
        if S < 1e-10:
            return

        K = self.P[:, 2] / S
        dx = K * y_val
        dx[ATT_Z] = 0
        self._apply_masked(dx)

        # P update
        I_KH = np.eye(N)
        I_KH[:, 2] -= K
        self.P = I_KH @ self.P @ I_KH.T + np.outer(K, K) * R_val
        self._enforce_constraints()

    def update_accel_att(self, accel):
        ba = self.x[BA_X:BA_Z+1]
        a_c = accel - ba
        R = quat_to_dcm(self.q)

        # Expected gravity in body
        g_exp = np.array([-GRAVITY*R[2,0], -GRAVITY*R[2,1], -GRAVITY*R[2,2]])
        y = a_c - g_exp

        # H matrix (attitude + accel bias)
        H = np.zeros((3, N))
        H[0,ATT_Y] = GRAVITY*R[2,2]
        H[0,ATT_Z] = -GRAVITY*R[2,1]
        H[1,ATT_X] = -GRAVITY*R[2,2]
        H[1,ATT_Z] = GRAVITY*R[2,0]
        H[2,ATT_X] = GRAVITY*R[2,1]
        H[2,ATT_Y] = -GRAVITY*R[2,0]
        H[0,BA_X] = 1; H[1,BA_Y] = 1; H[2,BA_Z] = 1

        R_mat = np.eye(3) * ACCEL_ATT_NOISE**2
        PHT = self.P @ H.T
        S = H @ PHT + R_mat
        try:
            Si = np.linalg.inv(S)
        except:
            return
        K = PHT @ Si
        dx = K @ y
        dx[ATT_Z] = 0
        # Clamp attitude corrections
        for i in [ATT_X, ATT_Y]:
            dx[i] = max(-ATT_CORRECTION_CLAMP, min(ATT_CORRECTION_CLAMP, dx[i]))
        self._apply_masked(dx)

        I_KH = np.eye(N) - K @ H
        self.P = I_KH @ self.P @ I_KH.T + K @ R_mat @ K.T
        self._enforce_constraints()

    def _apply_masked(self, dx):
        for i in range(N):
            if not ((self.active_mask >> i) & 1):
                dx[i] = 0
        # Apply to state
        self.x += dx
        # Attitude: quaternion correction
        dq = rot_vec_to_quat(dx[ATT_X:ATT_Z+1])
        self.q = quat_multiply(self.q, dq)
        self.q /= np.linalg.norm(self.q)
        # Zero out attitude error (absorbed into quaternion)
        self.x[ATT_X:ATT_Z+1] = 0

    def _enforce_constraints(self):
        for i in range(N):
            if not ((self.active_mask >> i) & 1):
                self.P[i,i] = self.init_P_diag[i]
                self.P[i,:] = 0
                self.P[:,i] = 0
                self.P[i,i] = self.init_P_diag[i]
        # Symmetry and lower bound
        self.P = 0.5 * (self.P + self.P.T)
        for i in range(N):
            self.P[i,i] = max(self.P[i,i], 1e-12)


def load_log(path):
    """Load log and extract sensor events sorted by timestamp"""
    events = []
    with open(path) as f:
        for line in f:
            try:
                d = json.loads(line)
            except:
                continue
            events.append(d)
    return events


def run_eskf(events, accel_noise, accel_bias_noise, flow_noise, t0):
    """Run ESKF replay and return time series of accel bias and position"""
    eskf = ESKF(accel_noise, accel_bias_noise, flow_noise)

    # Initialize from first IMU
    for e in events:
        if e['id'] == 'imu':
            gb = e.get('gyro_bias', [0,0,0])
            ab = e.get('accel_bias', [0,0,0])
            q = e['quat']  # [x,y,z,w]
            eskf.q = np.array(q)
            eskf.x[BG_X:BG_Z+1] = gb
            eskf.x[BA_X:BA_Z+1] = ab
            break

    results = {'t': [], 'ba_x': [], 'ba_y': [], 'ba_z': [],
               'pos_x': [], 'pos_y': [], 'pos_z': [],
               'vel_x': [], 'vel_y': []}

    last_imu_ts = None
    last_flow_ts = None
    imu_count = 0
    # Only process during flight (state=3)
    flying = False

    for e in events:
        ts = e['ts'] / 1e6
        t_rel = ts - t0

        if e['id'] == 'status':
            flying = e['flight_state'] == 3

        if e['id'] == 'imu' and flying:
            if last_imu_ts is not None:
                dt = ts - last_imu_ts
                if 0.001 < dt < 0.05:
                    accel = np.array(e['accel_raw'])
                    gyro = np.array(e['gyro_raw'])
                    eskf.predict(accel, gyro, dt)

                    # Accel attitude update (at IMU rate, but subsample for speed)
                    imu_count += 1
                    if imu_count % 4 == 0:  # ~100Hz
                        eskf.update_accel_att(accel)

                    # Record every 40th sample (~10Hz)
                    if imu_count % 40 == 0:
                        results['t'].append(t_rel)
                        results['ba_x'].append(eskf.x[BA_X])
                        results['ba_y'].append(eskf.x[BA_Y])
                        results['ba_z'].append(eskf.x[BA_Z])
                        results['pos_x'].append(eskf.x[POS_X])
                        results['pos_y'].append(eskf.x[POS_Y])
                        results['pos_z'].append(eskf.x[POS_Z])
                        results['vel_x'].append(eskf.x[VEL_X])
                        results['vel_y'].append(eskf.x[VEL_Y])

            last_imu_ts = ts

        elif e['id'] == 'flow' and flying:
            if last_flow_ts is not None:
                dt_flow = ts - last_flow_ts
                if 0.005 < dt_flow < 0.1:
                    # Need current ToF distance - use latest from state
                    # For simplicity, get from tof_b events
                    pass  # handled below
            last_flow_ts = ts

        elif e['id'] == 'tof_b' and flying:
            dist_mm = e.get('distance', 0)
            if dist_mm > 20:
                eskf.update_tof(dist_mm / 1000.0)

    return results


def run_eskf_v2(log_path, accel_noise, accel_bias_noise, flow_noise):
    """Run ESKF with proper flow+tof integration"""
    events = load_log(log_path)
    t0 = events[0]['ts'] / 1e6

    eskf = ESKF(accel_noise, accel_bias_noise, flow_noise)

    # Init from first IMU
    for e in events:
        if e['id'] == 'imu':
            q_wxyz = e['quat']  # log format: [w,x,y,z]
            eskf.q = np.array([q_wxyz[1], q_wxyz[2], q_wxyz[3], q_wxyz[0]])  # [x,y,z,w]
            eskf.x[BG_X:BG_Z+1] = e.get('gyro_bias', [0,0,0])
            eskf.x[BA_X:BA_Z+1] = e.get('accel_bias', [0,0,0])
            break

    results = {'t': [], 'ba_x': [], 'ba_y': [], 'ba_z': [],
               'pos_x': [], 'pos_y': [], 'pos_z': [],
               'vel_x': [], 'vel_y': []}

    last_imu_ts = None
    latest_tof = 0.0
    latest_gyro = np.zeros(3)
    imu_count = 0
    flying = False

    for e in events:
        ts = e['ts'] / 1e6

        if e['id'] == 'status':
            flying = e['flight_state'] == 3

        if not flying:
            if e['id'] == 'imu':
                last_imu_ts = ts
            continue

        if e['id'] == 'imu':
            if last_imu_ts is not None:
                dt = ts - last_imu_ts
                if 0.001 < dt < 0.05:
                    accel = np.array(e['accel_raw'])
                    gyro = np.array(e['gyro_raw'])
                    latest_gyro = gyro
                    eskf.predict(accel, gyro, dt)

                    imu_count += 1
                    if imu_count % 4 == 0:
                        eskf.update_accel_att(accel)

                    if imu_count % 40 == 0:
                        t_rel = ts - t0
                        results['t'].append(t_rel)
                        results['ba_x'].append(eskf.x[BA_X])
                        results['ba_y'].append(eskf.x[BA_Y])
                        results['ba_z'].append(eskf.x[BA_Z])
                        results['pos_x'].append(eskf.x[POS_X])
                        results['pos_y'].append(eskf.x[POS_Y])
                        results['pos_z'].append(eskf.x[POS_Z])
                        results['vel_x'].append(eskf.x[VEL_X])
                        results['vel_y'].append(eskf.x[VEL_Y])
            last_imu_ts = ts

        elif e['id'] == 'tof_b':
            dist_m = e.get('distance', 0)
            if dist_m > 0.02:  # distance is already in meters
                latest_tof = dist_m
                eskf.update_tof(latest_tof)

        elif e['id'] == 'flow':
            dx = e['dx']
            dy = e['dy']
            squal = e.get('quality', 0)
            if squal >= 25 and latest_tof > FLOW_MIN_HEIGHT:
                dt_flow = 0.01  # 100Hz
                eskf.update_flow(dx, dy, latest_tof, dt_flow,
                                latest_gyro[0], latest_gyro[1])

    return results


def evaluate(results):
    """Score a run: lower is better"""
    if len(results['t']) == 0:
        return {'ba_drift': 999, 'pos_drift': 999, 'score': 999}

    ba_x = np.array(results['ba_x'])
    ba_y = np.array(results['ba_y'])
    pos_x = np.array(results['pos_x'])
    pos_y = np.array(results['pos_y'])

    # Bias drift: total change from initial
    ba_drift_x = abs(ba_x[-1] - ba_x[0]) if len(ba_x) > 0 else 0
    ba_drift_y = abs(ba_y[-1] - ba_y[0]) if len(ba_y) > 0 else 0
    ba_drift = max(ba_drift_x, ba_drift_y)

    # Position drift: max absolute position
    pos_max = max(np.max(np.abs(pos_x)), np.max(np.abs(pos_y)))

    # Score: penalize both bias drift and position error
    score = ba_drift * 10 + pos_max * 0.1

    return {'ba_drift': ba_drift, 'pos_drift': pos_max, 'score': score}


def main():
    log_path = 'logs/stampfly_udp_20260406T140522.jsonl'
    print(f"Loading {log_path}...")

    # Current values for reference
    CURRENT_ACCEL_NOISE = 0.5
    CURRENT_ACCEL_BIAS_NOISE = 0.01
    CURRENT_FLOW_NOISE = 0.01

    # Parameter grid
    accel_bias_noises = [0.0001, 0.0005, 0.001, 0.002, 0.005, 0.01]
    flow_noises = [0.005, 0.01, 0.02, 0.05, 0.1, 0.2]

    print(f"\nSweeping {len(accel_bias_noises)} x {len(flow_noises)} = {len(accel_bias_noises)*len(flow_noises)} combinations")
    print(f"Current: ACCEL_BIAS_NOISE={CURRENT_ACCEL_BIAS_NOISE}, FLOW_NOISE={CURRENT_FLOW_NOISE}")
    print()
    print(f"{'AB_NOISE':>10} {'FLOW_N':>8} {'BA_drift':>10} {'Pos_max':>10} {'Score':>8}")
    print("-" * 52)

    best_score = 999
    best_params = None
    all_results = []

    for abn in accel_bias_noises:
        for fn in flow_noises:
            try:
                results = run_eskf_v2(log_path, CURRENT_ACCEL_NOISE, abn, fn)
                metrics = evaluate(results)
                all_results.append((abn, fn, metrics, results))

                marker = ""
                if abn == CURRENT_ACCEL_BIAS_NOISE and fn == CURRENT_FLOW_NOISE:
                    marker = " <-- CURRENT"
                if metrics['score'] < best_score:
                    best_score = metrics['score']
                    best_params = (abn, fn)

                print(f"{abn:10.4f} {fn:8.3f} {metrics['ba_drift']:10.4f} {metrics['pos_drift']:10.3f} {metrics['score']:8.3f}{marker}")
            except Exception as ex:
                print(f"{abn:10.4f} {fn:8.3f}  ERROR: {ex}")

    print()
    print(f"=== Best: ACCEL_BIAS_NOISE={best_params[0]}, FLOW_NOISE={best_params[1]}, score={best_score:.3f} ===")

    # Show top 5
    all_results.sort(key=lambda x: x[2]['score'])
    print()
    print("Top 5:")
    for abn, fn, m, _ in all_results[:5]:
        print(f"  AB_NOISE={abn:.4f}  FLOW_N={fn:.3f}  BA_drift={m['ba_drift']:.4f}  Pos={m['pos_drift']:.3f}")

    # Show bias trajectory for best vs current
    print()
    print("=== Bias trajectory comparison ===")
    for abn, fn, m, res in all_results:
        if (abn, fn) == best_params or (abn == CURRENT_ACCEL_BIAS_NOISE and fn == CURRENT_FLOW_NOISE):
            label = "BEST" if (abn, fn) == best_params else "CURRENT"
            print(f"\n{label} (AB_N={abn}, FL_N={fn}):")
            t = res['t']
            bax = res['ba_x']
            bay = res['ba_y']
            px = res['pos_x']
            py = res['pos_y']
            for i in range(0, len(t), max(1, len(t)//10)):
                print(f"  t={t[i]:5.1f}s  ba=[{bax[i]:.4f},{bay[i]:.4f}]  pos=[{px[i]:.2f},{py[i]:.2f}]")


if __name__ == '__main__':
    main()
