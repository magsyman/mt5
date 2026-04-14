from __future__ import annotations

from datetime import datetime, timezone

from trading_supervisor.mt5.mt5_market_data import (
    apply_server_time_offset,
    detect_server_time_offset_seconds,
    interpret_mt5_tick_time,
)


def test_interpret_mt5_tick_time_with_unix_timestamp() -> None:
    dt = interpret_mt5_tick_time(0)
    assert dt == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_detect_server_time_offset_seconds_detects_plus_3h_future_drift() -> None:
    now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    raw_assumed_utc = datetime(2026, 4, 14, 15, 0, 0, tzinfo=timezone.utc)
    assert detect_server_time_offset_seconds(now, raw_assumed_utc, max_reasonable_future_seconds=5.0) == 10800


def test_apply_server_time_offset_normalizes_correctly() -> None:
    raw_assumed_utc = datetime(2026, 4, 14, 15, 0, 0, tzinfo=timezone.utc)
    normalized = apply_server_time_offset(raw_assumed_utc, 10800)
    assert normalized == datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_normalized_age_near_zero_for_plus_3h_case() -> None:
    now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    raw_assumed_utc = datetime(2026, 4, 14, 15, 0, 0, tzinfo=timezone.utc)
    offset = detect_server_time_offset_seconds(now, raw_assumed_utc, max_reasonable_future_seconds=5.0)
    normalized = apply_server_time_offset(raw_assumed_utc, offset)
    assert normalized is not None
    age = (now - normalized).total_seconds()
    assert age == 0.0

