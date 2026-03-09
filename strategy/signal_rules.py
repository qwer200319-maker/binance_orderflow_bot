from __future__ import annotations

from config import settings
from strategy.regime_filter import is_no_trade_regime
from strategy.score_engine import compute_long_score, compute_short_score


def decide_signal(features: dict) -> tuple[str | None, int, int]:
    if is_no_trade_regime(features):
        return None, 0, 0

    long_score = compute_long_score(features)
    short_score = compute_short_score(features)

    if long_score >= settings.long_signal_score and long_score > short_score:
        return "LONG", long_score, short_score
    if short_score >= settings.short_signal_score and short_score > long_score:
        return "SHORT", long_score, short_score
    return None, long_score, short_score
