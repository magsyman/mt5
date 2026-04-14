from __future__ import annotations

from trading_supervisor.core.config import get_settings
from trading_supervisor.core.logging import configure_logging, get_logger


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger(__name__)
    log.info(
        "compare_spread_distributions: Phase 1–2 only; spread subsystem/comparison implemented in later phases."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

