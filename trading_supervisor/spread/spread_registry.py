from __future__ import annotations

from trading_supervisor.spread.spread_models import (
    FOREX_DEFAULT,
    METALS_DEFAULT,
    SpreadDistributionConfig,
    SymbolClass,
    XAUUSD_DEFAULT,
)


def classify_symbol(symbol: str) -> SymbolClass:
    s = symbol.upper()
    if "XAU" in s:
        return SymbolClass.METALS
    return SymbolClass.FOREX


def get_spread_config(symbol: str) -> SpreadDistributionConfig:
    normalized = symbol.strip().upper()
    if normalized == "XAUUSD":
        return XAUUSD_DEFAULT

    symbol_class = classify_symbol(normalized)
    if symbol_class == SymbolClass.METALS:
        return METALS_DEFAULT
    return FOREX_DEFAULT

