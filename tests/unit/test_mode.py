from __future__ import annotations

import pytest

from trading_supervisor.core.mode import ModeGuard, RunMode


def test_simulation_mode_allows_simulation() -> None:
    g = ModeGuard(RunMode.SIMULATION)
    g.assert_simulation_only()


def test_live_mode_blocks_simulation() -> None:
    g = ModeGuard(RunMode.LIVE)
    with pytest.raises(RuntimeError, match="simulation_only_operation"):
        g.assert_simulation_only()


def test_wrong_mode_raises_runtime_error() -> None:
    g = ModeGuard(RunMode.SIMULATION)
    with pytest.raises(RuntimeError, match="live_only_operation"):
        g.assert_live_allowed()

