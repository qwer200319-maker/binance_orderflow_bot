from __future__ import annotations

from typing import List


def detect_liquidity_sweep(
    candles: List[dict],
    swing_lookback: int,
    sweep_lookback: int,
) -> tuple[bool, bool, dict]:
    if len(candles) < swing_lookback * 2:
        return False, False, {}

    prev = candles[-swing_lookback * 2 : -swing_lookback]
    recent = candles[-sweep_lookback:]

    prev_high = max(c["high"] for c in prev)
    prev_low = min(c["low"] for c in prev)

    last_close = recent[-1]["close"]
    recent_low = min(c["low"] for c in recent)
    recent_high = max(c["high"] for c in recent)

    bullish_sweep = prev_low > 0 and recent_low < prev_low and last_close > prev_low
    bearish_sweep = prev_high > 0 and recent_high > prev_high and last_close < prev_high

    context = {
        "prev_high": prev_high,
        "prev_low": prev_low,
        "recent_low": recent_low,
        "recent_high": recent_high,
        "last_close": last_close,
    }
    return bullish_sweep, bearish_sweep, context
