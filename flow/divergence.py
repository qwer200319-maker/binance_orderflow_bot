from __future__ import annotations


def detect_bullish_divergence(price_change: float, cvd_change: float, oi_change: float, funding_rate: float) -> bool:
    return price_change <= 0 and cvd_change > 0 and (funding_rate < 0 or oi_change <= 0)


def detect_bearish_divergence(price_change: float, cvd_change: float, oi_change: float, funding_rate: float) -> bool:
    return price_change >= 0 and cvd_change < 0 and (funding_rate > 0 or oi_change >= 0)
