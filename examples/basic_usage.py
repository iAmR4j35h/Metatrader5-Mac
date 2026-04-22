#!/usr/bin/env python3
"""
Basic example of using MetaTrader5 on macOS.

This example demonstrates how to:
1. Start the bridge server (automatically or separately)
2. Connect to MT5 running in Wine/CrossOver or VM
3. Get account information
4. Retrieve symbol data
5. Place a trade (commented out for safety)

Quick Start:
    python basic_usage.py

The script will automatically start the bridge server, or you can run it
separately with: python -m MetaTrader5
"""

import MetaTrader5 as mt5
from datetime import datetime
import time
import subprocess
import sys
import os

# ============================================================
# CONFIGURATION
# ============================================================
# Set to True to automatically start bridge server in this script
# Set to False if you prefer to run server separately:
#   python -m MetaTrader5
AUTO_START_SERVER = True

BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 8222
SERVER_STARTUP_DELAY = 3  # Seconds to wait for server to start
# ============================================================


def is_server_running(host='127.0.0.1', port=8222):
    """Check if bridge server is already running."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def start_bridge_server():
    """Start bridge server as a subprocess."""
    # Check if server is already running
    if is_server_running(BRIDGE_HOST, BRIDGE_PORT):
        print("✓ Bridge server already running")
        print(f"  Host: {BRIDGE_HOST}")
        print(f"  Port: {BRIDGE_PORT}")
        return None  # Indicate server was already running

    print("Starting bridge server...")
    print(f"  Host: {BRIDGE_HOST}")
    print(f"  Port: {BRIDGE_PORT}")
    print()

    # Start server as background process
    try:
        process = subprocess.Popen(
            [sys.executable, '-m', 'MetaTrader5'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        # Wait for server to start
        print(f"Waiting {SERVER_STARTUP_DELAY}s for server startup...")
        time.sleep(SERVER_STARTUP_DELAY)

        # Check if process is still running
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            print("✗ Server failed to start!")
            print(f"Output: {stdout}")
            print(f"Errors: {stderr}")
            return None

        print("✓ Bridge server started")
        return process

    except Exception as e:
        print(f"✗ Failed to start server: {e}")
        return None


def main():
    print("MetaTrader5 macOS Example")
    print("=" * 50)

    server_process = None

    # Start bridge server if auto-start is enabled
    if AUTO_START_SERVER:
        print("\n[Auto-start] Starting bridge server...")
        server_process = start_bridge_server()

        if server_process is None:
            print("\nFailed to auto-start server. You can:")
            print("  1. Set AUTO_START_SERVER = False and run server separately:")
            print("     python -m MetaTrader5")
            print("  2. Or fix the error above")
            return
    else:
        print("\n[Manual] Make sure bridge server is running:")
        print("  python -m MetaTrader5")
        print()

    # Initialize connection
    print("\n1. Connecting to MT5...")
    if not mt5.initialize():
        print("Failed to connect to MT5!")
        print(f"Error code: {mt5.last_error()}")
        print("\nMake sure:")
        print("  1. Bridge server is running")
        if not AUTO_START_SERVER:
            print("     python -m MetaTrader5")
        print("  2. MT5 is running (in Wine/VM)")
        print("  3. MT5Bridge EA is attached to a chart in MT5")
        print("  4. EA shows 'Connected to Python server'")

        # Cleanup server if we started it
        if server_process:
            print("\nStopping bridge server...")
            server_process.terminate()
            server_process.wait()
        return

    print("Connected successfully!")

    # Get terminal version
    print("\n2. Terminal Info:")
    version = mt5.version()
    print(f"   Version: {version}")

    terminal = mt5.terminal_info()
    if terminal:
        print(f"   Connected: {terminal.connected}")
        print(f"   Path: {terminal.path}")

    # Get account info
    print("\n3. Account Information:")
    account = mt5.account_info()
    if account:
        print(f"   Login: {account.login}")
        print(f"   Server: {account.server}")
        print(f"   Currency: {account.currency}")
        print(f"   Balance: {account.balance:,.2f}")
        print(f"   Equity: {account.equity:,.2f}")
        print(f"   Margin: {account.margin:,.2f}")
        print(f"   Free Margin: {account.margin_free:,.2f}")
    else:
        print("   Unable to get account info")

    # Get symbols
    print("\n4. Available Symbols (first 10):")
    symbols = mt5.symbols_get()
    if symbols:
        for i, symbol in enumerate(symbols[:10]):
            print(f"   {i+1}. {symbol}")
    else:
        print("   No symbols available")

    # Get tick data
    print("\n5. Current Price Data:")
    tick = mt5.symbol_info_tick("EURUSD")
    if tick:
        print(f"   EURUSD Bid: {tick.bid:.5f}")
        print(f"   EURUSD Ask: {tick.ask:.5f}")
        print(f"   Spread: {(tick.ask - tick.bid):.5f}")
        print(f"   Last: {tick.last:.5f}")
    else:
        print("   Unable to get EURUSD tick data")

    # Get positions
    print("\n6. Open Positions:")
    positions = mt5.positions_get()
    if positions:
        print(f"   Total positions: {len(positions)}")
        for pos in positions:
            print(f"   - {pos.symbol} | {pos.volume} lots | Profit: ${pos.profit:.2f}")
    else:
        print("   No open positions")

    # Get orders
    print("\n7. Pending Orders:")
    orders = mt5.orders_get()
    if orders:
        print(f"   Total orders: {len(orders)}")
        for order in orders:
            print(f"   - Ticket: {order.ticket} | {order.symbol} | Vol: {order.volume_current}")
    else:
        print("   No pending orders")

    # Example: Place a trade (COMMENTED OUT FOR SAFETY)
    print("\n8. Trading Example (Disabled):")
    print("   To place a trade, uncomment the code below:")
    print("""
    # request = {
    #     "action": mt5.TRADE_ACTION_DEAL,
    #     "symbol": "EURUSD",
    #     "volume": 0.1,
    #     "type": mt5.ORDER_TYPE_BUY,
    #     "price": mt5.symbol_info_tick("EURUSD").ask,
    #     "deviation": 10,
    #     "comment": "Test from macOS",
    # }
    # result = mt5.order_send(request)
    # if result.retcode == mt5.TRADE_RETCODE_DONE:
    #     print(f"Trade executed: {result.order}")
    # else:
    #     print(f"Trade failed: {result.comment}")
    """)

    # Shutdown
    print("\n9. Disconnecting...")
    mt5.shutdown()
    print("Disconnected successfully!")

    # Stop bridge server if we started it
    # (Don't stop if it was already running before we started)
    if server_process:
        print("\nStopping bridge server...")
        server_process.terminate()
        try:
            server_process.wait(timeout=2)
            print("✓ Server stopped")
        except subprocess.TimeoutExpired:
            server_process.kill()
            print("✓ Server killed")
    elif is_server_running():
        print("\n(Bridge server was already running - not stopping it)")

    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    main()
