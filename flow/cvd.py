from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CVDTracker:
    value: float = 0.0
    deltas: List[Dict[str, float]] = field(default_factory=list)

    def update_from_trade(self, trade: Dict[str, float | str]) -> float:
        qty = float(trade["qty"])
        side = str(trade["side"])
        ts = float(trade["ts"])
        delta = qty if side == "buy" else -qty
        self.value += delta
        self.deltas.append({"ts": ts, "delta": delta})
        return self.value

    def trim(self, now_ts: float, max_age: int = 600) -> None:
        self.deltas = [d for d in self.deltas if now_ts - d["ts"] <= max_age]

    def window_delta(self, now_ts: float, window_sec: int) -> float:
        return sum(d["delta"] for d in self.deltas if now_ts - d["ts"] <= window_sec)
