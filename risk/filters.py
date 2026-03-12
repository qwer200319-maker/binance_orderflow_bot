from __future__ import annotations


def signal_allowed(last_signal_ts: float | None, now_ts: float, cooldown_seconds: int) -> bool:
    if last_signal_ts is None:
        return True
    return (now_ts - last_signal_ts) >= cooldown_seconds


def trend_continuation_block(side: str, features: dict) -> bool:
    if side == "SHORT":
        return (
            features.get("trend_higher_highs", False)
            and features.get("delta_expanding_up", False)
            and features.get("active_buy_liq_cluster", False)
        )
    return (
        features.get("trend_lower_lows", False)
        and features.get("delta_expanding_down", False)
        and features.get("active_sell_liq_cluster", False)
    )
