from __future__ import annotations


def resolve_symbol(input_symbol: str, available_symbols: list[str]) -> str | None:
    """
    Resolve symbol by exact match only.

    - Uppercase and trim input.
    - No substring matching.
    - Return None if not found.
    """
    normalized = input_symbol.strip().upper()
    if normalized == "":
        return None

    for candidate in available_symbols:
        if candidate.strip().upper() == normalized:
            return candidate
    return None

