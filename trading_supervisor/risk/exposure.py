from __future__ import annotations

from trading_supervisor.positions.position_models import Position


def check_max_open_positions(
    open_positions: list[Position],
    symbol: str,
    max_per_symbol: int,
    max_total: int,
) -> tuple[bool, str]:
    total = len(open_positions)
    symbol_count = sum(1 for p in open_positions if p.symbol == symbol)

    if total >= max_total:
        return (False, "max_total_positions_exceeded")
    if symbol_count >= max_per_symbol:
        return (False, "max_symbol_positions_exceeded")
    return (True, "ok")

