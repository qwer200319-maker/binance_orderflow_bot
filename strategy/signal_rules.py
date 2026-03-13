from __future__ import annotations

from config import settings
from risk.filters import trend_continuation_block
from strategy.regime_filter import is_no_trade_regime
from strategy.score_engine import orderflow_confirmations
from strategy.signal_quality import compute_quality


def decide_signal(features: dict) -> tuple[str | None, int, str, str]:
    if is_no_trade_regime(features):
        return None, 0, "", ""

    htf_bias = features.get("htf_bias", "NEUTRAL")
    setup_signal = features.get("setup_signal", "NONE")
    bullish_sweep = features.get("bullish_sweep", False)
    bearish_sweep = features.get("bearish_sweep", False)
    vwap_reclaim = features.get("vwap_reclaim", False)
    vwap_reject = features.get("vwap_reject", False)
    regime = features.get("market_regime", "UNKNOWN")
    volatility = features.get("volatility_state", "UNKNOWN")
    if htf_bias == "NEUTRAL":
        return None, 0, "", ""
    if regime != "UNKNOWN" and regime not in settings.allowed_regimes:
        return None, 0, "", ""
    if volatility == "LOW":
        return None, 0, "", ""

    if setup_signal == "NONE":
        return None, 0, "", ""

    if trend_continuation_block("LONG", features):
        bullish_sweep = False
    if trend_continuation_block("SHORT", features):
        bearish_sweep = False

    side = "LONG" if setup_signal == "LONG_SETUP" else "SHORT"
    if (side == "LONG" and htf_bias != "BULLISH") or (side == "SHORT" and htf_bias != "BEARISH"):
        return None, 0, "", ""

    confirm_count, confirmations = orderflow_confirmations(features, side)
    if confirm_count < 2:
        return None, 0, "", ""

    setup_ok = True
    quality_score, quality_grade, reason_summary = compute_quality(
        side,
        features,
        confirmations,
        setup_ok,
    )

    if quality_score < 2:
        return None, quality_score, quality_grade, reason_summary
    if not _grade_allowed(quality_grade, volatility):
        return None, quality_score, quality_grade, reason_summary

    return side, quality_score, quality_grade, reason_summary


def _grade_allowed(grade: str, volatility: str) -> bool:
    order = {"A": 3, "B": 2, "C": 1}
    min_grade = settings.min_quality_grade.upper()
    if volatility == "HIGH":
        min_grade = settings.high_vol_min_quality.upper()
    return order.get(grade, 0) >= order.get(min_grade, 2)
