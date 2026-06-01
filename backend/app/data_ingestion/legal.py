from typing import Protocol

from app.data_ingestion.base import AdapterResult, SourceLog


class LegalAdapter(Protocol):
    def fetch_legal_references(
        self,
        topic: str,
        jurisdiction: str = "TW",
    ) -> AdapterResult:
        """Fetch legal rule references for a topic."""


class MockLegalAdapter:
    source_name = "legal_reference_library"

    def fetch_legal_references(
        self,
        topic: str,
        jurisdiction: str = "TW",
    ) -> AdapterResult:
        query = {
            "topic": topic,
            "jurisdiction": jurisdiction,
        }
        records = [
            {
                "reference_id": "MOCK-LEGAL-001",
                "topic": topic,
                "jurisdiction": jurisdiction,
                "title": "Mock legal reference placeholder",
                "usage_note": "For report source tracking only until a verified legal source is wired.",
            }
        ]

        return AdapterResult(
            records=records,
            source_log=SourceLog(
                source_name=self.source_name,
                source_type="legal_reference",
                retrieval_mode="mock",
                query=query,
                status="success",
                record_count=len(records),
                notes="Mock legal reference. Replace with approved legal database or CSV ETL.",
            ),
        )
