"""Simple heuristic mortgage risk scoring for the Lite demo."""

from __future__ import annotations


def evaluate_mortgage_risk(
    monthly_income: int,
    monthly_debt: int,
    cash: int,
    property_count: int,
    mortgage_count: int,
    property_price: int,
) -> dict[str, object]:
    """Return an explainable heuristic score. This is not underwriting."""

    traces: list[str] = []
    score = 0
    debt_ratio = monthly_debt / monthly_income if monthly_income else 1
    down_payment_ratio = cash / property_price if property_price else 0
    if debt_ratio > 0.5:
        score += 35
        traces.append("每月負債占收入超過 50%")
    elif debt_ratio > 0.35:
        score += 20
        traces.append("每月負債占收入高於 35%")
    if down_payment_ratio < 0.2:
        score += 30
        traces.append("可用現金低於物件價格 20%")
    if property_count >= 2:
        score += 15
        traces.append("名下房屋數達 2 戶以上")
    if mortgage_count >= 2:
        score += 20
        traces.append("既有房貸數達 2 筆以上")
    score = min(score, 100)
    color = "green" if score <= 24 else "yellow" if score <= 54 else "red"
    return {"risk_score": score, "signal_color": color, "traces": traces or ["未發現明顯 heuristic 風險"]}

