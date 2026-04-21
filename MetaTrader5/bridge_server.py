#!/usr/bin/env python3
"""
MetaTrader 5 Bridge Server

This server acts as a bridge between Python scripts and MT5.
- MT5 (via MT5BridgeClient EA) connects to this server
- Python scripts connect to this server
- Server forwards requests between them

Usage:
    python -m MetaTrader5.bridge_server
"""

import socket
import threading
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any

HOST = '127.0.0.1'
PORT = 8222


class MT5BridgeServer:
    """Bridge server that connects Python scripts to MT5."""

    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.mt5_socket = None  # Connection from MT5 EA
        self.script_sockets = []  # Connections from Python scripts
        self.running = False
        self.lock = threading.Lock()

    def start(self):
        """Start the bridge server."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)

        print("=" * 70)
        print("         MetaTrader 5 Bridge Server")
        print("=" * 70)
        print(f"\nListening on {self.host}:{self.port}")
        print("\nWaiting for connections:")
        print("  1. MT5 Client EA (from MetaTrader)")
        print("  2. Python scripts (e.g., login_and_show_balance.py)")
        print("\n" + "=" * 70)

        self.running = True

        while self.running:
            try:
                client, addr = self.server_socket.accept()
                print(f"\n[+] New connection from {addr}")
                print(f"    MT5 connected status: {self.mt5_socket is not None}")

                # Determine if this is MT5 or a Python script
                handler = threading.Thread(
                    target=self.handle_client,
                    args=(client, addr)
                )
                handler.daemon = True
                handler.start()

            except Exception as e:
                if self.running:
                    print(f"\n[!] Error: {e}")

    def handle_client(self, client: socket.socket, addr):
        """Handle a new client connection."""
        try:
            # First message determines client type
            # Read without strip to preserve newlines for protocol detection
            data = client.recv(1024).decode('utf-8')
            print(f"    First message: {repr(data)}")

            # Remove just trailing whitespace, keep content for processing
            data_stripped = data.strip()
            if not data_stripped:
                print(f"    [!] Empty first message from {addr}, closing")
                client.close()
                return

            # MT5 EA connects and immediately sends PING or INIT to identify itself
            # Python scripts send commands like ACCOUNT, VERSION, etc.
            # Distinguish by checking message patterns:
            # - MT5 sends exactly "PING" or "INIT" (no params) to identify
            # - Python sends commands with or without params for actual operations
            # - Also check if MT5 is already connected to avoid confusion

            parts = data_stripped.split('|')
            command = parts[0] if parts else ""

            with self.lock:
                mt5_not_connected = self.mt5_socket is None

            # MT5 identifies itself by sending bare PING or INIT (no parameters)
            # Python might send PING too but with different context
            is_mt5_identify = (command == "PING" or command == "INIT") and len(parts) == 1

            print(f"    Command: {command}, parts: {len(parts)}, is_mt5_identify: {is_mt5_identify}, mt5_not_connected: {mt5_not_connected}")

            if mt5_not_connected and is_mt5_identify:
                print(f"[+] MetaTrader 5 connected from {addr}")
                self.handle_mt5_client(client, addr, data_stripped)
            else:
                print(f"[+] Python client connected from {addr}")
                self.handle_script_client(client, addr, data)

        except Exception as e:
            print(f"\n[!] Error handling client {addr}: {e}")
            client.close()

    def handle_mt5_client(self, client: socket.socket, addr, initial_data: str = ""):
        """Handle MT5 connection.

        MT5 connects and maintains a persistent connection.
        The server only sends responses to MT5's initial identification (PING/INIT).
        After that, MT5 just listens for forwarded commands from Python.
        """
        with self.lock:
            # Close existing MT5 connection if any
            if self.mt5_socket:
                try:
                    self.mt5_socket.close()
                except:
                    pass
            self.mt5_socket = client

        print(f"[*] MT5 bridge active - waiting for commands")

        try:
            # Only process the initial identification message (PING/INIT)
            buffer = initial_data

            # Process complete messages in initial data
            while '\n' in buffer:
                pos = buffer.find('\n')
                message = buffer[:pos]
                buffer = buffer[pos + 1:]

                if message:
                    response = self.process_mt5_message(message)
                    client.send((response + '\n').encode('utf-8'))
                    print(f"    [Server→MT5] {response[:50]}")

            # Keep connection alive - MT5 doesn't send commands, only receives forwarded ones
            # forward_to_mt5 will read responses when Python sends commands
            # Just sleep here until MT5 disconnects or server stops
            while self.running and self.mt5_socket == client:
                time.sleep(1)

        except Exception as e:
            print(f"\n[!] MT5 connection error: {e}")
        finally:
            with self.lock:
                if self.mt5_socket == client:
                    self.mt5_socket = None
            try:
                client.close()
            except:
                pass
            print(f"\n[-] MetaTrader 5 disconnected")

    def handle_script_client(self, client: socket.socket, addr, first_message: str):
        """Handle Python script connection."""
        with self.lock:
            self.script_sockets.append(client)

        try:
            # Process first message and any subsequent ones
            buffer = first_message

            while self.running:
                # Wait for complete message
                while '\n' not in buffer:
                    data = client.recv(4096).decode('utf-8')
                    if not data:
                        return
                    buffer += data

                pos = buffer.find('\n')
                message = buffer[:pos]
                buffer = buffer[pos + 1:]

                if message:
                    # Forward to MT5 and get response
                    response = self.forward_to_mt5(message)
                    client.send((response + '\n').encode('utf-8'))

        except Exception as e:
            print(f"\n[!] Script error: {e}")
        finally:
            with self.lock:
                if client in self.script_sockets:
                    self.script_sockets.remove(client)
            try:
                client.close()
            except:
                pass
            print(f"\n[-] Python script disconnected")

    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.mt5_socket = None  # Connection from MT5 EA
        self.script_sockets = []  # Connections from Python scripts
        self.running = False
        self.lock = threading.Lock()
        self._mt5_response_buffer = ""  # Buffer for MT5 responses

    def forward_to_mt5(self, message: str) -> str:
        """Forward a message to MT5 and return the response."""
        with self.lock:
            if not self.mt5_socket:
                print(f"    [!] Cannot forward '{message[:20]}...' - MT5 not connected")
                return "ERR|code=-10004|message=MT5 not connected"

            try:
                # Send to MT5
                print(f"    [→MT5] {message[:50]}")
                self.mt5_socket.send((message + '\n').encode('utf-8'))

                # Wait for response (with timeout)
                # MT5 might send multiple responses if commands were queued
                self.mt5_socket.settimeout(30)

                # Read data until we have at least one complete response
                while '\n' not in self._mt5_response_buffer:
                    data = self.mt5_socket.recv(4096).decode('utf-8')
                    if not data:
                        return "ERR|code=-10002|message=MT5 disconnected"
                    self._mt5_response_buffer += data

                # Extract first complete response
                pos = self._mt5_response_buffer.find('\n')
                response = self._mt5_response_buffer[:pos].strip()
                self._mt5_response_buffer = self._mt5_response_buffer[pos + 1:]

                self.mt5_socket.settimeout(None)

                print(f"    [←MT5] {response[:50]}")
                return response

            except socket.timeout:
                print(f"    [!] MT5 timeout waiting for response")
                return "ERR|code=-10005|message=MT5 timeout"
            except Exception as e:
                print(f"    [!] Error forwarding to MT5: {e}")
                return f"ERR|code=-10000|message={str(e)}"

    def process_mt5_message(self, message: str) -> str:
        """Process a message from MT5 (ping, etc.)."""
        parts = message.split('|')
        command = parts[0] if parts else ""

        if command == "PING":
            print(f"    [MT5→Server] PING")
            return "OK|result=pong"
        elif command == "INIT":
            print(f"    [MT5→Server] INIT")
            return "OK|success=true|path=MT5"
        else:
            print(f"    [Python→MT5] {message[:50]}...")
            # Forward to MT5 and get response
            return self.forward_to_mt5(message)

    def stop(self):
        """Stop the server."""
        self.running = False
        if self.mt5_socket:
            self.mt5_socket.close()
        for sock in self.script_sockets:
            sock.close()
        if self.server_socket:
            self.server_socket.close()


def main():
    """Main entry point."""
    server = MT5BridgeServer()

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\n[!] Shutting down...")
        server.stop()
        print("[*] Server stopped")


if __name__ == "__main__":
    main()
