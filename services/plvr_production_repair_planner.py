"""Pure planning primitives for a read-only PLVR production repair dry run."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any, Iterable, Mapping


class RepairClassification(StrEnum):
    SAFE_AUTOMATIC_REPAIR = "SAFE_AUTOMATIC_REPAIR"
    REPAIR_WITH_SUPPORTING_EVIDENCE = "REPAIR_WITH_SUPPORTING_EVIDENCE"
    AMBIGUOUS = "AMBIGUOUS"
    SOURCE_CORRUPT_OR_UNRESOLVED = "SOURCE_CORRUPT_OR_UNRESOLVED"


class CollisionClassification(StrEnum):
    NO_COLLISION = "NO_COLLISION"
    EXACT_DUPLICATE_AFTER_REPAIR = "EXACT_DUPLICATE_AFTER_REPAIR"
    NATURAL_KEY_COLLISION = "NATURAL_KEY_COLLISION"
    AMBIGUOUS_COLLISION = "AMBIGUOUS_COLLISION"


class FutureClassification(StrEnum):
    VALID_SOURCE_BUT_WRONG_PRODUCT_SEMANTIC = "VALID_SOURCE_BUT_WRONG_PRODUCT_SEMANTIC"
    SOURCE_DATE_PARSE_ERROR = "SOURCE_DATE_PARSE_ERROR"
    SOURCE_DATA_ANOMALY = "SOURCE_DATA_ANOMALY"
    IMPORT_ERROR = "IMPORT_ERROR"
    UNRESOLVED = "UNRESOLVED"


@dataclass(frozen=True)
class GeographyEvidence:
    row_id: int | str
    source: str
    dedupe_key: str
    current_city: str
    current_district: str
    period: str
    district_owner_counties: tuple[str, ...] = ()
    canonical_district: str = ""
    source_artifact_city: str = ""
    import_run_city: str = ""
    raw_city: str = ""
    address_city: str = ""
    source_artifact_id: str = ""
    import_run_id: str = ""
    row_fingerprint: str = ""
    source_transaction_identifier_preserved: bool = False


@dataclass(frozen=True)
class GeographyDecision:
    classification: RepairClassification
    proposed_city: str
    proposed_district: str
    confidence: str
    evidence_codes: tuple[str, ...]
    reason_code: str


@dataclass(frozen=True)
class CollisionEvidence:
    exact_match_count: int = 0
    natural_key_match_count: int = 0
    proposed_dedupe_key_match_count: int = 0
    contradictory_match_count: int = 0


@dataclass(frozen=True)
class FutureEvidence:
    source_artifact_verified: bool = False
    raw_transaction_period: str = ""
    normalized_period: str = ""
    transaction_type: str = ""
    presale_semantic_supported: bool = False
    date_parse_mismatch: bool = False
    importer_override_detected: bool = False
    source_marks_row_anomalous: bool = False
    aggregate_source_transaction_count: int | None = None
    aggregate_record_count: int | None = None


@dataclass(frozen=True)
class ReconciliationInput:
    baseline_rows: int
    baseline_valid_rows: int
    baseline_invalid_rows: int
    safe_automatic: int
    supporting_evidence: int
    ambiguous: int
    unresolved: int
    future_rows: int
    affected_scopes: int
    aggregate_rows_before: int
    aggregate_rows_after_without_deduplication: int


def classify_geography_evidence(evidence: GeographyEvidence) -> GeographyDecision:
    """Classify one invalid geography row without guessing a target."""

    owners = tuple(dict.fromkeys(_clean_text(value) for value in evidence.district_owner_counties if value))
    authoritative = {
        code: _clean_text(value)
        for code, value in (
            ("source_artifact_city", evidence.source_artifact_city),
            ("import_run_city", evidence.import_run_city),
            ("raw_city", evidence.raw_city),
        )
        if _clean_text(value)
    }
    address_city = _clean_text(evidence.address_city)
    target_district = _clean_text(evidence.canonical_district) or evidence.current_district
    evidence_codes = tuple(authoritative) + (("address_city",) if address_city else ())
    authoritative_targets = set(authoritative.values())

    if len(authoritative_targets) > 1:
        return _ambiguous(evidence, evidence_codes, "authoritative_lineage_conflict")

    if authoritative_targets:
        target = next(iter(authoritative_targets))
        if target not in owners:
            return _ambiguous(evidence, evidence_codes, "lineage_conflicts_with_canonical_district")
        if address_city and address_city != target:
            return _ambiguous(evidence, evidence_codes, "address_conflicts_with_lineage")
        codes = evidence_codes + ("canonical_district_agrees",)
        return GeographyDecision(
            RepairClassification.SAFE_AUTOMATIC_REPAIR,
            target,
            target_district,
            "high",
            codes,
            "authoritative_lineage_and_canonical_region_agree",
        )

    if len(owners) == 1 and address_city == owners[0]:
        return GeographyDecision(
            RepairClassification.REPAIR_WITH_SUPPORTING_EVIDENCE,
            owners[0],
            target_district,
            "medium",
            ("address_city", "canonical_district_unique"),
            "address_and_unique_district_owner_agree_without_lineage",
        )

    if address_city or len(owners) > 1:
        codes = evidence_codes + (("canonical_district_shared",) if len(owners) > 1 else ())
        return _ambiguous(evidence, codes, "supporting_evidence_is_not_deterministic")

    return GeographyDecision(
        RepairClassification.SOURCE_CORRUPT_OR_UNRESOLVED,
        "",
        "",
        "none",
        (("canonical_district_unique_only",) if len(owners) == 1 else ("canonical_district_unrecognized",)),
        "authoritative_lineage_and_independent_support_are_missing",
    )


def classify_collision(evidence: CollisionEvidence) -> CollisionClassification:
    """Classify target identity overlap before any repair is attempted."""

    if evidence.contradictory_match_count or evidence.proposed_dedupe_key_match_count:
        return CollisionClassification.AMBIGUOUS_COLLISION
    if evidence.exact_match_count:
        return CollisionClassification.EXACT_DUPLICATE_AFTER_REPAIR
    if evidence.natural_key_match_count:
        return CollisionClassification.NATURAL_KEY_COLLISION
    return CollisionClassification.NO_COLLISION


def classify_future_evidence(evidence: FutureEvidence) -> FutureClassification:
    """Classify a future-period row without prescribing deletion."""

    if evidence.importer_override_detected:
        return FutureClassification.IMPORT_ERROR
    if evidence.date_parse_mismatch:
        return FutureClassification.SOURCE_DATE_PARSE_ERROR
    if evidence.source_marks_row_anomalous:
        return FutureClassification.SOURCE_DATA_ANOMALY
    if (
        evidence.source_artifact_verified
        and evidence.raw_transaction_period
        and evidence.raw_transaction_period == evidence.normalized_period
        and evidence.presale_semantic_supported
    ):
        return FutureClassification.VALID_SOURCE_BUT_WRONG_PRODUCT_SEMANTIC
    return FutureClassification.UNRESOLVED


def future_aggregate_lineage_matches(evidence: FutureEvidence) -> bool:
    """Return true only when the aggregate count is explicitly linked to source rows."""

    return (
        evidence.aggregate_source_transaction_count is not None
        and evidence.aggregate_record_count is not None
        and evidence.aggregate_source_transaction_count == evidence.aggregate_record_count
        and evidence.aggregate_record_count > 0
    )


def build_manifest_entry(
    evidence: GeographyEvidence,
    decision: GeographyDecision,
    collision: CollisionClassification,
) -> dict[str, Any]:
    """Build a privacy-bounded manifest row with opaque identifiers and hashes."""

    stable_seed = evidence.dedupe_key.strip() or str(evidence.row_id).strip()
    if not stable_seed:
        raise ValueError("a persisted primary key or dedupe key is required for a stable manifest identity")
    stable_identifier = _hash_payload({"source": evidence.source, "identity": stable_seed})
    before = {
        "stable_identifier": stable_identifier,
        "city": evidence.current_city,
        "district": evidence.current_district,
        "period": evidence.period,
        "row_fingerprint": evidence.row_fingerprint,
    }
    after = {
        **before,
        "city": decision.proposed_city or evidence.current_city,
        "district": decision.proposed_district or evidence.current_district,
    }
    lineage = [
        _hash_payload({"kind": kind, "identifier": value})
        for kind, value in (
            ("source_artifact", evidence.source_artifact_id),
            ("import_run", evidence.import_run_id),
        )
        if value
    ]
    return {
        "stable_transaction_identifier": stable_identifier,
        "current_city": evidence.current_city,
        "current_district": evidence.current_district,
        "proposed_city": decision.proposed_city,
        "proposed_district": decision.proposed_district,
        "repair_classification": decision.classification.value,
        "confidence": decision.confidence,
        "evidence_codes": list(decision.evidence_codes),
        "source_import_lineage_identifiers": lineage,
        "before_hash": _hash_payload(before),
        "proposed_after_hash": _hash_payload(after),
        "reason_code": decision.reason_code,
        "collision_classification": collision.value,
        "dedupe_regeneration_status": (
            "deterministic_source_identifier_available"
            if evidence.source_transaction_identifier_preserved
            else "requires_authoritative_source_identifier"
        ),
    }


def simulate_reconciliation(values: ReconciliationInput) -> dict[str, int]:
    """Calculate a no-write, no-deduplication before/after reconciliation."""

    proposed = values.safe_automatic + values.supporting_evidence
    remaining_invalid = values.ambiguous + values.unresolved
    if values.baseline_invalid_rows != proposed + remaining_invalid:
        raise ValueError("repair classification counts do not reconcile with baseline invalid rows")
    return {
        "transaction_rows_before": values.baseline_rows,
        "transaction_rows_after": values.baseline_rows,
        "valid_rows_before": values.baseline_valid_rows,
        "valid_rows_after_without_deduplication": values.baseline_valid_rows + proposed,
        "invalid_rows_before": values.baseline_invalid_rows,
        "remaining_invalid_rows": remaining_invalid,
        "future_rows_after": values.future_rows,
        "affected_scopes": values.affected_scopes,
        "aggregate_rows_before": values.aggregate_rows_before,
        "aggregate_rows_after_without_deduplication": values.aggregate_rows_after_without_deduplication,
    }


def summary_checksum(payload: Mapping[str, Any]) -> str:
    """Hash a summary after excluding its own checksum field."""

    clean = {key: value for key, value in payload.items() if key != "summary_checksum"}
    return _hash_payload(clean)


def manifest_checksum(entries: Iterable[Mapping[str, Any]]) -> str:
    """Hash manifest rows in stable transaction identifier order."""

    ordered = sorted(entries, key=lambda row: str(row.get("stable_transaction_identifier", "")))
    return _hash_payload(ordered)


def dataclass_payload(value: Any) -> dict[str, Any]:
    """Convert a planner dataclass to a JSON-safe mapping."""

    return asdict(value)


def _ambiguous(
    evidence: GeographyEvidence,
    evidence_codes: tuple[str, ...],
    reason_code: str,
) -> GeographyDecision:
    return GeographyDecision(
        RepairClassification.AMBIGUOUS,
        "",
        "",
        "low",
        evidence_codes,
        reason_code,
    )


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _hash_payload(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
