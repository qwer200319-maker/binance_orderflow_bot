from __future__ import annotations

from typing import List

from strategy.htf_bias import ema


def _ranges(candles: List[dict]) -> tuple[float, float]:
    if not candles:
        return 0.0, 0.0
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    return max(highs) - min(lows), sum(h - l for h, l in zip(highs, lows)) / len(candles)


def _cross_count(values: List[float], ref: float) -> int:
    if len(values) < 2:
        return 0
    count = 0
    prev = values[0] - ref
    for v in values[1:]:
        curr = v - ref
        if (prev <= 0 < curr) or (prev >= 0 > curr):
            count += 1
        prev = curr
    return count


def detect_regime(
    candles: List[dict],
    lookback: int,
    ema_fast: int,
    ema_slow: int,
    flat_ratio: float,
    expansion_ratio: float,
    chop_crosses: int,
    range_ratio: float,
) -> tuple[str, dict]:
    if len(candles) < max(lookback * 2, ema_slow):
        return "UNKNOWN", {}

    recent = candles[-lookback:]
    prev = candles[-lookback * 2 : -lookback]

    recent_range, recent_avg_range = _ranges(recent)
    prev_range, prev_avg_range = _ranges(prev)

    closes = [c["close"] for c in candles]
    last_close = closes[-1]
    ema_fast_val = ema(closes[-ema_fast:], ema_fast)
    ema_slow_val = ema(closes[-ema_slow:], ema_slow)
    ema_sep = abs(ema_fast_val - ema_slow_val) / ema_slow_val if ema_slow_val > 0 else 0.0

    recent_high = max(c["high"] for c in recent)
    recent_low = min(c["low"] for c in recent)
    prev_high = max(c["high"] for c in prev)
    prev_low = min(c["low"] for c in prev)

    higher_highs = recent_high > prev_high and recent_low >= prev_low
    lower_lows = recent_low < prev_low and recent_high <= prev_high

    expansion = prev_avg_range > 0 and recent_avg_range >= prev_avg_range * expansion_ratio

    chop = _cross_count([c["close"] for c in recent], ema_fast_val) >= chop_crosses and ema_sep < flat_ratio

    ranging = not (higher_highs or lower_lows) and prev_range > 0 and recent_range <= prev_range * range_ratio

    regime = "RANGING"
    if expansion:
        regime = "EXPANSION"
    elif chop:
        regime = "CHOPPY"
    elif (higher_highs or lower_lows) and ema_sep >= flat_ratio:
        regime = "TRENDING"
    elif ranging:
        regime = "RANGING"

    context = {
        "last_close": last_close,
        "ema_fast": ema_fast_val,
        "ema_slow": ema_slow_val,
        "ema_sep": ema_sep,
        "recent_range": recent_range,
        "prev_range": prev_range,
        "recent_avg_range": recent_avg_range,
        "prev_avg_range": prev_avg_range,
        "higher_highs": higher_highs,
        "lower_lows": lower_lows,
        "expansion": expansion,
        "choppy": chop,
    }
    return regime, context
