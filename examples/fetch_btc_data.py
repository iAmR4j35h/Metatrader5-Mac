#!/usr/bin/env python3
"""
BTC Data Fetcher - Test script for MetaTrader5 macOS API

This script demonstrates how to fetch various data for Bitcoin (BTC)
from MetaTrader 5 using the macOS-compatible Python API.

Usage:
    python fetch_btc_data.py

Requirements:
    - MetaTrader 5 running with MT5Bridge EA attached
    - BTCUSD or BTCUSDT symbol available in MT5
    - Internet connection for real-time data

Author: MT5 macOS Port
"""

import MetaTrader5 as mt5
from datetime import datetime, timedelta
import sys
import subprocess
import time

# ============================================================
# CONFIGURATION
# ============================================================
# Set to False to run bridge server manually:
#   python -m MetaTrader5
AUTO_START_SERVER = True

BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 8222
SERVER_STARTUP_DELAY = 3  # Seconds to wait for server startup
# ============================================================

# Common BTC symbol names in MT5
BTC_SYMBOLS = ['BTCUSD', 'BTCUSDT', 'BTC/USD', 'XBTUSD', 'Bitcoin']


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


def connect_to_mt5():
    """Establish connection to MT5."""
    print("=" * 60)
    print("BTC Data Fetcher - MetaTrader5 macOS")
    print("=" * 60)
    print()

    print("[1] Connecting to MetaTrader 5...")

    if not AUTO_START_SERVER:
        print("    (Make sure bridge server is running: python -m MetaTrader5)")

    if not mt5.initialize():
        print("    ✗ Failed to connect!")
        print(f"    Error code: {mt5.last_error()}")
        print()
        print("Troubleshooting:")
        if AUTO_START_SERVER:
            print("  1. Bridge server was auto-started")
            print("  2. Make sure MT5 is running (in Wine/CrossOver or VM)")
            print("  3. Attach the MT5Bridge EA to any chart in MT5")
            print("  4. Check that the EA shows 'Connected to Python server'")
        else:
            print("  1. Start the bridge server:")
            print("     python -m MetaTrader5")
            print()
            print("  2. Make sure MT5 is running (in Wine/CrossOver or VM)")
            print("  3. Attach the MT5Bridge EA to any chart in MT5")
            print("  4. Check that the EA shows 'Connected to Python server'")
        print("  5. Verify firewall settings allow port 8222")
        print()
        print("Environment variables:")
        print("  export MT5_HOST=127.0.0.1  # Bridge server host")
        print("  export MT5_PORT=8222       # Bridge server port")
        return False, None

    print("    ✓ Connected successfully!")
    print()
    return True, None


def get_terminal_info():
    """Display terminal and account information."""
    print("[2] Terminal Information:")

    version = mt5.version()
    print(f"    MT5 Version: {version}")

    terminal = mt5.terminal_info()
    if terminal:
        print(f"    Connected: {terminal.connected}")
        print(f"    Trade Allowed: {terminal.trade_allowed}")
        print(f"    DLLs Allowed: {terminal.dlls_allowed}")

    account = mt5.account_info()
    if account:
        print(f"    Account: {account.login}")
        print(f"    Server: {account.server}")
        print(f"    Currency: {account.currency}")
        print(f"    Balance: ${account.balance:,.2f}")
        print(f"    Equity: ${account.equity:,.2f}")

    print()


def find_btc_symbol():
    """Find the BTC symbol available in MT5."""
    print("[3] Searching for BTC Symbol:")

    # Try common BTC symbol names
    for symbol in BTC_SYMBOLS:
        tick = mt5.symbol_info_tick(symbol)
        if tick is not None:
            print(f"    ✓ Found: {symbol}")
            return symbol

    # If not found, try to get all symbols and search
    print("    Searching all symbols...")
    symbols = mt5.symbols_get()

    if symbols:
        for sym in symbols:
            sym_str = str(sym)
            if 'BTC' in sym_str.upper() or 'BITCOIN' in sym_str.upper():
                print(f"    ✓ Found: {sym}")
                return sym

    print("    ✗ BTC symbol not found!")
    print("    Available symbols (first 20):")
    if symbols:
        for i, sym in enumerate(symbols[:20]):
            print(f"      {i+1}. {sym}")
    print()
    return None


def get_symbol_info(symbol):
    """Get detailed information about the BTC symbol."""
    print(f"[4] Symbol Information for {symbol}:")

    info = mt5.symbol_info(symbol)
    if info:
        print(f"    Description: {info.description}")
        print(f"    Digits: {info.digits}")
        print(f"    Trade Mode: {info.trade_mode}")
        print(f"    Min Volume: {info.volume_min}")
        print(f"    Max Volume: {info.volume_max}")
        print(f"    Volume Step: {info.volume_step}")
        print(f"    Point: {info.point}")

    tick = mt5.symbol_info_tick(symbol)
    if tick:
        spread = tick.ask - tick.bid
        print(f"    Current Bid: {tick.bid:,.2f}")
        print(f"    Current Ask: {tick.ask:,.2f}")
        print(f"    Spread: {spread:,.2f}")
        print(f"    Last Price: {tick.last:,.2f}")
        print(f"    Volume: {tick.volume}")
        print(f"    Time: {datetime.fromtimestamp(tick.time)}")

    print()


def get_historical_rates(symbol, timeframe=mt5.TIMEFRAME_H1, count=24):
    """Fetch historical OHLCV data for BTC."""
    print(f"[5] Historical Rates ({symbol}, last {count} candles):")

    timeframe_names = {
        mt5.TIMEFRAME_M1: "1 Minute",
        mt5.TIMEFRAME_M5: "5 Minutes",
        mt5.TIMEFRAME_M15: "15 Minutes",
        mt5.TIMEFRAME_M30: "30 Minutes",
        mt5.TIMEFRAME_H1: "1 Hour",
        mt5.TIMEFRAME_H4: "4 Hours",
        mt5.TIMEFRAME_D1: "Daily",
    }

    tf_name = timeframe_names.get(timeframe, f"TF_{timeframe}")
    print(f"    Timeframe: {tf_name}")

    # Calculate date range
    to_date = datetime.now()

    # Approximate bars based on timeframe
    if timeframe == mt5.TIMEFRAME_M1:
        from_date = to_date - timedelta(minutes=count)
    elif timeframe == mt5.TIMEFRAME_H1:
        from_date = to_date - timedelta(hours=count)
    elif timeframe == mt5.TIMEFRAME_D1:
        from_date = to_date - timedelta(days=count)
    else:
        from_date = to_date - timedelta(hours=count * 4)

    rates = mt5.copy_rates_range(symbol, timeframe, from_date, to_date)

    if rates is None:
        print("    ✗ Failed to retrieve rates")
        print()
        return

    print(f"    Retrieved: {len(rates)} candles")
    print()

    # Display last 10 candles
    display_count = min(10, len(rates))
    print(f"    Last {display_count} candles:")
    print(f"    {'Time':<20} {'Open':<12} {'High':<12} {'Low':<12} {'Close':<12} {'Volume':<10}")
    print(f"    {'-'*90}")

    for rate in list(rates)[-display_count:]:
        time_str = datetime.fromtimestamp(rate.time).strftime('%Y-%m-%d %H:%M')
        print(f"    {time_str:<20} {rate.open:<12.2f} {rate.high:<12.2f} "
              f"{rate.low:<12.2f} {rate.close:<12.2f} {rate.tick_volume:<10}")

    print()


def get_historical_ticks(symbol, count=100):
    """Fetch historical tick data for BTC."""
    print(f"[6] Historical Ticks ({symbol}, last {count} ticks):")

    from_date = datetime.now() - timedelta(hours=1)

    ticks = mt5.copy_ticks_from(symbol, from_date, count, mt5.COPY_TICKS_ALL)

    if ticks is None:
        print("    ✗ Failed to retrieve ticks")
        print()
        return

    print(f"    Retrieved: {len(ticks)} ticks")
    print()

    # Display last 10 ticks
    display_count = min(10, len(ticks))
    print(f"    Last {display_count} ticks:")
    print(f"    {'Time':<25} {'Bid':<12} {'Ask':<12} {'Last':<12} {'Volume':<10}")
    print(f"    {'-'*75}")

    for tick in list(ticks)[-display_count:]:
        time_str = datetime.fromtimestamp(tick.time).strftime('%Y-%m-%d %H:%M:%S')
        bid = tick.bid if tick.bid > 0 else '-'
        ask = tick.ask if tick.ask > 0 else '-'
        last = tick.last if tick.last > 0 else '-'
        vol = tick.volume if tick.volume > 0 else '-'
        print(f"    {time_str:<25} {bid:<12} {ask:<12} {last:<12} {vol:<10}")

    print()


def check_trading_conditions(symbol):
    """Check if trading is possible for BTC."""
    print(f"[7] Trading Conditions for {symbol}:")

    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        print("    ✗ Symbol not available")
        print()
        return

    # Calculate margin for a sample trade
    volume = 0.01  # Minimum volume

    margin = mt5.order_calc_margin(
        mt5.ORDER_TYPE_BUY,
        symbol,
        volume,
        tick.ask
    )

    print(f"    Sample Trade Calculation:")
    print(f"    Volume: {volume} lots")
    print(f"    Entry Price: {tick.ask:,.2f}")

    if margin:
        print(f"    Required Margin: ${margin:,.2f}")
    else:
        print(f"    Required Margin: Unable to calculate")

    # Check current spread
    spread = tick.ask - tick.bid
    spread_pct = (spread / tick.ask) * 100
    print(f"    Current Spread: {spread:,.2f} ({spread_pct:.4f}%)")

    # Get open positions
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        print(f"    Open Positions: {len(positions)}")
        for pos in positions:
            pnl = "(profit)" if pos.profit > 0 else "(loss)" if pos.profit < 0 else ""
            print(f"      - {pos.type} {pos.volume} lots @ {pos.price_open} "
                  f"P&L: ${pos.profit:.2f} {pnl}")
    else:
        print(f"    Open Positions: None")

    print()


def main():
    """Main function."""
    server_process = None

    # Auto-start bridge server if enabled
    if AUTO_START_SERVER:
        server_process = start_bridge_server()
        if server_process is None:
            print("\n[!] Failed to auto-start bridge server.")
            print("Set AUTO_START_SERVER = False and run manually:")
            print("  python -m MetaTrader5")
            print("\nContinuing anyway...")
            print()

    # Connect to MT5
    connected, _ = connect_to_mt5()
    if not connected:
        if server_process:
            print("\nStopping bridge server...")
            server_process.terminate()
            server_process.wait()
        sys.exit(1)

    try:
        # Get terminal info
        get_terminal_info()

        # Find BTC symbol
        symbol = find_btc_symbol()

        if symbol is None:
            print("[!] Could not find BTC symbol. Exiting.")
            return

        # Get symbol info
        get_symbol_info(symbol)

        # Get historical data
        get_historical_rates(symbol, mt5.TIMEFRAME_H1, 24)
        get_historical_rates(symbol, mt5.TIMEFRAME_D1, 7)
        get_historical_ticks(symbol, 100)

        # Check trading conditions
        check_trading_conditions(symbol)

        # Summary
        print("=" * 60)
        print("Summary:")
        print("=" * 60)
        tick = mt5.symbol_info_tick(symbol)
        if tick:
            print(f"Current {symbol} Price:")
            print(f"  Bid: ${tick.bid:,.2f}")
            print(f"  Ask: ${tick.ask:,.2f}")
            print(f"  Spread: ${tick.ask - tick.bid:,.2f}")
        print()
        print("✓ Data fetching complete!")
        print()
        print("Note: All times are in local timezone")
        print("      Prices are from your MT5 broker")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Always shutdown
        print()
        print("[8] Disconnecting from MT5...")
        mt5.shutdown()
        print("    ✓ Disconnected")
        print()
        print("=" * 60)

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
