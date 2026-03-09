from __future__ import annotations


def parse_force_order_message(payload: dict) -> dict:
    order = payload.get("o", {})
    ts = float(payload.get("E", 0)) / 1000.0
    return {
        "symbol": order.get("s", ""),
        "side": order.get("S", ""),
        "price": float(order.get("ap") or order.get("p") or 0.0),
        "qty": float(order.get("q", 0.0)),
        "ts": ts,
    }
