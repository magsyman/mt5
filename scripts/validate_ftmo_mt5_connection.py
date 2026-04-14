from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone


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


def compute_tick_age_seconds(now_utc: datetime, tick_dt_utc: datetime | None) -> float | None:
    if tick_dt_utc is None:
        return None
    return (now_utc - tick_dt_utc).total_seconds()


def classify_tick_time_alignment(age_seconds: float | None, tolerance_seconds: float = 5.0) -> str:
    if age_seconds is None:
        return "unknown"
    if abs(age_seconds) <= tolerance_seconds:
        return "ok"
    if age_seconds < -tolerance_seconds:
        return "tick_in_future"
    return "stale"


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


def summarize_time_status(
    ok_tick_count: int,
    stale_tick_count: int,
    future_tick_count: int,
) -> str:
    if future_tick_count > 0:
        return "INVALID"
    total = ok_tick_count + stale_tick_count + future_tick_count
    stale_ratio = (stale_tick_count / float(total)) if total > 0 else 0.0
    if stale_ratio > 0.2:
        return "INVALID"
    return "OK"


def _london_session_allowed(now_utc: datetime) -> bool:
    # Diagnostic-only: treat London session as roughly 08:00–17:00 UTC.
    h = now_utc.hour
    return 8 <= h < 17


def main() -> int:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except Exception:
        print("MT5 initialized: False")
        print("error=metatrader5_import_failed")
        return 1

    initialized = bool(mt5.initialize())
    print(f"MT5 initialized: {initialized}")
    if not initialized:
        try:
            err = mt5.last_error()
        except Exception:
            err = None
        print(f"mt5_last_error={err}")
        mt5.shutdown()
        return 1

    try:
        ai = mt5.account_info()
        if ai is None:
            print("account_info: None")
        else:
            print(f"login={getattr(ai, 'login', None)}")
            print(f"server={getattr(ai, 'server', None)}")
            print(f"balance={getattr(ai, 'balance', None)}")
            print(f"equity={getattr(ai, 'equity', None)}")
            print(f"company={getattr(ai, 'company', None)}")

        symbol = "XAUUSD"
        selected = bool(mt5.symbol_select(symbol, True))
        print(f"symbol_select({symbol})={selected}")

        si = mt5.symbol_info(symbol)
        if si is None:
            print("symbol_info: None")
            return 1

        point = getattr(si, "point", None)
        digits = getattr(si, "digits", None)
        contract_size = getattr(si, "trade_contract_size", None)
        print(f"symbol={getattr(si, 'name', symbol)}")
        print(f"point={point}")
        print(f"digits={digits}")
        print(f"trade_contract_size={contract_size}")

        if point is None or float(point) <= 0:
            return 1
        symbol_point = float(point)

        iterations = 30
        sleep_seconds = 1.0
        ok_tick_count = 0
        stale_tick_count = 0
        future_tick_count = 0
        spread_points_samples: list[float] = []
        detected_server_offset_seconds_last: int | None = None
        for i in range(1, iterations + 1):
            now_utc = datetime.now(timezone.utc)
            tick = mt5.symbol_info_tick(symbol)

            if tick is None:
                print(
                    f"ITER {i:02d} | now_utc={now_utc.isoformat(timespec='seconds')} | "
                    f"raw_tick_time=NA | raw_tick_dt_assumed_utc=NA | detected_server_offset_seconds=NA | "
                    f"normalized_tick_utc=NA | normalized_tick_age_seconds=NA | normalized_tick_time_alignment=unknown | "
                    f"bid=NA | ask=NA | spread_price=NA | spread_points=NA | "
                    f"london={_london_session_allowed(now_utc)} | tick_available=False"
                )
                time.sleep(sleep_seconds)
                continue

            bid = getattr(tick, "bid", None)
            ask = getattr(tick, "ask", None)
            tick_time_raw = getattr(tick, "time", None)
            raw_tick_dt_assumed_utc = interpret_mt5_tick_time(tick_time_raw)
            detected_server_offset_seconds = detect_server_time_offset_seconds(
                now_utc=now_utc,
                raw_tick_dt_assumed_utc=raw_tick_dt_assumed_utc,
            )
            detected_server_offset_seconds_last = detected_server_offset_seconds
            normalized_tick_utc = apply_server_time_offset(
                raw_tick_dt_assumed_utc=raw_tick_dt_assumed_utc,
                offset_seconds=detected_server_offset_seconds,
            )
            normalized_tick_age_seconds = compute_tick_age_seconds(now_utc, normalized_tick_utc)
            normalized_tick_time_alignment = classify_tick_time_alignment(normalized_tick_age_seconds)

            tick_available = bid is not None and ask is not None and normalized_tick_utc is not None
            if not tick_available:
                print(
                    f"ITER {i:02d} | now_utc={now_utc.isoformat(timespec='seconds')} | "
                    f"raw_tick_time={tick_time_raw} | raw_tick_dt_assumed_utc={raw_tick_dt_assumed_utc} | "
                    f"detected_server_offset_seconds={detected_server_offset_seconds} | "
                    f"normalized_tick_utc=NA | normalized_tick_age_seconds=NA | "
                    f"normalized_tick_time_alignment=unknown | bid={bid} | ask={ask} | "
                    f"spread_price=NA | spread_points=NA | "
                    f"london={_london_session_allowed(now_utc)} | tick_available=False"
                )
                time.sleep(sleep_seconds)
                continue

            spread_price = float(ask) - float(bid)
            spread_points = spread_price / symbol_point
            spread_points_samples.append(float(spread_points))
            if normalized_tick_time_alignment == "ok":
                ok_tick_count += 1
            elif normalized_tick_time_alignment == "stale":
                stale_tick_count += 1
            elif normalized_tick_time_alignment == "tick_in_future":
                future_tick_count += 1

            print(
                f"ITER {i:02d} | now_utc={now_utc.isoformat(timespec='seconds')} | "
                f"raw_tick_time={tick_time_raw} | "
                f"raw_tick_dt_assumed_utc={raw_tick_dt_assumed_utc.isoformat(timespec='seconds') if raw_tick_dt_assumed_utc else 'NA'} | "
                f"detected_server_offset_seconds={detected_server_offset_seconds} | "
                f"normalized_tick_utc={normalized_tick_utc.isoformat(timespec='seconds') if normalized_tick_utc else 'NA'} | "
                f"normalized_tick_age_seconds={normalized_tick_age_seconds:.3f} | "
                f"normalized_tick_time_alignment={normalized_tick_time_alignment} | "
                f"bid={float(bid):.{digits}f} | ask={float(ask):.{digits}f} | "
                f"spread_price={spread_price:.{digits}f} | spread_points={spread_points:.2f} | "
                f"london={_london_session_allowed(now_utc)} | tick_available=True"
            )

            time.sleep(sleep_seconds)

        if spread_points_samples:
            avg_spread_points = sum(spread_points_samples) / float(len(spread_points_samples))
            min_spread_points = min(spread_points_samples)
            max_spread_points = max(spread_points_samples)
        else:
            avg_spread_points = 0.0
            min_spread_points = 0.0
            max_spread_points = 0.0

        print(f"future_tick_count={future_tick_count}")
        print(f"stale_tick_count={stale_tick_count}")
        print(f"ok_tick_count={ok_tick_count}")
        print(f"avg_spread_points={avg_spread_points:.2f}")
        print(f"min_spread_points={min_spread_points:.2f}")
        print(f"max_spread_points={max_spread_points:.2f}")
        print(f"detected_server_offset_seconds_last={detected_server_offset_seconds_last}")

        print(f"TIME_STATUS={summarize_time_status(ok_tick_count, stale_tick_count, future_tick_count)}")

        return 0
    finally:
        mt5.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())

