# Troubleshooting MT5 Connection Issues

If the Python server is running but MT5 doesn't connect, here are the solutions:

## Most Common Fix: Whitelist the Server in MT5

MT5 requires explicit permission to connect to external servers.

### Step 1: Add Server to Allowed List

1. In MetaTrader 5, go to **Tools → Options → Expert Advisors**
2. Check **"Allow WebRequest for listed URL"**
3. Click **Add new URL** and enter:
   ```
   127.0.0.1:8222
   ```
   OR just:
   ```
   127.0.0.1
   ```
4. Click **OK**

![MT5 WebRequest Settings](https://i.imgur.com/example.png)

### Step 2: Enable Required Options

In the same **Expert Advisors** tab, ensure these are checked:
- ✅ **Allow automated trading**
- ✅ **Allow DLL imports** (if using DLLs)
- ✅ **Allow WebRequest for listed URL** (with 127.0.0.1 added)

### Step 3: Restart MT5

Close and reopen MetaTrader 5 to apply changes.

---

## Check EA Properties

### Verify EA Settings

1. In MT5 Navigator window, find **MT5BridgeClient**
2. Double-click it or drag to chart
3. In the Properties dialog:
   - **Common** tab:
     - ✅ Allow live trading
     - ✅ Allow DLL imports (if needed)
   - **Inputs** tab:
     - Check `ServerHost` is `127.0.0.1`
     - Check `ServerPort` is `8222`

### Check for Compilation Errors

1. Press **F4** to open MetaEditor
2. Open **MT5BridgeClient.mq5**
3. Press **F7** to compile
4. Check the **Errors** tab at the bottom:
   - Should show: `0 errors, 0 warnings`
   - If errors appear, fix them before continuing

---

## Check Connection Manually

### Test with Telnet/Netcat

From your Mac terminal:

```bash
# Test if port is accessible
nc -zv 127.0.0.1 8222
```

If it says `Connection refused`, the Python server might not be listening properly.

If it says `Connection succeeded`, the server is working.

### Test Python Server

In another terminal:

```bash
# Check if Python server is listening
lsof -i :8222
```

You should see Python process listening on port 8222.

---

## MT5 "Common" Tab Settings

When attaching the EA, this dialog appears. Ensure:

```
┌─────────────────────────────────────┐
│  Expert - MT5BridgeClient           │
├─────────────────────────────────────┤
│  ☑ Allow live trading             │
│  ☑ Allow DLL imports               │
│  ☐ Confirm DLL function calls      │
│                                     │
│  [Long position]  [Short position]  │
│  ☑ Buy   ☑ Sell                    │
│                                     │
│         [OK]  [Cancel]            │
└─────────────────────────────────────┘
```

---

## Enable Auto-Trading

### Global Setting

1. Look for **AutoTrading** button in toolbar (top of MT5)
2. It should be **pressed/highlighted** (enabled)
3. If not, click it to enable

### Per-EA Setting

1. Right-click on chart with EA
2. Select **Expert Advisors → Properties**
3. Check **Allow live trading**

---

## Check Logs

### In MT5 (Experts Tab)

Look for these messages:

**Good signs:**
```
MT5 Client Bridge initializing...
Will connect to Python server at 127.0.0.1:8222
Connecting to 127.0.0.1:8222...
Connected to Python server!
```

**Bad signs:**
```
Failed to create socket, error: 4014
Failed to connect to 127.0.0.1:8222, error: 5272
```

### Common Error Codes

| Error | Code | Meaning | Solution |
|-------|------|---------|----------|
| `ERR_TRADE_NOT_ALLOWED` | 4111 | Trading not allowed | Enable AutoTrading |
| `ERR_DLL_CALLS_NOT_ALLOWED` | 4014 | DLL calls not allowed | Enable DLL imports in EA properties |
| `ERR_NETSOCKET_CANNOT_CONNECT` | 5272 | Can't connect to server | Whitelist 127.0.0.1 in Tools → Options |
| `ERR_NETSOCKET_TOO_MANY_OPENED` | 5271 | Too many sockets | Close other EAs |
| `ERR_NETSOCKET_INVALIDHANDLE` | 5270 | Invalid socket handle | Restart MT5 |

---

## Alternative: Use Named Pipes via Wine

If socket connection fails, you can use Wine's built-in functionality:

### For Wine/CrossOver on macOS:

```bash
# Check if wineserver is running
ps aux | grep wineserver

# List Wine processes
wine tasklist
```

### Enable Wine Debugging:

```bash
# Run with debug output
WINEDEBUG=+winsock wine /path/to/terminal64.exe
```

---

## Quick Diagnostic Script

I've created a diagnostic script to test connections:

```bash
# Run this in terminal
cd /Users/r4j35h/Documents/Projects/MT5-Reverse
source venv/bin/activate
python -c "
import socket
import time

# Test 1: Can we bind to the port?
print('Test 1: Binding to port 8222...')
try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('127.0.0.1', 8222))
    s.listen(1)
    print('✓ Port 8222 is available')
    s.close()
except Exception as e:
    print(f'✗ Cannot bind: {e}')

# Test 2: Check if something is already listening
print('\nTest 2: Checking if server is running...')
import subprocess
result = subprocess.run(['lsof', '-i', ':8222'], capture_output=True, text=True)
if 'python' in result.stdout:
    print('✓ Python server is running')
else:
    print('✗ No Python process found on port 8222')
    print('Start the server: python MetaTrader5/server.py')

print('\nDone. Check MT5 Tools → Options → Expert Advisors')
print('Make sure 127.0.0.1:8222 is in the allowed URLs list')
"
```

---

## Checklist

Before trying to connect, verify:

- [ ] Python server is running (`python MetaTrader5/server.py`)
- [ ] MT5BridgeClient.mq5 compiles with 0 errors
- [ ] EA is attached to chart (smiley face visible)
- [ ] AutoTrading is enabled (toolbar button)
- [ ] EA Properties: Allow live trading is checked
- [ ] EA Properties: Allow DLL imports is checked
- [ ] Tools → Options → Expert Advisors: 127.0.0.1 is whitelisted
- [ ] Terminal restarted after changing options

---

## Still Not Working?

### Try Different Port

Sometimes port 8222 is blocked. Try another:

**In Python server:**
Edit `MetaTrader5/server.py`:
```python
PORT = 8080  # Change from 8222
```

**In MT5 EA:**
Set input `ServerPort` to `8080`

And add `127.0.0.1:8080` to whitelist.

### Check Firewall

On macOS:
```bash
# Check if firewall is blocking
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --getglobalstate
```

If it's on, you might need to allow the connection:
```bash
# Add Python to firewall allowed apps
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add $(which python3)
```

### Try Direct IP

Instead of `127.0.0.1`, try your actual IP:

1. Find your IP: `ifconfig | grep inet`
2. Use that IP in both Python and MT5
3. Add that IP to whitelist

---

## Success Indicators

When everything works, you'll see:

**In Python terminal:**
```
✓ MetaTrader 5 connected from ('127.0.0.1', 51234)
```

**In MT5 Experts tab:**
```
Connected to Python server!
```

---

## Need More Help?

1. Check MT5 log: **View → Strategy Tester → Journal** or **Experts** tab
2. Try running MT5 as Administrator (if on Windows VM)
3. Disable antivirus temporarily (some block socket connections)
4. Open an issue on GitHub: https://github.com/iAmR4j35h/Metatrader5-Mac/issues

Include these details in your issue:
- MT5 build number (Help → About)
- Operating system (macOS version, Wine/CrossOver/Parallels)
- Error messages from Experts tab
- Output of `python MetaTrader5/server.py`
