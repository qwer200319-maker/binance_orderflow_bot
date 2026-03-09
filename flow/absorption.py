from __future__ import annotations

from typing import Tuple


def detect_absorption(
    delta_15s: float,
    price_move_ticks: float,
    bid_persistence_count: int,
    ask_persistence_count: int,
    delta_threshold: float,
    max_price_move_ticks: int,
    min_persistence: int,
) -> Tuple[bool, bool]:
    bullish = (
        delta_15s < -delta_threshold
        and price_move_ticks >= -max_price_move_ticks
        and bid_persistence_count >= min_persistence
    )
    bearish = (
        delta_15s > delta_threshold
        and price_move_ticks <= max_price_move_ticks
        and ask_persistence_count >= min_persistence
    )
    return bullish, bearish
