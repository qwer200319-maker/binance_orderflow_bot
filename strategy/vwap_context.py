from __future__ import annotations

from typing import List


def compute_vwap(candles: List[dict], lookback: int) -> tuple[float, dict]:
    if not candles:
        return 0.0, {}
    recent = candles[-lookback:] if lookback > 0 else candles
    total_pv = 0.0
    total_vol = 0.0
    for c in recent:
        typical = (c["high"] + c["low"] + c["close"]) / 3.0
        vol = c["volume"]
        total_pv += typical * vol
        total_vol += vol
    vwap = total_pv / total_vol if total_vol > 0 else 0.0
    return vwap, {"candles_used": len(recent)}


def vwap_context(candles: List[dict], lookback: int) -> tuple[str, bool, bool, float]:
    if len(candles) < 2:
        return "NEUTRAL", False, False, 0.0
    vwap, _ = compute_vwap(candles, lookback)
    last_close = candles[-1]["close"]
    prev_close = candles[-2]["close"]

    reclaim = prev_close < vwap and last_close > vwap
    reject = prev_close > vwap and last_close < vwap

    context = "NEUTRAL"
    if last_close < vwap:
        context = "DISCOUNT"
    elif last_close > vwap:
        context = "PREMIUM"

    return context, reclaim, reject, vwap
