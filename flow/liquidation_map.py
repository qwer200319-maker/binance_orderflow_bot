from __future__ import annotations

from collections import deque
from typing import Deque, Dict, List, Tuple


class LiquidationMap:
    def __init__(self, max_age_seconds: int = 600) -> None:
        self.max_age_seconds = max_age_seconds
        self.events: Deque[Dict[str, float | str]] = deque()

    def add(self, event: Dict[str, float | str]) -> None:
        self.events.append(event)

    def trim(self, now_ts: float) -> None:
        while self.events and now_ts - float(self.events[0]["ts"]) > self.max_age_seconds:
            self.events.popleft()

    def cluster(self, now_ts: float, window_sec: int, price_bin: float) -> Dict[Tuple[str, float], Dict[str, float]]:
        clusters: Dict[Tuple[str, float], Dict[str, float]] = {}
        for event in self.events:
            if now_ts - float(event["ts"]) > window_sec:
                continue
            side = str(event["side"])
            price = float(event["price"])
            qty = float(event["qty"])
            bucket = round(price / price_bin) * price_bin
            key = (side, bucket)
            if key not in clusters:
                clusters[key] = {"count": 0, "qty": 0.0}
            clusters[key]["count"] += 1
            clusters[key]["qty"] += qty
        return clusters

    def summarize(self, now_ts: float, window_sec: int, price_bin: float, min_count: int) -> Dict[str, bool | list]:
        clusters = self.cluster(now_ts, window_sec, price_bin)
        recent_sell = []
        recent_buy = []
        for (side, bucket), data in clusters.items():
            if data["count"] < min_count:
                continue
            row = {"side": side, "bucket": bucket, "count": data["count"], "qty": data["qty"]}
            if side.upper() == "SELL":
                recent_sell.append(row)
            else:
                recent_buy.append(row)
        return {
            "recent_sell_liq_cluster": len(recent_sell) > 0,
            "recent_buy_liq_cluster": len(recent_buy) > 0,
            "sell_clusters": recent_sell,
            "buy_clusters": recent_buy,
        }
