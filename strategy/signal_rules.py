from __future__ import annotations

from config import settings
from risk.filters import trend_continuation_block
from strategy.regime_filter import is_no_trade_regime
from strategy.score_engine import compute_confirmation_scores, compute_setup_scores
from strategy.signal_quality import compute_quality


def decide_signal(features: dict) -> tuple[str | None, int, int, int, int, int, int, str]:
    if is_no_trade_regime(features):
        return None, 0, 0, 0, 0, 0, 0, ""

    htf_bias = features.get("htf_bias", "NEUTRAL")
    setup_signal = features.get("setup_signal", "NONE")
    bullish_sweep = features.get("bullish_sweep", False)
    bearish_sweep = features.get("bearish_sweep", False)
    vwap_reclaim = features.get("vwap_reclaim", False)
    vwap_reject = features.get("vwap_reject", False)
    regime = features.get("market_regime", "UNKNOWN")
    volatility = features.get("volatility_state", "UNKNOWN")
    if htf_bias == "NEUTRAL":
        return None, 0, 0, 0, 0, 0, 0, ""
    if regime not in settings.allowed_regimes:
        return None, 0, 0, 0, 0, 0, 0, ""
    if volatility == "LOW":
        return None, 0, 0, 0, 0, 0, 0, ""

    setup_long, setup_short = compute_setup_scores(features)
    confirm_long, confirm_short = compute_confirmation_scores(features)

    if trend_continuation_block("LONG", features):
        setup_long = 0
        confirm_long = 0
    if trend_continuation_block("SHORT", features):
        setup_short = 0
        confirm_short = 0

    if htf_bias == "BULLISH":
        setup_short = 0
        confirm_short = 0
    elif htf_bias == "BEARISH":
        setup_long = 0
        confirm_long = 0

    if setup_signal == "LONG_SETUP":
        setup_short = 0
        confirm_short = 0
        if not bullish_sweep or not vwap_reclaim:
            return None, setup_long, setup_short, confirm_long, confirm_short, 0, 0, ""
    elif setup_signal == "SHORT_SETUP":
        setup_long = 0
        confirm_long = 0
        if not bearish_sweep or not vwap_reject:
            return None, setup_long, setup_short, confirm_long, confirm_short, 0, 0, ""
    elif setup_signal == "NONE":
        return None, setup_long, setup_short, confirm_long, confirm_short, 0, 0, ""

    long_quality_score, long_quality_grade = compute_quality("LONG", features, setup_long, confirm_long)
    short_quality_score, short_quality_grade = compute_quality("SHORT", features, setup_short, confirm_short)

    if (
        setup_long >= settings.setup_long_score
        and confirm_long >= settings.confirm_long_score
        and (setup_long + confirm_long) > (setup_short + confirm_short)
        and _grade_allowed(long_quality_grade, volatility)
    ):
        return "LONG", setup_long, setup_short, confirm_long, confirm_short, long_quality_score, short_quality_score, long_quality_grade

    if (
        setup_short >= settings.setup_short_score
        and confirm_short >= settings.confirm_short_score
        and (setup_short + confirm_short) > (setup_long + confirm_long)
        and _grade_allowed(short_quality_grade, volatility)
    ):
        return "SHORT", setup_long, setup_short, confirm_long, confirm_short, long_quality_score, short_quality_score, short_quality_grade

    return None, setup_long, setup_short, confirm_long, confirm_short, long_quality_score, short_quality_score, ""


def _grade_allowed(grade: str, volatility: str) -> bool:
    order = {"A": 3, "B": 2, "C": 1}
    min_grade = settings.min_quality_grade.upper()
    if volatility == "HIGH":
        min_grade = settings.high_vol_min_quality.upper()
    return order.get(grade, 0) >= order.get(min_grade, 2)
