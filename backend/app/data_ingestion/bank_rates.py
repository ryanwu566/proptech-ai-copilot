from typing import Protocol

from app.data_ingestion.base import AdapterResult, SourceLog


class BankRatesAdapter(Protocol):
    def fetch_mortgage_rates(
        self,
        bank_code: str | None = None,
        product_type: str = "mortgage",
    ) -> AdapterResult:
        """Fetch bank mortgage-rate references."""


class MockBankRatesAdapter:
    source_name = "bank_rate_sheet"

    def fetch_mortgage_rates(
        self,
        bank_code: str | None = None,
        product_type: str = "mortgage",
    ) -> AdapterResult:
        query = {
            "bank_code": bank_code,
            "product_type": product_type,
        }
        records = [
            {
                "bank_code": bank_code or "MOCKBANK",
                "product_type": product_type,
                "base_rate": "2.25%",
                "stress_rate": "4.00%",
                "effective_month": "2026-05",
            }
        ]

        return AdapterResult(
            records=records,
            source_log=SourceLog(
                source_name=self.source_name,
                source_type="bank_rate",
                retrieval_mode="mock",
                query=query,
                status="success",
                record_count=len(records),
                notes="Mock mortgage-rate sheet. Replace with bank API or CSV ETL adapter later.",
            ),
        )
