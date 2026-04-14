from __future__ import annotations

from trading_supervisor.core.logging import get_logger

log = get_logger(__name__)


def _get_mt5():  # type: ignore[no-untyped-def]
    try:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]

        return mt5
    except Exception as e:  # pragma: no cover
        log.error("MetaTrader5 import failed: %s", e)
        return None


def initialize_mt5() -> bool:
    """
    Initialize MT5 terminal connection.

    Returns False on any failure; never raises uncontrolled exceptions.
    """
    mt5 = _get_mt5()
    if mt5 is None:
        return False

    try:
        ok = bool(mt5.initialize())
        if not ok:
            err = mt5.last_error()
            log.error("mt5.initialize() failed: %s", err)
        return ok
    except Exception as e:  # pragma: no cover
        log.error("mt5.initialize() raised: %s", e)
        return False


def shutdown_mt5() -> None:
    mt5 = _get_mt5()
    if mt5 is None:
        return
    try:
        mt5.shutdown()
    except Exception as e:  # pragma: no cover
        log.error("mt5.shutdown() raised: %s", e)


def is_connected() -> bool:
    mt5 = _get_mt5()
    if mt5 is None:
        return False
    try:
        info = mt5.terminal_info()
        return info is not None
    except Exception as e:  # pragma: no cover
        log.error("mt5.terminal_info() raised: %s", e)
        return False

