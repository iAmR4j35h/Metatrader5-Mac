#!/usr/bin/env python3
"""Simple test to debug connection."""

import socket
import sys

def test_raw_connection():
    print("=" * 60)
    print("Raw Connection Test")
    print("=" * 60)

    try:
        # Connect to bridge
        print("\n[1] Connecting to bridge server...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 8222))
        print("    ✓ Connected")

        # Send VERSION
        print("\n[2] Sending VERSION...")
        sock.send(b"VERSION\n")
        print("    → Sent: VERSION")

        # Receive response
        print("\n[3] Waiting for response...")
        sock.settimeout(10)
        response = sock.recv(4096)
        print(f"    ← Raw: {response}")
        print(f"    ← Decoded: {response.decode('utf-8').strip()}")

        # Send ACCOUNT
        print("\n[4] Sending ACCOUNT...")
        sock.send(b"ACCOUNT\n")
        print("    → Sent: ACCOUNT")

        response = sock.recv(4096)
        print(f"    ← Raw: {response}")
        print(f"    ← Decoded: {response.decode('utf-8').strip()}")

        sock.close()
        print("\n[5] Done!")

    except Exception as e:
        print(f"\n    ✗ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_raw_connection()
