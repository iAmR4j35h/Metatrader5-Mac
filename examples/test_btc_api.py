#!/usr/bin/env python3
"""
BTC API Test Script - MetaTrader5 macOS

This script tests the MetaTrader5 API for fetching Bitcoin data.
It demonstrates all the key functions needed for BTC trading.

Usage:
    python test_btc_api.py

Requirements:
    - MetaTrader 5 running with MT5Bridge EA attached
    - Bridge server (auto-started or run manually with: python -m MetaTrader5)

Author: MT5 macOS Port
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import subprocess
import time
import sys

# ============================================================
# CONFIGURATION
# ============================================================
AUTO_START_SERVER = True  # Set to False to run server manually
BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 8222
SERVER_STARTUP_DELAY = 3
# ============================================================


def start_bridge_server():
    """Start bridge server as a subprocess."""
    print("[Auto] Starting bridge server...")
    print(f"  Host: {BRIDGE_HOST}")
    print(f"  Port: {BRIDGE_PORT}")

    try:
        process = subprocess.Popen(
            [sys.executable, '-m', 'MetaTrader5'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        print(f"[Auto] Waiting {SERVER_STARTUP_DELAY}s for server startup...")
        time.sleep(SERVER_STARTUP_DELAY)

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


def test_connection():
    """Test connection to MT5."""
    print("Testing MT5 Connection...")
    print("-" * 50)

    if not AUTO_START_SERVER:
        print("(Make sure bridge server is running: python -m MetaTrader5)")

    if not mt5.initialize():
        print("✗ Failed to connect to MT5")
        print(f"  Error code: {mt5.last_error()}")
        print("\nPlease ensure:")
        if AUTO_START_SERVER:
            print("  1. Bridge server was auto-started")
            print("  2. MetaTrader 5 is running")
            print("  3. MT5Bridge EA is attached to a chart")
            print("  4. EA shows 'Connected to Python server'")
        else:
            print("  1. Bridge server is running:")
            print("     python -m MetaTrader5")
            print()
            print("  2. MetaTrader 5 is running")
            print("  3. MT5Bridge EA is attached to a chart")
            print("  4. EA shows 'Connected to Python server'")
        return False

    print("✓ Connected to MT5")
    print(f"  Version: {mt5.version()}")
    return True


def test_account_info():
    """Test account information retrieval."""
    print("\nTesting Account Info...")
    print("-" * 50)

    account = mt5.account_info()
    if account is None:
        print("✗ Failed to get account info")
        return False

    print("✓ Account Info:")
    print(f"  Login: {account.login}")
    print(f"  Server: {account.server}")
    print(f"  Balance: ${account.balance:,.2f}")
    print(f"  Equity: ${account.equity:,.2f}")
    return True


def test_btc_symbol():
    """Test BTC symbol data."""
    print("\nTesting BTC Symbol...")
    print("-" * 50)

    # Try common BTC symbols
    btc_symbols = ['BTCUSD', 'BTCUSDT', 'BTC/USD', 'XBTUSD']

    for symbol in btc_symbols:
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None:
            print(f"✓ Found BTC symbol: {symbol}")
            print(f"  Bid: ${tick.bid:,.2f}")
            print(f"  Ask: ${tick.ask:,.2f}")
            print(f"  Spread: ${tick.ask - tick.bid:,.2f}")
            print(f"  Last: ${tick.last:,.2f}")
            return symbol

    print("✗ BTC symbol not found. Trying to get all symbols...")
    symbols = mt5.symbols_get()
    if symbols:
        print(f"  Total symbols: {len(symbols)}")
        btc_syms = [s for s in symbols if 'BTC' in str(s)]
        if btc_syms:
            print(f"  BTC-related symbols: {btc_syms[:5]}")
            return btc_syms[0]

    return None


def test_historical_data(symbol):
    """Test fetching historical data."""
    print("\nTesting Historical Data...")
    print("-" * 50)

    # Get hourly rates for last 24 hours
    to_date = datetime.now()
    from_date = to_date - timedelta(hours=24)

    rates = mt5.copy_rates_range(symbol, mt5.TIMEFRAME_H1, from_date, to_date)

    if rates is None:
        print("✗ Failed to get rates")
        return False

    print(f"✓ Got {len(rates)} hourly candles")

    if len(rates) > 0:
        latest = rates[-1]
        print(f"\nLatest Hour Candle:")
        print(f"  Time: {datetime.fromtimestamp(latest.time)}")
        print(f"  Open: ${latest.open:,.2f}")
        print(f"  High: ${latest.high:,.2f}")
        print(f"  Low: ${latest.low:,.2f}")
        print(f"  Close: ${latest.close:,.2f}")
        print(f"  Volume: {latest.tick_volume}")

    return True


def test_positions():
    """Test position retrieval."""
    print("\nTesting Positions...")
    print("-" * 50)

    positions = mt5.positions_get()
    if positions is None:
        print("✗ Failed to get positions")
        return False

    print(f"✓ Open Positions: {len(positions)}")

    for pos in positions:
        print(f"  - {pos.symbol}: {pos.type} {pos.volume} lots "
              f"P&L: ${pos.profit:.2f}")

    return True


def test_orders():
    """Test order retrieval."""
    print("\nTesting Orders...")
    print("-" * 50)

    orders = mt5.orders_get()
    if orders is None:
        print("✗ Failed to get orders")
        return False

    print(f"✓ Pending Orders: {len(orders)}")

    for order in orders:
        print(f"  - Ticket: {order.ticket}, Symbol: {order.symbol}, "
              f"Type: {order.type}, Volume: {order.volume_current}")

    return True


def test_margin_calculation(symbol):
    """Test margin calculation."""
    print("\nTesting Margin Calculation...")
    print("-" * 50)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print("✗ Cannot get tick data")
        return False

    volume = 0.01  # 0.01 lots
    margin = mt5.order_calc_margin(
        mt5.ORDER_TYPE_BUY,
        symbol,
        volume,
        tick.ask
    )

    if margin is None:
        print("✗ Failed to calculate margin")
        return False

    print(f"✓ Margin Calculation:")
    print(f"  Symbol: {symbol}")
    print(f"  Volume: {volume} lots")
    print(f"  Price: ${tick.ask:,.2f}")
    print(f"  Required Margin: ${margin:,.2f}")

    return True


def demo_trade_request(symbol):
    """Show example trade request (doesn't execute)."""
    print("\nDemo Trade Request...")
    print("-" * 50)

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        return False

    print("Example Buy Order Request:")
    print("-" * 50)

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.01,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "sl": tick.ask * 0.95,  # 5% stop loss
        "tp": tick.ask * 1.10,  # 10% take profit
        "deviation": 10,
        "magic": 123456,
        "comment": "BTC Test from macOS",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    for key, value in request.items():
        if isinstance(value, float):
            print(f"  {key}: ${value:,.2f}")
        else:
            print(f"  {key}: {value}")

    print("\nTo execute this trade, uncomment:")
    print("  result = mt5.order_send(request)")
    print("  print(result)")

    return True


def main():
    """Main function."""
    server_process = None

    print("=" * 50)
    print("BTC API Test - MetaTrader5 macOS")
    print("=" * 50)

    # Auto-start bridge server if enabled
    if AUTO_START_SERVER:
        server_process = start_bridge_server()
        if server_process is None:
            print("\n[!] Failed to auto-start bridge server.")
            print("Set AUTO_START_SERVER = False and run manually:")
            print("  python -m MetaTrader5")
            print("\nContinuing anyway...")

    # Test connection
    if not test_connection():
        print("\n✗ Tests aborted - no connection")
        if server_process:
            print("\nStopping bridge server...")
            server_process.terminate()
            server_process.wait()
        sys.exit(1)

    try:
        # Run tests
        tests_passed = 0
        tests_total = 0

        # Test 1: Account
        tests_total += 1
        if test_account_info():
            tests_passed += 1

        # Test 2: BTC Symbol
        tests_total += 1
        symbol = test_btc_symbol()
        if symbol:
            tests_passed += 1

            # Test 3: Historical data
            tests_total += 1
            if test_historical_data(symbol):
                tests_passed += 1

            # Test 4: Margin calculation
            tests_total += 1
            if test_margin_calculation(symbol):
                tests_passed += 1

            # Test 5: Demo trade
            tests_total += 1
            if demo_trade_request(symbol):
                tests_passed += 1

        # Test 6: Positions
        tests_total += 1
        if test_positions():
            tests_passed += 1

        # Test 7: Orders
        tests_total += 1
        if test_orders():
            tests_passed += 1

        # Summary
        print("\n" + "=" * 50)
        print("TEST SUMMARY")
        print("=" * 50)
        print(f"Tests Passed: {tests_passed}/{tests_total}")

        if tests_passed == tests_total:
            print("✓ All tests passed!")
        else:
            print(f"⚠ {tests_total - tests_passed} test(s) failed")

    except Exception as e:
        print(f"\n✗ Error during tests: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup
        print("\n" + "=" * 50)
        print("Disconnecting from MT5...")
        mt5.shutdown()
        print("✓ Disconnected")
        print("=" * 50)

        # Stop bridge server if we started it
        if server_process:
            print("\nStopping bridge server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=2)
                print("✓ Server stopped")
            except subprocess.TimeoutExpired:
                server_process.kill()
                print("✓ Server killed")


if __name__ == "__main__":
    main()
</content>