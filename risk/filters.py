from __future__ import annotations


def signal_allowed(last_signal_ts: float | None, now_ts: float, cooldown_seconds: int) -> bool:
    if last_signal_ts is None:
        return True
    return (now_ts - last_signal_ts) >= cooldown_seconds
