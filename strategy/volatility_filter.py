from __future__ import annotations

from typing import List


def _true_ranges(candles: List[dict]) -> List[float]:
    if len(candles) < 2:
        return []
    ranges = []
    prev_close = candles[0]["close"]
    for c in candles[1:]:
        high = c["high"]
        low = c["low"]
        tr = max(high - low, abs(high - prev_close), abs(low - prev_close))
        ranges.append(tr)
        prev_close = c["close"]
    return ranges


def atr(candles: List[dict], length: int) -> float:
    trs = _true_ranges(candles[-(length + 1) :])
    if not trs:
        return 0.0
    return sum(trs) / len(trs)


def classify_volatility(
    candles: List[dict],
    atr_length: int,
    low_ratio: float,
    high_ratio: float,
) -> tuple[str, float]:
    if len(candles) < atr_length + 2:
        return "UNKNOWN", 0.0
    value = atr(candles, atr_length)
    price = candles[-1]["close"]
    ratio = value / price if price > 0 else 0.0

    if ratio <= low_ratio:
        return "LOW", value
    if ratio >= high_ratio:
        return "HIGH", value
    return "NORMAL", value
