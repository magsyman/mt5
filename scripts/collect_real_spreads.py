from __future__ import annotations

import csv
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from trading_supervisor.core.config import get_settings
from trading_supervisor.core.logging import configure_logging, get_logger
from trading_supervisor.mt5.mt5_connection import initialize_mt5, shutdown_mt5
from trading_supervisor.mt5.mt5_market_data import get_symbol_point
from trading_supervisor.spread.spread_registry import get_spread_config
from trading_supervisor.spread.spread_stats import compute_spread_stats
from trading_supervisor.spread.spread_validation import (
    generate_sample,
    is_realistic,
    validate_synthetic_vs_observed,
)


def _get_mt5():  # type: ignore[no-untyped-def]
    try:
        import MetaTrader5 as mt5  # type: ignore[import-not-found]

        return mt5
    except Exception:
        return None


@dataclass(frozen=True)
class TickSample:
    symbol: str
    raw_tick_time: int
    tick_time_utc: datetime
    bid: float
    ask: float
    symbol_point: float
    spread_price: float
    spread_points: float


def is_valid_tick(bid: float, ask: float) -> bool:
    return bid > 0 and ask > 0 and ask >= bid


def duplicate_key(raw_tick_time: int, bid: float, ask: float) -> tuple[int, float, float]:
    return (int(raw_tick_time), float(bid), float(ask))


def compute_spread_points(bid: float, ask: float, symbol_point: float) -> float:
    if symbol_point <= 0:
        raise ValueError("symbol_point must be > 0")
    return float((ask - bid) / symbol_point)


def ensure_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(timezone.utc)


def collect_spread_samples(
    *,
    symbol: str,
    symbol_point: float,
    target_samples: int,
    max_polls: int,
    poll_sleep_seconds: float,
) -> tuple[list[TickSample], dict[str, int]]:
    if target_samples <= 0:
        raise ValueError("target_samples must be > 0")
    if max_polls <= 0:
        raise ValueError("max_polls must be > 0")
    if poll_sleep_seconds < 0:
        raise ValueError("poll_sleep_seconds must be >= 0")

    mt5 = _get_mt5()
    if mt5 is None:
        raise RuntimeError("MetaTrader5 package not available")

    total_polled = 0
    accepted_ticks = 0
    skipped_missing = 0
    skipped_invalid = 0
    skipped_duplicate = 0

    seen: set[tuple[int, float, float]] = set()
    samples: list[TickSample] = []

    for _ in range(max_polls):
        total_polled += 1
        tick = mt5.symbol_info_tick(symbol)
        if tick is None:
            skipped_missing += 1
            time.sleep(poll_sleep_seconds)
            continue

        raw_tick_time = int(tick.time)
        bid = float(tick.bid)
        ask = float(tick.ask)

        if not is_valid_tick(bid=bid, ask=ask):
            skipped_invalid += 1
            time.sleep(poll_sleep_seconds)
            continue

        key = duplicate_key(raw_tick_time=raw_tick_time, bid=bid, ask=ask)
        if key in seen:
            skipped_duplicate += 1
            time.sleep(poll_sleep_seconds)
            continue
        seen.add(key)

        tick_time_utc = ensure_utc(datetime.fromtimestamp(float(raw_tick_time), tz=timezone.utc))
        spread_price = float(ask - bid)
        spread_points = compute_spread_points(bid=bid, ask=ask, symbol_point=symbol_point)

        samples.append(
            TickSample(
                symbol=str(symbol),
                raw_tick_time=raw_tick_time,
                tick_time_utc=tick_time_utc,
                bid=bid,
                ask=ask,
                symbol_point=float(symbol_point),
                spread_price=spread_price,
                spread_points=float(spread_points),
            )
        )
        accepted_ticks += 1

        if accepted_ticks >= target_samples:
            break

        time.sleep(poll_sleep_seconds)

    counters = {
        "total_polled": total_polled,
        "accepted_ticks": accepted_ticks,
        "skipped_missing": skipped_missing,
        "skipped_invalid": skipped_invalid,
        "skipped_duplicate": skipped_duplicate,
    }
    return samples, counters


def write_spread_samples_csv(samples: list[TickSample], csv_path: str) -> None:
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "symbol",
                "raw_tick_time",
                "tick_time_utc",
                "bid",
                "ask",
                "symbol_point",
                "spread_price",
                "spread_points",
            ],
        )
        w.writeheader()
        for s in samples:
            w.writerow(
                {
                    "symbol": s.symbol,
                    "raw_tick_time": s.raw_tick_time,
                    "tick_time_utc": s.tick_time_utc.isoformat(),
                    "bid": s.bid,
                    "ask": s.ask,
                    "symbol_point": s.symbol_point,
                    "spread_price": s.spread_price,
                    "spread_points": s.spread_points,
                }
            )


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger(__name__)

    symbol = "XAUUSD"
    target_samples = 1000
    max_polls = 20000
    poll_sleep_seconds = 0.05
    seed = 123
    csv_path = "/mnt/data/xauusd_real_spreads.csv"

    ok = initialize_mt5()
    if not ok:
        log.error("MT5 initialize failed. Install/configure MT5 terminal and python MetaTrader5 package.")
        return 1

    try:
        symbol_point = get_symbol_point(symbol)
        if symbol_point is None or symbol_point <= 0:
            log.error("Failed to resolve symbol point for %s", symbol)
            return 1

        try:
            samples, counters = collect_spread_samples(
                symbol=symbol,
                symbol_point=float(symbol_point),
                target_samples=target_samples,
                max_polls=max_polls,
                poll_sleep_seconds=poll_sleep_seconds,
            )
        except Exception as e:
            log.error("Failed collecting spreads: %s", e)
            return 1

        if len(samples) == 0:
            log.error("No valid samples collected.")
            return 1

        if len(samples) < target_samples:
            log.warning(
                "Target samples not reached: collected=%s target=%s max_polls=%s",
                len(samples),
                target_samples,
                max_polls,
            )

        write_spread_samples_csv(samples=samples, csv_path=csv_path)

        observed_points = [s.spread_points for s in samples]

        observed_stats = compute_spread_stats(observed_points)

        config = get_spread_config(symbol)
        synthetic_points = generate_sample(config=config, n=len(observed_points), seed=seed)
        synthetic_stats = compute_spread_stats(synthetic_points)

        comparison = validate_synthetic_vs_observed(
            synthetic_points=synthetic_points,
            observed_points=observed_points,
        )

        print("total_polled:", counters["total_polled"])
        print("accepted_ticks:", counters["accepted_ticks"])
        print("skipped_missing:", counters["skipped_missing"])
        print("skipped_invalid:", counters["skipped_invalid"])
        print("skipped_duplicate:", counters["skipped_duplicate"])
        print("observed_stats:", observed_stats.model_dump())
        print("synthetic_stats:", synthetic_stats.model_dump())
        print("ratios:", comparison.ratios)
        print("realistic:", is_realistic(comparison))
        print("csv_path:", csv_path)
        return 0
    finally:
        shutdown_mt5()


if __name__ == "__main__":
    raise SystemExit(main())

