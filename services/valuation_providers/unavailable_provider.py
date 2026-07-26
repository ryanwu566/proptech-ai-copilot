"""Safe provider used when official valuation data cannot be confirmed."""

from __future__ import annotations

from typing import Any


class UnavailableValuationProvider:
    source = "unavailable"
    is_demo_data = False
    is_full_taiwan = False

    def available(self) -> bool:
        return False

    def load_transactions(self) -> tuple[dict[str, Any], ...]:
        return ()

    def query_comparables(self, _request: dict[str, Any], limit: int = 50) -> list[dict[str, Any]]:
        return []

    def query_trend_rows(self, _request: dict[str, Any], limit: int = 10_000) -> list[dict[str, Any]]:
        return []

    def query_property_search_rows(self, _request: dict[str, Any], limit: int = 5_000) -> list[dict[str, Any]]:
        return []

    def data_status(self) -> dict[str, Any]:
        return {
            "active_source": self.source,
            "is_demo_data": False,
            "is_full_taiwan": False,
            "data_composition": "unavailable",
            "official_records_count": 0,
            "sample_records_count": 0,
            "coverage": {"cities": [], "districts": [], "roads_count": 0, "records_count": 0},
            "last_updated": None,
            "latest_import_status": None,
            "freshness_status": "unavailable",
            "freshness_reason_code": "provider_unavailable",
            "freshness_as_of": None,
            "latest_import_at": None,
            "latest_import_age_days": None,
            "newest_effective_period": None,
            "newest_effective_period_lag_months": None,
            "operator_attention_required": True,
            "freshness_user_message": "目前無法讀取官方 PLVR 資料新鮮度，請稍後再試。",
            "source_note": "官方估價資料目前無法使用。",
            "user_message": "估價資料目前無法使用，請稍後再試。",
        }
