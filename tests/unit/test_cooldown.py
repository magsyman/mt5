from __future__ import annotations

from datetime import datetime, timedelta, timezone

from trading_supervisor.core.enums import Direction
from trading_supervisor.positions.position_models import Position
from trading_supervisor.risk.cooldown import check_symbol_cooldown


def _closed(symbol: str, close_ts: datetime | None) -> Position:
    now = datetime.now(timezone.utc)
    return Position(
        position_id="p1",
        symbol=symbol,
        direction=Direction.BUY,
        entry_price=1.0,
        stop_loss=0.9,
        take_profit=1.1,
        size=1.0,
        open_timestamp=now,
        status="closed",
        close_price=1.0,
        close_timestamp=close_ts,
        pnl=1.0,
    )


def test_no_closed_positions_ok() -> None:
    now = datetime.now(timezone.utc)
    ok, reason = check_symbol_cooldown([], symbol="EURUSD", now=now, cooldown_seconds=60)
    assert ok is True
    assert reason == "ok"


def test_last_close_older_than_cooldown_ok() -> None:
    now = datetime.now(timezone.utc)
    old = now - timedelta(seconds=61)
    ok, reason = check_symbol_cooldown([_closed("EURUSD", old)], symbol="EURUSD", now=now, cooldown_seconds=60)
    assert ok is True
    assert reason == "ok"


def test_last_close_inside_cooldown_reject() -> None:
    now = datetime.now(timezone.utc)
    recent = now - timedelta(seconds=10)
    ok, reason = check_symbol_cooldown([_closed("EURUSD", recent)], symbol="EURUSD", now=now, cooldown_seconds=60)
    assert ok is False
    assert reason == "cooldown_active"


def test_ignores_none_close_timestamp() -> None:
    now = datetime.now(timezone.utc)
    ok, reason = check_symbol_cooldown([_closed("EURUSD", None)], symbol="EURUSD", now=now, cooldown_seconds=60)
    assert ok is True
    assert reason == "ok"

