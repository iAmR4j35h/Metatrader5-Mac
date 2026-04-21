#!/usr/bin/env python3
"""
MetaTrader 5 Bridge Server

This server runs in Python and waits for MT5 to connect.
MT5 acts as a client, connecting to this server.
"""

import socket
import threading
import json
import time
from datetime import datetime

HOST = '127.0.0.1'
PORT = 8222


class MT5Server:
    def __init__(self, host=HOST, port=PORT):
        self.host = host
        self.port = port
        self.server_socket = None
        self.client_socket = None
        self.running = False

    def start(self):
        """Start the server and wait for MT5 connection."""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)

        print(f"MT5 Bridge Server listening on {self.host}:{self.port}")
        print("Waiting for MetaTrader 5 to connect...")
        print("(Attach MT5BridgeClient.mq5 to a chart in MT5)")

        self.running = True

        while self.running:
            try:
                client, addr = self.server_socket.accept()
                print(f"\n✓ MetaTrader 5 connected from {addr}")
                self.handle_client(client)
            except Exception as e:
                if self.running:
                    print(f"Error: {e}")

    def handle_client(self, client):
        """Handle communication with MT5."""
        self.client_socket = client
        buffer = b""

        try:
            while self.running:
                data = client.recv(4096)
                if not data:
                    break

                buffer += data

                # Process complete messages
                while b'\n' in buffer:
                    pos = buffer.find(b'\n')
                    message = buffer[:pos].decode('utf-8').strip()
                    buffer = buffer[pos + 1:]

                    if message:
                        response = self.process_command(message)
                        client.send((response + '\n').encode('utf-8'))

        except Exception as e:
            print(f"Client error: {e}")
        finally:
            print("\n✗ MetaTrader 5 disconnected")
            self.client_socket = None
            client.close()

    def process_command(self, cmd):
        """Process a command from MT5."""
        parts = cmd.split('|')
        if not parts:
            return "ERR|code=2|message=Empty command"

        command = parts[0]
        params = {}
        for part in parts[1:]:
            if '=' in part:
                k, v = part.split('=', 1)
                params[k] = v

        # Route to handler
        handlers = {
            'PING': lambda: "OK|result=pong",
            'INIT': lambda: "OK|success=true|path=MT5",
            'VERSION': lambda: "OK|version=5.0|build=4321",
            'SYMBOL_TOTAL': lambda: "OK|total=0",  # MT5 should provide this
            'SYMBOL_GET': lambda: "OK|symbols=",
            'TICK': lambda: self.handle_tick(params),
            'ORDERS_TOTAL': lambda: "OK|total=0",
            'ORDERS_GET': lambda: "OK|orders=",
            'POSITIONS_TOTAL': lambda: "OK|total=0",
            'POSITIONS_GET': lambda: "OK|positions=",
            'ACCOUNT': lambda: "OK|login=0|server=|currency=USD|balance=0|equity=0|margin=0|margin_free=0",
            'TRADE': lambda: "ERR|code=8|message=Trading not implemented in server",
        }

        handler = handlers.get(command)
        if handler:
            try:
                return handler()
            except Exception as e:
                return f"ERR|code=1|message={str(e)}"
        else:
            return f"ERR|code=7|message=Unknown command: {command}"

    def handle_tick(self, params):
        """Handle tick request - should get from MT5 but server doesn't have direct access."""
        symbol = params.get('symbol', '')
        return f"ERR|code=4|message=Server cannot access MT5 data directly. Use MT5BridgeClient.mq5"

    def stop(self):
        """Stop the server."""
        self.running = False
        if self.client_socket:
            self.client_socket.close()
        if self.server_socket:
            self.server_socket.close()


def main():
    """Main entry point."""
    print("=" * 60)
    print("MetaTrader 5 Bridge Server")
    print("=" * 60)
    print()

    server = MT5Server()

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\nShutting down...")
        server.stop()
        print("Server stopped")


if __name__ == "__main__":
    main()
