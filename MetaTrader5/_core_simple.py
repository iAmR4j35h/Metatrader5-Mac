"""
Simplified core IPC module using text-based protocol.

This is an alternative implementation that uses a simpler text-based
protocol compatible with the MT5BridgeSimple.mq5 EA (no external libraries needed).

Protocol format:
    Request:  CMD|PARAM1=VAL1|PARAM2=VAL2\n
    Response: OK|FIELD1=VAL1|FIELD2=VAL2\n         or:  ERR|code=CODE|message=TEXT\n"""

import socket
import time
import os
import threading
from collections import namedtuple
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

# Error codes (defined first)
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


def _send_message(sock: socket.socket, data: str) -> None:
    """Send a text message."""
    msg = data.encode('utf-8')
    sock.sendall(msg + b'\n')


def _recv_message(sock: socket.socket, timeout: int = DEFAULT_TIMEOUT) -> Optional[str]:
    """Receive a text message."""
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


def _parse_response(msg: str) -> Optional[Dict[str, str]]:
    """Parse a text response into a dictionary."""
    if not msg:
        return None

    parts = msg.split('|')
    if len(parts) < 1:
        return None

    status = parts[0]
    result = {'_status': status}

    for i in range(1, len(parts)):
        if '=' in parts[i]:
            key, val = parts[i].split('=', 1)
            result[key] = val
        else:
            result[f'field_{i}'] = parts[i]

    return result


def _ensure_connection() -> bool:
    """Ensure we have an active connection to MT5."""
    global _connection, _last_error

    with _connection_lock:
        if _connection is not None:
            # Test if connection is still alive
            try:
                _connection.settimeout(1)
                _send_message(_connection, 'PING')
                response = _recv_message(_connection, 5)
                if response and 'pong' in response:
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


def _call_mt5_simple(command: str, **params) -> Optional[Dict[str, str]]:
    """Call an MT5 function via the simple text protocol."""
    global _last_error

    if not _ensure_connection():
        _last_error = RES_E_INTERNAL_FAIL_CONNECT
        return None

    # Build command string
    cmd = command
    for key, val in params.items():
        if val is not None:
            cmd += f'|{key}={val}'

    try:
        with _connection_lock:
            _send_message(_connection, cmd)
            response = _recv_message(_connection)

        if response is None:
            _last_error = RES_E_INTERNAL_FAIL_TIMEOUT
            return None

        parsed = _parse_response(response)
        if parsed is None:
            _last_error = RES_E_INTERNAL_FAIL_RECEIVE
            return None

        if parsed.get('_status') == 'ERR':
            _last_error = int(parsed.get('code', -1))
            return None

        _last_error = RES_S_OK
        return parsed
    except Exception as e:
        _last_error = RES_E_INTERNAL_FAIL
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
    'price_change_percent', 'price_theoretical', 'option_mode',
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
    """
    global DEFAULT_TIMEOUT, _last_error

    if timeout:
        DEFAULT_TIMEOUT = timeout

    params = {}
    if login:
        params['login'] = login
    if server:
        params['server'] = server

    result = _call_mt5_simple('INIT', **params)
    if result and result.get('success') == 'true':
        _last_error = RES_S_OK
        return True

    _last_error = RES_E_INTERNAL_FAIL_INIT
    return False


def shutdown() -> bool:
    """Shutdown the connection."""
    global _connection, _last_error

    try:
        _call_mt5_simple('SHUTDOWN')
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
    """Get the version of the MetaTrader 5 terminal."""
    result = _call_mt5_simple('VERSION')
    if result:
        return (result.get('version', ''), result.get('build', ''), result.get('date', ''))
    return ()


def last_error() -> int:
    """Get the last error code."""
    return _last_error


def symbols_total() -> int:
    """Get the total number of symbols in the Market Watch."""
    result = _call_mt5_simple('SYMBOL_TOTAL')
    if result:
        return int(result.get('total', 0))
    return 0


def symbols_get(group: Optional[str] = None) -> Optional[tuple]:
    """Get all symbols matching the specified group."""
    params = {}
    if group:
        params['group'] = group

    result = _call_mt5_simple('SYMBOL_GET', **params)
    if result and 'symbols' in result:
        symbols = result['symbols'].split(',') if result['symbols'] else []
        return tuple(symbols)
    return None


def symbol_info(symbol: str) -> Optional[SymbolInfo]:
    """Get information about a symbol."""
    # For simple protocol, we get tick data as symbol info
    result = _call_mt5_simple('TICK', symbol=symbol)
    if result:
        info = {
            'name': symbol,
            'bid': float(result.get('bid', 0)),
            'ask': float(result.get('ask', 0)),
            'digits': 5,  # Default, would need SYMBOL_GET for real value
        }
        return SymbolInfo(**{k: v for k, v in zip(SymbolInfo._fields, [None] * len(SymbolInfo._fields))})
    return None


def symbol_info_tick(symbol: str) -> Optional[Tick]:
    """Get the last tick information for a symbol."""
    result = _call_mt5_simple('TICK', symbol=symbol)
    if result:
        return Tick(
            time=int(result.get('time', 0)),
            bid=float(result.get('bid', 0)),
            ask=float(result.get('ask', 0)),
            last=float(result.get('last', 0)),
            volume=int(result.get('volume', 0)),
            time_msc=0,
            flags=0,
            volume_real=0,
            spread=0,
            is_new_tick=False
        )
    return None


def symbol_select(symbol: str, enable: bool = True) -> bool:
    """Select a symbol in the Market Watch or hide it."""
    # Not implemented in simple protocol
    return True


def market_book_add(symbol: str) -> bool:
    """Subscribe to market depth updates for a symbol."""
    return False


def market_book_get(symbol: str) -> Optional[tuple]:
    """Get the market depth data for a symbol."""
    return None


def market_book_release(symbol: str) -> bool:
    """Unsubscribe from market depth updates."""
    return False


def get_ticks(symbol: str, start: datetime, count: int) -> Optional[tuple]:
    """Get ticks for a symbol (deprecated, use copy_ticks_from/range)."""
    return copy_ticks_from(symbol, start, count)


def get_rates(symbol: str, timeframe: int, start: datetime, count: int) -> Optional[tuple]:
    """Get rates for a symbol (deprecated, use copy_rates_from/range)."""
    return copy_rates_from(symbol, timeframe, start, count)


def orders_total() -> int:
    """Get the total number of active orders."""
    result = _call_mt5_simple('ORDERS_TOTAL')
    if result:
        return int(result.get('total', 0))
    return 0


def orders_get(group: Optional[str] = None,
               ticket: Optional[int] = None,
               symbol: Optional[str] = None) -> Optional[tuple]:
    """Get active orders with optional filters."""
    params = {}
    if group:
        params['group'] = group
    if ticket:
        params['ticket'] = ticket
    if symbol:
        params['symbol'] = symbol

    result = _call_mt5_simple('ORDERS_GET', **params)
    if result and 'orders' in result:
        orders = []
        if result['orders']:
            for order_str in result['orders'].split(';'):
                parts = order_str.split(',')
                if len(parts) >= 4:
                    orders.append(OrderInfo(
                        ticket=int(parts[0]),
                        symbol=parts[1],
                        type=int(parts[2]),
                        volume_current=float(parts[3]),
                        time_setup=0, time_setup_msc=0, time_done=0, time_done_msc=0,
                        time_expiration=0, type_time=0, type_filling=0, state=0,
                        magic=0, position_id=0, volume_initial=0, price_open=0, sl=0, tp=0,
                        price_current=0, price_stoplimit=0, comment='', external_id='', reason=0
                    ))
        return tuple(orders)
    return None


def positions_total() -> int:
    """Get the total number of open positions."""
    result = _call_mt5_simple('POSITIONS_TOTAL')
    if result:
        return int(result.get('total', 0))
    return 0


def positions_get(group: Optional[str] = None,
                  ticket: Optional[int] = None,
                  symbol: Optional[str] = None) -> Optional[tuple]:
    """Get open positions with optional filters."""
    params = {}
    if group:
        params['group'] = group
    if ticket:
        params['ticket'] = ticket
    if symbol:
        params['symbol'] = symbol

    result = _call_mt5_simple('POSITIONS_GET', **params)
    if result and 'positions' in result:
        positions = []
        if result['positions']:
            for pos_str in result['positions'].split(';'):
                parts = pos_str.split(',')
                if len(parts) >= 5:
                    positions.append(PositionInfo(
                        ticket=int(parts[0]),
                        symbol=parts[1],
                        type=int(parts[2]),
                        volume=float(parts[3]),
                        profit=float(parts[4]),
                        time=0, time_msc=0, time_update=0, time_update_msc=0,
                        magic=0, identifier=0, reason=0, price_open=0, sl=0, tp=0,
                        price_current=0, swap=0, comment='', external_id='',
                        volume_real=0, price_gross=0, commission=0
                    ))
        return tuple(positions)
    return None


def history_orders_total(from_date: datetime, to_date: datetime) -> int:
    """Get the total number of orders in history within the specified period."""
    return 0


def history_orders_get(from_date: datetime,
                       to_date: datetime,
                       group: Optional[str] = None,
                       position: Optional[int] = None) -> Optional[tuple]:
    """Get orders from history within the specified period."""
    return None


def history_deals_total(from_date: datetime, to_date: datetime) -> int:
    """Get the total number of deals in history within the specified period."""
    return 0


def history_deals_get(from_date: datetime,
                      to_date: datetime,
                      group: Optional[str] = None,
                      position: Optional[int] = None) -> Optional[tuple]:
    """Get deals from history within the specified period."""
    return None


def order_calc_margin(action: int, symbol: str, volume: float, price: float) -> Optional[float]:
    """Calculate margin required for a trade."""
    return None


def order_calc_profit(action: int, symbol: str, volume: float,
                      price_open: float, price_close: float) -> Optional[float]:
    """Calculate profit for a trade."""
    return None


def order_calc_check(request: dict) -> OrderCheckResult:
    """Check if a trade request is valid."""
    return None


def order_send(request: dict) -> OrderSendResult:
    """Send a trade request to the server."""
    result = _call_mt5_simple('TRADE',
                               action=request.get('action', 1),
                               symbol=request.get('symbol', ''),
                               volume=request.get('volume', 0.01),
                               type=request.get('type', 0),
                               price=request.get('price', 0),
                               sl=request.get('sl', 0),
                               tp=request.get('tp', 0),
                               comment=request.get('comment', ''))
    if result:
        return OrderSendResult(
            retcode=int(result.get('retcode', 0)),
            order=int(result.get('order', 0)),
            deal=int(result.get('deal', 0)),
            volume=float(result.get('volume', 0)),
            price=float(result.get('price', 0)),
            bid=0, ask=0, comment='', request_id=0, retcode_external=0
        )
    return None


def order_check(request: dict) -> OrderCheckResult:
    """Check if a trade request is valid (same as order_calc_check)."""
    return order_calc_check(request)


def copy_ticks_from(symbol: str, date_from: datetime, count: int, flags: int = -1) -> Optional[tuple]:
    """Get ticks starting from the specified date."""
    return None


def copy_ticks_range(symbol: str, date_from: datetime, date_to: datetime, flags: int = -1) -> Optional[tuple]:
    """Get ticks within the specified date range."""
    return None


Rate = namedtuple('Rate', [
    'time', 'open', 'high', 'low', 'close', 'tick_volume',
    'spread', 'real_volume'
])


def copy_rates_from(symbol: str, timeframe: int, date_from: datetime, count: int) -> Optional[tuple]:
    """Get rates starting from the specified date."""
    return None


def copy_rates_range(symbol: str, timeframe: int, date_from: datetime, date_to: datetime) -> Optional[tuple]:
    """Get rates within the specified date range."""
    return None


def terminal_info() -> TerminalInfo:
    """Get information about the MetaTrader 5 terminal."""
    result = _call_mt5_simple('ACCOUNT')
    if result:
        return TerminalInfo(
            community_account=False,
            community_connection=False,
            connected=True,
            dlls_allowed=True,
            trade_allowed=True,
            tradeapi_disabled_broadcast=False,
            tradeapi_disabled_crash=False,
            tradeapi_disabled_exception=False,
            tradeapi_disabled_crash_course=False,
            tradeapi_disabled_timeout=False,
            peers_online=0,
            peers_online_total=0,
            name='MetaTrader 5',
            path=result.get('server', ''),
            data_path='',
            common_data_path='',
            language='English'
        )
    return None


def account_info() -> Optional[AccountInfo]:
    """Get account information."""
    result = _call_mt5_simple('ACCOUNT')
    if result:
        return AccountInfo(
            login=int(result.get('login', 0)),
            server=result.get('server', ''),
            currency=result.get('currency', ''),
            balance=float(result.get('balance', 0)),
            equity=float(result.get('equity', 0)),
            margin=float(result.get('margin', 0)),
            margin_free=float(result.get('margin_free', 0)),
            margin_level=0, margin_call_level=0, margin_stop_out_level=0,
            trade_allowed=True, trade_expert=True, limit_orders=0,
            margin_mode=0, currency_digits=2, fifo_close=False,
            hedged=False, credit=0, profit=0, assets=0, liabilities=0,
            commission_blocked=0, name='', leverage=0, trade_mode=0
        )
    return None
