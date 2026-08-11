"""Tests for the SELECT-only PLVR production repair planner."""

from __future__ import annotations

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from types import ModuleType

import pytest

from scripts import plan_plvr_production_repair as script
from services.plvr_import_service import OFFICIAL_SOURCE
from services.plvr_production_repair_planner import (
    CollisionClassification,
    CollisionEvidence,
    FutureClassification,
    FutureEvidence,
    GeographyEvidence,
    ReconciliationInput,
    RepairClassification,
    build_manifest_entry,
    classify_collision,
    classify_future_evidence,
    classify_geography_evidence,
    future_aggregate_lineage_matches,
    manifest_checksum,
    simulate_reconciliation,
    summary_checksum,
)


ROOT = Path(__file__).resolve().parents[1]


def evidence(**overrides: object) -> GeographyEvidence:
    values: dict[str, object] = {
        "row_id": 7,
        "source": OFFICIAL_SOURCE,
        "dedupe_key": "opaque-dedupe-key",
        "current_city": "台南市",
        "current_district": "中壢區",
        "period": "2025-02",
        "district_owner_counties": ("桃園市",),
        "canonical_district": "中壢區",
        "row_fingerprint": "opaque-row-fingerprint",
    }
    values.update(overrides)
    return GeographyEvidence(**values)


def transaction(**overrides: object) -> dict[str, object]:
    values: dict[str, object] = {
        "id": 1,
        "transaction_period": "2025-02",
        "city": "桃園市",
        "district": "中壢區",
        "road": "中正路",
        "address_text": "桃園市中壢區中正路1號",
        "building_type": "住宅大樓",
        "area_ping": 20,
        "building_age_years": 5,
        "floor": 3,
        "total_floor": 12,
        "unit_price_per_ping": 45,
        "total_price": 900,
        "source": OFFICIAL_SOURCE,
        "raw_note": "",
        "dedupe_key": "dedupe-1",
        "imported_at": datetime(2026, 6, 7),
    }
    values.update(overrides)
    return values


def test_authoritative_filename_and_canonical_district_are_safe() -> None:
    result = classify_geography_evidence(evidence(source_artifact_city="桃園市"))

    assert result.classification == RepairClassification.SAFE_AUTOMATIC_REPAIR
    assert result.proposed_city == "桃園市"
    assert result.confidence == "high"


def test_source_lineage_and_canonical_district_conflict_is_ambiguous() -> None:
    result = classify_geography_evidence(evidence(source_artifact_city="高雄市"))

    assert result.classification == RepairClassification.AMBIGUOUS
    assert result.proposed_city == ""


def test_unique_district_without_independent_evidence_is_not_automatic() -> None:
    result = classify_geography_evidence(evidence())

    assert result.classification == RepairClassification.SOURCE_CORRUPT_OR_UNRESOLVED
    assert "canonical_district_unique_only" in result.evidence_codes


def test_raw_city_and_source_filename_agreement_has_high_confidence() -> None:
    result = classify_geography_evidence(
        evidence(source_artifact_city="桃園市", raw_city="桃園市")
    )

    assert result.classification == RepairClassification.SAFE_AUTOMATIC_REPAIR
    assert result.confidence == "high"


def test_source_filename_and_address_agreement_has_high_confidence() -> None:
    result = classify_geography_evidence(
        evidence(source_artifact_city="桃園市", address_city="桃園市")
    )

    assert result.classification == RepairClassification.SAFE_AUTOMATIC_REPAIR
    assert {"source_artifact_city", "address_city"} <= set(result.evidence_codes)


def test_conflicting_address_makes_authoritative_candidate_ambiguous() -> None:
    result = classify_geography_evidence(
        evidence(source_artifact_city="桃園市", address_city="高雄市")
    )

    assert result.classification == RepairClassification.AMBIGUOUS
    assert result.reason_code == "address_conflicts_with_lineage"


def test_address_and_unique_district_are_supporting_evidence_only() -> None:
    result = classify_geography_evidence(evidence(address_city="桃園市"))

    assert result.classification == RepairClassification.REPAIR_WITH_SUPPORTING_EVIDENCE
    assert result.confidence == "medium"


def test_shared_district_with_address_only_is_ambiguous() -> None:
    result = classify_geography_evidence(
        evidence(
            current_district="東區",
            district_owner_counties=("新竹市", "嘉義市"),
            address_city="新竹市",
        )
    )

    assert result.classification == RepairClassification.AMBIGUOUS


def test_no_target_overlap_is_no_collision() -> None:
    assert classify_collision(CollisionEvidence()) == CollisionClassification.NO_COLLISION


def test_exact_duplicate_after_repair_is_classified() -> None:
    result = classify_collision(CollisionEvidence(exact_match_count=1, natural_key_match_count=1))

    assert result == CollisionClassification.EXACT_DUPLICATE_AFTER_REPAIR


def test_natural_key_collision_is_classified() -> None:
    result = classify_collision(CollisionEvidence(natural_key_match_count=1))

    assert result == CollisionClassification.NATURAL_KEY_COLLISION


def test_proposed_dedupe_key_collision_is_detected_before_apply() -> None:
    result = classify_collision(CollisionEvidence(proposed_dedupe_key_match_count=1))

    assert result == CollisionClassification.AMBIGUOUS_COLLISION


def test_future_classification_never_prescribes_deletion() -> None:
    unresolved = classify_future_evidence(FutureEvidence(normalized_period="2026-10"))
    verified = classify_future_evidence(
        FutureEvidence(
            source_artifact_verified=True,
            raw_transaction_period="2026-10",
            normalized_period="2026-10",
            transaction_type="presale",
            presale_semantic_supported=True,
        )
    )

    assert unresolved == FutureClassification.UNRESOLVED
    assert verified == FutureClassification.VALID_SOURCE_BUT_WRONG_PRODUCT_SEMANTIC
    assert "delete" not in unresolved.value.lower()
    assert "delete" not in verified.value.lower()


def test_future_aggregate_requires_explicit_count_lineage() -> None:
    assert future_aggregate_lineage_matches(
        FutureEvidence(aggregate_source_transaction_count=1, aggregate_record_count=1)
    )
    assert not future_aggregate_lineage_matches(
        FutureEvidence(aggregate_source_transaction_count=1, aggregate_record_count=2)
    )


def test_manifest_uses_opaque_identity_and_does_not_emit_raw_address() -> None:
    item = evidence(
        address_city="桃園市",
        source_artifact_id="private-artifact-id",
        import_run_id="private-run-id",
    )
    decision = classify_geography_evidence(item)
    manifest = build_manifest_entry(item, decision, CollisionClassification.NO_COLLISION)
    encoded = json.dumps(manifest, ensure_ascii=False)

    assert manifest["stable_transaction_identifier"] != item.dedupe_key
    assert "private-artifact-id" not in encoded
    assert "private-run-id" not in encoded
    assert "中正路1號" not in encoded
    assert len(manifest["before_hash"]) == 64
    assert len(manifest["proposed_after_hash"]) == 64


def test_manifest_checksum_is_order_independent() -> None:
    rows = [
        {"stable_transaction_identifier": "b", "value": 2},
        {"stable_transaction_identifier": "a", "value": 1},
    ]

    assert manifest_checksum(rows) == manifest_checksum(list(reversed(rows)))


def test_manifest_refuses_to_invent_identity_without_primary_or_dedupe_key() -> None:
    item = evidence(row_id="", dedupe_key="", address_city="桃園市")
    decision = classify_geography_evidence(item)

    with pytest.raises(ValueError, match="persisted primary key or dedupe key"):
        build_manifest_entry(item, decision, CollisionClassification.NO_COLLISION)


def test_reconciliation_preserves_total_and_excludes_unresolved() -> None:
    result = simulate_reconciliation(
        ReconciliationInput(
            baseline_rows=100,
            baseline_valid_rows=60,
            baseline_invalid_rows=40,
            safe_automatic=10,
            supporting_evidence=20,
            ambiguous=4,
            unresolved=6,
            future_rows=1,
            affected_scopes=8,
            aggregate_rows_before=12,
            aggregate_rows_after_without_deduplication=15,
        )
    )

    assert result["transaction_rows_after"] == 100
    assert result["valid_rows_after_without_deduplication"] == 90
    assert result["remaining_invalid_rows"] == 10


def test_reconciliation_rejects_non_reconciling_counts() -> None:
    with pytest.raises(ValueError, match="do not reconcile"):
        simulate_reconciliation(
            ReconciliationInput(100, 60, 40, 10, 20, 4, 5, 1, 8, 12, 15)
        )


def test_all_executable_database_queries_are_select_only() -> None:
    forbidden = re.compile(r"\b(update|delete|insert|truncate|drop|alter|create|call)\b", re.IGNORECASE)

    for query in script.EXECUTABLE_QUERIES:
        assert query.lstrip().lower().startswith("select")
        assert forbidden.search(query) is None


def test_cli_exposes_no_apply_or_database_write_switch() -> None:
    destinations = {action.dest for action in script.build_parser()._actions}

    assert not destinations & {"apply", "write", "update", "delete", "confirm_update"}


def test_postgres_connection_enforces_default_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}
    fake_psycopg = ModuleType("psycopg")
    fake_rows = ModuleType("psycopg.rows")
    fake_rows.dict_row = object()

    def connect(database_url: str, **kwargs: object) -> object:
        captured.update({"database_url": database_url, **kwargs})
        return object()

    fake_psycopg.connect = connect
    monkeypatch.setitem(sys.modules, "psycopg", fake_psycopg)
    monkeypatch.setitem(sys.modules, "psycopg.rows", fake_rows)

    script.ReadOnlyPostgresRepository("postgresql://redacted")._connect()

    assert "default_transaction_read_only=on" in str(captured["options"])
    assert captured["database_url"] == "postgresql://redacted"


class FakeRepository:
    def iter_transactions(self):
        existing = transaction()
        repair = transaction(id=2, city="台南市", dedupe_key="dedupe-2")
        unresolved = transaction(
            id=3,
            city="台南市",
            district="不存在區",
            address_text="不完整資料",
            dedupe_key="dedupe-3",
        )
        future = transaction(
            id=4,
            transaction_period="2026-10",
            city="臺北市",
            district="南港區",
            address_text="臺北市南港區研究院路1號",
            dedupe_key="dedupe-4",
        )
        return iter((existing, repair, unresolved, future))

    def aggregate_stats(self, _as_of_period: str) -> dict[str, int]:
        return {"aggregate_rows": 3, "future_aggregate_rows": 1}

    def future_aggregates(self, _as_of_period: str) -> list[dict[str, object]]:
        return [
            {
                "county": "臺北市",
                "district": "南港區",
                "period": "2026-10",
                "transaction_count": 1,
                "record_count": 1,
            }
        ]


def test_end_to_end_fake_plan_is_read_only_and_reconciles() -> None:
    summary, manifest = script.build_production_repair_plan(
        FakeRepository(), as_of_period="2026-08", top=10
    )

    assert summary["planner_mode"] == "select_only_dry_run"
    assert summary["baseline"] == {
        "official_rows": 4,
        "canonical_valid_rows": 2,
        "canonical_invalid_rows": 2,
        "future_rows": 1,
        "aggregate_rows": 3,
        "future_aggregate_rows": 1,
    }
    assert summary["geography_classification"] == {
        "REPAIR_WITH_SUPPORTING_EVIDENCE": 1,
        "SOURCE_CORRUPT_OR_UNRESOLVED": 1,
    }
    assert summary["collision_classification"]["EXACT_DUPLICATE_AFTER_REPAIR"] == 1
    assert summary["future"]["classification"] == "UNRESOLVED"
    assert summary["future"]["aggregate_lineage_matches"] is True
    assert summary["reconciliation"]["remaining_invalid_rows"] == 1
    assert len(manifest) == 2
    assert summary["summary_checksum"] == summary_checksum(summary)


def test_missing_runtime_configuration_fails_closed_without_connection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)

    assert script.main([]) == 2
    assert json.loads(capsys.readouterr().out)["reason_code"] == "database_runtime_not_configured"


def test_committed_summary_is_aggregate_only_and_checksum_verified() -> None:
    payload = json.loads(
        (ROOT / "docs" / "plvr-production-repair-summary-v1.json").read_text(encoding="utf-8")
    )
    encoded = json.dumps(payload, ensure_ascii=False).lower()

    assert payload["baseline"]["official_rows"] == 451_672
    assert payload["geography_classification"]["SAFE_AUTOMATIC_REPAIR"] == 0
    assert payload["manifest"]["committed_row_level_manifest"] is False
    assert payload["summary_checksum"] == summary_checksum(payload)
    assert "address_text" not in encoded
    assert "database_url" not in encoded


def test_repair_document_defines_rollback_quarantine_and_not_ready_gate() -> None:
    document = (ROOT / "docs" / "plvr-production-repair-plan.md").read_text(encoding="utf-8")

    assert "snapshot and rollback specification" in document
    assert "Quarantine options" in document
    assert "NOT_READY_FOR_PHASE_2B2" in document
    assert "No quarantine schema is created" in document
