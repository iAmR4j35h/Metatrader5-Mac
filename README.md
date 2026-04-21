# MetaTrader5 for macOS

A reverse-engineered macOS-compatible implementation of the MetaTrader5 Python API.

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## Overview

The official `metatrader5` Python package only works on Windows because it uses Windows Named Pipes for IPC communication with the MT5 terminal. This package provides a macOS-compatible implementation that uses TCP sockets instead, allowing you to control MetaTrader 5 from macOS.

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│                 │      │                  │      │                 │
│  Python Script  │◄────►│  TCP Socket      │◄────►│  MT5 Terminal   │
│  (macOS)        │      │  Bridge          │      │  (Windows/VM)   │
│                 │      │                  │      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘

  MetaTrader5           localhost:8222              MT5Bridge EA
  Python API                                   (MQL5 Expert Advisor)
```

## Prerequisites

### Option 1: MetaTrader 5 on Wine/CrossOver (Recommended for local use)

1. Install [CrossOver](https://www.codeweavers.com/crossover) or [Wine](https://www.winehq.org/)
2. Install MetaTrader 5 in the Wine/CrossOver environment
3. Compile and run the MT5Bridge EA in MT5

### Option 2: MetaTrader 5 on Windows VM

1. Install a Windows VM (Parallels Desktop, VMware Fusion, or VirtualBox)
2. Install MetaTrader 5 in the VM
3. Configure the VM network for host access
4. Compile and run the MT5Bridge EA in MT5

### Option 3: Remote Windows Machine

1. MetaTrader 5 running on a Windows machine accessible via network
2. Port 8222 (default) accessible from your Mac
3. Compile and run the MT5Bridge EA in MT5

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/metatrader5-macos.git
cd metatrader5-macos

# Install the package
pip install -e .

# Or for production use
pip install .
```

## Setup

### Step 1: Configure the Bridge EA

1. Open MetaTrader 5 (in Wine/VM)
2. Copy `MQL5/Experts/MT5Bridge/MT5Bridge.mq5` to your MT5 data folder:
   - In MT5: File → Open Data Folder → MQL5 → Experts
3. Compile the EA (may need JSON/Socket libraries - see below)
4. Add the EA to a chart (any symbol)
5. The EA will listen on port 8222 by default

### Required MQL5 Libraries

The EA requires the following MQL5 libraries:

1. **JAson** - JSON library for MQL5
   - Download from: https://www.mql5.com/en/code/13663
   - Place in: `MQL5/Include/JAson.mqh`

2. **Sockets** - Socket library for MQL5
   - Download from: https://www.mql5.com/en/code/ WSA socket implementation
   - Alternative: Use built-in `Socket*` functions if available in your MT5 build

### Step 2: Configure Environment Variables (Optional)

```bash
export MT5_HOST=127.0.0.1    # MT5 Bridge host (default: localhost)
export MT5_PORT=8222         # MT5 Bridge port (default: 8222)
export MT5_TIMEOUT=30        # Connection timeout (default: 30 seconds)
```

## Usage

The API is designed to be compatible with the official Windows MetaTrader5 package:

```python
import MetaTrader5 as mt5

# Initialize connection to MT5
if not mt5.initialize():
    print("Failed to initialize MT5 connection")
    mt5.shutdown()
    exit()

# Get terminal version
print(mt5.version())

# Get account info
account_info = mt5.account_info()
if account_info:
    print(f"Balance: {account_info.balance}")
    print(f"Equity: {account_info.equity}")

# Get symbol info
tick = mt5.symbol_info_tick("EURUSD")
if tick:
    print(f"EURUSD Bid: {tick.bid}, Ask: {tick.ask}")

# Get all symbols
symbols = mt5.symbols_get()
print(f"Total symbols: {len(symbols)}")

# Get open positions
positions = mt5.positions_get()
for pos in positions:
    print(f"Position {pos.ticket}: {pos.symbol} {pos.volume} lots")

# Send a market order
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "EURUSD",
    "volume": 0.1,
    "type": mt5.ORDER_TYPE_BUY,
    "price": mt5.symbol_info_tick("EURUSD").ask,
    "deviation": 10,
    "comment": "Test order from macOS",
}

result = mt5.order_send(request)
if result.retcode == mt5.TRADE_RETCODE_DONE:
    print(f"Order executed: {result.order}")
else:
    print(f"Order failed: {result.comment}")

# Shutdown
mt5.shutdown()
```

## API Reference

This package implements the full MetaTrader5 Python API. Key functions:

### Connection Management
- `initialize()` - Connect to MT5 bridge
- `shutdown()` - Disconnect from MT5 bridge
- `version()` - Get terminal version
- `last_error()` - Get last error code

### Account Information
- `account_info()` - Get account details
- `terminal_info()` - Get terminal information

### Symbol Information
- `symbols_total()` - Total number of symbols
- `symbols_get(group)` - Get symbols matching pattern
- `symbol_info(symbol)` - Get symbol information
- `symbol_info_tick(symbol)` - Get current tick
- `symbol_select(symbol, enable)` - Add/remove symbol from Market Watch

### Trading Operations
- `order_send(request)` - Send trading order
- `order_check(request)` - Check order before sending
- `order_calc_margin(...)` - Calculate margin required
- `order_calc_profit(...)` - Calculate potential profit
- `Buy(symbol, volume, ...)` - Helper to buy
- `Sell(symbol, volume, ...)` - Helper to sell
- `Close(symbol, ...)` - Close positions

### Market Data
- `copy_rates_from(...)` - Get historical bars
- `copy_rates_range(...)` - Get bars in date range
- `copy_ticks_from(...)` - Get historical ticks
- `copy_ticks_range(...)` - Get ticks in date range
- `market_book_add(symbol)` - Subscribe to market depth
- `market_book_get(symbol)` - Get market depth
- `market_book_release(symbol)` - Unsubscribe from market depth

### Order/Position Management
- `orders_total()` - Get number of pending orders
- `orders_get(...)` - Get pending orders
- `positions_total()` - Get number of open positions
- `positions_get(...)` - Get open positions
- `history_orders_total(from, to)` - Get historical order count
- `history_orders_get(...)` - Get historical orders
- `history_deals_total(from, to)` - Get historical deal count
- `history_deals_get(...)` - Get historical deals

## Timeframes

All standard MT5 timeframes are supported:
- `TIMEFRAME_M1`, `TIMEFRAME_M2`, `TIMEFRAME_M3`, `TIMEFRAME_M4`, `TIMEFRAME_M5`
- `TIMEFRAME_M6`, `TIMEFRAME_M10`, `TIMEFRAME_M12`, `TIMEFRAME_M15`, `TIMEFRAME_M20`
- `TIMEFRAME_M30`
- `TIMEFRAME_H1`, `TIMEFRAME_H2`, `TIMEFRAME_H3`, `TIMEFRAME_H4`, `TIMEFRAME_H6`
- `TIMEFRAME_H8`, `TIMEFRAME_H12`
- `TIMEFRAME_D1`, `TIMEFRAME_W1`, `TIMEFRAME_MN1`

## Constants

All MT5 constants are available:
- Order types: `ORDER_TYPE_BUY`, `ORDER_TYPE_SELL`, etc.
- Trade actions: `TRADE_ACTION_DEAL`, `TRADE_ACTION_PENDING`, etc.
- Order filling: `ORDER_FILLING_FOK`, `ORDER_FILLING_IOC`, etc.
- Position types: `POSITION_TYPE_BUY`, `POSITION_TYPE_SELL`
- Deal types: `DEAL_TYPE_BUY`, `DEAL_TYPE_SELL`, etc.
- Return codes: `TRADE_RETCODE_DONE`, `TRADE_RETCODE_REQUOTE`, etc.

## Error Handling

All functions return `None` on error. Check `last_error()` for error codes:

```python
import MetaTrader5 as mt5

tick = mt5.symbol_info_tick("INVALID")
if tick is None:
    error_code = mt5.last_error()
    print(f"Error: {error_code}")
    # RES_E_NOT_FOUND = -4 (symbol not found)
```

Common error codes:
- `RES_S_OK` (1) - Success
- `RES_E_FAIL` (-1) - Generic error
- `RES_E_INVALID_PARAMS` (-2) - Invalid parameters
- `RES_E_NOT_FOUND` (-4) - Not found
- `RES_E_INTERNAL_FAIL_CONNECT` (-10004) - Cannot connect to bridge
- `RES_E_INTERNAL_FAIL_TIMEOUT` (-10005) - Connection timeout

## Differences from Windows Version

1. **Connection**: Requires running the MT5Bridge EA in MT5 (Windows version connects directly)
2. **Path parameter**: `initialize(path)` is ignored (path only relevant on Windows)
3. **Network dependency**: Requires network connection to MT5 (even for local Wine)
4. **Performance**: Slightly slower due to network overhead (still very fast for most use cases)
5. **Installation**: Requires manual setup of the MQL5 bridge

## Troubleshooting

### Cannot connect to MT5

1. Verify MT5 is running with the Bridge EA attached
2. Check the EA is running (look for "MT5 Bridge listening" in MT5 Experts tab)
3. Verify firewall settings allow port 8222
4. Check environment variables: `MT5_HOST` and `MT5_PORT`

### Bridge EA compilation errors

1. Install required MQL5 libraries (JAson, Sockets)
2. Make sure to use "Compile" button (F7) in MetaEditor
3. Check MT5 version is up to date

### ModuleNotFoundError

Make sure you're installing on macOS/Linux, not Windows:
```bash
python -c "import sys; print(sys.platform)"  # Should print 'darwin' on Mac
```

## Performance Considerations

- The socket connection adds minimal latency (~1-2ms for local connections)
- Use `symbol_info_tick()` for real-time data
- Batch historical data requests when possible
- Consider using `market_book_add()` only when needed (increases data transfer)

## Security Notes

1. **Network Access**: The bridge EA opens a TCP socket. By default, it only listens on localhost (127.0.0.1).
2. **Remote Access**: To allow remote connections, set `AllowRemote = true` in the EA settings (not recommended for production).
3. **Authentication**: The current implementation does not include authentication. Only use on trusted networks.

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit your changes: `git commit -am 'Add feature'`
4. Push to the branch: `git push origin feature-name`
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

## Disclaimer

This is an unofficial implementation. MetaQuotes Software Corp. is not affiliated with this project. Use at your own risk. Trading forex and CFDs carries a high risk of losing money.

## Credits

- Original MetaTrader5 Python API by MetaQuotes Ltd.
- macOS implementation by reverse engineering the Windows API
- MQL5 JSON library by various contributors on MQL5.com

## Examples

The `examples/` directory contains ready-to-use scripts:

### `fetch_btc_data.py` - Comprehensive BTC Data Fetcher

Fetches complete Bitcoin data from MT5:

```bash
python examples/fetch_btc_data.py
```

Features:
- Automatically finds BTC symbol (BTCUSD, BTCUSDT, XBTUSD, etc.)
- Displays current price, spread, and market info
- Fetches hourly and daily OHLCV data
- Retrieves historical tick data
- Shows trading conditions and margin requirements
- Displays open positions for BTC

### `test_btc_api.py` - API Test Suite

Tests all major API functions with BTC:

```bash
python examples/test_btc_api.py
```

Tests:
- Connection to MT5
- Account info retrieval
- BTC symbol discovery
- Historical data fetching
- Position and order retrieval
- Margin calculation
- Demo trade request structure

### `basic_usage.py` - Getting Started

Simple introduction to the API:

```bash
python examples/basic_usage.py
```

Shows:
- Basic connection
- Terminal and account info
- Symbol listing
- Tick data retrieval
- Position checking

## Quick Start for BTC Trading

```python
import MetaTrader5 as mt5
from datetime import datetime, timedelta

# Connect
mt5.initialize()

# Get BTC price
tick = mt5.symbol_info_tick("BTCUSD")
print(f"BTC: Bid=${tick.bid}, Ask=${tick.ask}")

# Get last 24 hours of hourly data
rates = mt5.copy_rates_from(
    "BTCUSD",
    mt5.TIMEFRAME_H1,
    datetime.now() - timedelta(hours=24),
    24
)

# Calculate SMA
closes = [r.close for r in rates]
sma = sum(closes) / len(closes)
print(f"24H SMA: ${sma:,.2f}")

# Check positions
positions = mt5.positions_get(symbol="BTCUSD")
print(f"Open BTC positions: {len(positions)}")

# Disconnect
mt5.shutdown()
```

## Project Structure

```
metatrader5-macos/
├── MetaTrader5/              # Python package
│   ├── __init__.py          # Main module with constants
│   ├── _core.py             # Full JSON protocol implementation
│   └── _core_simple.py      # Text protocol (simpler bridge)
├── MQL5/
│   └── Experts/MT5Bridge/   # MQL5 Expert Advisors
│       ├── MT5Bridge.mq5       # Full-featured (needs JSON lib)
│       └── MT5BridgeSimple.mq5  # Simple (no external libs)
├── examples/                 # Example scripts
│   ├── basic_usage.py
│   ├── fetch_btc_data.py
│   └── test_btc_api.py
├── setup.py                 # Package setup
├── pyproject.toml           # Modern packaging
└── README.md                # This file
```

## Advanced Configuration

### Using Custom Host/Port

```python
import MetaTrader5 as mt5
import os

# Method 1: Environment variables
os.environ['MT5_HOST'] = '192.168.1.100'  # Remote MT5
os.environ['MT5_PORT'] = '9000'
mt5.initialize()

# Method 2: Direct connection (not yet implemented)
# Future versions may support:
# mt5.initialize(host='192.168.1.100', port=9000)
```

### Running Multiple Instances

You can run multiple Python scripts simultaneously:

```python
# Script 1: Price monitor
import MetaTrader5 as mt5
mt5.initialize()
while True:
    tick = mt5.symbol_info_tick("BTCUSD")
    print(f"Price: {tick.bid}")
    time.sleep(1)
```

```python
# Script 2: Trading bot
import MetaTrader5 as mt5
mt5.initialize()
# ... trading logic ...
```

Each script maintains its own connection to the MT5 bridge.

## Common Use Cases

### 1. Price Alert System

```python
import MetaTrader5 as mt5
import time

mt5.initialize()
target_price = 70000.0

while True:
    tick = mt5.symbol_info_tick("BTCUSD")
    if tick.ask >= target_price:
        print(f"Alert: BTC reached ${tick.ask}!")
        # Send notification, email, etc.
        break
    time.sleep(5)

mt5.shutdown()
```

### 2. Simple Trading Bot

```python
import MetaTrader5 as mt5

mt5.initialize()

# Get current price
tick = mt5.symbol_info_tick("EURUSD")

# Calculate SMA
from datetime import datetime, timedelta
rates = mt5.copy_rates_from(
    "EURUSD", mt5.TIMEFRAME_H1,
    datetime.now() - timedelta(hours=20), 20
)
sma = sum(r.close for r in rates) / len(rates)

# Trading logic
if tick.ask > sma:
    # Buy above SMA
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": "EURUSD",
        "volume": 0.1,
        "type": mt5.ORDER_TYPE_BUY,
        "price": tick.ask,
        "deviation": 10,
    }
    result = mt5.order_send(request)
    print(f"Trade result: {result}")

mt5.shutdown()
```

### 3. Data Export to CSV

```python
import MetaTrader5 as mt5
import pandas as pd

mt5.initialize()

# Get data
rates = mt5.copy_rates_range(
    "BTCUSD", mt5.TIMEFRAME_H1,
    datetime(2024, 1, 1), datetime(2024, 1, 31)
)

# Convert to DataFrame
df = pd.DataFrame(rates)
df['time'] = pd.to_datetime(df['time'], unit='s')

# Save to CSV
df.to_csv('btc_january_2024.csv', index=False)
print("Data exported to btc_january_2024.csv")

mt5.shutdown()
```

## Comparison with Windows Version

| Feature | Windows (Official) | macOS (This Package) |
|---------|-------------------|----------------------|
| Connection | Direct Named Pipe | TCP Socket via Bridge |
| Setup | `pip install` | `pip install` + Bridge EA |
| Performance | Native | ~1-2ms overhead |
| Real-time Data | Yes | Yes |
| Trading | Yes | Yes |
| Historical Data | Yes | Yes |
| Multi-symbol | Yes | Yes |
| Indicators | No | No |
| Chart Operations | No | No |

## Troubleshooting

### Cannot connect to MT5

1. Verify MT5 is running with the Bridge EA attached
2. Check the EA is running (look for "MT5 Bridge listening" in MT5 Experts tab)
3. Verify firewall settings allow port 8222
4. Check environment variables: `MT5_HOST` and `MT5_PORT`

### Bridge EA compilation errors

1. Install required MQL5 libraries (JAson, Sockets)
2. Make sure to use "Compile" button (F7) in MetaEditor
3. Check MT5 version is up to date

### ModuleNotFoundError

Make sure you're installing on macOS/Linux, not Windows:
```bash
python -c "import sys; print(sys.platform)"  # Should print 'darwin' on Mac
```

### Getting "Symbol not found" errors

Not all brokers offer the same symbols. Check available symbols:

```python
import MetaTrader5 as mt5
mt5.initialize()
symbols = mt5.symbols_get()
for s in symbols:
    if 'BTC' in str(s) or 'ETH' in str(s):
        print(s)
```

### Connection timeouts

Increase timeout value:
```bash
export MT5_TIMEOUT=60
```

## Performance Considerations

- The socket connection adds minimal latency (~1-2ms for local connections)
- Use `symbol_info_tick()` for real-time data
- Batch historical data requests when possible
- Consider using `market_book_add()` only when needed (increases data transfer)
- Reuse connections - don't initialize/shutdown repeatedly

## Security Notes

1. **Network Access**: The bridge EA opens a TCP socket. By default, it only listens on localhost (127.0.0.1).
2. **Remote Access**: To allow remote connections, set `AllowRemote = true` in the EA settings (not recommended for production).
3. **Authentication**: The current implementation does not include authentication. Only use on trusted networks.
4. **API Keys**: Never commit API keys or passwords to version control

## Support

For issues and feature requests, please use the GitHub issue tracker.

For MT5-specific questions, refer to the official MQL5 documentation:
https://www.mql5.com/en/docs/integration/python_metatrader5
