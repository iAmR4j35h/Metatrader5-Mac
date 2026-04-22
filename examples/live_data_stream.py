#!/usr/bin/env python3
"""
Live Data Stream - Real-time BTC/Forex price streaming

This script demonstrates how to listen to live market data by:
1. Polling for real-time tick data in a loop
2. Detecting price changes
3. Streaming OHLCV updates

Usage:
    python live_data_stream.py

Requirements:
    - MetaTrader 5 running with MT5Bridge EA attached
    - Active internet connection for real-time market data
"""

import MetaTrader5 as mt5
import sys
import subprocess
import time
from datetime import datetime
from collections import deque

# ============================================================
# CONFIGURATION
# ============================================================
AUTO_START_SERVER = True
BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 8222
SERVER_STARTUP_DELAY = 3

# Stream settings
SYMBOL = 'BTCUSDm'  # Change to 'EURUSD', 'XAUUSD', 'BTCUSD', etc.
REFRESH_RATE = 1.0  # Seconds between updates
MAX_HISTORY = 100   # Keep last N ticks for analysis
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
    if is_server_running(BRIDGE_HOST, BRIDGE_PORT):
        print("✓ Bridge server already running")
        return None

    print("[Auto] Starting bridge server...")
    try:
        process = subprocess.Popen(
            [sys.executable, '-m', 'MetaTrader5'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(SERVER_STARTUP_DELAY)
        if process.poll() is not None:
            print("✗ Server failed to start!")
            return None
        print("✓ Bridge server started")
        return process
    except Exception as e:
        print(f"✗ Failed to start server: {e}")
        return None


class LiveDataStream:
    """Live market data stream handler."""

    def __init__(self, symbol, refresh_rate=1.0, max_history=100):
        self.symbol = symbol
        self.refresh_rate = refresh_rate
        self.tick_history = deque(maxlen=max_history)
        self.price_changes = deque(maxlen=20)
        self.running = False
        self.last_tick = None
        self.session_high = None
        self.session_low = None
        self.start_time = datetime.now()

    def format_price(self, price):
        """Format price with appropriate decimals."""
        if price > 1000:
            return f"{price:,.2f}"
        elif price > 100:
            return f"{price:.3f}"
        else:
            return f"{price:.5f}"

    def calculate_spread_pct(self, bid, ask):
        """Calculate spread as percentage."""
        if bid > 0:
            return ((ask - bid) / bid) * 100
        return 0

    def detect_trend(self):
        """Detect short-term trend from recent prices."""
        if len(self.price_changes) < 5:
            return "WAITING"

        recent = list(self.price_changes)[-10:]
        ups = sum(1 for c in recent if c > 0)
        downs = sum(1 for c in recent if c < 0)

        if ups > downs + 2:
            return "BULLISH ↑"
        elif downs > ups + 2:
            return "BEARISH ↓"
        return "NEUTRAL →"

    def print_header(self):
        """Print stream header."""
        print("\n" + "=" * 70)
        print(f"  LIVE DATA STREAM - {self.symbol}")
        print("=" * 70)
        print(f"  Started: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"  Refresh: {self.refresh_rate}s | Press Ctrl+C to stop")
        print("=" * 70)
        print()

    def print_tick(self, tick):
        """Print formatted tick data."""
        now = datetime.now()
        time_str = now.strftime('%H:%M:%S')

        # Calculate spread
        spread = tick.ask - tick.bid
        spread_pct = self.calculate_spread_pct(tick.bid, tick.ask)

        # Calculate price change from last tick
        change_str = ""
        if self.last_tick:
            price_change = tick.last - self.last_tick.last
            self.price_changes.append(price_change)

            if price_change > 0:
                change_str = f"+{self.format_price(price_change)} ↑"
            elif price_change < 0:
                change_str = f"{self.format_price(price_change)} ↓"
            else:
                change_str = "0.00 →"

        # Update session high/low
        if self.session_high is None or tick.last > self.session_high:
            self.session_high = tick.last
        if self.session_low is None or tick.last < self.session_low:
            self.session_low = tick.last

        # Build output
        trend = self.detect_trend()
        trend_symbol = {"BULLISH ↑": "🟢", "BEARISH ↓": "🔴", "NEUTRAL →": "⚪", "WAITING": "⚪"}[trend]

        print(f"\r[{time_str}] {trend_symbol} ", end="")
        print(f"Bid: {self.format_price(tick.bid):>12} ", end="")
        print(f"Ask: {self.format_price(tick.ask):>12} ", end="")
        print(f"Last: {self.format_price(tick.last):>12} ", end="")
        print(f"Spread: {spread:.2f} ({spread_pct:.4f}%) ", end="")
        print(f"Change: {change_str:>15} ", end="")
        print(f"Vol: {tick.volume}", end="")

        # Print new line every 10 ticks for readability
        if len(self.tick_history) % 10 == 0:
            print()
        else:
            print("  ", end="", flush=True)

    def print_stats(self):
        """Print streaming statistics."""
        if not self.tick_history:
            return

        print("\n" + "-" * 70)
        print("  SESSION STATISTICS")
        print("-" * 70)
        print(f"  Session High: {self.format_price(self.session_high)}")
        print(f"  Session Low:  {self.format_price(self.session_low)}")
        print(f"  Range:        {self.format_price(self.session_high - self.session_low)}")
        print(f"  Ticks Count:  {len(self.tick_history)}")
        print(f"  Uptime:       {datetime.now() - self.start_time}")
        print("-" * 70)

    def run(self):
        """Main streaming loop."""
        self.print_header()
        self.running = True

        try:
            while self.running:
                # Get current tick
                tick = mt5.symbol_info_tick(self.symbol)

                if tick is None:
                    print(f"\r[!] Waiting for {self.symbol} data...", end="", flush=True)
                    time.sleep(self.refresh_rate)
                    continue

                # Store tick
                self.tick_history.append(tick)

                # Print update
                self.print_tick(tick)

                # Update last tick reference
                self.last_tick = tick

                # Sleep until next update
                time.sleep(self.refresh_rate)

        except KeyboardInterrupt:
            print("\n\n[!] Stream stopped by user")
        finally:
            self.running = False
            self.print_stats()


def main():
    """Main function."""
    server_process = None

    print("=" * 70)
    print("MetaTrader 5 Live Data Stream")
    print("=" * 70)

    # Start bridge server if needed
    if AUTO_START_SERVER:
        server_process = start_bridge_server()
        if server_process is None and not is_server_running(BRIDGE_HOST, BRIDGE_PORT):
            print("[!] Failed to start bridge server")
            sys.exit(1)

    # Connect to MT5
    print("\n[1] Connecting to MT5...")
    if not mt5.initialize():
        print(f"✗ Connection failed: {mt5.last_error()}")
        if server_process:
            server_process.terminate()
        sys.exit(1)
    print("✓ Connected")

    # Verify symbol exists
    print(f"\n[2] Checking for {SYMBOL}...")
    symbol_info = mt5.symbol_info(SYMBOL)
    if symbol_info is None:
        print(f"✗ Symbol {SYMBOL} not found")
        print("Available symbols (searching for similar):")
        symbols = mt5.symbols_get()
        for s in symbols:
            if SYMBOL[:3] in str(s) or SYMBOL[:4] in str(s):
                print(f"  - {s}")
        mt5.shutdown()
        sys.exit(1)

    print(f"✓ {SYMBOL} available")
    print(f"  Description: {symbol_info.description}")

    # Start streaming
    print("\n[3] Starting live stream...")
    stream = LiveDataStream(SYMBOL, REFRESH_RATE, MAX_HISTORY)
    stream.run()

    # Cleanup
    print("\n[4] Disconnecting...")
    mt5.shutdown()

    if server_process:
        print("Stopping bridge server...")
        server_process.terminate()
        server_process.wait()

    print("✓ Done")


if __name__ == "__main__":
    main()
