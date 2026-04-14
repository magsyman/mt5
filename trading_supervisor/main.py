from __future__ import annotations

from trading_supervisor.core.config import get_settings
from trading_supervisor.core.logging import configure_logging, get_logger


def main() -> int:
    settings = get_settings()
    configure_logging(settings.log_level)
    log = get_logger(__name__)
    log.info("Trading supervisor starting.")
    log.info("APP_ENV=%s", settings.app_env)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

