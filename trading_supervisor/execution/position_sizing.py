from __future__ import annotations


def calculate_position_size(
    account_balance: float,
    risk_percent: float,
    entry: float,
    stop_loss: float,
    symbol_point: float,
    contract_size: float,
) -> float:
    if account_balance <= 0:
        raise ValueError("account_balance must be > 0")
    if risk_percent <= 0:
        raise ValueError("risk_percent must be > 0")
    if entry <= 0:
        raise ValueError("entry must be > 0")
    if stop_loss <= 0:
        raise ValueError("stop_loss must be > 0")
    if symbol_point <= 0:
        raise ValueError("symbol_point must be > 0")
    if contract_size <= 0:
        raise ValueError("contract_size must be > 0")
    if stop_loss == entry:
        raise ValueError("stop_loss must not equal entry")

    risk_amount = account_balance * risk_percent
    sl_distance_price = abs(entry - stop_loss)
    sl_distance_points = sl_distance_price / symbol_point
    value_per_point = contract_size * symbol_point

    position_size = risk_amount / (sl_distance_points * value_per_point)
    if position_size <= 0:
        raise ValueError("position_size must be > 0")
    return float(position_size)

