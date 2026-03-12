from __future__ import annotations

from typing import List


def _recent_swings(candles: List[dict], lookback: int) -> tuple[float, float, float, float]:
    if len(candles) < lookback * 2:
        return 0.0, 0.0, 0.0, 0.0
    recent = candles[-lookback:]
    prev = candles[-lookback * 2 : -lookback]
    recent_high = max(c["high"] for c in recent)
    recent_low = min(c["low"] for c in recent)
    prev_high = max(c["high"] for c in prev)
    prev_low = min(c["low"] for c in prev)
    return recent_high, recent_low, prev_high, prev_low


def _avg_range(candles: List[dict], lookback: int) -> float:
    if len(candles) < lookback:
        return 0.0
    recent = candles[-lookback:]
    ranges = [c["high"] - c["low"] for c in recent]
    return sum(ranges) / len(ranges) if ranges else 0.0


def detect_setup(
    candles: List[dict],
    swing_lookback: int,
    buffer_mult: float,
) -> tuple[str, dict]:
    if len(candles) < swing_lookback * 2:
        return "NONE", {}

    last = candles[-1]
    last_close = last["close"]
    recent_high, recent_low, prev_high, prev_low = _recent_swings(candles, swing_lookback)
    avg_range = _avg_range(candles, swing_lookback)
    buffer = avg_range * buffer_mult

    sweep_low = prev_low > 0 and recent_low < prev_low
    sweep_high = prev_high > 0 and recent_high > prev_high

    higher_low = recent_low > prev_low
    lower_high = recent_high < prev_high

    near_support = recent_low > 0 and last_close <= (recent_low + buffer)
    near_resistance = recent_high > 0 and last_close >= (recent_high - buffer)

    long_setup = (sweep_low and last_close > prev_low) or (higher_low and near_support)
    short_setup = (sweep_high and last_close < prev_high) or (lower_high and near_resistance)

    setup = "NONE"
    if long_setup and not short_setup:
        setup = "LONG_SETUP"
    elif short_setup and not long_setup:
        setup = "SHORT_SETUP"

    context = {
        "setup": setup,
        "last_close": last_close,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "prev_high": prev_high,
        "prev_low": prev_low,
        "support": recent_low,
        "resistance": recent_high,
        "trigger_high": recent_high,
        "trigger_low": recent_low,
        "sweep_low": sweep_low,
        "sweep_high": sweep_high,
        "higher_low": higher_low,
        "lower_high": lower_high,
    }
    return setup, context
