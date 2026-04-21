"""
Core IPC module for MetaTrader5 macOS implementation.

This module implements a socket-based IPC protocol to communicate with
MetaTrader 5 running on Windows (via Wine/CrossOver) or in a VM.

Protocol:
    - Uses TCP sockets for cross-platform compatibility
    - Binary protocol matching the Windows Named Pipe format
    - Message format: [4-byte length][JSON payload]

MT5 Bridge Setup:
    For this to work, you need one of:
    1. MT5 running in Wine/CrossOver with the socket bridge EA
    2. MT5 running in a Windows VM with the socket bridge EA
    3. MT5 running on a remote Windows machine with network access
"""

import socket
import struct
import json
import os
import time
import threading
from collections import namedtuple
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# Error codes (defined first as they are used in globals)
RES_S_OK                            = 1
RES_E_FAIL                          = -1
RES_E_INVALID_PARAMS                = -2
RES_E_NO_MEMORY                     = -3
RES_E_NOT_FOUND                     = -4
RES_E_INVALID_VERSION               = -5
RES_E_AUTH_FAILED                   = -6
RES_E_UNSUPPORTED                   = -7
RES_E_AUTO_TRADING_DISABLED         = -8
RES_E_INTERNAL_FAIL                 = -10000
RES_E_INTERNAL_FAIL_SEND            = -10001
RES_E_INTERNAL_FAIL_RECEIVE         = -10002
RES_E_INTERNAL_FAIL_INIT            = -10003
RES_E_INTERNAL_FAIL_CONNECT         = -10004
RES_E_INTERNAL_FAIL_TIMEOUT         = -10005

# Connection settings
DEFAULT_HOST = os.environ.get('MT5_HOST', '127.0.0.1')
DEFAULT_PORT = int(os.environ.get('MT5_PORT', '8222'))
DEFAULT_TIMEOUT = int(os.environ.get('MT5_TIMEOUT', '30'))

# Global connection state
_connection: Optional[socket.socket] = None
_last_error = RES_E_INTERNAL_FAIL_CONNECT
_connection_lock = threading.Lock()


class MT5Error(Exception):
    """Custom exception for MT5 errors."""
    pass


def _send_message(sock: socket.socket, data: dict) -> None:
    """Send a JSON message with length prefix."""
    payload = json.dumps(data).encode('utf-8')
    length = struct.pack('<I', len(payload))
    sock.sendall(length + payload)


def _recv_message(sock: socket.socket, timeout: int = DEFAULT_TIMEOUT) -> Optional[dict]:
    """Receive a JSON message with length prefix."""
    sock.settimeout(timeout)
    try:
        # Read 4-byte length
        length_data = b''
        while len(length_data) < 4:
            chunk = sock.recv(4 - len(length_data))
            if not chunk:
                return None
            length_data += chunk
        length = struct.unpack('<I', length_data)[0]

        # Read payload
        payload = b''
        while len(payload) < length:
            chunk = sock.recv(length - len(payload))
            if not chunk:
                return None
            payload += chunk

        return json.loads(payload.decode('utf-8'))
    except socket.timeout:
        return None
    except Exception:
        return None


def _ensure_connection() -> bool:
    """Ensure we have an active connection to MT5."""
    global _connection, _last_error

    with _connection_lock:
        if _connection is not None:
            # Test if connection is still alive
            try:
                _connection.settimeout(1)
                _send_message(_connection, {'cmd': 'ping'})
                response = _recv_message(_connection, 5)
                if response and response.get('result') == 'pong':
                    return True
            except:
                pass
            # Connection is dead
            try:
                _connection.close()
            except:
                pass
            _connection = None

        # Try to connect
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(DEFAULT_TIMEOUT)
            sock.connect((DEFAULT_HOST, DEFAULT_PORT))
            _connection = sock
            _last_error = RES_S_OK
            return True
        except Exception as e:
            _last_error = RES_E_INTERNAL_FAIL_CONNECT
            return False


def _call_mt5(command: str, **params) -> Optional[dict]:
    """Call an MT5 function via the IPC protocol."""
    global _last_error

    if not _ensure_connection():
        _last_error = RES_E_INTERNAL_FAIL_CONNECT
        return None

    message = {
        'cmd': command,
        'params': params
    }

    try:
        with _connection_lock:
            _send_message(_connection, message)
            response = _recv_message(_connection)

        if response is None:
            _last_error = RES_E_INTERNAL_FAIL_TIMEOUT
            return None

        if 'error' in response:
            _last_error = response.get('error_code', RES_E_FAIL)
            return None

        _last_error = RES_S_OK
        return response.get('result')
    except Exception as e:
        _last_error = RES_E_INTERNAL_FAIL
        # Reset connection on error
        with _connection_lock:
            if _connection:
                try:
                    _connection.close()
                except:
                    pass
            _connection = None
        return None


# Result namedtuples
AccountInfo = namedtuple('AccountInfo', [
    'login', 'server', 'currency', 'balance', 'equity', 'margin',
    'margin_free', 'margin_level', 'margin_call_level', 'margin_stop_out_level',
    'trade_allowed', 'trade_expert', 'limit_orders', 'margin_mode', 'currency_digits',
    'fifo_close', 'hedged', 'credit', 'profit', 'assets', 'liabilities',
    'commission_blocked', 'name', 'leverage', 'trade_mode'
])

SymbolInfo = namedtuple('SymbolInfo', [
    'custom', 'chart_mode', 'select', 'visible', 'session_deals', 'session_buy_orders',
    'session_sell_orders', 'volume', 'volumehigh', 'volumelow', 'time', 'digits',
    'spread', 'spread_float', 'ticks_bookdepth', 'trade_calc_mode', 'trade_mode',
    'start_time', 'expiration_time', 'trade_stops_level', 'trade_freeze_level',
    'trade_exemode', 'swap_mode', 'swap_rollover3days', 'margin_hedged_use_leg',
    'expiration_mode', 'filling_mode', 'order_mode', 'name', 'path', 'description',
    'currency_base', 'currency_profit', 'currency_margin', 'session_volume',
    'session_turnover', 'session_interest', 'session_buy_orders_volume',
    'session_sell_orders_volume', 'session_open', 'session_close', 'session_aw',
    'session_price_settlement', 'session_price_limit_min', 'session_price_limit_max',
    'margin_initial', 'margin_maintenance', 'margin_hedged', 'price_change',
    'price_change_percent', 'price_volatility', 'price_theoretical', 'option_mode',
    'option_right', 'bid', 'bidhigh', 'bidlow', 'ask', 'askhigh', 'asklow',
    'last', 'lasthigh', 'lastlow', 'volume_real', 'volumehigh_real', 'volumelow_real',
    'option_strike', 'point', 'trade_tick_value', 'trade_tick_value_profit',
    'trade_tick_value_loss', 'trade_tick_size', 'trade_contract_size',
    'trade_accrued_interest', 'trade_face_value', 'trade_liquidity_rate',
    'volume_min', 'volume_max', 'volume_step', 'volume_limit', 'swap_long',
    'swap_short', 'margin_initial_amount', 'margin_maintenance_amount',
    'inventory_initial_margin', 'inventory_maintenance_margin',
    'background_color', 'foreground_color', 'bar_up_color', 'bar_down_color',
    'bull_candle_color', 'bear_candle_color', 'line_chart_color',
    'volume_color', 'bid_line_color', 'ask_line_color', 'last_line_color',
    'is_line_chart', 'is_colored_candle_chart', 'is_bar_chart'
])

Tick = namedtuple('Tick', [
    'time', 'bid', 'ask', 'last', 'volume', 'time_msc', 'flags',
    'volume_real', 'spread', 'is_new_tick'
])

OrderInfo = namedtuple('OrderInfo', [
    'ticket', 'time_setup', 'time_setup_msc', 'time_done', 'time_done_msc',
    'time_expiration', 'type', 'type_time', 'type_filling', 'state',
    'magic', 'position_id', 'volume_current', 'volume_initial',
    'price_open', 'sl', 'tp', 'price_current', 'price_stoplimit', 'symbol',
    'comment', 'external_id', 'reason'
])

PositionInfo = namedtuple('PositionInfo', [
    'ticket', 'time', 'time_msc', 'time_update', 'time_update_msc',
    'type', 'magic', 'identifier', 'reason', 'volume', 'price_open',
    'sl', 'tp', 'price_current', 'swap', 'profit', 'symbol', 'comment',
    'external_id', 'volume_real', 'price_gross', 'commission'
])

DealInfo = namedtuple('DealInfo', [
    'ticket', 'order', 'time', 'time_msc', 'type', 'entry', 'magic',
    'position_id', 'reason', 'volume', 'price', 'commission', 'swap',
    'profit', 'fee', 'symbol', 'comment', 'external_id', 'volume_real'
])

TerminalInfo = namedtuple('TerminalInfo', [
    'community_account', 'community_connection', 'connected', 'dlls_allowed',
    'trade_allowed', 'tradeapi_disabled_broadcast', 'tradeapi_disabled_crash',
    'tradeapi_disabled_exception', 'tradeapi_disabled_crash_course',
    'tradeapi_disabled_timeout', 'peers_online', 'peers_online_total',
    'name', 'path', 'data_path', 'common_data_path', 'language'
])

OrderSendResult = namedtuple('OrderSendResult', [
    'retcode', 'deal', 'order', 'volume', 'price', 'bid', 'ask',
    'comment', 'request_id', 'retcode_external'
])

OrderCheckResult = namedtuple('OrderCheckResult', [
    'retcode', 'balance', 'equity', 'profit', 'margin', 'margin_free',
    'margin_level', 'comment', 'request_id'
])

BookInfo = namedtuple('BookInfo', [
    'type', 'price', 'volume', 'volume_real'
])


def initialize(path: Optional[str] = None,
               login: Optional[int] = None,
               password: Optional[str] = None,
               server: Optional[str] = None,
               timeout: Optional[int] = None) -> bool:
    """
    Initialize connection to the MetaTrader 5 terminal.

    Args:
        path: Path to the MT5 terminal (not used in macOS, MT5 must be running)
        login: Account login (optional, for auto-login)
        password: Account password (optional)
        server: Trade server name (optional)
        timeout: Connection timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    global DEFAULT_TIMEOUT, _last_error

    if timeout:
        DEFAULT_TIMEOUT = timeout

    # Build initialization parameters
    params = {}
    if login:
        params['login'] = login
    if password:
        params['password'] = password
    if server:
        params['server'] = server

    result = _call_mt5('initialize', **params)
    if result and result.get('success'):
        _last_error = RES_S_OK
        return True

    _last_error = RES_E_INTERNAL_FAIL_INIT
    return False


def shutdown() -> bool:
    """
    Shutdown the connection to the MetaTrader 5 terminal.

    Returns:
        True if successful
    """
    global _connection, _last_error

    try:
        _call_mt5('shutdown')
    except:
        pass

    with _connection_lock:
        if _connection:
            try:
                _connection.close()
            except:
                pass
            _connection = None

    _last_error = RES_S_OK
    return True


def version() -> tuple:
    """
    Get the version of the MetaTrader 5 terminal.

    Returns:
        Tuple of (version, build, release_date)
    """
    result = _call_mt5('version')
    if result:
        return (result.get('version'), result.get('build'), result.get('date'))
    return ()


def last_error() -> int:
    """
    Get the last error code.

    Returns:
        Error code
    """
    return _last_error


def symbols_total() -> int:
    """
    Get the total number of symbols in the Market Watch.

    Returns:
        Number of symbols
    """
    result = _call_mt5('symbols_total')
    if result:
        return result.get('total', 0)
    return 0


def symbols_get(group: Optional[str] = None) -> Optional[tuple]:
    """
    Get all symbols matching the specified group.

    Args:
        group: Group name filter (optional, glob pattern like "*USD*")

    Returns:
        Tuple of symbol names or None on error
    """
    params = {}
    if group:
        params['group'] = group

    result = _call_mt5('symbols_get', **params)
    if result:
        return tuple(result.get('symbols', []))
    return None


def symbol_info(symbol: str) -> Optional[SymbolInfo]:
    """
    Get information about a symbol.

    Args:
        symbol: Symbol name

    Returns:
        SymbolInfo namedtuple or None on error
    """
    result = _call_mt5('symbol_info', symbol=symbol)
    if result:
        return SymbolInfo(**result)
    return None


def symbol_info_tick(symbol: str) -> Optional[Tick]:
    """
    Get the last tick information for a symbol.

    Args:
        symbol: Symbol name

    Returns:
        Tick namedtuple or None on error
    """
    result = _call_mt5('symbol_info_tick', symbol=symbol)
    if result:
        return Tick(**result)
    return None


def symbol_select(symbol: str, enable: bool = True) -> bool:
    """
    Select a symbol in the Market Watch or hide it.

    Args:
        symbol: Symbol name
        enable: True to add to Market Watch, False to remove

    Returns:
        True if successful
    """
    result = _call_mt5('symbol_select', symbol=symbol, enable=enable)
    if result:
        return result.get('success', False)
    return False


def market_book_add(symbol: str) -> bool:
    """
    Subscribe to market depth updates for a symbol.

    Args:
        symbol: Symbol name

    Returns:
        True if successful
    """
    result = _call_mt5('market_book_add', symbol=symbol)
    if result:
        return result.get('success', False)
    return False


def market_book_get(symbol: str) -> Optional[tuple]:
    """
    Get the market depth data for a symbol.

    Args:
        symbol: Symbol name

    Returns:
        Tuple of BookInfo namedtuples or None on error
    """
    result = _call_mt5('market_book_get', symbol=symbol)
    if result:
        books = result.get('books', [])
        return tuple(BookInfo(**b) for b in books)
    return None


def market_book_release(symbol: str) -> bool:
    """
    Unsubscribe from market depth updates.

    Args:
        symbol: Symbol name

    Returns:
        True if successful
    """
    result = _call_mt5('market_book_release', symbol=symbol)
    if result:
        return result.get('success', False)
    return False


def get_ticks(symbol: str,
              start: datetime,
              count: int) -> Optional[tuple]:
    """
    Get ticks for a symbol (deprecated, use copy_ticks_from/range).

    Args:
        symbol: Symbol name
        start: Start date
        count: Number of ticks to retrieve

    Returns:
        Tuple of Tick namedtuples or None on error
    """
    return copy_ticks_from(symbol, start, count)


def get_rates(symbol: str,
              timeframe: int,
              start: datetime,
              count: int) -> Optional[tuple]:
    """
    Get rates for a symbol (deprecated, use copy_rates_from/range).

    Args:
        symbol: Symbol name
        timeframe: Timeframe constant (e.g., TIMEFRAME_M1)
        start: Start date
        count: Number of bars to retrieve

    Returns:
        Tuple of Rate namedtuples or None on error
    """
    return copy_rates_from(symbol, timeframe, start, count)


def orders_total() -> int:
    """
    Get the total number of active orders.

    Returns:
        Number of orders
    """
    result = _call_mt5('orders_total')
    if result:
        return result.get('total', 0)
    return 0


def orders_get(group: Optional[str] = None,
               ticket: Optional[int] = None,
               symbol: Optional[str] = None) -> Optional[tuple]:
    """
    Get active orders with optional filters.

    Args:
        group: Group filter (glob pattern)
        ticket: Specific order ticket
        symbol: Symbol name filter

    Returns:
        Tuple of OrderInfo namedtuples or None on error
    """
    params = {}
    if group:
        params['group'] = group
    if ticket:
        params['ticket'] = ticket
    if symbol:
        params['symbol'] = symbol

    result = _call_mt5('orders_get', **params)
    if result:
        orders = result.get('orders', [])
        return tuple(OrderInfo(**o) for o in orders)
    return None


def positions_total() -> int:
    """
    Get the total number of open positions.

    Returns:
        Number of positions
    """
    result = _call_mt5('positions_total')
    if result:
        return result.get('total', 0)
    return 0


def positions_get(group: Optional[str] = None,
                  ticket: Optional[int] = None,
                  symbol: Optional[str] = None) -> Optional[tuple]:
    """
    Get open positions with optional filters.

    Args:
        group: Group filter (glob pattern)
        ticket: Specific position ticket
        symbol: Symbol name filter

    Returns:
        Tuple of PositionInfo namedtuples or None on error
    """
    params = {}
    if group:
        params['group'] = group
    if ticket:
        params['ticket'] = ticket
    if symbol:
        params['symbol'] = symbol

    result = _call_mt5('positions_get', **params)
    if result:
        positions = result.get('positions', [])
        return tuple(PositionInfo(**p) for p in positions)
    return None


def history_orders_total(from_date: datetime,
                         to_date: datetime) -> int:
    """
    Get the total number of orders in history within the specified period.

    Args:
        from_date: Start date
        to_date: End date

    Returns:
        Number of orders
    """
    result = _call_mt5('history_orders_total',
                       from_date=from_date.timestamp(),
                       to_date=to_date.timestamp())
    if result:
        return result.get('total', 0)
    return 0


def history_orders_get(from_date: datetime,
                       to_date: datetime,
                       group: Optional[str] = None,
                       position: Optional[int] = None) -> Optional[tuple]:
    """
    Get orders from history within the specified period.

    Args:
        from_date: Start date
        to_date: End date
        group: Group filter (glob pattern)
        position: Position ID filter

    Returns:
        Tuple of OrderInfo namedtuples or None on error
    """
    params = {
        'from_date': from_date.timestamp(),
        'to_date': to_date.timestamp()
    }
    if group:
        params['group'] = group
    if position:
        params['position'] = position

    result = _call_mt5('history_orders_get', **params)
    if result:
        orders = result.get('orders', [])
        return tuple(OrderInfo(**o) for o in orders)
    return None


def history_deals_total(from_date: datetime,
                        to_date: datetime) -> int:
    """
    Get the total number of deals in history within the specified period.

    Args:
        from_date: Start date
        to_date: End date

    Returns:
        Number of deals
    """
    result = _call_mt5('history_deals_total',
                       from_date=from_date.timestamp(),
                       to_date=to_date.timestamp())
    if result:
        return result.get('total', 0)
    return 0


def history_deals_get(from_date: datetime,
                      to_date: datetime,
                      group: Optional[str] = None,
                      position: Optional[int] = None) -> Optional[tuple]:
    """
    Get deals from history within the specified period.

    Args:
        from_date: Start date
        to_date: End date
        group: Group filter (glob pattern)
        position: Position ID filter

    Returns:
        Tuple of DealInfo namedtuples or None on error
    """
    params = {
        'from_date': from_date.timestamp(),
        'to_date': to_date.timestamp()
    }
    if group:
        params['group'] = group
    if position:
        params['position'] = position

    result = _call_mt5('history_deals_get', **params)
    if result:
        deals = result.get('deals', [])
        return tuple(DealInfo(**d) for d in deals)
    return None


def order_calc_margin(action: int,
                      symbol: str,
                      volume: float,
                      price: float) -> Optional[float]:
    """
    Calculate margin required for a trade.

    Args:
        action: Order type (e.g., ORDER_TYPE_BUY)
        symbol: Symbol name
        volume: Trade volume
        price: Trade price

    Returns:
        Margin amount or None on error
    """
    result = _call_mt5('order_calc_margin',
                       action=action,
                       symbol=symbol,
                       volume=volume,
                       price=price)
    if result:
        return result.get('margin')
    return None


def order_calc_profit(action: int,
                      symbol: str,
                      volume: float,
                      price_open: float,
                      price_close: float) -> Optional[float]:
    """
    Calculate profit for a trade.

    Args:
        action: Order type (e.g., ORDER_TYPE_BUY)
        symbol: Symbol name
        volume: Trade volume
        price_open: Open price
        price_close: Close price

    Returns:
        Profit amount or None on error
    """
    result = _call_mt5('order_calc_profit',
                       action=action,
                       symbol=symbol,
                       volume=volume,
                       price_open=price_open,
                       price_close=price_close)
    if result:
        return result.get('profit')
    return None


def order_calc_check(request: dict) -> OrderCheckResult:
    """
    Check if a trade request is valid.

    Args:
        request: Trade request dictionary

    Returns:
        OrderCheckResult namedtuple or None on error
    """
    result = _call_mt5('order_calc_check', request=request)
    if result:
        return OrderCheckResult(**result)
    return None


def order_send(request: dict) -> OrderSendResult:
    """
    Send a trade request to the server.

    Args:
        request: Trade request dictionary with action, symbol, volume, etc.

    Returns:
        OrderSendResult namedtuple or None on error
    """
    result = _call_mt5('order_send', request=request)
    if result:
        return OrderSendResult(**result)
    return None


def order_check(request: dict) -> OrderCheckResult:
    """
    Check if a trade request is valid (same as order_calc_check).

    Args:
        request: Trade request dictionary

    Returns:
        OrderCheckResult namedtuple or None on error
    """
    return order_calc_check(request)


def copy_ticks_from(symbol: str,
                    date_from: datetime,
                    count: int,
                    flags: int = -1) -> Optional[tuple]:
    """
    Get ticks starting from the specified date.

    Args:
        symbol: Symbol name
        date_from: Start date
        count: Number of ticks to retrieve
        flags: Tick flags (default -1 for all)

    Returns:
        Tuple of Tick namedtuples or None on error
    """
    result = _call_mt5('copy_ticks_from',
                       symbol=symbol,
                       date_from=date_from.timestamp(),
                       count=count,
                       flags=flags)
    if result:
        ticks = result.get('ticks', [])
        return tuple(Tick(**t) for t in ticks)
    return None


def copy_ticks_range(symbol: str,
                     date_from: datetime,
                     date_to: datetime,
                     flags: int = -1) -> Optional[tuple]:
    """
    Get ticks within the specified date range.

    Args:
        symbol: Symbol name
        date_from: Start date
        date_to: End date
        flags: Tick flags (default -1 for all)

    Returns:
        Tuple of Tick namedtuples or None on error
    """
    result = _call_mt5('copy_ticks_range',
                       symbol=symbol,
                       date_from=date_from.timestamp(),
                       date_to=date_to.timestamp(),
                       flags=flags)
    if result:
        ticks = result.get('ticks', [])
        return tuple(Tick(**t) for t in ticks)
    return None


# Rate namedtuple
Rate = namedtuple('Rate', [
    'time', 'open', 'high', 'low', 'close', 'tick_volume',
    'spread', 'real_volume'
])


def copy_rates_from(symbol: str,
                    timeframe: int,
                    date_from: datetime,
                    count: int) -> Optional[tuple]:
    """
    Get rates starting from the specified date.

    Args:
        symbol: Symbol name
        timeframe: Timeframe constant (e.g., TIMEFRAME_M1)
        date_from: Start date
        count: Number of bars to retrieve

    Returns:
        Tuple of Rate namedtuples or None on error
    """
    result = _call_mt5('copy_rates_from',
                       symbol=symbol,
                       timeframe=timeframe,
                       date_from=date_from.timestamp(),
                       count=count)
    if result:
        rates = result.get('rates', [])
        return tuple(Rate(**r) for r in rates)
    return None


def copy_rates_range(symbol: str,
                     timeframe: int,
                     date_from: datetime,
                     date_to: datetime) -> Optional[tuple]:
    """
    Get rates within the specified date range.

    Args:
        symbol: Symbol name
        timeframe: Timeframe constant (e.g., TIMEFRAME_M1)
        date_from: Start date
        date_to: End date

    Returns:
        Tuple of Rate namedtuples or None on error
    """
    result = _call_mt5('copy_rates_range',
                       symbol=symbol,
                       timeframe=timeframe,
                       date_from=date_from.timestamp(),
                       date_to=date_to.timestamp())
    if result:
        rates = result.get('rates', [])
        return tuple(Rate(**r) for r in rates)
    return None


def terminal_info() -> TerminalInfo:
    """
    Get information about the MetaTrader 5 terminal.

    Returns:
        TerminalInfo namedtuple or None on error
    """
    result = _call_mt5('terminal_info')
    if result:
        return TerminalInfo(**result)
    return None


def account_info() -> Optional[AccountInfo]:
    """
    Get information about the currently active account.

    Returns:
        AccountInfo namedtuple or None on error
    """
    result = _call_mt5('account_info')
    if result:
        return AccountInfo(**result)
    return None
