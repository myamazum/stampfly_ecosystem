#!/usr/bin/env python3
"""
StampFly CLI Helper - Send commands to StampFly via WiFi CLI

Usage:
    python tools/stampfly_cli.py jump [altitude] [hover_duration]
    python tools/stampfly_cli.py takeoff [altitude]
    python tools/stampfly_cli.py land
    python tools/stampfly_cli.py hover [altitude] [duration]
    python tools/stampfly_cli.py flight status
    python tools/stampfly_cli.py flight cancel

Examples:
    python tools/stampfly_cli.py jump 0.15 0.5
    python tools/stampfly_cli.py takeoff 0.5
    python tools/stampfly_cli.py land
"""

import socket
import sys
import time

# StampFly default WiFi AP settings
STAMPFLY_IP = "192.168.4.1"
STAMPFLY_PORT = 23  # Telnet port for WiFi CLI
TIMEOUT = 2.0

def send_command(cmd, silent=False):
    """Send a command to StampFly and return response"""
    try:
        if not silent:
            print(f"🚁 Connecting to StampFly at {STAMPFLY_IP}:{STAMPFLY_PORT}...")

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        sock.connect((STAMPFLY_IP, STAMPFLY_PORT))

        if not silent:
            print("✅ Connected.")

        # Read welcome message
        welcome = sock.recv(1024).decode('utf-8', errors='ignore')

        # Send command
        if not silent:
            print(f"📤 Sending command: {cmd}")
        sock.send(f"{cmd}\n".encode())

        # Wait a bit for response
        time.sleep(0.1)

        # Read response
        response = sock.recv(2048).decode('utf-8', errors='ignore')

        sock.close()

        if not silent:
            print(f"📥 Response: {response.strip()}")

        return True, response

    except socket.timeout:
        if not silent:
            print("❌ Timeout: StampFly not responding")
        return False, "Timeout"
    except ConnectionRefusedError:
        if not silent:
            print("❌ Connection refused: Is StampFly powered on and WiFi enabled?")
        return False, "Connection refused"
    except Exception as e:
        if not silent:
            print(f"❌ Error: {e}")
        return False, str(e)

def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python tools/stampfly_cli.py jump [altitude] [hover_duration]")
        print("  python tools/stampfly_cli.py takeoff [altitude]")
        print("  python tools/stampfly_cli.py land")
        print("  python tools/stampfly_cli.py hover [altitude] [duration]")
        print("  python tools/stampfly_cli.py flight status")
        print("  python tools/stampfly_cli.py flight cancel")
        print("")
        print("Examples:")
        print("  python tools/stampfly_cli.py jump 0.15 0.5")
        print("  python tools/stampfly_cli.py takeoff 0.5")
        print("  python tools/stampfly_cli.py land")
        sys.exit(1)

    # Build command from arguments
    cmd = " ".join(sys.argv[1:])

    success, response = send_command(cmd)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()
