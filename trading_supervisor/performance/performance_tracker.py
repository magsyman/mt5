from __future__ import annotations

from trading_supervisor.positions.position_models import Position


class PerformanceTracker:
    def __init__(self) -> None:
        self.total_trades: int = 0
        self.winning_trades: int = 0
        self.losing_trades: int = 0
        self.total_pnl: float = 0.0
        self.trade_history: list[Position] = []

    def record_closed_position(self, position: Position) -> None:
        if position.status != "closed":
            raise ValueError("position must be closed")
        if position.pnl is None:
            raise ValueError("position.pnl must not be None")

        self.total_trades += 1
        pnl = float(position.pnl)
        if pnl > 0:
            self.winning_trades += 1
        else:
            self.losing_trades += 1
        self.total_pnl += pnl
        self.trade_history.append(position)

    def get_win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return float(self.winning_trades / self.total_trades)

    def get_average_pnl(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return float(self.total_pnl / self.total_trades)

    def get_total_pnl(self) -> float:
        return float(self.total_pnl)

