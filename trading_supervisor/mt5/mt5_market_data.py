from __future__ import annotations

from datetime import datetime, timedelta, timezone

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
        now_utc = datetime.now(timezone.utc)
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            return None
        raw_tick_time = getattr(tick, "time", None)
        raw_tick_dt_assumed_utc = interpret_mt5_tick_time(raw_tick_time)
        detected_server_offset_seconds = detect_server_time_offset_seconds(
            now_utc=now_utc,
            raw_tick_dt_assumed_utc=raw_tick_dt_assumed_utc,
        )
        normalized_tick_utc = apply_server_time_offset(
            raw_tick_dt_assumed_utc=raw_tick_dt_assumed_utc,
            offset_seconds=detected_server_offset_seconds,
        )
        if normalized_tick_utc is None:
            return None
        return {
            "symbol": str(symbol),
            "bid": float(tick.bid),
            "ask": float(tick.ask),
            "time": normalized_tick_utc,
            "raw_tick_time": raw_tick_time,
            "raw_tick_dt_assumed_utc": raw_tick_dt_assumed_utc,
            "detected_server_offset_seconds": detected_server_offset_seconds,
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


def interpret_mt5_tick_time(raw_value: int | float | datetime | None) -> datetime | None:
    if raw_value is None:
        return None

    if isinstance(raw_value, datetime):
        dt = raw_value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    if isinstance(raw_value, (int, float)):
        return datetime.fromtimestamp(float(raw_value), tz=timezone.utc)

    return None


def detect_server_time_offset_seconds(
    now_utc: datetime,
    raw_tick_dt_assumed_utc: datetime | None,
    max_reasonable_future_seconds: float = 5.0,
) -> int | None:
    if raw_tick_dt_assumed_utc is None:
        return None

    age = (now_utc - raw_tick_dt_assumed_utc).total_seconds()
    if age >= -max_reasonable_future_seconds:
        return 0

    best_offset_seconds = 0
    best_abs_age = abs(age)
    for hours in range(-12, 13):
        offset_seconds = hours * 3600
        normalized = raw_tick_dt_assumed_utc - timedelta(seconds=offset_seconds)
        norm_age = (now_utc - normalized).total_seconds()
        abs_norm_age = abs(norm_age)
        if abs_norm_age < best_abs_age:
            best_abs_age = abs_norm_age
            best_offset_seconds = offset_seconds

    return best_offset_seconds


def apply_server_time_offset(
    raw_tick_dt_assumed_utc: datetime | None,
    offset_seconds: int | None,
) -> datetime | None:
    if raw_tick_dt_assumed_utc is None:
        return None
    if offset_seconds is None:
        return raw_tick_dt_assumed_utc
    return raw_tick_dt_assumed_utc - timedelta(seconds=int(offset_seconds))

