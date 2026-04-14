from __future__ import annotations

from datetime import datetime, timezone

from scripts.validate_ftmo_mt5_connection import (
    classify_tick_time_alignment,
    compute_tick_age_seconds,
    detect_server_time_offset_seconds,
    interpret_mt5_tick_time,
    apply_server_time_offset,
    summarize_time_status,
)


def test_interpret_mt5_tick_time_with_unix_timestamp() -> None:
    dt = interpret_mt5_tick_time(0)
    assert dt == datetime(1970, 1, 1, 0, 0, 0, tzinfo=timezone.utc)


def test_interpret_mt5_tick_time_with_aware_datetime() -> None:
    raw = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    dt = interpret_mt5_tick_time(raw)
    assert dt == raw


def test_interpret_mt5_tick_time_with_naive_datetime_assumes_utc() -> None:
    raw = datetime(2026, 4, 14, 12, 0, 0)
    dt = interpret_mt5_tick_time(raw)
    assert dt == datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_compute_tick_age_seconds_exact_case() -> None:
    now = datetime(2026, 4, 14, 12, 0, 5, tzinfo=timezone.utc)
    tick = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert compute_tick_age_seconds(now, tick) == 5.0


def test_classify_tick_time_alignment_ok() -> None:
    assert classify_tick_time_alignment(0.0, tolerance_seconds=5.0) == "ok"
    assert classify_tick_time_alignment(5.0, tolerance_seconds=5.0) == "ok"
    assert classify_tick_time_alignment(-5.0, tolerance_seconds=5.0) == "ok"


def test_classify_tick_time_alignment_tick_in_future() -> None:
    assert classify_tick_time_alignment(-5.1, tolerance_seconds=5.0) == "tick_in_future"


def test_classify_tick_time_alignment_stale() -> None:
    assert classify_tick_time_alignment(5.1, tolerance_seconds=5.0) == "stale"


def test_detect_server_time_offset_seconds_returns_zero_when_aligned() -> None:
    now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    raw = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    assert detect_server_time_offset_seconds(now, raw, max_reasonable_future_seconds=5.0) == 0


def test_detect_server_time_offset_seconds_detects_plus_3h_future_drift() -> None:
    now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    raw_assumed_utc = datetime(2026, 4, 14, 15, 0, 0, tzinfo=timezone.utc)
    assert detect_server_time_offset_seconds(now, raw_assumed_utc, max_reasonable_future_seconds=5.0) == 10800


def test_apply_server_time_offset_shifts_correctly() -> None:
    raw_assumed_utc = datetime(2026, 4, 14, 15, 0, 0, tzinfo=timezone.utc)
    normalized = apply_server_time_offset(raw_assumed_utc, 10800)
    assert normalized == datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)


def test_normalized_age_near_zero_for_plus_3h_case() -> None:
    now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)
    raw_assumed_utc = datetime(2026, 4, 14, 15, 0, 0, tzinfo=timezone.utc)
    offset = detect_server_time_offset_seconds(now, raw_assumed_utc, max_reasonable_future_seconds=5.0)
    normalized = apply_server_time_offset(raw_assumed_utc, offset)
    age = compute_tick_age_seconds(now, normalized)
    assert age == 0.0


def test_summarize_time_status_invalid_for_future_ticks() -> None:
    assert summarize_time_status(ok_tick_count=10, stale_tick_count=0, future_tick_count=1) == "INVALID"


def test_summarize_time_status_invalid_for_stale_ratio_over_20_percent() -> None:
    assert summarize_time_status(ok_tick_count=4, stale_tick_count=2, future_tick_count=0) == "INVALID"


def test_summarize_time_status_ok_otherwise() -> None:
    assert summarize_time_status(ok_tick_count=5, stale_tick_count=1, future_tick_count=0) == "OK"
