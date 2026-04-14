from __future__ import annotations

from trading_supervisor.risk.kill_switch import check_kill_switch


def test_normal_balance_ok() -> None:
    ok, reason = check_kill_switch(current_balance=9000.0, starting_balance=10_000.0, min_balance_ratio=0.5)
    assert ok is True
    assert reason == "ok"


def test_exactly_threshold_reject() -> None:
    ok, reason = check_kill_switch(current_balance=5000.0, starting_balance=10_000.0, min_balance_ratio=0.5)
    assert ok is False
    assert reason == "kill_switch_triggered"


def test_below_threshold_reject() -> None:
    ok, reason = check_kill_switch(current_balance=4999.0, starting_balance=10_000.0, min_balance_ratio=0.5)
    assert ok is False
    assert reason == "kill_switch_triggered"

