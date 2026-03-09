from __future__ import annotations

import time
from datetime import datetime, timezone


def now_ts() -> float:
    return time.time()


def now_ms() -> int:
    return int(time.time() * 1000)


def iso_utc(ts: float | None = None) -> str:
    value = ts if ts is not None else time.time()
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
