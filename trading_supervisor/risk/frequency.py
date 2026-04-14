from __future__ import annotations

from datetime import datetime

from trading_supervisor.positions.position_models import Position


def check_trade_frequency(
    closed_positions: list[Position],
    symbol: str,
    now: datetime,
    max_trades: int,
    window_seconds: int,
) -> tuple[bool, str]:
    relevant: list[Position] = []
    for p in closed_positions:
        if p.symbol != symbol:
            continue
        if p.status != "closed":
            continue
        if p.close_timestamp is None:
            continue
        relevant.append(p)

    count = 0
    for p in relevant:
        if (now - p.close_timestamp).total_seconds() <= window_seconds:
            count += 1

    if count >= max_trades:
        return (False, "frequency_limit_exceeded")
    return (True, "ok")

