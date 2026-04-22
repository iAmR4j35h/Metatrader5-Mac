#!/usr/bin/env python3
"""
MetaTrader5 Bridge Server Entry Point

Run the bridge server as a module:
    python -m MetaTrader5
    python -m MetaTrader5 --host 127.0.0.1 --port 8222
"""

import argparse
import sys


def main():
    """Main entry point for running the bridge server."""
    parser = argparse.ArgumentParser(
        description='MetaTrader 5 Bridge Server for macOS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m MetaTrader5                    # Start server on default port 8222
  python -m MetaTrader5 --port 8080        # Start on custom port
  python -m MetaTrader5 --host 0.0.0.0     # Listen on all interfaces

Prerequisites:
  - MetaTrader 5 running with MT5BridgeClient EA attached
  - MT5 EA configured to connect to this host:port
        """
    )

    parser.add_argument(
        '--host',
        type=str,
        default='127.0.0.1',
        help='Host IP to listen on (default: 127.0.0.1)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8222,
        help='Port to listen on (default: 8222)'
    )

    args = parser.parse_args()

    print(f"Starting MetaTrader 5 Bridge Server on {args.host}:{args.port}")
    print()

    from ._bridge_server import MT5BridgeServer

    server = MT5BridgeServer(host=args.host, port=args.port)

    try:
        server.start()
    except KeyboardInterrupt:
        print("\n\n[!] Shutting down...")
        server.stop()
        print("[*] Server stopped")
        sys.exit(0)


if __name__ == '__main__':
    main()
