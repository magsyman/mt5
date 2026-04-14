from __future__ import annotations

import pytest

from trading_supervisor.execution.position_sizing import calculate_position_size


def test_correct_calculation_known_values() -> None:
    # account_balance=10_000, risk_percent=1% -> risk_amount=100
    # entry=1.1000, sl=1.0900 -> sl_distance_price=0.01
    # symbol_point=0.0001 -> sl_distance_points=100
    # contract_size=100_000 -> value_per_point=10
    # position_size=100 / (100*10) = 0.1
    size = calculate_position_size(
        account_balance=10_000,
        risk_percent=0.01,
        entry=1.1000,
        stop_loss=1.0900,
        symbol_point=0.0001,
        contract_size=100_000,
    )
    assert size == pytest.approx(0.1)
    assert size > 0


@pytest.mark.parametrize(
    "kwargs",
    [
        dict(account_balance=0, risk_percent=0.01, entry=1.1, stop_loss=1.0, symbol_point=0.0001, contract_size=1),
        dict(account_balance=1, risk_percent=0, entry=1.1, stop_loss=1.0, symbol_point=0.0001, contract_size=1),
        dict(account_balance=1, risk_percent=0.01, entry=0, stop_loss=1.0, symbol_point=0.0001, contract_size=1),
        dict(account_balance=1, risk_percent=0.01, entry=1.1, stop_loss=0, symbol_point=0.0001, contract_size=1),
        dict(account_balance=1, risk_percent=0.01, entry=1.1, stop_loss=1.0, symbol_point=0, contract_size=1),
        dict(account_balance=1, risk_percent=0.01, entry=1.1, stop_loss=1.0, symbol_point=0.0001, contract_size=0),
    ],
)
def test_zero_or_negative_inputs_fail(kwargs) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError):
        calculate_position_size(**kwargs)


def test_stop_loss_equals_entry_fails() -> None:
    with pytest.raises(ValueError, match="stop_loss must not equal entry"):
        calculate_position_size(
            account_balance=10_000,
            risk_percent=0.01,
            entry=1.1,
            stop_loss=1.1,
            symbol_point=0.0001,
            contract_size=100_000,
        )

