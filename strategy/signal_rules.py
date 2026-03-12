from __future__ import annotations

from config import settings
from risk.filters import trend_continuation_block
from strategy.regime_filter import is_no_trade_regime
from strategy.score_engine import compute_confirmation_scores, compute_setup_scores


def decide_signal(features: dict) -> tuple[str | None, int, int, int, int]:
    if is_no_trade_regime(features):
        return None, 0, 0, 0, 0

    htf_bias = features.get("htf_bias", "NEUTRAL")
    setup_signal = features.get("setup_signal", "NONE")
    bullish_sweep = features.get("bullish_sweep", False)
    bearish_sweep = features.get("bearish_sweep", False)
    vwap_reclaim = features.get("vwap_reclaim", False)
    vwap_reject = features.get("vwap_reject", False)
    if htf_bias == "NEUTRAL":
        return None, 0, 0, 0, 0

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
            return None, setup_long, setup_short, confirm_long, confirm_short
    elif setup_signal == "SHORT_SETUP":
        setup_long = 0
        confirm_long = 0
        if not bearish_sweep or not vwap_reject:
            return None, setup_long, setup_short, confirm_long, confirm_short
    elif setup_signal == "NONE":
        return None, setup_long, setup_short, confirm_long, confirm_short

    if (
        setup_long >= settings.setup_long_score
        and confirm_long >= settings.confirm_long_score
        and (setup_long + confirm_long) > (setup_short + confirm_short)
    ):
        return "LONG", setup_long, setup_short, confirm_long, confirm_short

    if (
        setup_short >= settings.setup_short_score
        and confirm_short >= settings.confirm_short_score
        and (setup_short + confirm_short) > (setup_long + confirm_long)
    ):
        return "SHORT", setup_long, setup_short, confirm_long, confirm_short

    return None, setup_long, setup_short, confirm_long, confirm_short
