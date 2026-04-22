#!/usr/bin/env python3
"""
Basic example of using MetaTrader5 on macOS.

This example demonstrates how to:
1. Start the bridge server (optional - can run separately)
2. Connect to MT5 running in Wine/CrossOver or VM
3. Get account information
4. Retrieve symbol data
5. Place a trade (commented out for safety)

Prerequisites:
- MT5 running with MT5Bridge EA attached
- Bridge server running (see below)

Running the Bridge Server:
    Option 1: Run separately
        $ python -m MetaTrader5

    Option 2: Start programmatically (see commented code below)
        server = mt5.start_bridge_server()

    Option 3: Console script (after pip install)
        $ mt5-bridge-server

Environment variables (optional):
    export MT5_HOST=127.0.0.1  # Bridge server host
    export MT5_PORT=8222       # Bridge server port
"""

import MetaTrader5 as mt5
from datetime import datetime
import time


def main():
    print("MetaTrader5 macOS Example")
    print("=" * 50)

    # Optional: Start bridge server programmatically
    # Uncomment the following lines if you want to start the server from this script
    # Note: You can also run 'python -m MetaTrader5' in a separate terminal
    #
    # print("\n[Optional] Starting bridge server...")
    # server = mt5.start_bridge_server()
    # time.sleep(2)  # Wait for server to start and MT5 to connect
    #
    # Or check if server is already running - if not, you need to start it
    # separately with: python -m MetaTrader5

    # Initialize connection
    print("\n1. Connecting to MT5...")
    print("   (Make sure bridge server is running: python -m MetaTrader5)")
    if not mt5.initialize():
        print("Failed to connect to MT5!")
        print(f"Error code: {mt5.last_error()}")
        print("\nMake sure:")
        print("  1. Bridge server is running:")
        print("     python -m MetaTrader5")
        print("  2. MT5 is running (in Wine/VM)")
        print("  3. MT5Bridge EA is attached to a chart in MT5")
        print("  4. EA shows 'Connected to Python server'")
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

    # Optional: Stop bridge server if started programmatically
    # if 'server' in locals():
    #     print("Stopping bridge server...")
    #     server.stop()
    #     print("Server stopped!")

    print("\n" + "=" * 50)
    print("Example completed!")


if __name__ == "__main__":
    main()
