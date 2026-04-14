from __future__ import annotations

from datetime import datetime

from trading_supervisor.positions.position_models import Position


def check_symbol_cooldown(
    closed_positions: list[Position],
    symbol: str,
    now: datetime,
    cooldown_seconds: int,
) -> tuple[bool, str]:
    relevant: list[datetime] = []
    for p in closed_positions:
        if p.symbol != symbol:
            continue
        if p.status != "closed":
            continue
        if p.close_timestamp is None:
            continue
        relevant.append(p.close_timestamp)

    if not relevant:
        return (True, "ok")

    last_close = max(relevant)
    delta = (now - last_close).total_seconds()
    if delta < cooldown_seconds:
        return (False, "cooldown_active")
    return (True, "ok")

