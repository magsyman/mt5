from __future__ import annotations


def test_run_live_simulation_imports_and_has_entrypoint() -> None:
    import scripts.run_live_simulation as mod

    assert hasattr(mod, "run_live_simulation")
    assert callable(mod.run_live_simulation)


def test_disabled_system_state_exits_immediately(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    import scripts.run_live_simulation as mod
    from trading_supervisor.risk.system_state import SystemState

    # avoid MT5 dependency
    monkeypatch.setattr(mod, "initialize_mt5", lambda: True)
    monkeypatch.setattr(mod, "shutdown_mt5", lambda: None)

    state = SystemState()
    state.disable_trading()

    assert mod.run_live_simulation(max_iterations=999, system_state=state) == 0

