from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from trading_supervisor.core.enums import Direction


class Position(BaseModel):
    model_config = ConfigDict(extra="forbid")

    position_id: str
    symbol: str
    direction: Direction
    entry_price: float = Field(gt=0)
    stop_loss: float
    take_profit: float
    size: float = Field(gt=0)
    open_timestamp: datetime
    status: str  # "open", "closed"
    close_price: float | None = None
    close_timestamp: datetime | None = None
    pnl: float | None = None

    @model_validator(mode="after")
    def _validate_structural(self) -> "Position":
        if self.stop_loss == self.entry_price:
            raise ValueError("stop_loss must not equal entry_price")
        if self.take_profit == self.entry_price:
            raise ValueError("take_profit must not equal entry_price")
        return self

