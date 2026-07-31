"""Versioned official-tax metadata and offline rule-file validation.

The existing TX001-TX009 engine remains the compatibility screening engine.
This module does not invent rates and does not silently choose another
jurisdiction when a local rule is missing.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from services.official_data_registry import provider_registry


TX_RULE_IDS = tuple(f"TX{index:03d}" for index in range(1, 10))
TAX_RULE_STATUSES = frozenset({"available", "not_configured", "unavailable", "stale", "partial", "unknown", "error"})


def missing_tax_inputs(required_inputs: list[str] | tuple[str, ...], inputs: dict[str, object]) -> dict[str, object]:
    """Classify missing facts without inferring a tax result."""

    missing = [name for name in required_inputs if name not in inputs or inputs[name] in (None, "")]
    return {"status": "missing_input" if missing else "inputs_complete", "missing_inputs": missing}


@dataclass(frozen=True)
class OfficialTaxRule:
    rule_id: str
    tax_type: str
    jurisdiction: str
    official_code: str | None
    rule_version: str
    effective_from: str | None
    effective_to: str | None
    legal_basis: str
    official_source_url: str
    official_agency: str
    rate_type: str
    rate_value_or_band: str | float | None
    conditions: tuple[str, ...]
    required_inputs: tuple[str, ...]
    source_fetched_at: str | None
    freshness_status: str
    limitation: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def compatibility_rule_catalog() -> list[dict[str, object]]:
    """Describe stable product rule IDs without claiming official rates."""

    source = provider_registry("tax")[0]
    return [
        OfficialTaxRule(
            rule_id=rule_id,
            tax_type="taxoracle_qualification_screening",
            jurisdiction="TW",
            official_code=None,
            rule_version="compatibility-screening-v1",
            effective_from=None,
            effective_to=None,
            legal_basis="需依個案適用之現行法規與主管機關審查",
            official_source_url=str(source["source_url"]),
            official_agency=str(source["agency"]),
            rate_type="not_applicable",
            rate_value_or_band=None,
            conditions=("既有 TaxOracle compatibility rule",),
            required_inputs=("case_input",),
            source_fetched_at=None,
            freshness_status="not_checked",
            limitation="TX code is a stable product identifier, not a government ruling or personal tax record.",
        ).to_dict()
        for rule_id in TX_RULE_IDS
    ]


def select_tax_rules(records: list[dict[str, Any]], jurisdiction: str, effective_on: str) -> dict[str, object]:
    """Select only exact jurisdiction and effective-date matches."""

    _parse_date(effective_on)
    matches = [
        record
        for record in records
        if record.get("jurisdiction") == jurisdiction and _date_in_range(effective_on, record.get("effective_from"), record.get("effective_to"))
    ]
    if not matches:
        return {"status": "jurisdiction_data_unavailable", "rules": [], "message": "指定 jurisdiction 與有效日期沒有可追溯的官方規則。"}
    return {"status": "available", "rules": [dict(item) for item in matches], "message": "已選用精確 jurisdiction 與有效日期的規則版本。"}


def build_tax_rule_trace(case_input: dict[str, object], *, jurisdiction: str | None = None, effective_on: str | None = None) -> dict[str, object]:
    """Build safe trace metadata around the unchanged TX001-TX009 result."""

    return {
        "rule_ids": list(TX_RULE_IDS),
        "rule_version": "compatibility-screening-v1",
        "jurisdiction": jurisdiction or "not_provided",
        "effective_date": effective_on,
        "used_inputs": sorted(str(key) for key in case_input if key not in {"client_name"}),
        "missing_inputs": [] if case_input else ["case_input"],
        "source_provider_id": "mof_house_tax_law",
        "source_name": "財政部主管法規共用系統",
        "source_status": "not_checked",
        "calculation_kind": "preliminary_screening",
        "limitation": "結果不是官方核定、稅單、最終法律意見，也不表示存取個人稅務紀錄。",
    }


def validate_tax_rule_snapshot(payload: object) -> dict[str, object]:
    """Validate a versioned JSON rule snapshot without applying it."""

    records = payload.get("rules") if isinstance(payload, dict) else payload
    errors: list[str] = []
    if not isinstance(records, list):
        return {"valid": False, "errors": ["rules_missing"], "rule_count": 0, "rejected_count": 0}
    seen: set[tuple[object, object, object]] = set()
    accepted = 0
    rejected = 0
    required = {"rule_id", "tax_type", "jurisdiction", "rule_version", "effective_from", "effective_to", "legal_basis", "official_source_url", "official_agency", "rate_type", "rate_value_or_band", "conditions", "required_inputs", "limitation"}
    for record in records:
        if not isinstance(record, dict) or not required.issubset(record):
            rejected += 1
            continue
        try:
            if record["effective_from"]:
                _parse_date(str(record["effective_from"]))
            if record["effective_to"]:
                _parse_date(str(record["effective_to"]))
            if record["effective_from"] and record["effective_to"] and str(record["effective_from"]) > str(record["effective_to"]):
                raise ValueError("date_range")
        except ValueError:
            rejected += 1
            continue
        key = (record["rule_id"], record["jurisdiction"], record["rule_version"])
        if key in seen:
            rejected += 1
            continue
        seen.add(key)
        accepted += 1
    if not records:
        errors.append("no_rules")
    if rejected:
        errors.append("invalid_or_duplicate_rules")
    return {"valid": not errors, "errors": errors, "rule_count": accepted, "rejected_count": rejected}


def ingest_tax_rule_snapshot(path: str | Path, *, dry_run: bool = True) -> dict[str, object]:
    raw = Path(path).read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    validation = validate_tax_rule_snapshot(payload)
    return {
        "status": "validated" if validation["valid"] else "rejected",
        "dry_run": dry_run,
        "source_checksum_sha256": hashlib.sha256(raw).hexdigest(),
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "rule_count": validation["rule_count"],
        "rejected_count": validation["rejected_count"],
        "validation_errors": validation["errors"],
        "mutation": "none",
    }


def tax_source_status() -> dict[str, object]:
    return {
        "status": "not_configured",
        "source_status": "not_checked",
        "rules": compatibility_rule_catalog(),
        "message": "尚未載入具有效日期與 jurisdiction 的官方機器可讀規則；不套用替代稅率。",
        "calculation_boundary": "preliminary_screening_only",
    }


def _parse_date(value: str) -> date:
    return date.fromisoformat(value)


def _date_in_range(value: str, start: object, end: object) -> bool:
    try:
        current = _parse_date(value)
        return (not start or current >= _parse_date(str(start))) and (not end or current <= _parse_date(str(end)))
    except (TypeError, ValueError):
        return False
