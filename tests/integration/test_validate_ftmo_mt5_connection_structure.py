from __future__ import annotations


def test_script_imports_and_main_exists() -> None:
    import scripts.validate_ftmo_mt5_connection as mod

    assert hasattr(mod, "main")
    assert callable(mod.main)

