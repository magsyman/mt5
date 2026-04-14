from __future__ import annotations

from datetime import datetime

from trading_supervisor.core.config import get_settings
from trading_supervisor.signals.models import RiskResult, SignalInput, ValidationResult

from trading_supervisor.risk.rules import (
    rule_position_size_positive,
    rule_signal_not_stale,
    rule_sl_tp_structurally_valid,
    rule_spread_within_hard_limit,
)


def run_hard_risk_checks(
    signal: SignalInput,
    market_validation: ValidationResult,
    now: datetime,
    position_size: float,
) -> RiskResult:
    settings = get_settings()

    rule_hits: list[str] = []

    ok, reason = rule_signal_not_stale(signal, now=now, max_age_seconds=int(settings.max_signal_age_seconds))
    if not ok:
        rule_hits.append(reason)

    ok, reason = rule_spread_within_hard_limit(signal, market_validation=market_validation, symbol=signal.symbol)
    if not ok:
        rule_hits.append(reason)

    ok, reason = rule_sl_tp_structurally_valid(signal)
    if not ok:
        rule_hits.append(reason)

    ok, reason = rule_position_size_positive(position_size)
    if not ok:
        rule_hits.append(reason)

    if rule_hits:
        return RiskResult(
            allowed=False,
            rule_hits=rule_hits,
            final_position_size=None,
            reason="hard_risk_rejected",
        )

    return RiskResult(
        allowed=True,
        rule_hits=[],
        final_position_size=float(position_size),
        reason="ok",
    )

