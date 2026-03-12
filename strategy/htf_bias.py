from __future__ import annotations

from typing import List

def ema(values: List[float], length: int) -> float:
    if not values:
        return 0.0
    if length <= 1:
        return values[-1]
    k = 2 / (length + 1)
    ema_val = values[0]
    for v in values[1:]:
        ema_val = v * k + ema_val * (1 - k)
    return ema_val


def recent_swings(candles: List[dict], lookback: int) -> tuple[float, float, float, float]:
    if len(candles) < lookback * 2:
        return 0.0, 0.0, 0.0, 0.0
    recent = candles[-lookback:]
    prev = candles[-lookback * 2 : -lookback]
    recent_high = max(c["high"] for c in recent)
    recent_low = min(c["low"] for c in recent)
    prev_high = max(c["high"] for c in prev)
    prev_low = min(c["low"] for c in prev)
    return recent_high, recent_low, prev_high, prev_low


def classify_bias(
    candles: List[dict],
    ema_fast: int,
    ema_slow: int,
    swing_lookback: int,
    flat_ratio: float,
) -> tuple[str, dict]:
    if len(candles) < max(ema_slow, swing_lookback * 2):
        return "NEUTRAL", {}

    closes = [c["close"] for c in candles]
    last_close = closes[-1]
    ema_fast_val = ema(closes[-ema_fast:], ema_fast)
    ema_slow_val = ema(closes[-ema_slow:], ema_slow)

    recent_high, recent_low, prev_high, prev_low = recent_swings(candles, swing_lookback)

    bullish_structure = recent_high > prev_high and recent_low >= prev_low
    bearish_structure = recent_high < prev_high and recent_low <= prev_low

    bias = "NEUTRAL"
    ema_separation = abs(ema_fast_val - ema_slow_val) / ema_slow_val if ema_slow_val > 0 else 0.0
    tangled = ema_separation < flat_ratio or (min(ema_fast_val, ema_slow_val) <= last_close <= max(ema_fast_val, ema_slow_val))

    if not tangled and last_close > ema_fast_val and ema_fast_val > ema_slow_val and bullish_structure:
        bias = "BULLISH"
    elif not tangled and last_close < ema_fast_val and ema_fast_val < ema_slow_val and bearish_structure:
        bias = "BEARISH"

    context = {
        "ema_fast": ema_fast_val,
        "ema_slow": ema_slow_val,
        "last_close": last_close,
        "recent_high": recent_high,
        "recent_low": recent_low,
        "prev_high": prev_high,
        "prev_low": prev_low,
        "bullish_structure": bullish_structure,
        "bearish_structure": bearish_structure,
        "ema_separation": ema_separation,
        "tangled": tangled,
    }
    return bias, context
