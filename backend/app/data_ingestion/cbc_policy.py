from typing import Protocol

from app.data_ingestion.base import AdapterResult, SourceLog


class CbcPolicyAdapter(Protocol):
    def fetch_credit_controls(
        self,
        region: str | None = None,
        property_use: str | None = None,
    ) -> AdapterResult:
        """Fetch central bank credit-control policy references."""


class MockCbcPolicyAdapter:
    source_name = "cbc_policy_rules"

    def fetch_credit_controls(
        self,
        region: str | None = None,
        property_use: str | None = None,
    ) -> AdapterResult:
        query = {
            "region": region,
            "property_use": property_use,
        }
        records = [
            {
                "policy_id": "MOCK-CBC-001",
                "region": region or "national",
                "property_use": property_use or "residential",
                "max_ltv_note": "Mock reference band only; not an official policy value.",
                "review_required": True,
            }
        ]

        return AdapterResult(
            records=records,
            source_log=SourceLog(
                source_name=self.source_name,
                source_type="credit_policy",
                retrieval_mode="mock",
                query=query,
                status="success",
                record_count=len(records),
                notes="Mock central-bank policy source. No external policy endpoint was called.",
            ),
        )
