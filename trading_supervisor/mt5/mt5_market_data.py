from __future__ import annotations

from datetime import datetime, timezone

from trading_supervisor.core.logging import get_logger

log = get_logger(__name__)


def _get_mt5():  # type: ignore[no-untyped-def]
    try:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]

        return mt5
    except Exception as e:  # pragma: no cover
        log.error("MetaTrader5 import failed: %s", e)
        return None


def get_latest_tick(symbol: str) -> dict | None:
    mt5 = _get_mt5()
    if mt5 is None:
        return None

    try:
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        # MetaTrader5 tick time is seconds since epoch in terminal time; treat as UTC for consistency.
        t_utc = datetime.fromtimestamp(float(tick.time), tz=timezone.utc)
        return {
            "symbol": str(symbol),
            "bid": float(tick.bid),
            "ask": float(tick.ask),
            "time": t_utc,
        }
    except Exception as e:  # pragma: no cover
        log.error("get_latest_tick(%r) failed: %s", symbol, e)
        return None


def get_symbol_point(symbol: str) -> float | None:
    mt5 = _get_mt5()
    if mt5 is None:
        return None
    try:
        info = mt5.symbol_info(symbol)
        if info is None:
            return None
        point = float(info.point)
        if point <= 0:
            return None
        return point
    except Exception as e:  # pragma: no cover
        log.error("get_symbol_point(%r) failed: %s", symbol, e)
        return None

