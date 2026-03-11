from __future__ import annotations

from config import settings


def build_trade_plan(side: str, price: float, atr: float) -> dict:
    del atr
    sl_usd = settings.sl_usd
    tp1_usd = settings.tp1_usd
    tp2_usd = settings.tp2_usd
    if side == "LONG":
        sl = price - sl_usd
        tp1 = price + tp1_usd
        tp2 = price + tp2_usd
    else:
        sl = price + sl_usd
        tp1 = price - tp1_usd
        tp2 = price - tp2_usd
    return {"entry": price, "sl": sl, "tp1": tp1, "tp2": tp2}
