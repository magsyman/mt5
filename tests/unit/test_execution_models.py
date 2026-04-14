from __future__ import annotations

import pytest

from trading_supervisor.execution.execution_models import ExecutionResult


def test_accepted_true_requires_latency_ms() -> None:
    with pytest.raises(Exception):
        ExecutionResult(
            accepted=True,
            broker_order_id="1",
            fill_price=1.0,
            latency_ms=None,
        )


def test_accepted_false_requires_error_code() -> None:
    with pytest.raises(Exception):
        ExecutionResult(
            accepted=False,
            error_code=None,
        )

