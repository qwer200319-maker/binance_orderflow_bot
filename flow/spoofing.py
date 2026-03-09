from __future__ import annotations

from typing import Dict, Iterable

from orderbook.wall_tracker import WallState


def compute_spoof_score(
    wall: WallState,
    avg_level_qty: float,
    min_size_multiplier: float,
    max_lifetime_ms: int,
    max_execution_ratio: float,
) -> int:
    score = 0
    max_qty_ratio = wall.max_qty / avg_level_qty if avg_level_qty > 0 else 0.0
    canceled_before_touch = not wall.price_touched and wall.current_qty == 0.0 and wall.canceled_qty_est > 0.0

    if max_qty_ratio >= min_size_multiplier:
        score += 1
    if wall.lifetime_ms <= max_lifetime_ms:
        score += 1
    if wall.execution_ratio <= max_execution_ratio:
        score += 1
    if canceled_before_touch:
        score += 1
    return score


def summarize_spoofing(
    walls: Iterable[WallState],
    bid_avg_qty: float,
    ask_avg_qty: float,
    min_size_multiplier: float,
    max_lifetime_ms: int,
    max_execution_ratio: float,
) -> Dict[str, int]:
    bid_score = 0
    ask_score = 0
    for wall in walls:
        avg_qty = bid_avg_qty if wall.side == "bid" else ask_avg_qty
        score = compute_spoof_score(
            wall,
            avg_qty,
            min_size_multiplier,
            max_lifetime_ms,
            max_execution_ratio,
        )
        if wall.side == "bid":
            bid_score = max(bid_score, score)
        else:
            ask_score = max(ask_score, score)
    return {"bid_spoof_score": bid_score, "ask_spoof_score": ask_score}
