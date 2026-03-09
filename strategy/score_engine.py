from __future__ import annotations

from config import settings


def compute_long_score(features: dict) -> int:
    score = 0
    if features["imbalance"] > settings.imbalance_long_threshold:
        score += 1
    if features["bullish_absorption"]:
        score += 3
    if features["bullish_divergence"]:
        score += 2
    if features["recent_sell_liq_cluster"]:
        score += 2
    if features["ask_spoof_score"] >= 2:
        score += 1
    if features["funding_rate"] < 0:
        score += 1
    return score


def compute_short_score(features: dict) -> int:
    score = 0
    if features["imbalance"] < settings.imbalance_short_threshold:
        score += 1
    if features["bearish_absorption"]:
        score += 3
    if features["bearish_divergence"]:
        score += 2
    if features["recent_buy_liq_cluster"]:
        score += 2
    if features["bid_spoof_score"] >= 2:
        score += 1
    if features["funding_rate"] > 0:
        score += 1
    return score
