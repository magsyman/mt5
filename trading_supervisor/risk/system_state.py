from __future__ import annotations


class SystemState:
    def __init__(self) -> None:
        self.trading_enabled: bool = True

    def disable_trading(self) -> None:
        self.trading_enabled = False

    def is_trading_enabled(self) -> bool:
        return bool(self.trading_enabled)

