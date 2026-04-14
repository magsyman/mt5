"""Read-only MetaTrader 5 integration helpers."""

from trading_supervisor.mt5.mt5_connection import initialize_mt5, is_connected, shutdown_mt5
from trading_supervisor.mt5.mt5_market_data import get_latest_tick, get_symbol_point

__all__ = [
    "get_latest_tick",
    "get_symbol_point",
    "initialize_mt5",
    "is_connected",
    "shutdown_mt5",
]

