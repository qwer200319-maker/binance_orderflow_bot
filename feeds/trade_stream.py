from __future__ import annotations


def parse_agg_trade_message(payload: dict) -> dict:
    price = float(payload.get("p", 0.0))
    qty = float(payload.get("q", 0.0))
    # m=true means buyer is market maker -> aggressive sell, else aggressive buy
    is_buyer_maker = bool(payload.get("m", False))
    side = "sell" if is_buyer_maker else "buy"
    ts = float(payload.get("T", 0)) / 1000.0
    return {
        "price": price,
        "qty": qty,
        "side": side,
        "ts": ts,
    }
