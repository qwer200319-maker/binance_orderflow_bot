from __future__ import annotations

from config import settings


def grade_quality(score: int) -> str:
    if score >= settings.quality_grade_a:
        return "A"
    if score >= settings.quality_grade_b:
        return "B"
    return "C"


def compute_quality(
    side: str,
    features: dict,
    setup_score: int,
    confirm_score: int,
) -> tuple[int, str]:
    score = 0

    htf_bias = features.get("htf_bias", "NEUTRAL")
    if (side == "LONG" and htf_bias == "BULLISH") or (side == "SHORT" and htf_bias == "BEARISH"):
        score += 2

    if side == "LONG" and features.get("bullish_sweep", False):
        score += 1
    if side == "SHORT" and features.get("bearish_sweep", False):
        score += 1

    if side == "LONG" and features.get("vwap_reclaim", False):
        score += 1
    if side == "SHORT" and features.get("vwap_reject", False):
        score += 1

    if confirm_score >= settings.confirm_long_score + 1 and side == "LONG":
        score += 2
    elif confirm_score >= settings.confirm_short_score + 1 and side == "SHORT":
        score += 2
    elif confirm_score >= (settings.confirm_long_score if side == "LONG" else settings.confirm_short_score):
        score += 1

    regime = features.get("market_regime", "UNKNOWN")
    if regime in settings.allowed_regimes:
        score += 1
    else:
        score -= 1

    volatility = features.get("volatility_state", "UNKNOWN")
    if volatility == "NORMAL":
        score += 1
    elif volatility == "HIGH":
        score -= 1
    elif volatility == "LOW":
        score -= 2

    score += max(setup_score, 0)
    return score, grade_quality(score)
