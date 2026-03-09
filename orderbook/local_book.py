from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


@dataclass
class LocalBook:
    bids: Dict[float, float] = field(default_factory=dict)
    asks: Dict[float, float] = field(default_factory=dict)
    last_update_id: int | None = None

    def clear(self) -> None:
        self.bids.clear()
        self.asks.clear()
        self.last_update_id = None

    def load_snapshot(self, snapshot: dict) -> None:
        self.last_update_id = int(snapshot["lastUpdateId"])
        self.bids = {float(price): float(qty) for price, qty in snapshot.get("bids", [])}
        self.asks = {float(price): float(qty) for price, qty in snapshot.get("asks", [])}

    def apply_update(self, bid_updates: List[List[str]], ask_updates: List[List[str]], final_update_id: int) -> None:
        for price, qty in bid_updates:
            self._apply_level(self.bids, price, qty)
        for price, qty in ask_updates:
            self._apply_level(self.asks, price, qty)
        self.last_update_id = int(final_update_id)

    @staticmethod
    def _apply_level(side_map: Dict[float, float], price: str | float, qty: str | float) -> None:
        p = float(price)
        q = float(qty)
        if q == 0.0:
            side_map.pop(p, None)
        else:
            side_map[p] = q

    def best_bid(self) -> float | None:
        return max(self.bids.keys()) if self.bids else None

    def best_ask(self) -> float | None:
        return min(self.asks.keys()) if self.asks else None

    def top_bids(self, levels: int) -> List[Tuple[float, float]]:
        return sorted(self.bids.items(), key=lambda x: x[0], reverse=True)[:levels]

    def top_asks(self, levels: int) -> List[Tuple[float, float]]:
        return sorted(self.asks.items(), key=lambda x: x[0])[:levels]
