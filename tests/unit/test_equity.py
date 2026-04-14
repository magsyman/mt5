from __future__ import annotations

from trading_supervisor.risk.equity import check_max_drawdown


def test_no_drawdown_ok() -> None:
    ok, reason = check_max_drawdown(1000.0, 1000.0, 0.2)
    assert ok is True
    assert reason == "ok"


def test_small_drawdown_ok() -> None:
    ok, reason = check_max_drawdown(1000.0, 900.0, 0.2)
    assert ok is True
    assert reason == "ok"


def test_exactly_max_drawdown_reject() -> None:
    ok, reason = check_max_drawdown(1000.0, 800.0, 0.2)
    assert ok is False
    assert reason == "max_drawdown_exceeded"


def test_above_max_drawdown_reject() -> None:
    ok, reason = check_max_drawdown(1000.0, 799.0, 0.2)
    assert ok is False
    assert reason == "max_drawdown_exceeded"

