#!/usr/bin/env python3
"""Debug script to test MT5 connection."""

import socket
import sys

def test_connection():
    print("=" * 60)
    print("Testing MT5 Bridge Connection")
    print("=" * 60)

    # Test 1: Connect to bridge server
    print("\n[1] Connecting to bridge server...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect(('127.0.0.1', 8222))
        print("    ✓ Connected to bridge server")
    except Exception as e:
        print(f"    ✗ Failed: {e}")
        return

    # Test 2: Send VERSION command
    print("\n[2] Sending VERSION command...")
    try:
        message = "VERSION\n"
        sock.send(message.encode('utf-8'))
        print(f"    → Sent: {repr(message)}")

        # Receive response
        sock.settimeout(5)
        response = sock.recv(4096)
        print(f"    ← Raw response: {repr(response)}")

        if response:
            text = response.decode('utf-8').strip()
            print(f"    ← Decoded: {text}")

            if text.startswith("OK|"):
                print("    ✓ Got valid response")
            else:
                print(f"    ✗ Unexpected response format")
        else:
            print("    ✗ Empty response")

    except socket.timeout:
        print("    ✗ Timeout waiting for response")
    except Exception as e:
        print(f"    ✗ Error: {e}")

    # Test 3: Send ACCOUNT command
    print("\n[3] Sending ACCOUNT command...")
    try:
        message = "ACCOUNT\n"
        sock.send(message.encode('utf-8'))
        print(f"    → Sent: {repr(message)}")

        sock.settimeout(5)
        response = sock.recv(4096)
        print(f"    ← Raw response: {repr(response)}")

        if response:
            text = response.decode('utf-8').strip()
            print(f"    ← Decoded: {text}")

            if text.startswith("OK|"):
                print("    ✓ Got account info")
            elif text.startswith("ERR|"):
                print(f"    ! Account error (might not be logged in)")
            else:
                print(f"    ✗ Unexpected response")

    except socket.timeout:
        print("    ✗ Timeout")
    except Exception as e:
        print(f"    ✗ Error: {e}")

    sock.close()
    print("\n[4] Connection closed")
    print("=" * 60)

if __name__ == "__main__":
    test_connection()
