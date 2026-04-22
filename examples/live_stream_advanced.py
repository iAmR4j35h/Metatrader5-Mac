#!/usr/bin/env python3
"""
True Live Data Streaming - High-frequency tick streaming via MT5 OnTick

This demonstrates TRUE streaming where MT5 pushes updates as they arrive,
rather than Python polling. Requires the modified EA to be installed.

For now, this example uses rapid polling (100ms) to simulate streaming.

Usage:
    python live_stream_advanced.py
"""

import MetaTrader5 as mt5
import sys
import subprocess
import time
import threading
from datetime import datetime
from collections import deque

# ============================================================
# CONFIGURATION
# ============================================================
AUTO_START_SERVER = True
BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 8222

# Stream settings
SYMBOL = 'BTCUSDm'
POLL_INTERVAL = 0.1  # 100ms for near real-time streaming
MAX_TICKS = 1000
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
    """Start bridge server."""
    if is_server_running(BRIDGE_HOST, BRIDGE_PORT):
        return None

    try:
        process = subprocess.Popen(
            [sys.executable, '-m', 'MetaTrader5'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        time.sleep(3)
        if process.poll() is None:
            return process
        return None
    except:
        return None


class TrueLiveStream:
    """
    High-frequency market data stream.

    This class polls at 100ms intervals to achieve near real-time
    streaming. True push-based streaming would require:

    1. MT5 EA modification to subscribe to OnTick events
    2. EA automatically pushes ticks to Python via socket
    3. Python receives unsolicited updates in a separate thread

    Current architecture: Python polls (pull model)
    Optimal architecture: MT5 pushes (push model)
    """

    def __init__(self, symbol, interval=0.1):
        self.symbol = symbol
        self.interval = interval
        self.ticks = deque(maxlen=MAX_TICKS)
        self.running = False
        self.tick_count = 0
        self.price_changes = 0
        self.last_bid = None
        self.last_ask = None
        self.lock = threading.Lock()

    def start(self):
        """Start streaming."""
        self.running = True
        print(f"\n🚀 Starting high-frequency stream for {self.symbol}")
        print(f"   Poll interval: {self.interval*1000:.0f}ms")
        print(f"   Press Ctrl+C to stop\n")

        stream_thread = threading.Thread(target=self._stream_loop)
        display_thread = threading.Thread(target=self._display_loop)

        stream_thread.daemon = True
        display_thread.daemon = True

        stream_thread.start()
        display_thread.start()

        try:
            while self.running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop()

        stream_thread.join(timeout=2)
        display_thread.join(timeout=2)

    def _stream_loop(self):
        """Main streaming loop - polls for new ticks."""
        while self.running:
            tick = mt5.symbol_info_tick(self.symbol)

            if tick:
                with self.lock:
                    # Only store if price changed
                    if (self.last_bid != tick.bid or self.last_ask != tick.ask):
                        self.ticks.append({
                            'time': datetime.now(),
                            'bid': tick.bid,
                            'ask': tick.ask,
                            'last': tick.last,
                            'volume': tick.volume
                        })
                        self.price_changes += 1
                        self.last_bid = tick.bid
                        self.last_ask = tick.ask

                    self.tick_count += 1

            time.sleep(self.interval)

    def _display_loop(self):
        """Display loop - prints stats every second."""
        last_display = time.time()
        last_tick_count = 0

        while self.running:
            time.sleep(1.0)

            if not self.running:
                break

            with self.lock:
                current_ticks = self.tick_count
                changes = self.price_changes

                if self.ticks:
                    latest = self.ticks[-1]
                    bid = latest['bid']
                    ask = latest['ask']
                    spread = ask - bid
                else:
                    bid = ask = spread = 0

            # Calculate rates
            elapsed = time.time() - last_display
            poll_rate = (current_ticks - last_tick_count) / elapsed
            last_tick_count = current_ticks
            last_display = time.time()

            # Print status line
            time_str = datetime.now().strftime('%H:%M:%S')
            print(f"[{time_str}] Ticks: {current_ticks:>6} | "
                  f"Changes: {changes:>5} | "
                  f"Rate: {poll_rate:>6.1f}/s | "
                  f"Bid: {bid:>12.2f} | "
                  f"Ask: {ask:>12.2f} | "
                  f"Spread: {spread:>8.2f}")

    def stop(self):
        """Stop streaming."""
        self.running = False
        print("\n📊 STREAM SUMMARY")
        print("-" * 50)
        print(f"Total polls:    {self.tick_count}")
        print(f"Price changes:  {self.price_changes}")
        print(f"Efficiency:     {(self.price_changes/max(1,self.tick_count))*100:.1f}%")

        if self.ticks:
            prices = [t['last'] for t in self.ticks]
            print(f"High:           {max(prices):.2f}")
            print(f"Low:            {min(prices):.2f}")
            print(f"Range:          {max(prices)-min(prices):.2f}")


def main():
    server_process = None

    if AUTO_START_SERVER:
        server_process = start_bridge_server()

    print("[1] Connecting to MT5...")
    if not mt5.initialize():
        print("✗ Failed")
        sys.exit(1)
    print("✓ Connected")

    # Check symbol
    if not mt5.symbol_info(SYMBOL):
        print(f"✗ {SYMBOL} not found")
        mt5.shutdown()
        sys.exit(1)

    # Start streaming
    stream = TrueLiveStream(SYMBOL, POLL_INTERVAL)
    stream.start()

    # Cleanup
    mt5.shutdown()
    if server_process:
        server_process.terminate()


if __name__ == "__main__":
    main()
