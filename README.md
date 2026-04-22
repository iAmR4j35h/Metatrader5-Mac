# MetaTrader5 for macOS 🍎

[![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/iAmR4j35h/Metatrader5-Mac)](https://github.com/iAmR4j35h/Metatrader5-Mac/stargazers)
[![GitHub issues](https://img.shields.io/github/issues/iAmR4j35h/Metatrader5-Mac)](https://github.com/iAmR4j35h/Metatrader5-Mac/issues)

> ☕ **[Support this project](#support-and-donate)** – Help keep this macOS port maintained!

> 🚀 **Trade on MetaTrader 5 from your Mac!** A reverse-engineered, macOS-compatible Python API for MetaTrader 5.

## Why This Package?

The official `metatrader5` Python package only works on **Windows** (uses Windows Named Pipes). This package provides a **macOS-compatible** implementation using TCP sockets, enabling full MT5 control from macOS.

| Feature | Windows Official | macOS (This Package) |
|---------|------------------|---------------------|
| Native Python API | ✅ | ✅ |
| Real-time price streaming | ✅ | ✅ |
| Trading operations | ✅ | ✅ |
| Historical data | ✅ | ✅ |
| Live tick streaming | ✅ | ✅ |
| Works on macOS | ❌ | ✅ |

## 📚 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Examples](#examples)
- [Live Data Streaming](#live-data-streaming)
- [API Reference](#api-reference)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)

---

## Quick Start

```python
import MetaTrader5 as mt5

# Connect to MT5 (auto-starts bridge server)
mt5.initialize()

# Get real-time BTC price
tick = mt5.symbol_info_tick("BTCUSD")
print(f"BTC: ${tick.bid:,.2f}")

# Check account
account = mt5.account_info()
print(f"Balance: ${account.balance:,.2f}")

# Get historical data
from datetime import datetime, timedelta
rates = mt5.copy_rates_range(
    "EURUSD", mt5.TIMEFRAME_H1,
    datetime.now() - timedelta(hours=24),
    datetime.now()
)
print(f"Got {len(rates)} hourly candles")

# Place a trade (example)
request = {
    "action": mt5.TRADE_ACTION_DEAL,
    "symbol": "EURUSD",
    "volume": 0.1,
    "type": mt5.ORDER_TYPE_BUY,
    "price": mt5.symbol_info_tick("EURUSD").ask,
    "deviation": 10,
}
# result = mt5.order_send(request)  # Uncomment to trade

# Disconnect
mt5.shutdown()
```

---

## Installation

### Prerequisites

You need MetaTrader 5 running on your Mac via one of:

1. **[CrossOver](https://www.codeweavers.com/crossover)** (Recommended - easiest)
2. **[Wine](https://www.winehq.org/)** (Free alternative)
3. **Windows VM** (Parallels, VMware, VirtualBox)
4. **Remote Windows PC** (accessible via network)

### Step 1: Install Python Package

```bash
# Clone and install
git clone https://github.com/iAmR4j35h/Metatrader5-Mac.git
cd Metatrader5-Mac
pip install -e .

# Or directly from GitHub
pip install git+https://github.com/iAmR4j35h/Metatrader5-Mac.git
```

### Step 2: Install MT5 Bridge EA

1. Open MetaTrader 5 (in Wine/VM)
2. Copy `MQL5/Experts/MT5Bridge/MT5Bridge.mq5` to your MT5 Data Folder:
   - In MT5: **File → Open Data Folder → MQL5 → Experts**
3. Compile the EA in MetaEditor (F7)
4. Attach the EA to any chart
5. Check the "Experts" tab - you should see "MT5 Bridge connected"

### Step 3: Run an Example

```bash
python examples/basic_usage.py
```

---

## Examples

All examples auto-start the bridge server and work out of the box:

### Basic Examples

| Script | Description | Command |
|--------|-------------|---------|
| `basic_usage.py` | Introduction to the API | `python examples/basic_usage.py` |
| `login_and_show_balance.py` | Login & display account info | `python examples/login_and_show_balance.py` |
| `fetch_btc_data.py` | Comprehensive BTC data fetcher | `python examples/fetch_btc_data.py` |
| `test_btc_api.py` | Test all API functions with BTC | `python examples/test_btc_api.py` |

### Live Streaming Examples ⭐ NEW

| Script | Description | Command |
|--------|-------------|---------|
| `live_data_stream.py` | Real-time price stream with trend detection | `python examples/live_data_stream.py` |
| `live_stream_advanced.py` | High-frequency streaming (100ms polling) | `python examples/live_stream_advanced.py` |

#### Live Stream Features:
- **Real-time updates**: 1-second or 100ms refresh rates
- **Trend detection**: Bullish/Bearish/Neutral indicators
- **Session statistics**: High, low, range, tick count
- **Price change tracking**: Up/down arrows with values
- **Auto-detect symbols**: Finds BTCUSD, BTCUSDm, etc.

Example output:
```
[14:32:05] 🟢 Bid:   77,574.31 Ask:   77,588.31 Last:   77,580.00 Spread: 14.00 Change: +12.50 ↑ Vol: 152
[14:32:06] 🟢 Bid:   77,575.12 Ask:   77,589.12 Last:   77,581.20 Spread: 14.00 Change:  +1.20 ↑ Vol: 89
```

---

## Live Data Streaming

### Basic Polling (1 second)

```python
import MetaTrader5 as mt5
import time

mt5.initialize()

symbol = "BTCUSDm"
last_price = None

while True:
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        if last_price != tick.last:
            print(f"{symbol}: ${tick.last:,.2f}")
            last_price = tick.last
    time.sleep(1)
```

### High-Frequency Streaming (100ms)

```python
import MetaTrader5 as mt5
from collections import deque
import time

mt5.initialize()

symbol = "EURUSD"
ticks = deque(maxlen=1000)

while True:
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        ticks.append({
            'time': time.time(),
            'bid': tick.bid,
            'ask': tick.ask,
            'last': tick.last
        })
    time.sleep(0.1)  # 100ms = 10 updates/second
```

---

## API Reference

### Connection
- `initialize()` - Connect to MT5 (auto-starts bridge)
- `shutdown()` - Disconnect from MT5
- `version()` - Get terminal version
- `last_error()` - Get last error code

### Account
- `account_info()` - Account details (balance, equity, margin)
- `terminal_info()` - Terminal information

### Market Data
- `symbol_info_tick(symbol)` - Current price (bid/ask/last)
- `symbol_info(symbol)` - Symbol details
- `symbols_get()` - List all symbols
- `copy_rates_range(symbol, timeframe, from, to)` - Historical OHLCV
- `copy_ticks_from(symbol, from, count)` - Historical ticks

### Trading
- `order_send(request)` - Execute trade
- `order_check(request)` - Validate order
- `order_calc_margin(...)` - Calculate margin required
- `positions_get()` - Get open positions
- `orders_get()` - Get pending orders
- `Close(symbol)` - Close positions

### Timeframes
`TIMEFRAME_M1`, `TIMEFRAME_M5`, `TIMEFRAME_M15`, `TIMEFRAME_H1`, `TIMEFRAME_H4`, `TIMEFRAME_D1`, `TIMEFRAME_W1`, `TIMEFRAME_MN1`

### Order Types
`ORDER_TYPE_BUY`, `ORDER_TYPE_SELL`, `ORDER_TYPE_BUY_LIMIT`, `ORDER_TYPE_SELL_LIMIT`, etc.

---

## Troubleshooting

### ❌ "Cannot connect to MT5 bridge"

1. ✅ MT5 is running with Bridge EA attached
2. ✅ EA shows "Connected to Python server" in Experts tab
3. ✅ Port 8222 not blocked by firewall
4. ✅ Bridge server is running (`python -m MetaTrader5`)

### ❌ "Address already in use"

The bridge server is already running. Examples auto-detect this - just run again.

### ❌ "Symbol not found"

Different brokers use different symbol names:
```python
# Try these variations
symbols = ['BTCUSD', 'BTCUSDm', 'BTCUSDT', 'XBTUSD']
for s in symbols:
    if mt5.symbol_info(s):
        print(f"Found: {s}")
        break
```

### Environment Variables

```bash
export MT5_HOST=127.0.0.1    # Bridge server host
export MT5_PORT=8222           # Bridge server port
export MT5_TIMEOUT=30          # Connection timeout
```

---

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│   Python Script │◄────►│  TCP Socket      │◆────►│  MT5 Terminal   │
│   (Your Mac)    │      │  Bridge Server   │      │  (Wine/VM/PC)   │
│                 │      │  localhost:8222  │      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘
        ▲                        ▲                           │
        │                        │                           │
   Calls API              Forwards requests              MT5Bridge EA
   (mt5.*)              (Python ↔ MT5)                 (MQL5)
```

**Protocol**: Text-based IPC via TCP socket
- Commands: `CMD|param1=value1|param2=value2\n`
- Responses: `OK|field=value|...` or `ERR|code=X|message=text`

---

## Project Structure

```
Metatrader5-Mac/
├── MetaTrader5/                 # Python package
│   ├── __init__.py             # Main API module
│   ├── _core.py                # Socket protocol implementation
│   ├── _bridge_server.py       # Bridge server (internal)
│   └── __main__.py             # `python -m MetaTrader5`
├── MQL5/Experts/MT5Bridge/      # MT5 Expert Advisors
│   └── MT5Bridge.mq5            # Bridge EA (compile in MT5)
├── examples/                     # Ready-to-use examples
│   ├── basic_usage.py
│   ├── login_and_show_balance.py
│   ├── fetch_btc_data.py
│   ├── test_btc_api.py
│   ├── live_data_stream.py      # ⭐ Real-time streaming
│   └── live_stream_advanced.py  # ⭐ High-frequency stream
├── setup.py
├── pyproject.toml
└── README.md
```

---

## Security

- **Localhost only**: Bridge defaults to `127.0.0.1` (no external access)
- **No authentication**: Use only on trusted networks
- **No passwords stored**: Login handled by MT5, not this package

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Commit: `git commit -am 'Add feature'`
4. Push: `git push origin feature-name`
5. Open a Pull Request

---

## License

MIT License - See [LICENSE](LICENSE) for details.

## Disclaimer

Unofficial implementation. MetaQuotes Software Corp. is not affiliated with this project. Trading forex/CFDs carries high risk of losing money.

## Support and Donate ☕

If this project helped you trade on macOS, consider supporting its development:

### GitHub Sponsors ⭐ (Zero fees!)
- [github.com/sponsors/iAmR4j35h](https://github.com/sponsors/iAmR4j35h)

### Cryptocurrency
| Chain | Address |
|-------|---------|
| **Bitcoin (BTC)** | `bc1qjav8denrl0yvqu20pxjeekwzuwx7j2trmjm5kh` |
| **Ethereum (ETH)** | `0x1F297d9174CdFd146992C30D3f31138eA430bf76` |
| **BNB Chain (BSC)** | `0x1F297d9174CdFd146992C30D3f31138eA430bf76` |
| **Tron (TRX/USDT)** | `TE7CaBstE66Ma3ZWpqHwpTh3Y152H1Xnpf` |

### What Your Support Covers
- 🐛 Bug fixes and maintenance
- ✨ New features (more brokers, indicators, etc.)
- 📚 Documentation and tutorials
- 🍎 Testing on latest macOS versions

---

**Other Ways to Support**
- ⭐ Star this repository
- 🐛 Report bugs via [GitHub Issues](https://github.com/iAmR4j35h/Metatrader5-Mac/issues)
- 📖 [Official MT5 Docs](https://www.mql5.com/en/docs/integration/python_metatrader5)

---

**⭐ Star this repo if you find it useful!**
