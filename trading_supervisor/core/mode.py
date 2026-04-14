from __future__ import annotations

from enum import Enum


class RunMode(str, Enum):
    SIMULATION = "simulation"
    LIVE = "live"


class ModeGuard:
    def __init__(self, mode: RunMode) -> None:
        self.mode = mode

    def is_simulation(self) -> bool:
        return self.mode == RunMode.SIMULATION

    def is_live(self) -> bool:
        return self.mode == RunMode.LIVE

    def assert_simulation_only(self) -> None:
        if self.mode != RunMode.SIMULATION:
            raise RuntimeError("simulation_only_operation")

    def assert_live_allowed(self) -> None:
        if self.mode != RunMode.LIVE:
            raise RuntimeError("live_only_operation")

