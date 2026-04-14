from __future__ import annotations

import json


def log_event(component: str, event_type: str, payload: dict) -> None:
    line = json.dumps(
        {
            "component": component,
            "event_type": event_type,
            "payload": payload,
        },
        separators=(",", ":"),
        sort_keys=True,
    )
    print(line)

