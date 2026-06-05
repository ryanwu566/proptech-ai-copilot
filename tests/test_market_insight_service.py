"""Market Insight Lite offline service tests."""

from __future__ import annotations

from services.market_insight_service import (
    calculate_esg_lite_score,
    calculate_livability_score,
    get_market_summary,
    load_market_insights,
)


def test_mock_market_insights_can_load() -> None:
    data = load_market_insights()
    assert len(data) == 5
    assert {"city", "district", "six_period_trend_json", "sdg11_note"}.issubset(data.columns)


def test_livability_score_is_bounded() -> None:
    row = load_market_insights().iloc[0]
    assert 0 <= calculate_livability_score(row) <= 100


def test_esg_lite_score_is_bounded() -> None:
    row = load_market_insights().iloc[0]
    assert 0 <= calculate_esg_lite_score(row) <= 100


def test_unknown_area_returns_none() -> None:
    assert get_market_summary("不存在縣市", "不存在行政區") is None
