from __future__ import annotations

from datetime import datetime

from trading_supervisor.core.enums import Direction
from trading_supervisor.positions.position_models import Position


class PositionTracker:
    def __init__(self) -> None:
        self.positions: dict[str, Position] = {}

    def open_position(self, position: Position) -> None:
        if position.position_id in self.positions:
            raise ValueError("position_id already exists")
        self.positions[position.position_id] = position

    def close_position(self, position_id: str, price: float, timestamp: datetime) -> None:
        if price <= 0:
            raise ValueError("price must be > 0")
        pos = self.positions.get(position_id)
        if pos is None:
            raise KeyError("position_id not found")
        if pos.status == "closed":
            return

        if pos.direction == Direction.BUY:
            pnl = (price - pos.entry_price) * pos.size
        else:
            pnl = (pos.entry_price - price) * pos.size

        self.positions[position_id] = pos.model_copy(
            update={
                "status": "closed",
                "close_price": float(price),
                "close_timestamp": timestamp,
                "pnl": float(pnl),
            }
        )

    def get_open_positions(self, symbol: str | None = None) -> list[Position]:
        out: list[Position] = []
        for p in self.positions.values():
            if p.status != "open":
                continue
            if symbol is not None and p.symbol != symbol:
                continue
            out.append(p)
        return out

    def update_positions_with_tick(self, symbol: str, price: float, timestamp: datetime) -> None:
        for p in list(self.positions.values()):
            if p.status != "open":
                continue
            if p.symbol != symbol:
                continue

            if p.direction == Direction.BUY:
                if price <= p.stop_loss:
                    self.close_position(p.position_id, price=price, timestamp=timestamp)
                elif price >= p.take_profit:
                    self.close_position(p.position_id, price=price, timestamp=timestamp)
            else:
                if price >= p.stop_loss:
                    self.close_position(p.position_id, price=price, timestamp=timestamp)
                elif price <= p.take_profit:
                    self.close_position(p.position_id, price=price, timestamp=timestamp)

