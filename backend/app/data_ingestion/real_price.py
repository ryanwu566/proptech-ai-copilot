from typing import Protocol

from app.data_ingestion.base import AdapterResult, SourceLog


class RealPriceAdapter(Protocol):
    def fetch_transactions(
        self,
        city: str,
        district: str | None = None,
        property_type: str | None = None,
    ) -> AdapterResult:
        """Fetch real-price transaction samples."""


class MockRealPriceAdapter:
    source_name = "real_price_registry"

    def fetch_transactions(
        self,
        city: str,
        district: str | None = None,
        property_type: str | None = None,
    ) -> AdapterResult:
        query = {
            "city": city,
            "district": district,
            "property_type": property_type,
        }
        records = [
            {
                "city": city,
                "district": district or "sample-district",
                "property_type": property_type or "residential",
                "unit_price_per_ping": 820000,
                "total_price": 18500000,
                "transaction_month": "2026-04",
            },
            {
                "city": city,
                "district": district or "sample-district",
                "property_type": property_type or "residential",
                "unit_price_per_ping": 790000,
                "total_price": 17200000,
                "transaction_month": "2026-03",
            },
        ]

        return AdapterResult(
            records=records,
            source_log=SourceLog(
                source_name=self.source_name,
                source_type="transaction_price",
                retrieval_mode="mock",
                query=query,
                status="success",
                record_count=len(records),
                notes="Mock real-price records. Replace with API or CSV ETL implementation later.",
            ),
        )
