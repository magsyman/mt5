from __future__ import annotations

import logging
import sys
from typing import Final


_CONFIGURED: bool = False
_DEFAULT_FORMAT: Final[str] = (
    "%(asctime)s.%(msecs)03dZ %(levelname)s %(name)s %(message)s"
)
_DEFAULT_DATEFMT: Final[str] = "%Y-%m-%dT%H:%M:%S"


def configure_logging(level: str | int = "INFO") -> None:
    """
    Configure process-wide logging exactly once.

    This project relies on structured, auditable logs; avoid ad-hoc print usage.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return

    if isinstance(level, str):
        level_name = level.strip().upper()
        resolved_level = logging._nameToLevel.get(level_name)  # type: ignore[attr-defined]
        if resolved_level is None:
            raise ValueError(f"Unknown LOG_LEVEL: {level!r}")
    else:
        resolved_level = level
    logging.basicConfig(
        level=resolved_level,
        format=_DEFAULT_FORMAT,
        datefmt=_DEFAULT_DATEFMT,
        stream=sys.stdout,
    )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)

