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
from trading_supervisor.risk.cooldown import check_symbol_cooldown
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
    MAX_POSITIONS = 3
    MIN_ENTRY_DISTANCE = 0.5

    if not initialize_mt5():
        return 1

    try:
        tracker = PositionTracker()
        performance = PerformanceTracker()
        if system_state is None:
            system_state = SystemState()
        mode_guard = ModeGuard(RunMode.SIMULATION)
        recorded_ids: set[str] = set()
        mid_history: list[float] = []
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
                offset_seconds = tick_dict.get("detected_server_offset_seconds")

                symbol_point = get_symbol_point(symbol)
                if symbol_point is None or symbol_point <= 0:
                    return 1

                tick_time = tick_dict["time"]
                if not isinstance(tick_time, datetime):
                    time.sleep(1.0)
                    continue
                # get_latest_tick() returns normalized UTC time

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

                mid_price = (float(tick.bid) + float(tick.ask)) / 2.0
                mid_history.append(float(mid_price))
                if len(mid_history) > 5:
                    mid_history.pop(0)

                delta: float | None = None
                if len(mid_history) >= 2:
                    delta = float(mid_history[-1] - mid_history[-2])

                net_move: float | None = None
                if len(mid_history) >= 5:
                    net_move = float(mid_history[-1] - mid_history[-5])
                avg_step: float | None = None
                position_in_range: float | None = None
                strong_breakout_buy: bool | None = None
                strong_breakout_sell: bool | None = None
                extreme_breakout_buy: bool | None = None
                extreme_breakout_sell: bool | None = None
                cooldown_override_used = False
                continuation_trade = False
                max_positions_blocked = False
                entry_distance_blocked = False

                min_step = 0.02
                min_net_move = 0.08
                min_avg_step = 0.05

                d1: float | None = None
                d2: float | None = None
                d3: float | None = None
                d4: float | None = None
                up_steps: int | None = None
                down_steps: int | None = None

                if len(mid_history) >= 5:
                    d1 = float(mid_history[-1] - mid_history[-2])
                    d2 = float(mid_history[-2] - mid_history[-3])
                    d3 = float(mid_history[-3] - mid_history[-4])
                    d4 = float(mid_history[-4] - mid_history[-5])
                    net_move = float(mid_history[-1] - mid_history[-5])
                    avg_step = (abs(d1) + abs(d2) + abs(d3) + abs(d4)) / 4.0

                    strong_breakout_buy = net_move >= 0.25 and avg_step >= 0.08
                    strong_breakout_sell = net_move <= -0.25 and avg_step >= 0.08

                    extreme_breakout_buy = (
                        net_move is not None
                        and net_move >= 0.60
                        and (avg_step is None or avg_step >= 0.12)
                    )
                    extreme_breakout_sell = (
                        net_move is not None
                        and net_move <= -0.60
                        and (avg_step is None or avg_step >= 0.12)
                    )

                    up_steps = sum(1 for d in (d1, d2, d3, d4) if d > 0)
                    down_steps = sum(1 for d in (d1, d2, d3, d4) if d < 0)

                tracker.update_positions_with_tick(symbol=symbol, price=float(tick.ask), timestamp=now)
                open_positions = tracker.get_open_positions(symbol)
                total_open_size = sum(float(p.size) for p in open_positions if p.size is not None)

                for p in tracker.positions.values():
                    if p.status == "closed" and p.position_id not in recorded_ids:
                        if (
                            p.symbol is not None
                            and p.direction is not None
                            and p.entry_price is not None
                            and p.close_price is not None
                            and p.pnl is not None
                        ):
                            result_str = "WIN" if float(p.pnl) > 0 else "LOSS"
                            pnl_str = f"{float(p.pnl):+.2f}"
                            print(
                                f"CLOSE | {p.symbol} | {p.direction.name} | "
                                f"{float(p.entry_price):.2f} | {float(p.close_price):.2f} | {pnl_str} | {result_str}"
                            )
                            log_event(
                                component="scripts.run_live_simulation",
                                event_type="position_closed",
                                payload={
                                    "timestamp": now.isoformat(timespec="seconds"),
                                    "symbol": str(p.symbol),
                                    "direction": p.direction.value,
                                    "entry_price": float(p.entry_price),
                                    "close_price": float(p.close_price),
                                    "pnl": float(p.pnl),
                                    "result": result_str,
                                },
                            )
                        performance.record_closed_position(p)
                        recorded_ids.add(p.position_id)

                current_balance = float(starting_balance + performance.get_total_pnl())

                # NOTE: position/continuation gating happens later (after direction is known),
                # so continuation passes through safety filters.

                closed_positions = [p for p in tracker.positions.values() if p.status == "closed"]
                cooldown_ok, _ = check_symbol_cooldown(
                    closed_positions=closed_positions,
                    symbol=symbol,
                    now=now,
                    cooldown_seconds=60,
                )
                cooldown_active = cooldown_ok is False
                if cooldown_active:
                    if extreme_breakout_buy is True or extreme_breakout_sell is True:
                        cooldown_override_used = True
                    else:
                        spread_points_str = (
                            f"{market_validation.spread_points:.1f}"
                            if market_validation.spread_points is not None
                            else "NA"
                        )
                        log_event(
                            component="scripts.run_live_simulation",
                            event_type="iteration_completed",
                            payload={
                                "timestamp": now.isoformat(timespec="seconds"),
                                "decision": "NO_SIGNAL",
                                "reason": "cooldown_active",
                                "balance": float(current_balance),
                                "open_positions": int(len(open_positions)),
                                "total_open_size": float(total_open_size),
                                "pnl": float(performance.get_total_pnl()),
                                "detected_server_offset_seconds": offset_seconds,
                                "delta": delta,
                                "net_move": net_move,
                                "avg_step": avg_step,
                                "position_in_range": position_in_range,
                                "strong_breakout_buy": strong_breakout_buy,
                                "strong_breakout_sell": strong_breakout_sell,
                                "extreme_breakout_buy": extreme_breakout_buy,
                                "extreme_breakout_sell": extreme_breakout_sell,
                                "cooldown_override_used": False,
                                "continuation_trade": continuation_trade,
                                "max_positions_blocked": max_positions_blocked,
                                "entry_distance_blocked": entry_distance_blocked,
                            },
                        )
                        print(
                            f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                            f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                            f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                            f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                            f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                            f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                            f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                            f"{(str(extreme_breakout_buy) if extreme_breakout_buy is not None else 'NA')} | "
                            f"{(str(extreme_breakout_sell) if extreme_breakout_sell is not None else 'NA')} | "
                            f"False | "
                            f"0.00 | False | cooldown_active | {len(open_positions)} | "
                            f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                            f"{current_balance:.2f} | {offset_seconds} | "
                            f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size:.2f}"
                        )
                        time.sleep(1.0)
                        continue

                recent_high = max(mid_history)
                recent_low = min(mid_history)
                range_size = float(recent_high - recent_low)
                if range_size <= 0:
                    spread_points_str = (
                        f"{market_validation.spread_points:.1f}"
                        if market_validation.spread_points is not None
                        else "NA"
                    )
                    log_event(
                        component="scripts.run_live_simulation",
                        event_type="iteration_completed",
                        payload={
                            "timestamp": now.isoformat(timespec="seconds"),
                            "decision": "NO_SIGNAL",
                            "reason": "invalid_range",
                            "balance": float(current_balance),
                            "open_positions": int(len(open_positions)),
                            "total_open_size": float(total_open_size),
                            "pnl": float(performance.get_total_pnl()),
                            "detected_server_offset_seconds": offset_seconds,
                            "delta": delta,
                            "net_move": net_move,
                            "avg_step": avg_step,
                            "position_in_range": None,
                            "strong_breakout_buy": strong_breakout_buy,
                            "strong_breakout_sell": strong_breakout_sell,
                            "extreme_breakout_buy": extreme_breakout_buy,
                            "extreme_breakout_sell": extreme_breakout_sell,
                            "cooldown_override_used": cooldown_override_used,
                            "continuation_trade": continuation_trade,
                            "max_positions_blocked": max_positions_blocked,
                            "entry_distance_blocked": entry_distance_blocked,
                        },
                    )
                    print(
                        f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                        f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                        f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                        f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                        f"NA | {(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                        f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                        f"{(str(extreme_breakout_buy) if extreme_breakout_buy is not None else 'NA')} | "
                        f"{(str(extreme_breakout_sell) if extreme_breakout_sell is not None else 'NA')} | "
                        f"{cooldown_override_used} | "
                        f"0.00 | False | invalid_range | {len(open_positions)} | "
                        f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                        f"{current_balance:.2f} | {offset_seconds} | "
                        f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size:.2f}"
                    )
                    time.sleep(1.0)
                    continue

                position_in_range = float((mid_price - float(recent_low)) / float(range_size))
                max_extension = 0.8
                min_extension = 0.2

                if len(mid_history) < 5:
                    spread_points_str = (
                        f"{market_validation.spread_points:.1f}"
                        if market_validation.spread_points is not None
                        else "NA"
                    )
                    log_event(
                        component="scripts.run_live_simulation",
                        event_type="iteration_completed",
                        payload={
                            "timestamp": now.isoformat(timespec="seconds"),
                            "decision": "NO_SIGNAL",
                            "reason": "warmup_insufficient_history",
                            "balance": float(current_balance),
                            "open_positions": int(len(open_positions)),
                            "total_open_size": float(total_open_size),
                            "pnl": float(performance.get_total_pnl()),
                            "detected_server_offset_seconds": offset_seconds,
                            "delta": delta,
                            "net_move": net_move,
                            "avg_step": avg_step,
                            "position_in_range": position_in_range,
                            "strong_breakout_buy": strong_breakout_buy,
                            "strong_breakout_sell": strong_breakout_sell,
                        },
                    )
                    print(
                        f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                        f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                        f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                        f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                        f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                        f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                        f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                        f"0.00 | False | warmup_insufficient_history | {len(open_positions)} | "
                        f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                        f"{current_balance:.2f} | {offset_seconds} | "
                        f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size:.2f}"
                    )
                    time.sleep(1.0)
                    continue

                spread_ok = (
                    market_validation.spread_points is not None
                    and float(market_validation.spread_points) <= 60
                )
                if not spread_ok:
                    spread_points_str = (
                        f"{market_validation.spread_points:.1f}"
                        if market_validation.spread_points is not None
                        else "NA"
                    )
                    log_event(
                        component="scripts.run_live_simulation",
                        event_type="iteration_completed",
                        payload={
                            "timestamp": now.isoformat(timespec="seconds"),
                            "decision": "NO_SIGNAL",
                            "reason": "spread_not_ok",
                            "balance": float(current_balance),
                            "open_positions": int(len(open_positions)),
                            "total_open_size": float(total_open_size),
                            "pnl": float(performance.get_total_pnl()),
                            "detected_server_offset_seconds": offset_seconds,
                            "delta": delta,
                            "net_move": net_move,
                            "avg_step": avg_step,
                            "position_in_range": position_in_range,
                            "strong_breakout_buy": strong_breakout_buy,
                            "strong_breakout_sell": strong_breakout_sell,
                        },
                    )
                    print(
                        f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                        f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                        f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                        f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                        f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                        f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                        f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                        f"0.00 | False | spread_not_ok | {len(open_positions)} | "
                        f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                        f"{current_balance:.2f} | {offset_seconds} | "
                        f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size:.2f}"
                    )
                    time.sleep(1.0)
                    continue

                direction: Direction | None = None
                if (
                    d1 is not None
                    and up_steps is not None
                    and d1 > min_step
                    and up_steps >= 2
                    and net_move >= min_net_move
                    and avg_step >= min_avg_step
                    and (position_in_range <= max_extension or strong_breakout_buy)
                ):
                    direction = Direction.BUY
                elif (
                    d1 is not None
                    and down_steps is not None
                    and d1 < -min_step
                    and down_steps >= 2
                    and net_move <= -min_net_move
                    and avg_step >= min_avg_step
                    and (position_in_range >= min_extension or strong_breakout_sell)
                ):
                    direction = Direction.SELL

                if direction is None:
                    tracker.update_positions_with_tick(symbol=symbol, price=float(tick.ask), timestamp=now)
                    open_positions = tracker.get_open_positions(symbol)

                    for p in tracker.positions.values():
                        if p.status == "closed" and p.position_id not in recorded_ids:
                            if (
                                p.symbol is not None
                                and p.direction is not None
                                and p.entry_price is not None
                                and p.close_price is not None
                                and p.pnl is not None
                            ):
                                result_str = "WIN" if float(p.pnl) > 0 else "LOSS"
                                pnl_str = f"{float(p.pnl):+.2f}"
                                print(
                                    f"CLOSE | {p.symbol} | {p.direction.name} | "
                                    f"{float(p.entry_price):.2f} | {float(p.close_price):.2f} | {pnl_str} | {result_str}"
                                )
                                log_event(
                                    component="scripts.run_live_simulation",
                                    event_type="position_closed",
                                    payload={
                                        "timestamp": now.isoformat(timespec="seconds"),
                                        "symbol": str(p.symbol),
                                        "direction": p.direction.value,
                                        "entry_price": float(p.entry_price),
                                        "close_price": float(p.close_price),
                                        "pnl": float(p.pnl),
                                        "result": result_str,
                                    },
                                )
                            performance.record_closed_position(p)
                            recorded_ids.add(p.position_id)

                    current_balance = float(starting_balance + performance.get_total_pnl())

                    spread_points_str = (
                        f"{market_validation.spread_points:.1f}"
                        if market_validation.spread_points is not None
                        else "NA"
                    )
                    log_event(
                        component="scripts.run_live_simulation",
                        event_type="iteration_completed",
                        payload={
                            "timestamp": now.isoformat(timespec="seconds"),
                            "decision": "NO_SIGNAL",
                            "reason": "no_multitick_confirmation",
                            "balance": float(current_balance),
                            "open_positions": int(len(open_positions)),
                            "total_open_size": float(total_open_size),
                            "pnl": float(performance.get_total_pnl()),
                            "detected_server_offset_seconds": offset_seconds,
                            "delta": delta,
                            "net_move": net_move,
                            "avg_step": avg_step,
                            "position_in_range": position_in_range,
                            "strong_breakout_buy": strong_breakout_buy,
                            "strong_breakout_sell": strong_breakout_sell,
                            "extreme_breakout_buy": extreme_breakout_buy,
                            "extreme_breakout_sell": extreme_breakout_sell,
                            "cooldown_override_used": cooldown_override_used,
                            "continuation_trade": continuation_trade,
                            "max_positions_blocked": max_positions_blocked,
                            "entry_distance_blocked": entry_distance_blocked,
                        },
                    )
                    print(
                        f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                        f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                        f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                        f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                        f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                        f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                        f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                        f"0.00 | False | no_multitick_confirmation | {len(open_positions)} | "
                        f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                        f"{current_balance:.2f} | {offset_seconds} | "
                        f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size:.2f}"
                    )
                    time.sleep(1.0)
                    continue

                if direction == Direction.BUY:
                    entry = float(tick.ask)
                    sl = entry - 1.0
                    tp = entry + 2.0
                else:
                    entry = float(tick.bid)
                    sl = entry + 1.0
                    tp = entry - 2.0

                open_positions_for_checks = tracker.get_open_positions(symbol)
                total_open_size_for_checks = sum(
                    float(p.size) for p in open_positions_for_checks if p.size is not None
                )
                if len(open_positions_for_checks) > 0:
                    if not (extreme_breakout_buy is True or extreme_breakout_sell is True):
                        spread_points_str = (
                            f"{market_validation.spread_points:.1f}"
                            if market_validation.spread_points is not None
                            else "NA"
                        )
                        log_event(
                            component="scripts.run_live_simulation",
                            event_type="iteration_completed",
                            payload={
                                "timestamp": now.isoformat(timespec="seconds"),
                                "decision": "NO_SIGNAL",
                                "reason": "position_already_open",
                                "balance": float(current_balance),
                                "open_positions": int(len(open_positions_for_checks)),
                                "total_open_size": float(total_open_size_for_checks),
                                "pnl": float(performance.get_total_pnl()),
                                "detected_server_offset_seconds": offset_seconds,
                                "delta": delta,
                                "net_move": net_move,
                                "avg_step": avg_step,
                                "position_in_range": position_in_range,
                                "strong_breakout_buy": strong_breakout_buy,
                                "strong_breakout_sell": strong_breakout_sell,
                                "extreme_breakout_buy": extreme_breakout_buy,
                                "extreme_breakout_sell": extreme_breakout_sell,
                                "cooldown_override_used": cooldown_override_used,
                                "continuation_trade": continuation_trade,
                                "max_positions_blocked": max_positions_blocked,
                                "entry_distance_blocked": entry_distance_blocked,
                            },
                        )
                        print(
                            f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                            f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                            f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                            f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                            f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                            f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                            f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                            f"{(str(extreme_breakout_buy) if extreme_breakout_buy is not None else 'NA')} | "
                            f"{(str(extreme_breakout_sell) if extreme_breakout_sell is not None else 'NA')} | "
                            f"{cooldown_override_used} | "
                            f"0.00 | False | position_already_open | {len(open_positions_for_checks)} | "
                            f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                            f"{current_balance:.2f} | {offset_seconds} | "
                            f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size_for_checks:.2f}"
                        )
                        time.sleep(1.0)
                        continue

                    continuation_trade = True

                    if len(open_positions_for_checks) >= MAX_POSITIONS:
                        max_positions_blocked = True
                        spread_points_str = (
                            f"{market_validation.spread_points:.1f}"
                            if market_validation.spread_points is not None
                            else "NA"
                        )
                        log_event(
                            component="scripts.run_live_simulation",
                            event_type="iteration_completed",
                            payload={
                                "timestamp": now.isoformat(timespec="seconds"),
                                "decision": "NO_SIGNAL",
                                "reason": "max_positions_reached",
                                "balance": float(current_balance),
                                "open_positions": int(len(open_positions_for_checks)),
                                "total_open_size": float(total_open_size_for_checks),
                                "pnl": float(performance.get_total_pnl()),
                                "detected_server_offset_seconds": offset_seconds,
                                "delta": delta,
                                "net_move": net_move,
                                "avg_step": avg_step,
                                "position_in_range": position_in_range,
                                "strong_breakout_buy": strong_breakout_buy,
                                "strong_breakout_sell": strong_breakout_sell,
                                "extreme_breakout_buy": extreme_breakout_buy,
                                "extreme_breakout_sell": extreme_breakout_sell,
                                "cooldown_override_used": cooldown_override_used,
                                "continuation_trade": continuation_trade,
                                "max_positions_blocked": max_positions_blocked,
                                "entry_distance_blocked": entry_distance_blocked,
                            },
                        )
                        print(
                            f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                            f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                            f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                            f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                            f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                            f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                            f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                            f"{(str(extreme_breakout_buy) if extreme_breakout_buy is not None else 'NA')} | "
                            f"{(str(extreme_breakout_sell) if extreme_breakout_sell is not None else 'NA')} | "
                            f"{cooldown_override_used} | "
                            f"0.00 | False | max_positions_reached | {len(open_positions_for_checks)} | "
                            f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                            f"{current_balance:.2f} | {offset_seconds} | "
                            f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size_for_checks:.2f}"
                        )
                        time.sleep(1.0)
                        continue

                    existing_dirs = {p.direction for p in open_positions_for_checks if p.direction is not None}
                    existing_dir = next(iter(existing_dirs)) if len(existing_dirs) == 1 else None
                    if existing_dir is None or direction != existing_dir:
                        spread_points_str = (
                            f"{market_validation.spread_points:.1f}"
                            if market_validation.spread_points is not None
                            else "NA"
                        )
                        log_event(
                            component="scripts.run_live_simulation",
                            event_type="iteration_completed",
                            payload={
                                "timestamp": now.isoformat(timespec="seconds"),
                                "decision": "NO_SIGNAL",
                                "reason": "direction_mismatch",
                                "balance": float(current_balance),
                                "open_positions": int(len(open_positions_for_checks)),
                                "total_open_size": float(total_open_size_for_checks),
                                "pnl": float(performance.get_total_pnl()),
                                "detected_server_offset_seconds": offset_seconds,
                                "delta": delta,
                                "net_move": net_move,
                                "avg_step": avg_step,
                                "position_in_range": position_in_range,
                                "strong_breakout_buy": strong_breakout_buy,
                                "strong_breakout_sell": strong_breakout_sell,
                                "extreme_breakout_buy": extreme_breakout_buy,
                                "extreme_breakout_sell": extreme_breakout_sell,
                                "cooldown_override_used": cooldown_override_used,
                                "continuation_trade": continuation_trade,
                                "max_positions_blocked": max_positions_blocked,
                                "entry_distance_blocked": entry_distance_blocked,
                            },
                        )
                        print(
                            f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                            f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                            f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                            f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                            f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                            f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                            f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                            f"{(str(extreme_breakout_buy) if extreme_breakout_buy is not None else 'NA')} | "
                            f"{(str(extreme_breakout_sell) if extreme_breakout_sell is not None else 'NA')} | "
                            f"{cooldown_override_used} | "
                            f"0.00 | False | direction_mismatch | {len(open_positions_for_checks)} | "
                            f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                            f"{current_balance:.2f} | {offset_seconds} | "
                            f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size_for_checks:.2f}"
                        )
                        time.sleep(1.0)
                        continue

                    latest_pos = max(
                        (
                            p
                            for p in open_positions_for_checks
                            if p.entry_price is not None and p.open_timestamp is not None
                        ),
                        key=lambda p: p.open_timestamp,
                        default=None,
                    )
                    if latest_pos is not None and latest_pos.entry_price is not None:
                        if abs(float(entry) - float(latest_pos.entry_price)) < MIN_ENTRY_DISTANCE:
                            entry_distance_blocked = True
                            spread_points_str = (
                                f"{market_validation.spread_points:.1f}"
                                if market_validation.spread_points is not None
                                else "NA"
                            )
                            log_event(
                                component="scripts.run_live_simulation",
                                event_type="iteration_completed",
                                payload={
                                    "timestamp": now.isoformat(timespec="seconds"),
                                    "decision": "NO_SIGNAL",
                                    "reason": "entry_distance_blocked",
                                    "balance": float(current_balance),
                                    "open_positions": int(len(open_positions_for_checks)),
                                    "total_open_size": float(total_open_size_for_checks),
                                    "pnl": float(performance.get_total_pnl()),
                                    "detected_server_offset_seconds": offset_seconds,
                                    "delta": delta,
                                    "net_move": net_move,
                                    "avg_step": avg_step,
                                    "position_in_range": position_in_range,
                                    "strong_breakout_buy": strong_breakout_buy,
                                    "strong_breakout_sell": strong_breakout_sell,
                                    "extreme_breakout_buy": extreme_breakout_buy,
                                    "extreme_breakout_sell": extreme_breakout_sell,
                                    "cooldown_override_used": cooldown_override_used,
                                    "continuation_trade": continuation_trade,
                                    "max_positions_blocked": max_positions_blocked,
                                    "entry_distance_blocked": entry_distance_blocked,
                                },
                            )
                            print(
                                f"{now.isoformat(timespec='seconds')} | NO_SIGNAL | "
                                f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                                f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                                f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                                f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                                f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                                f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                                f"{(str(extreme_breakout_buy) if extreme_breakout_buy is not None else 'NA')} | "
                                f"{(str(extreme_breakout_sell) if extreme_breakout_sell is not None else 'NA')} | "
                                f"{cooldown_override_used} | "
                                f"0.00 | False | entry_distance_blocked | {len(open_positions_for_checks)} | "
                                f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                                f"{current_balance:.2f} | {offset_seconds} | "
                                f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size_for_checks:.2f}"
                            )
                            time.sleep(1.0)
                            continue
                else:
                    continuation_trade = False

                signal = SignalInput(
                    signal_id=f"live-{iterations}",
                    strategy_id="live_sim",
                    symbol=symbol,
                    direction=direction,
                    timestamp=now,
                    proposed_entry=entry,
                    proposed_sl=sl,
                    proposed_tp=tp,
                )

                try:
                    position_size = calculate_position_size(
                        account_balance=current_balance,
                        risk_percent=risk_percent,
                        entry=signal.proposed_entry,
                        stop_loss=signal.proposed_sl,
                        symbol_point=float(symbol_point),
                        contract_size=contract_size,
                    )
                except Exception:
                    position_size = 0.0

                num_open = len(open_positions_for_checks)
                if continuation_trade:
                    if num_open == 1:
                        position_size = float(position_size) * 0.7
                    elif num_open == 2:
                        position_size = float(position_size) * 0.5
                    else:
                        position_size = float(position_size) * 0.3

                open_positions = tracker.get_open_positions(symbol)
                closed_positions = [p for p in tracker.positions.values() if p.status == "closed"]
                open_positions_for_pipeline = [] if continuation_trade else open_positions

                result = run_signal_pipeline(
                    PipelineInputs(
                        signal=signal,
                        market_validation=market_validation,
                        position_size=float(position_size),
                        now=now,
                        slippage_points=float(slippage_points),
                        open_positions=open_positions_for_pipeline,
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
                            symbol=signal.symbol,
                            direction=signal.direction,
                            entry_price=float(result.execution_result.fill_price),
                            stop_loss=signal.proposed_sl,
                            take_profit=signal.proposed_tp,
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
                total_open_size = sum(float(p.size) for p in open_positions if p.size is not None)

                for p in tracker.positions.values():
                    if p.status == "closed" and p.position_id not in recorded_ids:
                        if (
                            p.symbol is not None
                            and p.direction is not None
                            and p.entry_price is not None
                            and p.close_price is not None
                            and p.pnl is not None
                        ):
                            result_str = "WIN" if float(p.pnl) > 0 else "LOSS"
                            pnl_str = f"{float(p.pnl):+.2f}"
                            print(
                                f"CLOSE | {p.symbol} | {p.direction.name} | "
                                f"{float(p.entry_price):.2f} | {float(p.close_price):.2f} | {pnl_str} | {result_str}"
                            )
                            log_event(
                                component="scripts.run_live_simulation",
                                event_type="position_closed",
                                payload={
                                    "timestamp": now.isoformat(timespec="seconds"),
                                    "symbol": str(p.symbol),
                                    "direction": p.direction.value,
                                    "entry_price": float(p.entry_price),
                                    "close_price": float(p.close_price),
                                    "pnl": float(p.pnl),
                                    "result": result_str,
                                },
                            )
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
                        "total_open_size": float(total_open_size),
                        "pnl": float(performance.get_total_pnl()),
                        "detected_server_offset_seconds": offset_seconds,
                        "delta": delta,
                        "net_move": net_move,
                        "avg_step": avg_step,
                        "position_in_range": position_in_range,
                        "strong_breakout_buy": strong_breakout_buy,
                        "strong_breakout_sell": strong_breakout_sell,
                        "extreme_breakout_buy": extreme_breakout_buy,
                        "extreme_breakout_sell": extreme_breakout_sell,
                        "cooldown_override_used": cooldown_override_used,
                        "continuation_trade": continuation_trade,
                        "max_positions_blocked": max_positions_blocked,
                        "entry_distance_blocked": entry_distance_blocked,
                    },
                )
                print(
                    f"{now.isoformat(timespec='seconds')} | {result.decision.name} | "
                    f"{spread_points_str} | {(f'{delta:.2f}' if delta is not None else 'NA')} | "
                    f"{(f'{net_move:.2f}' if net_move is not None else 'NA')} | "
                    f"{(f'{avg_step:.2f}' if avg_step is not None else 'NA')} | "
                    f"{(f'{position_in_range:.2f}' if position_in_range is not None else 'NA')} | "
                    f"{(str(strong_breakout_buy) if strong_breakout_buy is not None else 'NA')} | "
                    f"{(str(strong_breakout_sell) if strong_breakout_sell is not None else 'NA')} | "
                    f"{(str(extreme_breakout_buy) if extreme_breakout_buy is not None else 'NA')} | "
                    f"{(str(extreme_breakout_sell) if extreme_breakout_sell is not None else 'NA')} | "
                    f"{cooldown_override_used} | "
                    f"{position_size:.2f} | "
                    f"{result.execution_result.accepted} | {reason} | {len(open_positions)} | "
                    f"{performance.total_trades} | {performance.get_win_rate():.2f} | {performance.get_total_pnl():.2f} | "
                    f"{current_balance:.2f} | {offset_seconds} | "
                    f"{continuation_trade} | {max_positions_blocked} | {entry_distance_blocked} | {total_open_size:.2f}"
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

