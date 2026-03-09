from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List


class TradesBuffer:
    def __init__(self, max_age_seconds: int = 600) -> None:
        self.max_age_seconds = max_age_seconds
        self.trades: Deque[Dict[str, float | str]] = deque()
        self.prices: Deque[Dict[str, float]] = deque()

    def add_trade(self, trade: Dict[str, float | str]) -> None:
        self.trades.append(trade)
        self.prices.append({"price": float(trade["price"]), "ts": float(trade["ts"])})

    def trim(self, now_ts: float) -> None:
        while self.trades and now_ts - float(self.trades[0]["ts"]) > self.max_age_seconds:
            self.trades.popleft()
        while self.prices and now_ts - float(self.prices[0]["ts"]) > self.max_age_seconds:
            self.prices.popleft()

    def snapshot(self) -> List[Dict[str, float | str]]:
        return list(self.trades)

    def latest_price(self) -> float:
        if not self.prices:
            return 0.0
        return float(self.prices[-1]["price"])
