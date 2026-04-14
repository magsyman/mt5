from __future__ import annotations

from trading_supervisor.risk.system_state import SystemState


def test_initial_state_enabled() -> None:
    s = SystemState()
    assert s.is_trading_enabled() is True


def test_disable_trading_works() -> None:
    s = SystemState()
    s.disable_trading()
    assert s.is_trading_enabled() is False


def test_once_disabled_always_disabled() -> None:
    s = SystemState()
    s.disable_trading()
    s.disable_trading()
    assert s.is_trading_enabled() is False

