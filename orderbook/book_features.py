from __future__ import annotations

from typing import Dict, List, Tuple

from config import settings
from orderbook.local_book import LocalBook
from utils.math_utils import mean, safe_div


def compute_mid_price(book: LocalBook) -> float:
    bid = book.best_bid()
    ask = book.best_ask()
    if bid is None or ask is None:
        return 0.0
    return (bid + ask) / 2.0


def compute_spread(book: LocalBook) -> float:
    bid = book.best_bid()
    ask = book.best_ask()
    if bid is None or ask is None:
        return 0.0
    return ask - bid


def compute_imbalance(book: LocalBook, levels: int) -> float:
    bids = book.top_bids(levels)
    asks = book.top_asks(levels)
    bid_vol = sum(q for _, q in bids)
    ask_vol = sum(q for _, q in asks)
    return safe_div(bid_vol - ask_vol, bid_vol + ask_vol, 0.0)


def detect_walls(book: LocalBook, levels: int, multiplier: float) -> Dict[str, List[Tuple[float, float]]]:
    bids = book.top_bids(levels)
    asks = book.top_asks(levels)
    bid_avg = mean([qty for _, qty in bids])
    ask_avg = mean([qty for _, qty in asks])
    bid_walls = [(p, q) for p, q in bids if bid_avg > 0 and q >= bid_avg * multiplier]
    ask_walls = [(p, q) for p, q in asks if ask_avg > 0 and q >= ask_avg * multiplier]
    return {"bid_walls": bid_walls, "ask_walls": ask_walls}


def build_book_snapshot(book: LocalBook) -> Dict[str, float | list]:
    walls = detect_walls(book, settings.top_levels, settings.wall_multiplier)
    return {
        "best_bid": book.best_bid() or 0.0,
        "best_ask": book.best_ask() or 0.0,
        "mid_price": compute_mid_price(book),
        "spread": compute_spread(book),
        "imbalance": compute_imbalance(book, settings.top_levels),
        "bid_walls": walls["bid_walls"],
        "ask_walls": walls["ask_walls"],
    }
