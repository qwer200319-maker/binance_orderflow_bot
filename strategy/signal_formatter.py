from __future__ import annotations


def _rr_ratios(side: str, entry: float, sl: float, tp1: float, tp2: float) -> tuple[float, float]:
    if side == "LONG":
        risk = max(entry - sl, 0.0)
        rr1 = (tp1 - entry) / risk if risk > 0 else 0.0
        rr2 = (tp2 - entry) / risk if risk > 0 else 0.0
    else:
        risk = max(sl - entry, 0.0)
        rr1 = (entry - tp1) / risk if risk > 0 else 0.0
        rr2 = (entry - tp2) / risk if risk > 0 else 0.0
    return rr1, rr2


def format_signal(symbol: str, side: str, features: dict, plan: dict, long_score: int, short_score: int) -> str:
    entry = float(plan["entry"])
    sl = float(plan["sl"])
    tp1 = float(plan["tp1"])
    tp2 = float(plan["tp2"])
    rr1, rr2 = _rr_ratios(side, entry, sl, tp1, tp2)
    side_icon = "🟢" if side == "LONG" else "🔴"
    return (
        f"🚨 ORDER FLOW SIGNAL\n\n"
        f"Symbol: {symbol}\n"
        f"Side: {side} {side_icon}\n"
        f"Entry: {entry:.2f}\n"
        f"SL: {sl:.2f}\n"
        f"TP1: {tp1:.2f}\n"
        f"TP2: {tp2:.2f}\n"
        f"R:R TP1: 1:{rr1:.2f} | TP2: 1:{rr2:.2f}"
    )
