from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from trading_supervisor.core.enums import RejectionReason, RejectionStage
from trading_supervisor.market.market_models import MarketValidationInput, TickData
from trading_supervisor.market.market_validator import validate_market
from trading_supervisor.market.symbol_resolver import resolve_symbol


def test_resolve_symbol_exact_match_works() -> None:
    assert resolve_symbol("EURUSD", ["EURUSD", "XAUUSD"]) == "EURUSD"


def test_resolve_symbol_normalizes_case_and_spaces() -> None:
    assert resolve_symbol("  eurusd ", ["EURUSD"]) == "EURUSD"


def test_resolve_symbol_partial_match_rejected() -> None:
    assert resolve_symbol("EUR", ["EURUSD"]) is None


def test_validate_market_missing_symbol() -> None:
    now = datetime.now(timezone.utc)
    inp = MarketValidationInput(
        symbol="EURUSD",
        tick=None,
        now=now,
        symbol_point=0.0001,
        available_symbols=["XAUUSD"],
    )
    r = validate_market(inp)
    assert r.success is False
    assert r.rejection_stage == RejectionStage.MARKET_VALIDATION
    assert r.rejection_reason == RejectionReason.INVALID_SYMBOL


def test_validate_market_missing_tick() -> None:
    now = datetime.now(timezone.utc)
    tick = None
    inp = MarketValidationInput(
        symbol="EURUSD",
        tick=tick,
        now=now,
        symbol_point=0.0001,
        available_symbols=["EURUSD"],
    )
    r = validate_market(inp)
    assert r.success is False
    assert r.rejection_reason == RejectionReason.NO_MARKET_DATA
    assert r.rejection_stage == RejectionStage.MARKET_VALIDATION


def test_validate_market_invalid_tick_bid_zero() -> None:
    now = datetime.now(timezone.utc)
    tick = TickData.model_construct(symbol="EURUSD", bid=0.0, ask=1.0, timestamp=now)
    inp = MarketValidationInput(
        symbol="EURUSD",
        tick=tick,
        now=now,
        symbol_point=0.0001,
        available_symbols=["EURUSD"],
    )
    r = validate_market(inp)
    assert r.success is False
    assert r.rejection_reason == RejectionReason.INVALID_TICK
    assert r.rejection_stage == RejectionStage.MARKET_VALIDATION


def test_validate_market_stale_tick() -> None:
    now = datetime.now(timezone.utc)
    old = now - timedelta(seconds=9999)
    tick = TickData(symbol="EURUSD", bid=1.0, ask=1.0002, timestamp=old)
    inp = MarketValidationInput(
        symbol="EURUSD",
        tick=tick,
        now=now,
        symbol_point=0.0001,
        available_symbols=["EURUSD"],
    )
    r = validate_market(inp)
    assert r.success is False
    assert r.rejection_reason == RejectionReason.STALE_SIGNAL
    assert r.rejection_stage == RejectionStage.MARKET_VALIDATION


def test_validate_market_valid_case() -> None:
    now = datetime.now(timezone.utc)
    tick = TickData(symbol="EURUSD", bid=1.0000, ask=1.0003, timestamp=now - timedelta(seconds=1))
    inp = MarketValidationInput(
        symbol="EURUSD",
        tick=tick,
        now=now,
        symbol_point=0.0001,
        available_symbols=["EURUSD"],
    )
    r = validate_market(inp)
    assert r.success is True
    assert r.rejection_reason is None
    assert r.rejection_stage is None
    assert r.spread_price == pytest.approx(0.0003)
    assert r.spread_points == pytest.approx(3.0)
    assert r.symbol_point == pytest.approx(0.0001)
    assert "spread" in " ".join(r.thresholds_used.keys()).lower()


def test_validate_market_spread_points_computation() -> None:
    now = datetime.now(timezone.utc)
    tick = TickData(symbol="EURUSD", bid=1.0, ask=1.0002, timestamp=now)
    inp = MarketValidationInput(
        symbol="EURUSD",
        tick=tick,
        now=now,
        symbol_point=0.0001,
        available_symbols=["EURUSD"],
    )
    r = validate_market(inp)
    assert r.success is True
    assert r.spread_price == pytest.approx(0.0002)
    assert r.spread_points == pytest.approx(2.0)

