from __future__ import annotations

from config import settings


def build_trade_plan(side: str, price: float, atr: float) -> dict:
    risk = max(atr * settings.sl_atr_multiplier, settings.default_tick_size * 5)
    if side == "LONG":
        sl = price - risk
        tp1 = price + risk * settings.tp1_rr
        tp2 = price + risk * settings.tp2_rr
    else:
        sl = price + risk
        tp1 = price - risk * settings.tp1_rr
        tp2 = price - risk * settings.tp2_rr
    return {"entry": price, "sl": sl, "tp1": tp1, "tp2": tp2}
