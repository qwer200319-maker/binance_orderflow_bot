from __future__ import annotations

def grade_quality(score: int) -> str:
    if score >= 5:
        return "A"
    if score >= 3:
        return "B"
    return "C"


def compute_quality(
    side: str,
    features: dict,
    confirmations: list[str],
    setup_ok: bool,
) -> tuple[int, str, str]:
    score = 0
    reasons: list[str] = []

    if setup_ok:
        score += 2
        reasons.append("setup")

    liquidity_event = False
    if side == "LONG":
        liquidity_event = (
            features.get("bullish_sweep", False)
            or features.get("recent_sell_liq_cluster", False)
            or features.get("active_sell_liq_cluster", False)
        )
    else:
        liquidity_event = (
            features.get("bearish_sweep", False)
            or features.get("recent_buy_liq_cluster", False)
            or features.get("active_buy_liq_cluster", False)
        )
    if liquidity_event:
        score += 1
        reasons.append("liquidity")

    if len(confirmations) >= 2:
        score += 2
        reasons.append(f"confirm({','.join(confirmations)})")

    context_hits: list[str] = []
    if side == "LONG":
        if features.get("vwap_reclaim", False):
            context_hits.append("vwap")
        if features.get("funding_rate", 0) < 0:
            context_hits.append("funding")
        if features.get("oi_change", 0) > 0:
            context_hits.append("oi")
    else:
        if features.get("vwap_reject", False):
            context_hits.append("vwap")
        if features.get("funding_rate", 0) > 0:
            context_hits.append("funding")
        if features.get("oi_change", 0) < 0:
            context_hits.append("oi")
    if context_hits:
        score += 1
        reasons.append(f"context({','.join(context_hits)})")

    grade = grade_quality(score)
    reason_summary = "; ".join(reasons)
    return score, grade, reason_summary
