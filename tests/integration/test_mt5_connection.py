from __future__ import annotations

from trading_supervisor.mt5.mt5_connection import initialize_mt5, is_connected, shutdown_mt5


def test_initialize_returns_bool() -> None:
    r = initialize_mt5()
    assert isinstance(r, bool)
    shutdown_mt5()


def test_is_connected_does_not_crash() -> None:
    r = is_connected()
    assert isinstance(r, bool)

