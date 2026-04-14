from __future__ import annotations

import pytest

from trading_supervisor.core.enums import FinalDecision, RejectionReason, RejectionStage
from trading_supervisor.validation.accounting import AccountingCounters, PerSignalAuditRow


def test_counters_increment_correctly() -> None:
    c = AccountingCounters()
    c.record_received()
    c.record_accepted()
    c.record_executed()
    assert c.total_signals == 1
    assert c.accepted_signals == 1
    assert c.executed_signals == 1
    assert c.rejected_signals == 0
    assert c.cancelled_signals == 0


def test_acceptance_rate_and_execution_rate() -> None:
    c = AccountingCounters()
    c.record_received()
    c.record_received()
    c.record_accepted()
    c.record_executed()
    assert c.acceptance_rate() == 0.5
    assert c.execution_rate() == 0.5


def test_zero_division_safe_behavior() -> None:
    c = AccountingCounters()
    assert c.acceptance_rate() == 0.0
    assert c.execution_rate() == 0.0


def test_rejected_cancelled_executed_not_merged() -> None:
    c = AccountingCounters()
    # One rejected
    c.record_received()
    c.record_rejected()

    # One accepted then cancelled
    c.record_received()
    c.record_accepted()
    c.record_cancelled()

    # One accepted then executed
    c.record_received()
    c.record_accepted()
    c.record_executed()

    assert c.rejected_signals == 1
    assert c.cancelled_signals == 1
    assert c.executed_signals == 1


def test_invariant_validation_raises_when_accepted_exceeds_total() -> None:
    c = AccountingCounters(total_signals=0, accepted_signals=1)
    with pytest.raises(ValueError):
        c.validate_or_raise()


def test_executed_cannot_exceed_accepted() -> None:
    c = AccountingCounters(total_signals=1, accepted_signals=0, executed_signals=1)
    with pytest.raises(ValueError):
        c.validate_or_raise()


def test_cancelled_cannot_exceed_accepted() -> None:
    c = AccountingCounters(total_signals=1, accepted_signals=0, cancelled_signals=1)
    with pytest.raises(ValueError):
        c.validate_or_raise()


def test_accepted_plus_rejected_cannot_exceed_total() -> None:
    c = AccountingCounters(total_signals=1, accepted_signals=1, rejected_signals=1)
    with pytest.raises(ValueError):
        c.validate_or_raise()


def test_minimal_signal_lifecycle_constraints() -> None:
    c = AccountingCounters()
    c.record_received()
    c.record_accepted()
    c.record_executed()
    assert c.accepted_signals == 1
    assert c.executed_signals == 1
    assert c.rejected_signals == 0

    c2 = AccountingCounters()
    c2.record_received()
    c2.record_rejected()
    assert c2.rejected_signals == 1
    assert c2.executed_signals == 0


def test_per_signal_audit_requires_rejection_fields_when_rejected() -> None:
    with pytest.raises(Exception):
        PerSignalAuditRow(
            signal_id="s1",
            symbol="EURUSD",
            thresholds_used={},
            final_decision=FinalDecision.REJECTED,
        )

    row = PerSignalAuditRow(
        signal_id="s1",
        symbol=" eurusd ",
        thresholds_used={"max_spread_points_hard": 30.0},
        rejection_reason=RejectionReason.SPREAD_TOO_WIDE,
        rejection_stage=RejectionStage.MARKET_VALIDATION,
        final_decision=FinalDecision.REJECTED,
    )
    assert row.symbol == "EURUSD"

