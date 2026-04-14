from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from trading_supervisor.core.enums import FinalDecision
from trading_supervisor.core.mode import ModeGuard
from trading_supervisor.core.structured_logging import log_event
from trading_supervisor.execution.execution_models import ExecutionResult
from trading_supervisor.execution.precheck import build_execution_decision
from trading_supervisor.execution.simulator import simulate_execution
from trading_supervisor.positions.position_models import Position
from trading_supervisor.risk.hard_risk import run_hard_risk_checks
from trading_supervisor.risk.system_state import SystemState
from trading_supervisor.signals.models import AuditRecord, RiskResult, SignalInput, ValidationResult


@dataclass(frozen=True)
class PipelineInputs:
    signal: SignalInput
    market_validation: ValidationResult
    position_size: float
    now: datetime
    slippage_points: float
    open_positions: list[Position]
    closed_positions: list[Position]
    starting_balance: float
    current_balance: float
    system_state: SystemState
    mode_guard: ModeGuard


@dataclass(frozen=True)
class PipelineResult:
    decision: FinalDecision
    decision_reason: str
    risk_result: RiskResult
    execution_result: ExecutionResult
    audit_record: AuditRecord


def run_signal_pipeline(inputs: PipelineInputs) -> PipelineResult:
    if inputs.system_state.is_trading_enabled() is False:
        decision = FinalDecision.REJECTED
        decision_reason = "system_disabled"
        risk_result = RiskResult(allowed=False, reason="system_disabled")
        execution_result = ExecutionResult(
            accepted=False,
            broker_order_id=None,
            fill_price=None,
            error_code="not_executed",
            error_message="decision_not_accepted",
            latency_ms=0.0,
        )
        audit_record = AuditRecord(
            timestamp=inputs.now,
            component="pipeline.orchestrator",
            event_type="signal_pipeline_completed",
            payload={
                "signal_id": inputs.signal.signal_id,
                "symbol": inputs.signal.symbol,
                "decision": decision.value,
                "decision_reason": decision_reason,
                "risk_allowed": risk_result.allowed,
                "risk_rule_hits": risk_result.rule_hits,
                "execution_accepted": execution_result.accepted,
                "execution_error_code": execution_result.error_code,
                "final_position_size": risk_result.final_position_size,
            },
        )
        return PipelineResult(
            decision=decision,
            decision_reason=decision_reason,
            risk_result=risk_result,
            execution_result=execution_result,
            audit_record=audit_record,
        )

    risk_result = run_hard_risk_checks(
        signal=inputs.signal,
        market_validation=inputs.market_validation,
        now=inputs.now,
        position_size=inputs.position_size,
    )

    decision, decision_reason = build_execution_decision(
        signal=inputs.signal,
        market_validation=inputs.market_validation,
        risk_result=risk_result,
        now=inputs.now,
        open_positions=inputs.open_positions,
        closed_positions=inputs.closed_positions,
        starting_balance=inputs.starting_balance,
        current_balance=inputs.current_balance,
    )

    if decision_reason == "kill_switch_triggered":
        inputs.system_state.disable_trading()

    execution_result = simulate_execution(
        signal=inputs.signal,
        market_validation=inputs.market_validation,
        decision=decision,
        position_size=inputs.position_size,
        slippage_points=inputs.slippage_points,
        mode_guard=inputs.mode_guard,
    )

    audit_record = AuditRecord(
        timestamp=inputs.now,
        component="pipeline.orchestrator",
        event_type="signal_pipeline_completed",
        payload={
            "signal_id": inputs.signal.signal_id,
            "symbol": inputs.signal.symbol,
            "decision": decision.value,
            "decision_reason": decision_reason,
            "risk_allowed": risk_result.allowed,
            "risk_rule_hits": risk_result.rule_hits,
            "execution_accepted": execution_result.accepted,
            "execution_error_code": execution_result.error_code,
            "final_position_size": risk_result.final_position_size,
        },
    )
    log_event(
        component=audit_record.component,
        event_type=audit_record.event_type,
        payload=audit_record.payload,
    )

    return PipelineResult(
        decision=decision,
        decision_reason=decision_reason,
        risk_result=risk_result,
        execution_result=execution_result,
        audit_record=audit_record,
    )

