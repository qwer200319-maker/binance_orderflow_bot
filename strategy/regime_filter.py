from __future__ import annotations


def is_no_trade_regime(features: dict) -> bool:
    if features.get("spread", 0.0) <= 0:
        return True
    if abs(features.get("imbalance", 0.0)) < 0.03 and abs(features.get("delta_15s", 0.0)) < 5:
        return True
    if features.get("mid_price", 0.0) <= 0:
        return True
    return False
