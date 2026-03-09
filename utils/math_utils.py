from __future__ import annotations

from typing import Iterable, List


def safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def mean(values: Iterable[float]) -> float:
    values_list: List[float] = list(values)
    if not values_list:
        return 0.0
    return sum(values_list) / len(values_list)
