from __future__ import annotations


def parse_depth_message(payload: dict) -> dict:
    return {
        "event_type": payload.get("e"),
        "event_time": payload.get("E"),
        "symbol": payload.get("s"),
        "U": payload.get("U"),
        "u": payload.get("u"),
        "pu": payload.get("pu"),
        "b": payload.get("b", []),
        "a": payload.get("a", []),
    }
