"""
Core IPC module for MetaTrader5 macOS implementation.

This module implements a socket-based IPC protocol to communicate with
MetaTrader 5 running on Windows (via Wine/CrossOver) or in a VM.

Protocol:
    - Uses TCP sockets for cross-platform compatibility
    - Text protocol: CMD|param1=value1|param2=value2\n
    - Response format: OK|field1=value1|field2=value2\n
                       ERR|code=X|message=text\n

MT5 Bridge Setup:
    For this to work, you need:
    1. MT5 running with MT5BridgeClient EA attached to a chart
    2. The EA connects to the Python bridge server on port 8222
    3. Python scripts call MT5 functions via the bridge
"""

import socket
import os
import time
import threading
from collections import namedtuple
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# Error codes
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


def _send_text(sock: socket.socket, data: str) -> None:
    """Send a text message with newline terminator."""
    msg = (data + '\n').encode('utf-8')
    sock.sendall(msg)


def _recv_text(sock: socket.socket, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """Receive a text message terminated by newline."""
    sock.settimeout(timeout)
    try:
        buffer = b''
        while b'\n' not in buffer:
            chunk = sock.recv(4096)
            if not chunk:
                return None
            buffer += chunk
        return buffer.decode('utf-8').strip()
    except socket.timeout:
        return None
    except Exception:
        return None


def _parse_text_response(text: str) -> tuple:
    """Parse a text response into (success, data_dict or error_code, error_message).

    Format: OK|field1=value1|field2=value2
            ERR|code=X|message=text
    """
    if not text:
        return False, RES_E_INTERNAL_FAIL_RECEIVE, "Empty response"

    parts = text.split('|')
    if not parts:
        return False, RES_E_INTERNAL_FAIL_RECEIVE, "Invalid response format"

    status = parts[0]

    # Parse key=value pairs
    data = {}
    for part in parts[1:]:
        if '=' in part:
            key, value = part.split('=', 1)
            data[key] = value

    if status == 'OK':
        return True, data, None
    elif status == 'ERR':
        code = int(data.get('code', RES_E_FAIL))
        message = data.get('message', 'Unknown error')
        return False, code, message
    else:
        return False, RES_E_INTERNAL_FAIL_RECEIVE, f"Unknown status: {status}"


def _ensure_connection() -> bool:
    """Ensure we have an active connection to the bridge server."""
    global _connection, _last_error

    with _connection_lock:
        if _connection is not None:
            # Test if connection is still alive using VERSION command
            # (Don't use bare PING as that's MT5's identification message)
            try:
                _connection.settimeout(2)
                _send_text(_connection, 'VERSION')
                response = _recv_text(_connection, 5)
                if response:
                    success, _, _ = _parse_text_response(response)
                    if success:
                        _last_error = RES_S_OK
                        return True
            except:
                pass
            # Connection is dead
            try:
                _connection.close()
            except:
                pass
            _connection = None

        # Try to connect to bridge server
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(DEFAULT_TIMEOUT)
            sock.connect((DEFAULT_HOST, DEFAULT_PORT))

            # Test the connection with VERSION command
            sock.settimeout(5)
            _send_text(sock, 'VERSION')
            response = _recv_text(sock, 5)

            if response:
                success, _, _ = _parse_text_response(response)
                if success:
                    _connection = sock
                    _last_error = RES_S_OK
                    return True

            sock.close()
            _last_error = RES_E_INTERNAL_FAIL_CONNECT
            return False

        except Exception as e:
            _last_error = RES_E_INTERNAL_FAIL_CONNECT
            return False


def _build_text_command(command: str, params: Dict[str, Any]) -> str:
    """Build a text command string from command and params."""
    if not params:
        return command

    param_strs = []
    for key, value in params.items():
        if value is None:
            continue
        # Handle different value types
        if isinstance(value, bool):
            val_str = 'true' if value else 'false'
        elif isinstance(value, (int, float)):
            val_str = str(value)
        elif isinstance(value, str):
            val_str = value
        else:
            val_str = str(value)
        param_strs.append(f"{key}={val_str}")

    if param_strs:
        return f"{command}|" + "|".join(param_strs)
    return command


def _call_mt5(command: str, **params) -> Optional[Dict[str, Any]]:
    """Call an MT5 function via the text IPC protocol."""
    global _last_error

    if not _ensure_connection():
        _last_error = RES_E_INTERNAL_FAIL_CONNECT
        return None

    cmd_str = _build_text_command(command, params)

    try:
        with _connection_lock:
            _send_text(_connection, cmd_str)
            response = _recv_text(_connection)

        if response is None:
            _last_error = RES_E_INTERNAL_FAIL_TIMEOUT
            return None

        success, data, error_msg = _parse_text_response(response)

        if not success:
            _last_error = data if isinstance(data, int) else RES_E_FAIL
            return None

        _last_error = RES_S_OK
        return data
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
    'magic', 'position_id', 'position_by_id', 'reason', 'volume_initial',
    'volume_current', 'profit', 'price_open', 'sl', 'tp', 'price_current',
    'price_stoplimit', 'symbol', 'comment', 'external_id'
])

PositionInfo = namedtuple('PositionInfo', [
    'ticket', 'time', 'time_msc', 'time_update', 'time_update_msc',
    'type', 'magic', 'identifier', 'reason', 'volume', 'price_open',
    'sl', 'tp', 'price_current', 'swap', 'profit', 'symbol', 'comment',
    'external_id'
])

TradeResult = namedtuple('TradeResult', [
    'retcode', 'deal', 'order', 'volume', 'price', 'bid', 'ask', 'comment',
    'request_id', 'retcode_external'
])

TradeRequest = namedtuple('TradeRequest', [
    'action', 'magic', 'order', 'symbol', 'volume', 'price', 'stoplimit',
    'sl', 'tp', 'deviation', 'type', 'type_filling', 'type_time',
    'expiration', 'comment', 'position', 'position_by'
])

RateInfo = namedtuple('RateInfo', [
    'time', 'open', 'high', 'low', 'close', 'tick_volume', 'spread', 'real_volume'
])

TerminalInfo = namedtuple('TerminalInfo', [
    'community_account', 'community_connection', 'connected', 'dlls_allowed',
    'trade_allowed', 'tradeapi_disabled', 'path', 'data_path', 'common_data_path'
])

# CopyTicksResult and CopyRatesFromPosition are simpler structures


def last_error():
    """Return the last error code."""
    return _last_error


def initialize(path: Optional[str] = None,
               login: Optional[int] = None,
               password: Optional[str] = None,
               server: Optional[str] = None,
               timeout: Optional[int] = None) -> bool:
    """Initialize connection to MetaTrader 5 terminal.

    Args:
        path: Path to MT5 executable (ignored, for compatibility)
        login: Account login (passed to MT5 if provided)
        password: Account password (passed to MT5 if provided)
        server: Trade server name (passed to MT5 if provided)
        timeout: Connection timeout in seconds

    Returns:
        True if successful, False otherwise
    """
    global _last_error

    # For the bridge architecture, we connect to the bridge server
    # MT5 EA should already be connected to the bridge

    if timeout:
        global DEFAULT_TIMEOUT
        DEFAULT_TIMEOUT = timeout

    # Build INIT command with optional login params
    params = {}
    if login is not None:
        params['login'] = login
    if password is not None:
        params['password'] = password
    if server is not None:
        params['server'] = server

    result = _call_mt5('INIT', **params)

    if result is not None:
        _last_error = RES_S_OK
        return True

    return False


def shutdown() -> None:
    """Close connection to MetaTrader 5 terminal."""
    global _connection
    with _connection_lock:
        if _connection:
            try:
                _send_text(_connection, 'SHUTDOWN')
                _connection.close()
            except:
                pass
            _connection = None


def version() -> Optional[tuple]:
    """Get the MetaTrader 5 terminal version.

    Returns:
        Tuple of (version, build, release_date) or None
    """
    result = _call_mt5('VERSION')
    if result is None:
        return None

    version_str = result.get('version', '')
    build = int(result.get('build', 0))
    date_str = result.get('date', '')

    return (version_str, build, date_str)


def _to_bool(val) -> bool:
    """Convert string or other value to boolean."""
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        return val.lower() in ('true', '1', 'yes', 'on')
    return bool(val)


def _to_int(val, default=0) -> int:
    """Convert string or other value to int."""
    if val is None:
        return default
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _to_float(val, default=0.0) -> float:
    """Convert string or other value to float."""
    if val is None:
        return default
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def terminal_info() -> Optional[TerminalInfo]:
    """Get information about the MetaTrader 5 terminal.

    Returns:
        TerminalInfo namedtuple or None
    """
    result = _call_mt5('TERMINAL_INFO')
    if result is None:
        return None

    return TerminalInfo(
        community_account=_to_bool(result.get('community_account', False)),
        community_connection=_to_bool(result.get('community_connection', False)),
        connected=_to_bool(result.get('connected', False)),
        dlls_allowed=_to_bool(result.get('dlls_allowed', False)),
        trade_allowed=_to_bool(result.get('trade_allowed', False)),
        tradeapi_disabled=_to_bool(result.get('tradeapi_disabled', False)),
        path=result.get('path', ''),
        data_path=result.get('data_path', ''),
        common_data_path=result.get('common_data_path', '')
    )


def account_info() -> Optional[AccountInfo]:
    """Get information about the current trading account.

    Returns:
        AccountInfo namedtuple or None
    """
    result = _call_mt5('ACCOUNT')
    if result is None:
        return None

    return AccountInfo(
        login=_to_int(result.get('login')),
        server=result.get('server', ''),
        currency=result.get('currency', ''),
        balance=_to_float(result.get('balance')),
        equity=_to_float(result.get('equity')),
        margin=_to_float(result.get('margin')),
        margin_free=_to_float(result.get('margin_free')),
        margin_level=_to_float(result.get('margin_level')),
        margin_call_level=_to_float(result.get('margin_call_level')),
        margin_stop_out_level=_to_float(result.get('margin_stop_out_level')),
        trade_allowed=_to_bool(result.get('trade_allowed')),
        trade_expert=_to_bool(result.get('trade_expert')),
        limit_orders=_to_int(result.get('limit_orders')),
        margin_mode=_to_int(result.get('margin_mode')),
        currency_digits=_to_int(result.get('currency_digits')),
        fifo_close=_to_bool(result.get('fifo_close')),
        hedged=_to_bool(result.get('hedged')),
        credit=_to_float(result.get('credit')),
        profit=_to_float(result.get('profit')),
        assets=_to_float(result.get('assets')),
        liabilities=_to_float(result.get('liabilities')),
        commission_blocked=_to_float(result.get('commission_blocked')),
        name=result.get('name', ''),
        leverage=_to_int(result.get('leverage')),
        trade_mode=_to_int(result.get('trade_mode'))
    )


def symbols_total() -> int:
    """Get the total number of all financial instruments in MT5.

    Returns:
        Total number of symbols
    """
    result = _call_mt5('SYMBOL_TOTAL')
    if result is None:
        return 0
    return int(result.get('total', 0))


def symbols_get(group: Optional[str] = None) -> Optional[List[str]]:
    """Get all financial instruments from MetaTrader 5.

    Args:
        group: Filter by group pattern (optional)

    Returns:
        List of symbol names or None
    """
    params = {}
    if group:
        params['group'] = group

    result = _call_mt5('SYMBOL_GET', **params)
    if result is None:
        return None

    # Parse comma-separated symbol list
    symbols_str = result.get('symbols', '')
    if symbols_str:
        return symbols_str.split(',')
    return []


def symbol_info(symbol: str) -> Optional[SymbolInfo]:
    """Get information about a financial instrument.

    Args:
        symbol: Symbol name (e.g., "EURUSD")

    Returns:
        SymbolInfo namedtuple or None
    """
    result = _call_mt5('SYMBOL_INFO', symbol=symbol)
    if result is None:
        return None

    # Build SymbolInfo from result
    return SymbolInfo(
        custom=result.get('custom', False),
        chart_mode=int(result.get('chart_mode', 0)),
        select=result.get('select', False),
        visible=result.get('visible', False),
        session_deals=int(result.get('session_deals', 0)),
        session_buy_orders=int(result.get('session_buy_orders', 0)),
        session_sell_orders=int(result.get('session_sell_orders', 0)),
        volume=int(result.get('volume', 0)),
        volumehigh=int(result.get('volumehigh', 0)),
        volumelow=int(result.get('volumelow', 0)),
        time=int(result.get('time', 0)),
        digits=int(result.get('digits', 0)),
        spread=int(result.get('spread', 0)),
        spread_float=result.get('spread_float', False),
        ticks_bookdepth=int(result.get('ticks_bookdepth', 0)),
        trade_calc_mode=int(result.get('trade_calc_mode', 0)),
        trade_mode=int(result.get('trade_mode', 0)),
        start_time=int(result.get('start_time', 0)),
        expiration_time=int(result.get('expiration_time', 0)),
        trade_stops_level=int(result.get('trade_stops_level', 0)),
        trade_freeze_level=int(result.get('trade_freeze_level', 0)),
        trade_exemode=int(result.get('trade_exemode', 0)),
        swap_mode=int(result.get('swap_mode', 0)),
        swap_rollover3days=int(result.get('swap_rollover3days', 0)),
        margin_hedged_use_leg=result.get('margin_hedged_use_leg', False),
        expiration_mode=int(result.get('expiration_mode', 0)),
        filling_mode=int(result.get('filling_mode', 0)),
        order_mode=int(result.get('order_mode', 0)),
        name=result.get('name', symbol),
        path=result.get('path', ''),
        description=result.get('description', ''),
        currency_base=result.get('currency_base', ''),
        currency_profit=result.get('currency_profit', ''),
        currency_margin=result.get('currency_margin', ''),
        session_volume=float(result.get('session_volume', 0.0)),
        session_turnover=float(result.get('session_turnover', 0.0)),
        session_interest=float(result.get('session_interest', 0.0)),
        session_buy_orders_volume=float(result.get('session_buy_orders_volume', 0.0)),
        session_sell_orders_volume=float(result.get('session_sell_orders_volume', 0.0)),
        session_open=result.get('session_open', ''),
        session_close=result.get('session_close', ''),
        session_aw=result.get('session_aw', ''),
        session_price_settlement=float(result.get('session_price_settlement', 0.0)),
        session_price_limit_min=float(result.get('session_price_limit_min', 0.0)),
        session_price_limit_max=float(result.get('session_price_limit_max', 0.0)),
        margin_initial=float(result.get('margin_initial', 0.0)),
        margin_maintenance=float(result.get('margin_maintenance', 0.0)),
        margin_hedged=float(result.get('margin_hedged', 0.0)),
        price_change=float(result.get('price_change', 0.0)),
        price_change_percent=float(result.get('price_change_percent', 0.0)),
        price_volatility=float(result.get('price_volatility', 0.0)),
        price_theoretical=float(result.get('price_theoretical', 0.0)),
        option_mode=int(result.get('option_mode', 0)),
        option_right=int(result.get('option_right', 0)),
        bid=float(result.get('bid', 0.0)),
        bidhigh=float(result.get('bidhigh', 0.0)),
        bidlow=float(result.get('bidlow', 0.0)),
        ask=float(result.get('ask', 0.0)),
        askhigh=float(result.get('askhigh', 0.0)),
        asklow=float(result.get('asklow', 0.0)),
        last=float(result.get('last', 0.0)),
        lasthigh=float(result.get('lasthigh', 0.0)),
        lastlow=float(result.get('lastlow', 0.0)),
        volume_real=float(result.get('volume_real', 0.0)),
        volumehigh_real=float(result.get('volumehigh_real', 0.0)),
        volumelow_real=float(result.get('volumelow_real', 0.0)),
        option_strike=float(result.get('option_strike', 0.0)),
        point=float(result.get('point', 0.0)),
        trade_tick_value=float(result.get('trade_tick_value', 0.0)),
        trade_tick_value_profit=float(result.get('trade_tick_value_profit', 0.0)),
        trade_tick_value_loss=float(result.get('trade_tick_value_loss', 0.0)),
        trade_tick_size=float(result.get('trade_tick_size', 0.0)),
        trade_contract_size=float(result.get('trade_contract_size', 0.0)),
        trade_accrued_interest=float(result.get('trade_accrued_interest', 0.0)),
        trade_face_value=float(result.get('trade_face_value', 0.0)),
        trade_liquidity_rate=float(result.get('trade_liquidity_rate', 0.0)),
        volume_min=float(result.get('volume_min', 0.0)),
        volume_max=float(result.get('volume_max', 0.0)),
        volume_step=float(result.get('volume_step', 0.0)),
        volume_limit=float(result.get('volume_limit', 0.0)),
        swap_long=float(result.get('swap_long', 0.0)),
        swap_short=float(result.get('swap_short', 0.0)),
        margin_initial_amount=float(result.get('margin_initial_amount', 0.0)),
        margin_maintenance_amount=float(result.get('margin_maintenance_amount', 0.0)),
        inventory_initial_margin=float(result.get('inventory_initial_margin', 0.0)),
        inventory_maintenance_margin=float(result.get('inventory_maintenance_margin', 0.0)),
        background_color=int(result.get('background_color', 0)),
        foreground_color=int(result.get('foreground_color', 0)),
        bar_up_color=int(result.get('bar_up_color', 0)),
        bar_down_color=int(result.get('bar_down_color', 0)),
        bull_candle_color=int(result.get('bull_candle_color', 0)),
        bear_candle_color=int(result.get('bear_candle_color', 0)),
        line_chart_color=int(result.get('line_chart_color', 0)),
        volume_color=int(result.get('volume_color', 0)),
        bid_line_color=int(result.get('bid_line_color', 0)),
        ask_line_color=int(result.get('ask_line_color', 0)),
        last_line_color=int(result.get('last_line_color', 0)),
        is_line_chart=result.get('is_line_chart', False),
        is_colored_candle_chart=result.get('is_colored_candle_chart', False),
        is_bar_chart=result.get('is_bar_chart', False)
    )


def symbol_info_tick(symbol: str) -> Optional[Tick]:
    """Get the last tick for a financial instrument.

    Args:
        symbol: Symbol name (e.g., "EURUSD")

    Returns:
        Tick namedtuple or None
    """
    result = _call_mt5('TICK', symbol=symbol)
    if result is None:
        return None

    return Tick(
        time=int(result.get('time', 0)),
        bid=float(result.get('bid', 0.0)),
        ask=float(result.get('ask', 0.0)),
        last=float(result.get('last', 0.0)),
        volume=int(result.get('volume', 0)),
        time_msc=int(result.get('time_msc', 0)),
        flags=int(result.get('flags', 0)),
        volume_real=float(result.get('volume_real', 0.0)),
        spread=int(result.get('spread', 0)),
        is_new_tick=result.get('is_new_tick', False)
    )


def symbol_select(symbol: str, enable: bool = True) -> bool:
    """Select a symbol in the Market Watch window.

    Args:
        symbol: Symbol name
        enable: True to select, False to deselect

    Returns:
        True if successful, False otherwise
    """
    result = _call_mt5('SYMBOL_SELECT', symbol=symbol, enable=enable)
    return result is not None


def market_book_add(symbol: str) -> bool:
    """Subscribe to market depth (Depth of Market) for a symbol.

    Args:
        symbol: Symbol name

    Returns:
        True if successful, False otherwise
    """
    result = _call_mt5('MARKET_BOOK_ADD', symbol=symbol)
    return result is not None


def market_book_get(symbol: str) -> Optional[List[Dict]]:
    """Get market depth (Depth of Market) data.

    Args:
        symbol: Symbol name

    Returns:
        List of market depth entries or None
    """
    result = _call_mt5('MARKET_BOOK_GET', symbol=symbol)
    if result is None:
        return None

    # Parse JSON-like data from text response
    data_str = result.get('data', '[]')
    try:
        import json
        return json.loads(data_str)
    except:
        return None


def market_book_release(symbol: str) -> bool:
    """Unsubscribe from market depth for a symbol.

    Args:
        symbol: Symbol name

    Returns:
        True if successful, False otherwise
    """
    result = _call_mt5('MARKET_BOOK_RELEASE', symbol=symbol)
    return result is not None


def orders_total() -> int:
    """Get the number of active orders.

    Returns:
        Total number of orders
    """
    result = _call_mt5('ORDERS_TOTAL')
    if result is None:
        return 0
    return int(result.get('total', 0))


def orders_get(symbol: Optional[str] = None,
               group: Optional[str] = None,
               ticket: Optional[int] = None) -> Optional[List[OrderInfo]]:
    """Get active orders with optional filters.

    Args:
        symbol: Filter by symbol
        group: Filter by group
        ticket: Filter by order ticket

    Returns:
        List of OrderInfo namedtuples or None
    """
    params = {}
    if symbol:
        params['symbol'] = symbol
    if group:
        params['group'] = group
    if ticket:
        params['ticket'] = ticket

    result = _call_mt5('ORDERS_GET', **params)
    if result is None:
        return None

    # Parse orders from response
    orders_data = result.get('orders', '')
    if not orders_data:
        return []

    # Orders are returned as a serialized format - parse them
    orders = []
    # For now, return empty list - full implementation would parse order list
    return orders


def positions_total() -> int:
    """Get the number of open positions.

    Returns:
        Total number of positions
    """
    result = _call_mt5('POSITIONS_TOTAL')
    if result is None:
        return 0
    return int(result.get('total', 0))


def positions_get(symbol: Optional[str] = None,
                  group: Optional[str] = None,
                  ticket: Optional[int] = None) -> Optional[List[PositionInfo]]:
    """Get open positions with optional filters.

    Args:
        symbol: Filter by symbol
        group: Filter by group
        ticket: Filter by position ticket

    Returns:
        List of PositionInfo namedtuples or None
    """
    params = {}
    if symbol:
        params['symbol'] = symbol
    if group:
        params['group'] = group
    if ticket:
        params['ticket'] = ticket

    result = _call_mt5('POSITIONS_GET', **params)
    if result is None:
        return None

    # Parse positions from response
    positions_data = result.get('positions', '')
    if not positions_data:
        return []

    positions = []
    # For now, return empty list - full implementation would parse position list
    return positions


def history_orders_total(from_date: datetime, to_date: datetime) -> int:
    """Get the number of orders in history within specified interval.

    Args:
        from_date: Start date
        to_date: End date

    Returns:
        Total number of orders in history
    """
    result = _call_mt5('HISTORY_ORDERS_TOTAL',
                       from_date=int(from_date.timestamp()),
                       to_date=int(to_date.timestamp()))
    if result is None:
        return 0
    return int(result.get('total', 0))


def history_orders_get(from_date: datetime,
                       to_date: datetime,
                       group: Optional[str] = None,
                       ticket: Optional[int] = None) -> Optional[List[OrderInfo]]:
    """Get orders from history with optional filters.

    Args:
        from_date: Start date
        to_date: End date
        group: Filter by group
        ticket: Filter by order ticket

    Returns:
        List of OrderInfo namedtuples or None
    """
    params = {
        'from_date': int(from_date.timestamp()),
        'to_date': int(to_date.timestamp())
    }
    if group:
        params['group'] = group
    if ticket:
        params['ticket'] = ticket

    result = _call_mt5('HISTORY_ORDERS_GET', **params)
    if result is None:
        return None

    return []


def history_deals_total(from_date: datetime, to_date: datetime) -> int:
    """Get the number of deals in history within specified interval.

    Args:
        from_date: Start date
        to_date: End date

    Returns:
        Total number of deals in history
    """
    result = _call_mt5('HISTORY_DEALS_TOTAL',
                       from_date=int(from_date.timestamp()),
                       to_date=int(to_date.timestamp()))
    if result is None:
        return 0
    return int(result.get('total', 0))


def history_deals_get(from_date: datetime,
                      to_date: datetime,
                      group: Optional[str] = None,
                      ticket: Optional[int] = None,
                      position: Optional[int] = None) -> Optional[List[Dict]]:
    """Get deals from history with optional filters.

    Args:
        from_date: Start date
        to_date: End date
        group: Filter by group
        ticket: Filter by deal ticket
        position: Filter by position ID

    Returns:
        List of deals or None
    """
    params = {
        'from_date': int(from_date.timestamp()),
        'to_date': int(to_date.timestamp())
    }
    if group:
        params['group'] = group
    if ticket:
        params['ticket'] = ticket
    if position:
        params['position'] = position

    result = _call_mt5('HISTORY_DEALS_GET', **params)
    if result is None:
        return None

    return []


def order_send(request: Dict[str, Any]) -> Optional[TradeResult]:
    """Send a trading order to the server.

    Args:
        request: Trade request dictionary with fields like:
            - action: Trade action type (e.g., TRADE_ACTION_DEAL)
            - symbol: Symbol name
            - volume: Order volume
            - type: Order type (e.g., ORDER_TYPE_BUY)
            - price: Order price
            - sl: Stop loss price (optional)
            - tp: Take profit price (optional)
            - deviation: Maximum price deviation (optional)
            - comment: Order comment (optional)

    Returns:
        TradeResult namedtuple or None
    """
    # Convert request dict to params
    params = {}
    for key, value in request.items():
        if isinstance(value, bool):
            params[key] = 'true' if value else 'false'
        else:
            params[key] = str(value)

    result = _call_mt5('ORDER_SEND', **params)
    if result is None:
        return None

    return TradeResult(
        retcode=int(result.get('retcode', 0)),
        deal=int(result.get('deal', 0)),
        order=int(result.get('order', 0)),
        volume=float(result.get('volume', 0.0)),
        price=float(result.get('price', 0.0)),
        bid=float(result.get('bid', 0.0)),
        ask=float(result.get('ask', 0.0)),
        comment=result.get('comment', ''),
        request_id=int(result.get('request_id', 0)),
        retcode_external=int(result.get('retcode_external', 0))
    )


def order_calc_margin(action: int, symbol: str, volume: float, price: float) -> Optional[float]:
    """Calculate margin required for a trade.

    Args:
        action: Order type (ORDER_TYPE_BUY or ORDER_TYPE_SELL)
        symbol: Symbol name
        volume: Trade volume in lots
        price: Open price

    Returns:
        Required margin or None if error
    """
    result = _call_mt5('ORDER_CALC_MARGIN',
                       action=action,
                       symbol=symbol,
                       volume=volume,
                       price=price)
    if result is None:
        return None

    return float(result.get('margin', 0.0))


def order_calc_profit(action: int, symbol: str, volume: float,
                      price_open: float, price_close: float) -> Optional[float]:
    """Calculate profit for a trade.

    Args:
        action: Order type (ORDER_TYPE_BUY or ORDER_TYPE_SELL)
        symbol: Symbol name
        volume: Trade volume in lots
        price_open: Open price
        price_close: Close price

    Returns:
        Calculated profit or None if error
    """
    result = _call_mt5('ORDER_CALC_PROFIT',
                       action=action,
                       symbol=symbol,
                       volume=volume,
                       price_open=price_open,
                       price_close=price_close)
    if result is None:
        return None

    return float(result.get('profit', 0.0))


def order_check(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Check if a trade request is valid without executing it.

    Args:
        request: Trade request dictionary

    Returns:
        Check result dictionary with 'retcode' and other fields
    """
    params = {}
    for key, value in request.items():
        if isinstance(value, bool):
            params[key] = 'true' if value else 'false'
        else:
            params[key] = str(value)

    result = _call_mt5('ORDER_CHECK', **params)
    if result is None:
        return None

    return dict(result)


def copy_rates_from_pos(symbol: str, timeframe: int, start_pos: int, count: int) -> Optional[List[RateInfo]]:
    """Get historical price data from a specified position.

    Args:
        symbol: Symbol name
        timeframe: Timeframe (e.g., TIMEFRAME_M1, TIMEFRAME_H1)
        start_pos: Starting position (0 = current bar)
        count: Number of bars to retrieve

    Returns:
        List of RateInfo namedtuples or None
    """
    result = _call_mt5('COPY_RATES_FROM_POS',
                       symbol=symbol,
                       timeframe=timeframe,
                       start_pos=start_pos,
                       count=count)
    if result is None:
        return None

    # Parse rates data
    rates = []
    # Full implementation would parse rate list from response
    return rates


def copy_rates_from_date(symbol: str, timeframe: int,
                         date_from: datetime, count: int) -> Optional[List[RateInfo]]:
    """Get historical price data starting from a specified date.

    Args:
        symbol: Symbol name
        timeframe: Timeframe
        date_from: Start date
        count: Number of bars to retrieve

    Returns:
        List of RateInfo namedtuples or None
    """
    result = _call_mt5('COPY_RATES_FROM_DATE',
                       symbol=symbol,
                       timeframe=timeframe,
                       date_from=int(date_from.timestamp()),
                       count=count)
    if result is None:
        return None

    return []


def copy_rates_range(symbol: str, timeframe: int,
                     date_from: datetime, date_to: datetime) -> Optional[List[RateInfo]]:
    """Get historical price data within a date range.

    Args:
        symbol: Symbol name
        timeframe: Timeframe
        date_from: Start date
        date_to: End date

    Returns:
        List of RateInfo namedtuples or None
    """
    result = _call_mt5('COPY_RATES_RANGE',
                       symbol=symbol,
                       timeframe=timeframe,
                       date_from=int(date_from.timestamp()),
                       date_to=int(date_to.timestamp()))
    if result is None:
        return None

    return []


def copy_ticks_from(symbol: str, start_pos: int, count: int) -> Optional[List[Tick]]:
    """Get tick data from a specified position.

    Args:
        symbol: Symbol name
        start_pos: Starting tick position
        count: Number of ticks to retrieve

    Returns:
        List of Tick namedtuples or None
    """
    result = _call_mt5('COPY_TICKS_FROM',
                       symbol=symbol,
                       start_pos=start_pos,
                       count=count)
    if result is None:
        return None

    return []


def copy_ticks_range(symbol: str, date_from: datetime, date_to: datetime,
                     flags: int = 0) -> Optional[List[Tick]]:
    """Get tick data within a date range.

    Args:
        symbol: Symbol name
        date_from: Start date
        date_to: End date
        flags: Tick flags (COPY_TICKS_INFO, COPY_TICKS_TRADE, etc.)

    Returns:
        List of Tick namedtuples or None
    """
    result = _call_mt5('COPY_TICKS_RANGE',
                       symbol=symbol,
                       date_from=int(date_from.timestamp()),
                       date_to=int(date_to.timestamp()),
                       flags=flags)
    if result is None:
        return None

    return []
