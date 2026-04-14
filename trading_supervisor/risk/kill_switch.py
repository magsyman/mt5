from __future__ import annotations


def check_kill_switch(
    current_balance: float,
    starting_balance: float,
    min_balance_ratio: float,
) -> tuple[bool, str]:
    if current_balance <= 0:
        raise ValueError("current_balance must be > 0")
    if starting_balance <= 0:
        raise ValueError("starting_balance must be > 0")
    if min_balance_ratio <= 0:
        raise ValueError("min_balance_ratio must be > 0")

    ratio = current_balance / starting_balance
    if ratio <= min_balance_ratio:
        return (False, "kill_switch_triggered")
    return (True, "ok")

