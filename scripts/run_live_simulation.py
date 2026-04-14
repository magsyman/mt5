from __future__ import annotations

import time
from datetime import datetime, timezone

from trading_supervisor.core.enums import Direction, FinalDecision
from trading_supervisor.core.logging import configure_logging
from trading_supervisor.core.mode import ModeGuard, RunMode
from trading_supervisor.core.structured_logging import log_event
from trading_supervisor.execution.position_sizing import calculate_position_size
from trading_supervisor.market.market_models import MarketValidationInput, TickData
from trading_supervisor.market.market_validator import validate_market
from trading_supervisor.mt5.mt5_connection import initialize_mt5, shutdown_mt5
from trading_supervisor.mt5.mt5_market_data import get_latest_tick, get_symbol_point
from trading_supervisor.performance.performance_tracker import PerformanceTracker
from trading_supervisor.pipeline.orchestrator import PipelineInputs, run_signal_pipeline
from trading_supervisor.positions.position_models import Position
from trading_supervisor.positions.position_tracker import PositionTracker
from trading_supervisor.risk.system_state import SystemState
from trading_supervisor.signals.models import SignalInput


def run_live_simulation(
    max_iterations: int | None = None,
    *,
    system_state: SystemState | None = None,
) -> int:
    configure_logging("INFO")

    symbol = "XAUUSD"
    slippage_points = 2.0
    risk_percent = 0.005
    contract_size = 100.0
    starting_balance = 10_000.0
    current_balance = 10_000.0

    if not initialize_mt5():
        return 1

    try:
        tracker = PositionTracker()
        performance = PerformanceTracker()
        if system_state is None:
            system_state = SystemState()
        mode_guard = ModeGuard(RunMode.SIMULATION)
        recorded_ids: set[str] = set()
        iterations = 0
        while True:
            if max_iterations is not None and iterations >= max_iterations:
                return 0
            iterations += 1

            if system_state.is_trading_enabled() is False:
                print("SYSTEM DISABLED — EXITING LOOP")
                break

            try:
                now = datetime.now(timezone.utc)

                tick_dict = get_latest_tick(symbol)
                if tick_dict is None:
                    time.sleep(1.0)
                    continue

                symbol_point = get_symbol_point(symbol)
                if symbol_point is None or symbol_point <= 0:
                    return 1

                tick_time = tick_dict["time"]
                if not isinstance(tick_time, datetime):
                    time.sleep(1.0)
                    continue
                if tick_time.tzinfo is None:
                    tick_time = tick_time.replace(tzinfo=timezone.utc)
                tick_time = tick_time.astimezone(timezone.utc)

                tick = TickData(
                    symbol=symbol,
                    bid=float(tick_dict["bid"]),
                    ask=float(tick_dict["ask"]),
                    timestamp=tick_time,
                )

                mvi = MarketValidationInput(
                    symbol=symbol,
                    tick=tick,
                    now=now,
                    symbol_point=float(symbol_point),
                    available_symbols=[symbol],
                )
                market_validation = validate_market(mvi)

                entry = float(tick.ask)
                dummy_signal = SignalInput(
                    signal_id=f"live-{iterations}",
                    strategy_id="live_sim",
                    symbol=symbol,
                    direction=Direction.BUY,
                    timestamp=now,
                    proposed_entry=entry,
                    proposed_sl=entry - 1.0,
                    proposed_tp=entry + 2.0,
                )

                try:
                    position_size = calculate_position_size(
                        account_balance=current_balance,
                        risk_percent=risk_percent,
                        entry=dummy_signal.proposed_entry,
                        stop_loss=dummy_signal.proposed_sl,
                        symbol_point=float(symbol_point),
                        contract_size=contract_size,
                    )
                except Exception:
                    position_size = 0.0

                open_positions = tracker.get_open_positions(symbol)
                closed_positions = [p for p in tracker.positions.values() if p.status == "closed"]

                result = run_signal_pipeline(
                    PipelineInputs(
                        signal=dummy_signal,
                        market_validation=market_validation,
                        position_size=float(position_size),
                        now=now,
                        slippage_points=float(slippage_points),
                        open_positions=open_positions,
                        closed_positions=closed_positions,
                        starting_balance=float(starting_balance),
                        current_balance=float(current_balance),
                        system_state=system_state,
                        mode_guard=mode_guard,
                    )
                )

                if result.decision_reason == "kill_switch_triggered":
                    print("KILL SWITCH ACTIVATED — STOPPING SYSTEM")
                    break

                if system_state.is_trading_enabled() is False:
                    # hard guard: never open positions after kill/disable in same iteration
                    pass
                elif (
                    result.decision == FinalDecision.ACCEPTED
                    and result.execution_result.accepted is True
                    and result.decision_reason == "ok"
                    and system_state.is_trading_enabled() is True
                ):
                    try:
                        if result.execution_result.broker_order_id is None:
                            raise ValueError("missing broker_order_id")
                        if result.execution_result.fill_price is None:
                            raise ValueError("missing fill_price")
                        if result.risk_result.final_position_size is None:
                            raise ValueError("missing final_position_size")
                        position = Position(
                            position_id=str(result.execution_result.broker_order_id),
                            symbol=dummy_signal.symbol,
                            direction=dummy_signal.direction,
                            entry_price=float(result.execution_result.fill_price),
                            stop_loss=dummy_signal.proposed_sl,
                            take_profit=dummy_signal.proposed_tp,
                            size=float(result.risk_result.final_position_size),
                            open_timestamp=now,
                            status="open",
                            close_price=None,
                            close_timestamp=None,
                            pnl=None,
                        )
                        tracker.open_position(position)
                    except ValueError:
                        pass

                tracker.update_positions_with_tick(symbol=symbol, price=float(tick.ask), timestamp=now)
                open_positions = tracker.get_open_positions(symbol)

                for p in tracker.positions.values():
                    if p.status == "closed" and p.position_id not in recorded_ids:
                        performance.record_closed_position(p)
                        recorded_ids.add(p.position_id)

                current_balance = float(starting_balance + performance.get_total_pnl())

                spread_points_str = (
                    f"{market_validation.spread_points:.1f}"
                    if market_validation.spread_points is not None
                    else "NA"
                )
                reason = result.decision_reason
                log_event(
                    component="scripts.run_live_simulation",
                    event_type="iteration_completed",
                    payload={
                        "timestamp": now.isoformat(timespec="seconds"),
                        "decision": result.decision.value,
                        "reason": reason,
                        "balance": float(current_balance),
                        "open_positions": int(len(open_positions)),
                        "pnl": float(performance.get_total_pnl()),
                    },
                )
                print(
                    f"{now.isoformat(timespec='seconds')} | {result.decision.name} | "
                    f"{spread_points_str} | {position_size:.2f} | "
                    f"{result.execution_result.accepted} | {reason} | {len(open_positions)} | "
                    f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                    f"{current_balance:.2f}"
                )
            except Exception:
                # never crash loop
                pass

            time.sleep(1.0)
        return 0
    finally:
        shutdown_mt5()


def main() -> int:
    return run_live_simulation(max_iterations=None)


if __name__ == "__main__":
    raise SystemExit(main())

