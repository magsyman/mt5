from __future__ import annotations


def check_max_drawdown(
    starting_balance: float,
    current_balance: float,
    max_drawdown_percent: float,
) -> tuple[bool, str]:
    if starting_balance <= 0:
        raise ValueError("starting_balance must be > 0")
    if current_balance <= 0:
        raise ValueError("current_balance must be > 0")
    if max_drawdown_percent <= 0:
        raise ValueError("max_drawdown_percent must be > 0")

    if current_balance > starting_balance:
        return (True, "ok")

    drawdown = (starting_balance - current_balance) / starting_balance
    if drawdown >= max_drawdown_percent:
        return (False, "max_drawdown_exceeded")
    return (True, "ok")

