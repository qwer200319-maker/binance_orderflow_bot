from __future__ import annotations

from config import settings


def compute_setup_scores(features: dict) -> tuple[int, int]:
    long_score = 0
    short_score = 0

    if features["bullish_divergence"]:
        long_score += 2
    if features["recent_sell_liq_cluster"]:
        long_score += 1
    if features["ask_spoof_score"] >= 2:
        long_score += 1
    if features["funding_rate"] < 0:
        long_score += 1

    if features["bearish_divergence"]:
        short_score += 2
    if features["recent_buy_liq_cluster"]:
        short_score += 1
    if features["bid_spoof_score"] >= 2:
        short_score += 1
    if features["funding_rate"] > 0:
        short_score += 1

    return long_score, short_score


def compute_confirmation_scores(features: dict) -> tuple[int, int]:
    long_score = 0
    short_score = 0

    if features["imbalance"] > settings.imbalance_long_threshold:
        long_score += 1
    if features["delta_5s"] > 0 and features["delta_15s"] > 0:
        long_score += 1
    if features["bullish_absorption"]:
        long_score += 1
    if features["long_reclaim"]:
        long_score += 1
    if features["stopped_making_lows"]:
        long_score += 1
    if not features["active_sell_liq_cluster"]:
        long_score += 1

    if features["imbalance"] < settings.imbalance_short_threshold:
        short_score += 1
    if features["delta_5s"] < 0 and features["delta_15s"] < 0:
        short_score += 1
    if features["bearish_absorption"]:
        short_score += 1
    if features["short_break"]:
        short_score += 1
    if features["stopped_making_highs"]:
        short_score += 1
    if not features["active_buy_liq_cluster"]:
        short_score += 1

    return long_score, short_score
