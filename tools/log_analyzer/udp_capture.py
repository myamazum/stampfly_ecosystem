#!/usr/bin/env python3
"""
udp_capture.py - UDP Telemetry Capture Tool for StampFly

Captures full-rate sensor data from StampFly via UDP.
Each sensor type arrives as independent packets at its native rate.
StampFly からフルレートセンサデータを UDP でキャプチャ。
各センサは固有レートの独立パケットとして到着する。

Packet IDs:
    0x40  IMU + ESKF (400Hz, batch 4)
    0x41  Position + Velocity (400Hz, batch 4)
    0x42  Control Input (50Hz, batch 4)
    0x43  Optical Flow (100Hz, batch 4)
    0x44  ToF (30Hz, batch 4)
    0x45  Barometer (50Hz, batch 4)
    0x46  Magnetometer (25Hz, batch 4)
    0x4F  Status / Heartbeat (1Hz)

Usage:
    python udp_capture.py [options]
    sf log wifi [options]

Examples:
    python udp_capture.py -d 30              # 30 seconds capture
    python udp_capture.py -d 60 -o flight.csv
"""

import argparse
import csv
import socket
import struct
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# =============================================================================
# Packet definitions (must match udp_telemetry.hpp)
# パケット定義（udp_telemetry.hpp と一致させること）
# =============================================================================

PKT_IMU_ESKF  = 0x40
PKT_POS_VEL   = 0x41
PKT_CONTROL   = 0x42
PKT_FLOW      = 0x43
PKT_TOF       = 0x44
PKT_BARO      = 0x45
PKT_MAG       = 0x46
PKT_STATUS    = 0x4F

CMD_START_LOG  = 0xF0
CMD_STOP_LOG   = 0xF1
CMD_HEARTBEAT  = 0xF2

UDP_LOG_PORT = 8890

# struct format strings for each sample type
# 各サンプル型の struct フォーマット
# '<' = little-endian

# ImuEskfSample: 80 bytes
#   timestamp(I) + gyro(3f) + accel(3f) + gyro_raw(3f) + accel_raw(3f) + quat(4f) + bias(6h)
FMT_IMU_ESKF = '<I 3f 3f 3f 3f 4f 3h 3h'
assert struct.calcsize(FMT_IMU_ESKF) == 80

# PosVelSample: 28 bytes
FMT_POS_VEL = '<I 3f 3f'
assert struct.calcsize(FMT_POS_VEL) == 28

# ControlSample: 20 bytes
FMT_CONTROL = '<I 4f'
assert struct.calcsize(FMT_CONTROL) == 20

# FlowSample: 9 bytes
FMT_FLOW = '<I 2h B'
assert struct.calcsize(FMT_FLOW) == 9

# ToFSample: 14 bytes
FMT_TOF = '<I 2f 2B'
assert struct.calcsize(FMT_TOF) == 14

# BaroSample: 12 bytes
FMT_BARO = '<I 2f'
assert struct.calcsize(FMT_BARO) == 12

# MagSample: 16 bytes
FMT_MAG = '<I 3f'
assert struct.calcsize(FMT_MAG) == 16

# Header: 4 bytes
FMT_HEADER = '<B H B'
assert struct.calcsize(FMT_HEADER) == 4

SAMPLE_INFO = {
    PKT_IMU_ESKF: ('IMU+ESKF',  FMT_IMU_ESKF, 80),
    PKT_POS_VEL:  ('Pos+Vel',   FMT_POS_VEL,  28),
    PKT_CONTROL:  ('Control',   FMT_CONTROL,   20),
    PKT_FLOW:     ('Flow',      FMT_FLOW,       9),
    PKT_TOF:      ('ToF',       FMT_TOF,       14),
    PKT_BARO:     ('Baro',      FMT_BARO,      12),
    PKT_MAG:      ('Mag',       FMT_MAG,       16),
}

# CSV column names per packet type
# パケット型ごとの CSV 列名
CSV_COLUMNS = {
    PKT_IMU_ESKF: [
        'timestamp_us',
        'gyro_x', 'gyro_y', 'gyro_z',
        'accel_x', 'accel_y', 'accel_z',
        'gyro_raw_x', 'gyro_raw_y', 'gyro_raw_z',
        'accel_raw_x', 'accel_raw_y', 'accel_raw_z',
        'quat_w', 'quat_x', 'quat_y', 'quat_z',
        'gyro_bias_x', 'gyro_bias_y', 'gyro_bias_z',
        'accel_bias_x', 'accel_bias_y', 'accel_bias_z',
    ],
    PKT_POS_VEL: [
        'timestamp_us',
        'pos_x', 'pos_y', 'pos_z',
        'vel_x', 'vel_y', 'vel_z',
    ],
    PKT_CONTROL: [
        'timestamp_us',
        'ctrl_throttle', 'ctrl_roll', 'ctrl_pitch', 'ctrl_yaw',
    ],
    PKT_FLOW: [
        'timestamp_us',
        'flow_x', 'flow_y', 'flow_quality',
    ],
    PKT_TOF: [
        'timestamp_us',
        'tof_bottom', 'tof_front', 'tof_bottom_status', 'tof_front_status',
    ],
    PKT_BARO: [
        'timestamp_us',
        'baro_altitude', 'baro_pressure',
    ],
    PKT_MAG: [
        'timestamp_us',
        'mag_x', 'mag_y', 'mag_z',
    ],
}


# =============================================================================
# Packet parser
# パケットパーサー
# =============================================================================

def verify_checksum(data: bytes) -> bool:
    """Verify XOR checksum (last byte = XOR of all preceding bytes)"""
    xor_val = 0
    for b in data[:-1]:
        xor_val ^= b
    return xor_val == data[-1]


def parse_packet(data: bytes) -> list:
    """Parse a UDP telemetry packet into list of (packet_id, sample_dict) tuples.
    Returns empty list on error."""

    if len(data) < 5:  # minimum: header(4) + checksum(1)
        return []

    if not verify_checksum(data):
        return []

    # Parse header
    pkt_id, seq, count = struct.unpack_from(FMT_HEADER, data, 0)

    if pkt_id not in SAMPLE_INFO:
        # Status packet (0x4F) — handle separately
        if pkt_id == PKT_STATUS:
            return [(PKT_STATUS, {'raw': data})]
        return []

    name, fmt, sample_size = SAMPLE_INFO[pkt_id]
    columns = CSV_COLUMNS[pkt_id]

    expected_size = 4 + sample_size * count + 1
    if len(data) != expected_size:
        return []

    results = []
    offset = 4  # after header
    for i in range(count):
        values = struct.unpack_from(fmt, data, offset)
        sample = dict(zip(columns, values))

        # Scale bias values back from int16 × 10000 to float
        # バイアス値を int16 × 10000 から float に戻す
        if pkt_id == PKT_IMU_ESKF:
            for key in ['gyro_bias_x', 'gyro_bias_y', 'gyro_bias_z',
                        'accel_bias_x', 'accel_bias_y', 'accel_bias_z']:
                sample[key] = sample[key] / 10000.0

        results.append((pkt_id, sample))
        offset += sample_size

    return results


# =============================================================================
# UDP Capture class
# UDP キャプチャクラス
# =============================================================================

class UDPTelemetryCapture:
    """Captures UDP telemetry from StampFly and saves to CSV."""

    def __init__(self, vehicle_ip: str = '192.168.4.1', port: int = UDP_LOG_PORT):
        self.vehicle_ip = vehicle_ip
        self.port = port
        self.sock = None
        self.running = False

        # Per-sensor sample storage
        # センサごとのサンプル格納
        self.samples = defaultdict(list)  # {pkt_id: [sample_dict, ...]}

        # Statistics
        self.packet_count = defaultdict(int)
        self.sample_count = defaultdict(int)
        self.bytes_received = 0
        self.checksum_errors = 0
        self.seq_gaps = defaultdict(int)
        self.last_seq = {}
        self.start_time = 0
        self.end_time = 0

    def start(self):
        """Create socket, send start command, begin capture."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.settimeout(1.0)

        # Bind to receive responses
        # 応答を受信するためにバインド
        self.sock.bind(('', 0))  # OS picks a free port

        # Send start command
        # 開始コマンド送信
        self.sock.sendto(bytes([CMD_START_LOG]), (self.vehicle_ip, self.port))
        self.running = True
        self.start_time = time.time()

    def stop(self):
        """Send stop command and close socket."""
        if self.sock and self.running:
            try:
                self.sock.sendto(bytes([CMD_STOP_LOG]), (self.vehicle_ip, self.port))
            except Exception:
                pass
            self.running = False
            self.end_time = time.time()

    def _heartbeat_thread(self):
        """Send heartbeat every 2 seconds."""
        while self.running:
            try:
                self.sock.sendto(bytes([CMD_HEARTBEAT]), (self.vehicle_ip, self.port))
            except Exception:
                pass
            time.sleep(2.0)

    def capture(self, duration: float, progress_cb=None) -> bool:
        """Run capture for specified duration.
        Returns True on success."""

        self.start()

        # Start heartbeat thread
        # ハートビートスレッド開始
        hb_thread = threading.Thread(target=self._heartbeat_thread, daemon=True)
        hb_thread.start()

        deadline = time.time() + duration

        try:
            while time.time() < deadline and self.running:
                try:
                    data, addr = self.sock.recvfrom(2048)
                except socket.timeout:
                    continue

                self.bytes_received += len(data)

                # Parse packet
                results = parse_packet(data)
                if not results:
                    self.checksum_errors += 1
                    continue

                for pkt_id, sample in results:
                    if pkt_id == PKT_STATUS:
                        continue  # Skip status packets for CSV

                    self.sample_count[pkt_id] += 1
                    self.samples[pkt_id].append(sample)

                # Track packet-level stats
                pkt_id = data[0]
                self.packet_count[pkt_id] += 1

                # Sequence gap detection
                # シーケンスギャップ検出
                if pkt_id in SAMPLE_INFO:
                    _, seq, _ = struct.unpack_from(FMT_HEADER, data, 0)
                    if pkt_id in self.last_seq:
                        expected = (self.last_seq[pkt_id] + 1) & 0xFFFF
                        if seq != expected:
                            gap = (seq - expected) & 0xFFFF
                            self.seq_gaps[pkt_id] += gap
                    self.last_seq[pkt_id] = seq

                # Progress callback
                if progress_cb:
                    elapsed = time.time() - self.start_time
                    progress_cb(elapsed, duration, sum(self.sample_count.values()))

        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

        return sum(self.sample_count.values()) > 0

    def print_stats(self):
        """Print capture statistics."""
        duration = (self.end_time or time.time()) - self.start_time
        total_samples = sum(self.sample_count.values())

        print(f"\n{'='*60}")
        print(f"  UDP Telemetry Capture Statistics")
        print(f"{'='*60}")
        print(f"  Duration:     {duration:.1f}s")
        print(f"  Total bytes:  {self.bytes_received:,}")
        print(f"  Bandwidth:    {self.bytes_received / duration / 1024:.1f} KB/s")
        print(f"  Checksum err: {self.checksum_errors}")
        print()

        pkt_names = {v[0]: k for k, v in SAMPLE_INFO.items()}
        print(f"  {'Type':<12} {'Packets':>8} {'Samples':>8} {'Rate':>8} {'Gaps':>6}")
        print(f"  {'-'*12} {'-'*8} {'-'*8} {'-'*8} {'-'*6}")

        for pkt_id, (name, _, _) in sorted(SAMPLE_INFO.items()):
            pkts = self.packet_count.get(pkt_id, 0)
            samps = self.sample_count.get(pkt_id, 0)
            rate = samps / duration if duration > 0 else 0
            gaps = self.seq_gaps.get(pkt_id, 0)
            print(f"  {name:<12} {pkts:>8} {samps:>8} {rate:>7.1f}Hz {gaps:>6}")

        print(f"  {'─'*12} {'─'*8} {'─'*8} {'─'*8} {'─'*6}")
        print(f"  {'TOTAL':<12} {sum(self.packet_count.values()):>8} {total_samples:>8}")
        print()

    def save_jsonl(self, filepath: str):
        """Save captured data as JSONLines (1 line = 1 sensor sample).
        JSONLines形式で保存（1行 = 1センササンプル）。

        Each line is a self-describing JSON object with sensor type as 'id'.
        各行はセンサ種別を 'id' フィールドに持つ自己記述的 JSON オブジェクト。

        Example:
          {"id":"imu","ts":75834074,"gyro":[0.01,0.02,-0.003],"accel":[0.12,-0.08,-9.81],...}
          {"id":"posvel","ts":75834074,"pos":[1.2,0.5,-0.03],"vel":[0.01,-0.02,0.001]}
          {"id":"flow","ts":75836000,"dx":31,"dy":23,"quality":35}
        """
        import json

        # Sensor ID to human-readable name and field structure
        # センサIDから人間が読める名前とフィールド構造へのマッピング
        JSONL_FORMAT = {
            PKT_IMU_ESKF: lambda s: {
                'id': 'imu',
                'ts': s['timestamp_us'],
                'gyro': [s['gyro_x'], s['gyro_y'], s['gyro_z']],
                'accel': [s['accel_x'], s['accel_y'], s['accel_z']],
                'gyro_raw': [s['gyro_raw_x'], s['gyro_raw_y'], s['gyro_raw_z']],
                'accel_raw': [s['accel_raw_x'], s['accel_raw_y'], s['accel_raw_z']],
                'quat': [s['quat_w'], s['quat_x'], s['quat_y'], s['quat_z']],
                'gyro_bias': [s['gyro_bias_x'], s['gyro_bias_y'], s['gyro_bias_z']],
                'accel_bias': [s['accel_bias_x'], s['accel_bias_y'], s['accel_bias_z']],
            },
            PKT_POS_VEL: lambda s: {
                'id': 'posvel',
                'ts': s['timestamp_us'],
                'pos': [s['pos_x'], s['pos_y'], s['pos_z']],
                'vel': [s['vel_x'], s['vel_y'], s['vel_z']],
            },
            PKT_CONTROL: lambda s: {
                'id': 'ctrl',
                'ts': s['timestamp_us'],
                'throttle': s['ctrl_throttle'],
                'roll': s['ctrl_roll'],
                'pitch': s['ctrl_pitch'],
                'yaw': s['ctrl_yaw'],
            },
            PKT_FLOW: lambda s: {
                'id': 'flow',
                'ts': s['timestamp_us'],
                'dx': s['flow_x'],
                'dy': s['flow_y'],
                'quality': s['flow_quality'],
            },
            PKT_TOF: lambda s: {
                'id': 'tof',
                'ts': s['timestamp_us'],
                'bottom': s['tof_bottom'],
                'front': s['tof_front'],
                'status_bottom': s['tof_bottom_status'],
                'status_front': s['tof_front_status'],
            },
            PKT_BARO: lambda s: {
                'id': 'baro',
                'ts': s['timestamp_us'],
                'altitude': s['baro_altitude'],
                'pressure': s['baro_pressure'],
            },
            PKT_MAG: lambda s: {
                'id': 'mag',
                'ts': s['timestamp_us'],
                'x': s['mag_x'],
                'y': s['mag_y'],
                'z': s['mag_z'],
            },
        }

        # Collect all samples with their packet ID, sort by timestamp
        # 全サンプルをパケットID付きで収集し、タイムスタンプ順にソート
        all_entries = []
        for pkt_id, samples in self.samples.items():
            fmt_fn = JSONL_FORMAT.get(pkt_id)
            if not fmt_fn:
                continue
            for sample in samples:
                all_entries.append((sample['timestamp_us'], pkt_id, sample))

        all_entries.sort(key=lambda e: e[0])

        # Write JSONLines
        with open(filepath, 'w') as f:
            for ts, pkt_id, sample in all_entries:
                obj = JSONL_FORMAT[pkt_id](sample)
                f.write(json.dumps(obj, separators=(',', ':')) + '\n')

        print(f"  Saved: {filepath} ({len(all_entries)} lines)")


# =============================================================================
# Progress bar
# プログレスバー
# =============================================================================

def progress_bar(elapsed: float, duration: float, total_samples: int):
    """Print progress bar to stderr."""
    pct = min(elapsed / duration * 100, 100) if duration > 0 else 0
    bar_len = 30
    filled = int(bar_len * pct / 100)
    bar = '█' * filled + '░' * (bar_len - filled)
    sys.stderr.write(f"\r  [{bar}] {pct:5.1f}%  {total_samples:>6} samples  {elapsed:.1f}s/{duration:.0f}s")
    sys.stderr.flush()


# =============================================================================
# CLI entry point
# =============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="UDP telemetry capture for StampFly",
    )
    parser.add_argument('-o', '--output', help="Output CSV filename (auto-generated if not specified)")
    parser.add_argument('-d', '--duration', type=float, default=30.0, help="Capture duration in seconds (default: 30)")
    parser.add_argument('-i', '--ip', default='192.168.4.1', help="StampFly IP address (default: 192.168.4.1)")
    parser.add_argument('-p', '--port', type=int, default=UDP_LOG_PORT, help=f"UDP port (default: {UDP_LOG_PORT})")
    parser.add_argument('--no-save', action='store_true', help="Don't save to file, just display stats")
    args = parser.parse_args()

    # Generate output filename
    output = args.output
    if not output and not args.no_save:
        timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
        output = f"stampfly_udp_{timestamp}.jsonl"

    print(f"Capturing UDP telemetry from {args.ip}:{args.port}")
    print(f"  Duration: {args.duration}s")
    if output:
        print(f"  Output: {output}")
    print()

    capture = UDPTelemetryCapture(args.ip, args.port)
    success = capture.capture(args.duration, progress_bar)
    print()  # Newline after progress bar

    if not success:
        print("No data received. Check WiFi connection and StampFly power.")
        return 1

    capture.print_stats()

    if not args.no_save and output:
        capture.save_jsonl(output)

    return 0


if __name__ == '__main__':
    sys.exit(main() or 0)
