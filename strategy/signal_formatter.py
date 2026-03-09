from __future__ import annotations


def format_signal(symbol: str, side: str, features: dict, plan: dict, long_score: int, short_score: int) -> str:
    return (
        f"🚨 ORDER FLOW SIGNAL\n\n"
        f"Symbol: {symbol}\n"
        f"Side: {side}\n"
        f"Entry: {plan['entry']:.2f}\n"
        f"SL: {plan['sl']:.2f}\n"
        f"TP1: {plan['tp1']:.2f}\n"
        f"TP2: {plan['tp2']:.2f}\n\n"
        f"Mid Price: {features['mid_price']:.2f}\n"
        f"Spread: {features['spread']:.2f}\n"
        f"Imbalance: {features['imbalance']:.3f}\n"
        f"Delta 15s: {features['delta_15s']:.3f}\n"
        f"CVD: {features['cvd']:.3f}\n"
        f"Funding: {features['funding_rate']:.6f}\n"
        f"OI Change: {features['oi_change']:.3f}\n\n"
        f"Bullish Absorption: {features['bullish_absorption']}\n"
        f"Bearish Absorption: {features['bearish_absorption']}\n"
        f"Bullish Divergence: {features['bullish_divergence']}\n"
        f"Bearish Divergence: {features['bearish_divergence']}\n"
        f"Ask Spoof Score: {features['ask_spoof_score']}\n"
        f"Bid Spoof Score: {features['bid_spoof_score']}\n\n"
        f"Long Score: {long_score}\n"
        f"Short Score: {short_score}"
    )
