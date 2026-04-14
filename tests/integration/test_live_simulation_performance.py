from __future__ import annotations

from datetime import datetime, timezone

import pytest

from trading_supervisor.core.enums import Direction
from trading_supervisor.performance.performance_tracker import PerformanceTracker
from trading_supervisor.positions.position_models import Position
from trading_supervisor.positions.position_tracker import PositionTracker


def _mk_position(
    *,
    position_id: str,
    direction: Direction,
    entry: float,
    sl: float,
    tp: float,
    size: float,
) -> Position:
    now = datetime.now(timezone.utc)
    return Position(
        position_id=position_id,
        symbol="XAUUSD",
        direction=direction,
        entry_price=entry,
        stop_loss=sl,
        take_profit=tp,
        size=size,
        open_timestamp=now,
        status="open",
        close_price=None,
        close_timestamp=None,
        pnl=None,
    )


def test_closed_positions_recorded_once_and_duplicate_prevention_works() -> None:
    tracker = PositionTracker()
    perf = PerformanceTracker()
    recorded: set[str] = set()

    p = _mk_position(
        position_id="SIM-1",
        direction=Direction.BUY,
        entry=100.0,
        sl=99.0,
        tp=101.0,
        size=1.0,
    )
    tracker.open_position(p)
    ts = datetime.now(timezone.utc)
    tracker.update_positions_with_tick("XAUUSD", price=101.0, timestamp=ts)  # TP hit -> closes

    for pos in tracker.positions.values():
        if pos.status == "closed" and pos.position_id not in recorded:
            perf.record_closed_position(pos)
            recorded.add(pos.position_id)

    assert perf.total_trades == 1
    assert perf.get_win_rate() == pytest.approx(1.0)

    # attempt to record again (should not double count)
    for pos in tracker.positions.values():
        if pos.status == "closed" and pos.position_id not in recorded:
            perf.record_closed_position(pos)
            recorded.add(pos.position_id)

    assert perf.total_trades == 1


def test_win_rate_and_total_pnl_accumulates_multiple_closed_trades() -> None:
    tracker = PositionTracker()
    perf = PerformanceTracker()
    recorded: set[str] = set()

    p1 = _mk_position(
        position_id="SIM-A",
        direction=Direction.BUY,
        entry=100.0,
        sl=99.0,
        tp=101.0,
        size=2.0,
    )
    p2 = _mk_position(
        position_id="SIM-B",
        direction=Direction.SELL,
        entry=100.0,
        sl=103.0,
        tp=98.0,
        size=1.0,
    )
    tracker.open_position(p1)
    tracker.open_position(p2)

    ts = datetime.now(timezone.utc)
    tracker.update_positions_with_tick("XAUUSD", price=101.0, timestamp=ts)  # closes BUY win
    tracker.update_positions_with_tick("XAUUSD", price=103.0, timestamp=ts)  # closes SELL loss

    for pos in tracker.positions.values():
        if pos.status == "closed" and pos.position_id not in recorded:
            perf.record_closed_position(pos)
            recorded.add(pos.position_id)

    assert perf.total_trades == 2
    assert perf.winning_trades == 1
    assert perf.losing_trades == 1
    assert perf.get_win_rate() == pytest.approx(0.5)
    # pnl: BUY (101-100)*2 = +2, SELL (100-103)*1 = -3 => total -1
    assert perf.get_total_pnl() == pytest.approx(-1.0)

