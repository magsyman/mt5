from __future__ import annotations


class TradingSupervisorError(Exception):
    """Base class for all supervisor errors."""


class ConfigurationError(TradingSupervisorError):
    """Raised when config is invalid or inconsistent."""


class SignalModelError(TradingSupervisorError):
    """Raised when a signal fails structural/model validation."""


class MarketValidationError(TradingSupervisorError):
    """Raised when deterministic market validation fails."""


class HardRiskRejectionError(TradingSupervisorError):
    """Raised when hard risk rules deterministically reject execution."""


class ExecutionError(TradingSupervisorError):
    """Raised when execution fails after passing validation/risk."""

