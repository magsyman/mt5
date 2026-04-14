from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from trading_supervisor.core.enums import Environment
from trading_supervisor.core.errors import ConfigurationError


class AppConfig(BaseSettings):
    """
    Base configuration for Phase 1–2.

    Later phases will introduce config hierarchy (baseline, overrides, adaptive).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_env: Environment = Field(default=Environment.LOCAL, validation_alias="APP_ENV")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")

    max_signal_age_seconds: int = Field(
        default=10, ge=0, validation_alias="MAX_SIGNAL_AGE_SECONDS"
    )

    max_spread_points_forex_hard: int = Field(
        default=30, ge=0, validation_alias="MAX_SPREAD_POINTS_FOREX_HARD"
    )
    max_spread_points_metals_hard: int = Field(
        default=80, ge=0, validation_alias="MAX_SPREAD_POINTS_METALS_HARD"
    )

    def validate_semantics(self) -> None:
        # Enum parsing is handled by pydantic; this is a defensive check.
        if not isinstance(self.app_env, Environment):
            raise ConfigurationError("APP_ENV must be a valid Environment enum value.")
        if self.log_level.strip() == "":
            raise ConfigurationError("LOG_LEVEL must not be empty.")


def load_config() -> AppConfig:
    cfg = AppConfig()
    cfg.validate_semantics()
    return cfg


@lru_cache(maxsize=1)
def get_settings() -> AppConfig:
    """
    Cached settings getter for deterministic, single-source configuration access.
    """
    return load_config()

