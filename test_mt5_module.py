#!/usr/bin/env python3
"""Test MetaTrader5 module directly."""

import sys
sys.path.insert(0, '/Users/r4j35h/Documents/Projects/MT5-Reverse')

import MetaTrader5 as mt5

print("=" * 60)
print("Testing MetaTrader5 Module")
print("=" * 60)

print("\n[1] Calling initialize()...")
result = mt5.initialize()
print(f"    Result: {result}")
print(f"    Last error: {mt5.last_error()}")

if result:
    print("\n[2] Getting account info...")
    account = mt5.account_info()
    if account:
        print(f"    Login: {account.login}")
        print(f"    Server: {account.server}")
        print(f"    Balance: {account.balance}")
        print(f"    Equity: {account.equity}")
    else:
        print(f"    Failed: {mt5.last_error()}")

    print("\n[3] Shutting down...")
    mt5.shutdown()
else:
    print("\n    ✗ Initialize failed!")

print("\n" + "=" * 60)
