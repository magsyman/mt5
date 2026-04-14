from __future__ import annotations

from trading_supervisor.core.enums import Direction
from trading_supervisor.signals.models import SignalInput


def check_signal_sanity(signal: SignalInput) -> tuple[bool, str]:
    entry = float(signal.proposed_entry)
    sl = float(signal.proposed_sl)
    tp = float(signal.proposed_tp)

    if entry <= 0:
        return (False, "invalid_entry")
    if sl <= 0:
        return (False, "invalid_sl")
    if tp <= 0:
        return (False, "invalid_tp")

    if signal.direction == Direction.BUY:
        if not (sl < entry < tp):
            return (False, "invalid_structure")
    else:
        if not (tp < entry < sl):
            return (False, "invalid_structure")

    return (True, "ok")

