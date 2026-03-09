from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Tuple


@dataclass
class WallState:
    side: str
    price: float
    first_seen_ts: float
    last_seen_ts: float
    max_qty: float
    current_qty: float
    price_touched: bool = False
    executed_qty_est: float = 0.0
    canceled_qty_est: float = 0.0

    @property
    def lifetime_ms(self) -> int:
        return int((self.last_seen_ts - self.first_seen_ts) * 1000)

    @property
    def execution_ratio(self) -> float:
        if self.max_qty <= 0:
            return 0.0
        return min(self.executed_qty_est / self.max_qty, 1.0)


class WallTracker:
    def __init__(self) -> None:
        self.walls: Dict[tuple[str, float], WallState] = {}

    def observe(self, side: str, levels: Iterable[Tuple[float, float]], ts: float, best_bid: float | None, best_ask: float | None) -> None:
        current = {(side, price): qty for price, qty in levels}

        for key, qty in current.items():
            if key not in self.walls:
                self.walls[key] = WallState(
                    side=side,
                    price=key[1],
                    first_seen_ts=ts,
                    last_seen_ts=ts,
                    max_qty=qty,
                    current_qty=qty,
                )
            else:
                wall = self.walls[key]
                if qty < wall.current_qty:
                    wall.executed_qty_est += max(wall.current_qty - qty, 0.0)
                wall.current_qty = qty
                wall.last_seen_ts = ts
                wall.max_qty = max(wall.max_qty, qty)

        existing_keys = [k for k in self.walls.keys() if k[0] == side]
        for key in existing_keys:
            if key not in current:
                wall = self.walls[key]
                wall.canceled_qty_est += wall.current_qty
                wall.current_qty = 0.0
                wall.last_seen_ts = ts

                if side == "bid" and best_bid is not None and wall.price >= best_bid:
                    wall.price_touched = True
                if side == "ask" and best_ask is not None and wall.price <= best_ask:
                    wall.price_touched = True

    def get_recent(self) -> List[WallState]:
        return list(self.walls.values())
