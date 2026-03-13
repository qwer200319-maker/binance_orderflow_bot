from __future__ import annotations

from config import settings


def orderflow_confirmations(features: dict, side: str) -> tuple[int, list[str]]:
    confirmations: list[str] = []

    if side == "LONG":
        if features.get("delta_5s", 0) > 0 and features.get("delta_15s", 0) > 0:
            confirmations.append("delta")
        if features.get("imbalance", 0) > settings.imbalance_long_threshold:
            confirmations.append("imbalance")
        if features.get("bullish_absorption", False):
            confirmations.append("absorption")
        if features.get("recent_sell_liq_cluster", False):
            confirmations.append("liq_cluster")
    else:
        if features.get("delta_5s", 0) < 0 and features.get("delta_15s", 0) < 0:
            confirmations.append("delta")
        if features.get("imbalance", 0) < settings.imbalance_short_threshold:
            confirmations.append("imbalance")
        if features.get("bearish_absorption", False):
            confirmations.append("absorption")
        if features.get("recent_buy_liq_cluster", False):
            confirmations.append("liq_cluster")

    return len(confirmations), confirmations
