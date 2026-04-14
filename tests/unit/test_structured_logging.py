from __future__ import annotations

import json

from trading_supervisor.core.structured_logging import log_event


def test_log_event_emits_valid_json_and_fields(capsys) -> None:
    log_event(component="compA", event_type="evtB", payload={"x": 1, "y": "z"})
    out = capsys.readouterr().out.strip()
    parsed = json.loads(out)
    assert parsed["component"] == "compA"
    assert parsed["event_type"] == "evtB"
    assert parsed["payload"] == {"x": 1, "y": "z"}

