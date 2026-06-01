from typing import Protocol

from app.data_ingestion.base import AdapterResult, SourceLog


class JudicialAdapter(Protocol):
    def search_cases(
        self,
        property_address: str,
        owner_name: str | None = None,
        keywords: list[str] | None = None,
    ) -> AdapterResult:
        """Search judicial case references related to a property or owner."""


class MockJudicialAdapter:
    source_name = "judicial_case_index"

    def search_cases(
        self,
        property_address: str,
        owner_name: str | None = None,
        keywords: list[str] | None = None,
    ) -> AdapterResult:
        query = {
            "property_address": property_address,
            "owner_name": owner_name,
            "keywords": keywords or [],
        }
        records = [
            {
                "case_id": "MOCK-JUD-2026-001",
                "case_type": "civil_property_dispute",
                "matched_keyword": (keywords or ["property"])[0],
                "summary": "Mock case reference for future judicial data integration.",
            }
        ]

        return AdapterResult(
            records=records,
            source_log=SourceLog(
                source_name=self.source_name,
                source_type="judicial_case",
                retrieval_mode="mock",
                query=query,
                status="success",
                record_count=len(records),
                notes="Mock judicial search result. No court system was queried.",
            ),
        )
