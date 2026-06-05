"""Offline Market Insight Lite service backed by bundled mock CSV data."""

from __future__ import annotations

import json
from typing import Any

import pandas as pd

from services.data_service import MockDataError, load_mock_csv


MARKET_INSIGHT_DISCLAIMER = "展示型 mock data，不代表正式估價或投資建議。"


def load_market_insights() -> pd.DataFrame:
    """Load and validate the bundled Market Insight Lite dataset."""

    data = load_mock_csv("mock_market_insights.csv")
    required = {
        "city",
        "district",
        "avg_price_per_ping",
        "six_period_trend_json",
        "transaction_volume",
        "poi_score",
        "transit_score",
        "school_score",
        "park_score",
        "medical_score",
        "esg_score",
        "walkability_score",
        "sdg11_note",
        "summary",
    }
    missing = required.difference(data.columns)
    if missing:
        raise MockDataError(f"Market Insight 展示資料缺少欄位：{', '.join(sorted(missing))}")
    return data


def get_market_summary(city: str, district: str) -> dict[str, Any] | None:
    """Return a structured market insight result, or None when no area matches."""

    data = load_market_insights()
    matched = data[(data["city"] == city) & (data["district"] == district)]
    if matched.empty:
        return None
    return build_market_insight_result(matched.iloc[0])


def calculate_livability_score(row: pd.Series | dict[str, Any]) -> int:
    """Calculate an explainable weighted POI livability score from 0 to 100."""

    score = (
        float(row["poi_score"]) * 0.20
        + float(row["transit_score"]) * 0.25
        + float(row["school_score"]) * 0.15
        + float(row["park_score"]) * 0.20
        + float(row["medical_score"]) * 0.20
    )
    return _bounded_score(score)


def calculate_esg_lite_score(row: pd.Series | dict[str, Any]) -> int:
    """Calculate a mock ESG / SDG 11 Lite score from 0 to 100."""

    score = (
        float(row["esg_score"]) * 0.50
        + float(row["walkability_score"]) * 0.30
        + float(row["park_score"]) * 0.20
    )
    return _bounded_score(score)


def build_market_insight_result(row: pd.Series | dict[str, Any]) -> dict[str, Any]:
    """Build the stable UI-facing Market Insight Lite output contract."""

    trend = _parse_trend(row["six_period_trend_json"])
    return {
        "city": str(row["city"]),
        "district": str(row["district"]),
        "avg_price_per_ping": float(row["avg_price_per_ping"]),
        "trend": trend,
        "transaction_volume": int(row["transaction_volume"]),
        "livability_score": calculate_livability_score(row),
        "esg_lite_score": calculate_esg_lite_score(row),
        "poi_breakdown": {
            "綜合機能": int(row["poi_score"]),
            "交通便利": int(row["transit_score"]),
            "教育資源": int(row["school_score"]),
            "公園綠地": int(row["park_score"]),
            "醫療資源": int(row["medical_score"]),
        },
        "sdg11_note": str(row["sdg11_note"]),
        "summary": str(row["summary"]),
        "disclaimer": MARKET_INSIGHT_DISCLAIMER,
    }


def _parse_trend(value: Any) -> list[float]:
    """Parse six period trend JSON and reject malformed mock data."""

    try:
        trend = json.loads(str(value))
    except json.JSONDecodeError as exc:
        raise MockDataError("Market Insight 六期趨勢資料格式錯誤。") from exc
    if not isinstance(trend, list) or len(trend) != 6:
        raise MockDataError("Market Insight 六期趨勢必須包含六筆資料。")
    return [float(item) for item in trend]


def _bounded_score(value: float) -> int:
    """Clamp a rounded score into the display range."""

    return max(0, min(100, round(value)))
