"""Privacy-preserving fuzzy legal risk lookup for the Lite demo."""

from __future__ import annotations

import pandas as pd


def summarize_legal_risk(
    judgments: pd.DataFrame, city: str, district: str, road_masked: str, community: str
) -> dict[str, object]:
    """Match only privacy-safe location fields and summarize mock judgments."""

    filtered = judgments.copy()
    for column, value in {
        "city": city,
        "district": district,
        "road_masked": road_masked,
        "community": community,
    }.items():
        if value.strip():
            filtered = filtered[filtered[column].str.contains(value.strip(), case=False, na=False)]
    items = filtered[["city", "district", "road_masked", "community", "risk_type", "summary"]].to_dict("records")
    score = min(100, len(items) * 25)
    return {
        "risk_score": score,
        "match_count": len(items),
        "summary": "找到可能相關的匿名化風險紀錄，建議人工確認。" if items else "未找到相符的 mock 風險紀錄。",
        "matched_items": items,
    }

