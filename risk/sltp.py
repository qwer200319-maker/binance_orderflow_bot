from __future__ import annotations

from config import settings


def build_trade_plan(side: str, entry: float, features: dict) -> dict:
    micro_atr = float(features.get("micro_atr", 0.0))
    spread = float(features.get("spread", 0.0))
    swing_low_15m = float(features.get("swing_low_15m", 0.0))
    swing_high_15m = float(features.get("swing_high_15m", 0.0))
    support_15m = float(features.get("support_15m", 0.0))
    resistance_15m = float(features.get("resistance_15m", 0.0))
    swing_high_1h = float(features.get("swing_high_1h", 0.0))
    swing_low_1h = float(features.get("swing_low_1h", 0.0))

    buffer = max(micro_atr * settings.sl_volatility_atr_mult, spread * settings.sl_spread_buffer_mult)

    if side == "LONG":
        sl_base = swing_low_15m if swing_low_15m > 0 else entry - buffer
        sl = sl_base - buffer
        tp2 = swing_high_1h if swing_high_1h > entry else entry + micro_atr * settings.tp2_atr_fallback
        tp1_anchor = resistance_15m if resistance_15m > entry else 0.0
        tp1 = (
            tp1_anchor
            if tp1_anchor > entry
            else entry
            + max((tp2 - entry) * settings.tp1_structure_fraction, micro_atr * settings.tp1_atr_fallback)
        )
    else:
        sl_base = swing_high_15m if swing_high_15m > 0 else entry + buffer
        sl = sl_base + buffer
        tp2 = swing_low_1h if 0 < swing_low_1h < entry else entry - micro_atr * settings.tp2_atr_fallback
        tp1_anchor = support_15m if 0 < support_15m < entry else 0.0
        tp1 = (
            tp1_anchor
            if 0 < tp1_anchor < entry
            else entry
            - max((entry - tp2) * settings.tp1_structure_fraction, micro_atr * settings.tp1_atr_fallback)
        )

    return {"entry": entry, "sl": sl, "tp1": tp1, "tp2": tp2}
