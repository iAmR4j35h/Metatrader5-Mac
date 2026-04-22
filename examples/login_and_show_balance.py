#!/usr/bin/env python3
"""
MetaTrader 5 Login and Balance Display Script

This script demonstrates how to:
1. Auto-start the bridge server (or connect to existing one)
2. Login to a trading account (or use existing logged-in account)
3. Display comprehensive account information
4. Show balance, equity, margin, and other metrics

Usage:
    python login_and_show_balance.py

    Or with arguments:
    python login_and_show_balance.py --login 123456 --server "Broker-Demo"

Requirements:
    - MetaTrader 5 running with MT5Bridge EA attached
    - Valid trading account credentials (optional if already logged in)

Author: MetaTrader5 macOS Port
GitHub: https://github.com/iAmR4j35h/Metatrader5-Mac
"""

import MetaTrader5 as mt5
import sys
import argparse
import subprocess
import time
from datetime import datetime


# ============================================================
# CONFIGURATION - Edit these values with your account details
# ============================================================
DEFAULT_LOGIN = None          # Your MT5 account login (e.g., 245507058)
DEFAULT_PASSWORD = None       # Your MT5 account password (optional)
DEFAULT_SERVER = None         # Your broker server (e.g., "Exness-MT5Real24")

# Example:
# DEFAULT_LOGIN = 245507058
# DEFAULT_PASSWORD = "your_password_here"  # Not recommended for security
# DEFAULT_SERVER = "Exness-MT5Real24"
# ============================================================

# Bridge Server Configuration
AUTO_START_SERVER = True      # Set to False to run server manually
BRIDGE_HOST = '127.0.0.1'
BRIDGE_PORT = 8222
SERVER_STARTUP_DELAY = 3      # Seconds to wait for server to start


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

        # Wait for server to start
        print(f"[Auto] Waiting {SERVER_STARTUP_DELAY}s for server startup...")
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


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Login to MetaTrader 5 and display account balance',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                           # Use defaults from file or existing session
  %(prog)s --login 123456            # Specify login number
  %(prog)s --server "Broker-Demo"    # Specify server
  %(prog)s --password "password"     # Specify password (not recommended)

Configuration:
  Edit DEFAULT_LOGIN, DEFAULT_PASSWORD, DEFAULT_SERVER in this file.
  Set AUTO_START_SERVER = False to run server manually with:
      python -m MetaTrader5
        """
    )

    parser.add_argument(
        '--login', '-l',
        type=int,
        default=DEFAULT_LOGIN,
        help='Account login number (e.g., 123456)'
    )

    parser.add_argument(
        '--password', '-p',
        type=str,
        default=DEFAULT_PASSWORD,
        help='Account password (optional, not recommended to use via command line)'
    )

    parser.add_argument(
        '--server', '-s',
        type=str,
        default=DEFAULT_SERVER,
        help='Trading server name (e.g., "Broker-Demo", "Broker-Real")'
    )

    parser.add_argument(
        '--timeout', '-t',
        type=int,
        default=30,
        help='Connection timeout in seconds (default: 30)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Show detailed information'
    )

    parser.add_argument(
        '--no-auto-server',
        action='store_true',
        help='Disable auto-start of bridge server'
    )

    return parser.parse_args()


def connect_to_mt5(args, server_process=None):
    """
    Establish connection to MT5 and login to account.

    Args:
        args: Command line arguments
        server_process: Bridge server subprocess (if auto-started)

    Returns:
        bool: True if successful, False otherwise
    """
    print("=" * 70)
    print("         MetaTrader 5 Account Login & Balance Display")
    print("=" * 70)
    print()

    print("[1/4] Connecting to MetaTrader 5...")
    print("-" * 70)
    print()

    if not AUTO_START_SERVER or args.no_auto_server:
        print("Note: Auto-start disabled. Make sure bridge server is running:")
        print("      python -m MetaTrader5")
        print()

    # Prepare initialization parameters
    init_params = {}

    if args.login:
        init_params['login'] = args.login
        print(f"  Login ID: {args.login}")

    if args.server:
        init_params['server'] = args.server
        print(f"  Server: {args.server}")

    if args.password:
        init_params['password'] = args.password
        print(f"  Password: {'*' * len(args.password)}")

    if args.timeout:
        init_params['timeout'] = args.timeout
        print(f"  Timeout: {args.timeout} seconds")

    # Attempt to initialize
    if not mt5.initialize(**init_params):
        error_code = mt5.last_error()
        print()
        print("  ✗ Connection Failed!")
        print(f"  Error Code: {error_code}")
        print()

        # Provide specific error messages
        error_messages = {
            mt5.RES_E_INTERNAL_FAIL_INIT: "Initialization failed. MT5 may not be running.",
            mt5.RES_E_INTERNAL_FAIL_CONNECT: "Cannot connect to MT5 bridge. Check if EA is running.",
            mt5.RES_E_AUTH_FAILED: "Authentication failed. Check login/password.",
            mt5.RES_E_INVALID_VERSION: "Version mismatch between Python API and MT5.",
            mt5.RES_E_INTERNAL_FAIL_TIMEOUT: "Connection timeout. Check MT5 status.",
        }

        if error_code in error_messages:
            print(f"  Reason: {error_messages[error_code]}")
        else:
            print(f"  Reason: Unknown error (code {error_code})")

        print()
        print("Troubleshooting:")
        if server_process:
            print("  1. Bridge server was auto-started")
            print("  2. Make sure MetaTrader 5 is running")
            print("  3. Attach MT5Bridge EA to a chart in MT5")
            print("  4. Check that the EA shows 'Connected to Python server'")
        else:
            print("  1. Start the bridge server:")
            print("     python -m MetaTrader5")
            print()
            print("  2. Make sure MetaTrader 5 is running")
            print("  3. Attach MT5Bridge EA to a chart in MT5")
            print("  4. Check that the EA shows 'Connected to Python server'")
        print("  5. Verify firewall settings allow port 8222")
        print()
        print("Environment variables:")
        print("  export MT5_HOST=127.0.0.1  # Bridge server host")
        print("  export MT5_PORT=8222       # Bridge server port")
        return False

    print()
    print("  ✓ Connected to MetaTrader 5")
    return True


def display_terminal_info():
    """Display MetaTrader 5 terminal information."""
    print()
    print("[2/4] Terminal Information")
    print("-" * 70)

    # Get terminal version
    version = mt5.version()
    if version:
        print(f"  Platform Version: {version[0]}")
        print(f"  Build: {version[1]}")
        if len(version) > 2 and version[2]:
            build_date = datetime.fromtimestamp(version[2]).strftime('%Y-%m-%d')
            print(f"  Build Date: {build_date}")

    # Get terminal info
    terminal = mt5.terminal_info()
    if terminal:
        print(f"  Data Path: {terminal.data_path}")
        print(f"  Connected: {'Yes' if terminal.connected else 'No'}")
        print(f"  Trading Allowed: {'Yes' if terminal.trade_allowed else 'No'}")
        print(f"  DLLs Allowed: {'Yes' if terminal.dlls_allowed else 'No'}")
    else:
        print("  ⚠ Could not retrieve terminal information")


def display_account_info(verbose=False):
    """
    Display detailed account information.

    Args:
        verbose: Show additional details if True
    """
    print()
    print("[3/4] Account Information")
    print("-" * 70)

    account = mt5.account_info()

    if account is None:
        print("  ✗ Could not retrieve account information")
        print("  The account might not be logged in yet.")
        return False

    # Basic account info
    print()
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │ ACCOUNT DETAILS                                             │")
    print("  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │ Login:          {account.login:<45} │")
    print(f"  │ Server:         {account.server:<45} │")
    print(f"  │ Currency:       {account.currency:<45} │")
    print(f"  │ Trade Mode:     {'Demo' if account.trade_mode == 0 else 'Real' if account.trade_mode == 2 else 'Contest':<45} │")
    print("  └─────────────────────────────────────────────────────────────┘")

    # Financial summary
    print()
    print("  ┌─────────────────────────────────────────────────────────────┐")
    print("  │ FINANCIAL SUMMARY                                           │")
    print("  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │ Balance:        ${account.balance:>15,.2f} {account.currency:<23} │")
    print(f"  │ Equity:         ${account.equity:>15,.2f} {account.currency:<23} │")
    print(f"  │ Profit:         ${account.profit:>15,.2f} {account.currency:<23} │")
    print("  ├─────────────────────────────────────────────────────────────┤")
    print(f"  │ Margin:         ${account.margin:>15,.2f} {account.currency:<23} │")
    print(f"  │ Free Margin:    ${account.margin_free:>15,.2f} {account.currency:<23} │")

    # Calculate margin level safely
    if account.margin > 0:
        margin_level = (account.equity / account.margin) * 100
        margin_level_str = f"{margin_level:.2f}%"
    else:
        margin_level_str = "N/A (no margin used)"

    print(f"  │ Margin Level:   {margin_level_str:>15} {'':<24} │")

    if account.margin_level:
        print(f"  │ Margin %:       {account.margin_level:.2f}%{'':<36} │")

    print("  └─────────────────────────────────────────────────────────────┘")

    # Additional details in verbose mode
    if verbose:
        print()
        print("  ┌─────────────────────────────────────────────────────────────┐")
        print("  │ ADDITIONAL DETAILS                                          │")
        print("  ├─────────────────────────────────────────────────────────────┤")
        print(f"  │ Credit:         ${account.credit:>15,.2f} {account.currency:<23} │")
        print(f"  │ Assets:        ${account.assets:>15,.2f} {account.currency:<23} │")
        print(f"  │ Liabilities:   ${account.liabilities:>15,.2f} {account.currency:<23} │")

        if hasattr(account, 'leverage') and account.leverage:
            print(f"  │ Leverage:       1:{account.leverage:<44} │")

        if hasattr(account, 'limit_orders') and account.limit_orders:
            print(f"  │ Limit Orders:   {account.limit_orders:<46} │")

        print("  └─────────────────────────────────────────────────────────────┘")

    return True


def display_trading_status():
    """Display current trading status and positions."""
    print()
    print("[4/4] Trading Status")
    print("-" * 70)

    # Get open positions
    positions = mt5.positions_get()
    positions_count = len(positions) if positions else 0

    # Get pending orders
    orders = mt5.orders_get()
    orders_count = len(orders) if orders else 0

    print(f"  Open Positions: {positions_count}")
    print(f"  Pending Orders: {orders_count}")
    print()

    # Display positions if any
    if positions and len(positions) > 0:
        print("  Open Positions:")
        print(f"  {'Ticket':<12} {'Symbol':<12} {'Type':<8} {'Volume':<10} {'Profit':<15}")
        print(f"  {'-'*65}")

        total_profit = 0

        for pos in positions:
            type_str = "Buy" if pos.type == mt5.ORDER_TYPE_BUY else "Sell"
            profit_str = f"${pos.profit:,.2f}"
            total_profit += pos.profit

            print(f"  {pos.ticket:<12} {pos.symbol:<12} {type_str:<8} "
                  f"{pos.volume:<10.2f} {profit_str:<15}")

        print(f"  {'-'*65}")
        profit_color = "+" if total_profit >= 0 else ""
        print(f"  Total P&L: {profit_color}${total_profit:,.2f}")
    else:
        print("  No open positions")

    # Display orders if any
    if orders and len(orders) > 0:
        print()
        print("  Pending Orders:")
        print(f"  {'Ticket':<12} {'Symbol':<12} {'Type':<12} {'Volume':<10} {'Price':<12}")
        print(f"  {'-'*60}")

        for order in orders:
            type_str = {
                mt5.ORDER_TYPE_BUY_LIMIT: "Buy Limit",
                mt5.ORDER_TYPE_SELL_LIMIT: "Sell Limit",
                mt5.ORDER_TYPE_BUY_STOP: "Buy Stop",
                mt5.ORDER_TYPE_SELL_STOP: "Sell Stop",
            }.get(order.type, f"Type {order.type}")

            print(f"  {order.ticket:<12} {order.symbol:<12} {type_str:<12} "
                  f"{order.volume_current:<10.2f} {order.price_open:<12.5f}")


def show_sample_usage():
    """Show sample usage after successful login."""
    print()
    print("=" * 70)
    print("Sample Usage Commands:")
    print("=" * 70)
    print()
    print("Get BTC price:")
    print("  tick = mt5.symbol_info_tick('BTCUSD')")
    print("  print(f'BTC: ${tick.bid}')")
    print()
    print("Place a buy order:")
    print("  request = {")
    print("      'action': mt5.TRADE_ACTION_DEAL,")
    print("      'symbol': 'EURUSD',")
    print("      'volume': 0.1,")
    print("      'type': mt5.ORDER_TYPE_BUY,")
    print("      'price': mt5.symbol_info_tick('EURUSD').ask,")
    print("      'deviation': 10")
    print("  }")
    print("  result = mt5.order_send(request)")
    print()
    print("Close all positions:")
    print("  mt5.Close('EURUSD')")


def main():
    """Main function."""
    args = parse_arguments()

    server_process = None

    # Auto-start bridge server if enabled
    if AUTO_START_SERVER and not args.no_auto_server:
        server_process = start_bridge_server()
        if server_process is None:
            print()
            print("✗ Failed to auto-start bridge server.")
            print("You can:")
            print("  1. Set AUTO_START_SERVER = False and run manually:")
            print("     python -m MetaTrader5")
            print("  2. Or fix the error above")
            print()
            print("Continuing anyway...")
            print()

    # Step 1: Connect
    if not connect_to_mt5(args, server_process):
        # Cleanup server if we started it
        if server_process:
            print("\nStopping bridge server...")
            server_process.terminate()
            try:
                server_process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                server_process.kill()
        sys.exit(1)

    try:
        # Step 2: Show terminal info
        display_terminal_info()

        # Step 3: Show account info
        account_ok = display_account_info(args.verbose)

        if account_ok:
            # Step 4: Show trading status
            display_trading_status()

            # Show sample usage
            show_sample_usage()
        else:
            print()
            print("⚠ Could not retrieve account information.")
            print("If you're not logged in, please log in through the MT5 terminal.")

    except Exception as e:
        print()
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Always cleanup
        print()
        print("=" * 70)
        print("Disconnecting from MetaTrader 5...")
        mt5.shutdown()
        print("✓ Disconnected")

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

        print("=" * 70)


if __name__ == "__main__":
    main()
