"""Exact-version allowlist parsing for explicit SavedCase v1 copy imports."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Mapping

from services.vnext.errors import VNextError


LEGACY_FORMAT = "saved_case_v1"
LEGACY_SCHEMA_VERSION = 1
LEGACY_IMPORT_MODE = "copy"
MAX_LEGACY_PAYLOAD_BYTES = 65_536

_WORKFLOW_STEPS = frozenset(
    {"property_search", "valuation", "affordability", "location", "risk", "report", "tax"}
)
_TERRAIN_STATES = frozenset(
    {"available", "partial", "limited", "unknown", "not_assessed", "unavailable", "error", "no_match"}
)
_RAW_KEYS = frozenset(
    {
        "access_token", "api_key", "browser_history", "comparables", "coordinates",
        "credential", "credentials", "geometry", "hazard_geometries", "lat", "latitude",
        "lng", "longitude", "matched_transactions", "nearest_pois", "private_storage_path",
        "provider_payload", "raw", "raw_error", "raw_payload", "resolved_location",
        "secret", "source_url", "stack_trace", "storage_path", "tile_url_template", "token",
        "traceback",
    }
)
_FACT_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{2,119}$")

_ACCEPTED_ORDER = (
    "title", "legacy_timestamps", "workflow_snapshot", "address_input", "property_inputs",
    "property_search_summary", "valuation_evidence_summary", "valuation_summary",
    "trend_snapshot", "market_snapshot", "loan_artifact", "holding_cost_artifact",
    "location_summary", "terrain_reference", "risk_presentation", "tax_artifact",
    "report_activity", "journey_context",
)
_DROPPED_ORDER = (
    "legacy_client_payload_id", "unsupported_fields", "raw_provider_payload",
    "exact_coordinates", "raw_comparable_rows", "private_storage_paths",
    "corrupt_optional_section", "oversized_fields", "provider_internals",
)
_WARNING_ORDER = (
    "address_requires_resolution", "missing_address", "missing_valuation",
    "unsupported_fields_dropped", "raw_provider_fields_dropped",
    "exact_coordinates_dropped", "raw_comparable_rows_dropped",
    "private_storage_paths_dropped", "corrupt_optional_section_dropped",
    "oversized_fields_dropped", "legacy_timestamps_inconsistent",
    "legacy_snapshot_requires_revalidation", "terrain_reference_only",
    "terrain_safe_conclusion_blocked", "risk_presentation_not_authoritative",
)


@dataclass(frozen=True)
class LegacyEvidenceDraft:
    fact_type: str
    value: dict[str, object] | None
    value_schema: str
    evidence_status: str
    coverage_status: str
    quality_status: str
    limitations: tuple[str, ...]


@dataclass(frozen=True)
class ParsedLegacyCase:
    title: str
    client_created_at: datetime | None
    client_updated_at: datetime | None
    accepted_field_classes: tuple[str, ...]
    dropped_field_classes: tuple[str, ...]
    warnings: tuple[str, ...]
    evidence: tuple[LegacyEvidenceDraft, ...]


class _Collector:
    def __init__(self) -> None:
        self.accepted: set[str] = set()
        self.dropped: set[str] = set()
        self.warnings: set[str] = set()
        self.evidence: list[LegacyEvidenceDraft] = []

    def drop(self, field_class: str, warning: str) -> None:
        self.dropped.add(field_class)
        self.warnings.add(warning)

    def add(
        self,
        field_class: str,
        fact_type: str,
        value: dict[str, object] | None,
        value_schema: str,
        *,
        status: str = "unverified",
        coverage: str = "unknown",
        quality: str = "not_checked",
        limitations: tuple[str, ...] = ("legacy_unverified",),
    ) -> None:
        if not _FACT_TYPE.fullmatch(fact_type):
            raise VNextError.validation_failed()
        self.accepted.add(field_class)
        self.evidence.append(
            LegacyEvidenceDraft(
                fact_type=fact_type,
                value=value,
                value_schema=value_schema,
                evidence_status=status,
                coverage_status=coverage,
                quality_status=quality,
                limitations=limitations,
            )
        )


Rule = Callable[[object], tuple[object | None, str | None]]


def _text(maximum: int) -> Rule:
    def parse(value: object) -> tuple[object | None, str | None]:
        if not isinstance(value, str) or "\x00" in value or not value.strip():
            return None, "invalid"
        selected = value.strip()
        return (None, "oversized") if len(selected) > maximum else (selected, None)

    return parse


def _number(minimum: float, maximum: float, *, nullable: bool = False) -> Rule:
    def parse(value: object) -> tuple[object | None, str | None]:
        if value is None and nullable:
            return None, None
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None, "invalid"
        selected = float(value)
        if not math.isfinite(selected) or not minimum <= selected <= maximum:
            return None, "invalid"
        return value, None

    return parse


def _enum(*values: str) -> Rule:
    allowed = frozenset(values)
    return lambda value: (value, None) if isinstance(value, str) and value in allowed else (None, "invalid")


def _boolean(value: object) -> tuple[object | None, str | None]:
    return (value, None) if isinstance(value, bool) else (None, "invalid")


def _strings(maximum_items: int, maximum_length: int) -> Rule:
    def parse(value: object) -> tuple[object | None, str | None]:
        if not isinstance(value, list):
            return None, "invalid"
        selected: list[str] = []
        issue: str | None = "oversized" if len(value) > maximum_items else None
        for item in value[:maximum_items]:
            parsed, item_issue = _text(maximum_length)(item)
            if item_issue:
                return None, item_issue
            selected.append(str(parsed))
        return selected, issue

    return parse


def _select(value: object, rules: Mapping[str, Rule], collector: _Collector) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
        return None
    if set(value) - set(rules):
        collector.drop("unsupported_fields", "unsupported_fields_dropped")
    selected: dict[str, object] = {}
    for key, rule in rules.items():
        if key not in value:
            continue
        parsed, issue = rule(value[key])
        if issue:
            collector.drop(
                "oversized_fields" if issue == "oversized" else "corrupt_optional_section",
                "oversized_fields_dropped" if issue == "oversized" else "corrupt_optional_section_dropped",
            )
        else:
            selected[key] = parsed
    return selected or None


def _timestamp(value: object, collector: _Collector) -> datetime | None:
    if not isinstance(value, str) or len(value) > 64:
        collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
        return None
    try:
        selected = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
        return None
    if selected.tzinfo is None:
        collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
        return None
    return selected


def _scan_exclusions(payload: Mapping[str, object], collector: _Collector) -> None:
    stack: list[tuple[object, int]] = [(payload, 0)]
    found: set[str] = set()
    while stack:
        value, depth = stack.pop()
        if depth > 16:
            collector.drop("unsupported_fields", "unsupported_fields_dropped")
            continue
        if isinstance(value, Mapping):
            for key, child in value.items():
                normalized = str(key).lower()
                if normalized in _RAW_KEYS:
                    found.add(normalized)
                stack.append((child, depth + 1))
        elif isinstance(value, list):
            stack.extend((item, depth + 1) for item in value[:256])
    if found:
        collector.drop("raw_provider_payload", "raw_provider_fields_dropped")
    if found & {"coordinates", "lat", "latitude", "lng", "longitude"}:
        collector.drop("exact_coordinates", "exact_coordinates_dropped")
    if found & {"comparables", "matched_transactions"}:
        collector.drop("raw_comparable_rows", "raw_comparable_rows_dropped")
    if found & {"private_storage_path", "storage_path"}:
        collector.drop("private_storage_paths", "private_storage_paths_dropped")


def _add_section(
    data: Mapping[str, object],
    key: str,
    collector: _Collector,
    rules: Mapping[str, Rule],
    field_class: str,
    fact_type: str,
    schema: str,
    *,
    status: str = "unverified",
    coverage: str = "unknown",
    quality: str = "not_checked",
    limitations: tuple[str, ...] = ("legacy_unverified",),
) -> None:
    if key not in data:
        return
    selected = _select(data[key], rules, collector)
    if selected:
        collector.add(
            field_class, fact_type, selected, schema,
            status=status, coverage=coverage, quality=quality, limitations=limitations,
        )


def _add_terrain(data: Mapping[str, object], collector: _Collector) -> None:
    if "terrainReference" in data:
        raw = data["terrainReference"]
        if not isinstance(raw, Mapping) or raw.get("schema_version") != 1 or raw.get("kind") != "terrain_reference":
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
            return
        state = raw.get("status")
        if not isinstance(state, str) or state not in _TERRAIN_STATES:
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
            return
        value: dict[str, object] = {
            "schema_version": 1, "kind": "terrain_reference", "legacy_state": state,
            "conclusion": "reference_only",
        }
        for key in ("summary", "notice"):
            if key in raw:
                selected, issue = _text(1000)(raw[key])
                if issue:
                    collector.drop(
                        "oversized_fields" if issue == "oversized" else "corrupt_optional_section",
                        "oversized_fields_dropped" if issue == "oversized" else "corrupt_optional_section_dropped",
                    )
                else:
                    value[key] = selected
        layers: list[dict[str, object]] = []
        raw_layers = raw.get("layers")
        if isinstance(raw_layers, list):
            for raw_layer in raw_layers[:12]:
                layer = _select(
                    raw_layer,
                    {
                        "layer_id": _text(80), "display_name": _text(160),
                        "state": _enum(*sorted(_TERRAIN_STATES)), "source_name": _text(160),
                        "source_agency": _text(160), "data_updated_at": _text(64),
                        "data_version": _text(120),
                        "coverage_status": _enum("covered", "not_covered", "unknown"),
                        "caveat": _text(1000),
                    },
                    collector,
                )
                if layer:
                    layer["conclusion"] = "reference_only"
                    layers.append(layer)
            if len(raw_layers) > 12:
                collector.drop("oversized_fields", "oversized_fields_dropped")
        elif raw_layers is not None:
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
        if layers:
            value["layers"] = layers
    elif "terrainRisk" in data:
        raw = data["terrainRisk"]
        if not isinstance(raw, Mapping):
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
            return
        overall = raw.get("overall")
        data_quality = raw.get("data_quality")
        state = overall.get("level") if isinstance(overall, Mapping) else "unknown"
        quality_state = data_quality.get("status") if isinstance(data_quality, Mapping) else "limited"
        state = state if state in {"low", "medium", "high", "unknown"} else "unknown"
        quality_state = quality_state if quality_state in {"good", "limited", "unavailable"} else "limited"
        value = {
            "legacy_level": state, "data_quality_status": quality_state,
            "conclusion": "reference_only",
        }
    else:
        return

    collector.warnings.add("terrain_reference_only")
    if state in {"available", "low"}:
        collector.warnings.add("terrain_safe_conclusion_blocked")
    unavailable = state in {"unavailable", "error"} or value.get("data_quality_status") == "unavailable"
    unknown = state in {"unknown", "not_assessed"}
    collector.add(
        "terrain_reference", "legacy_saved_case.terrain_reference",
        None if unavailable or unknown else value, "legacy-terrain-reference-v1",
        status="unavailable" if unavailable else "unknown" if unknown else "limited",
        coverage="unavailable" if unavailable else "unknown" if unknown else "partial",
        quality="limited",
        limitations=("reference_only", "requires_current_authoritative_analysis"),
    )


class LegacySavedCaseV1Parser:
    """Produce typed bounded drafts without retaining the incoming object."""

    def parse(self, payload: Mapping[str, object]) -> ParsedLegacyCase:
        if not isinstance(payload, Mapping):
            raise VNextError.validation_failed()
        try:
            encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True).encode("utf-8")
        except (TypeError, ValueError):
            raise VNextError.validation_failed() from None
        if len(encoded) > MAX_LEGACY_PAYLOAD_BYTES:
            raise VNextError.validation_failed()
        version = payload.get("version")
        if isinstance(version, bool) or version != LEGACY_SCHEMA_VERSION:
            raise VNextError.unsupported_input()
        if payload.get("workflowMode") not in {None, "buying_wizard"}:
            raise VNextError.unsupported_input()

        collector = _Collector()
        _scan_exclusions(payload, collector)
        known_top = {
            "id", "title", "createdAt", "updatedAt", "version", "workflowMode",
            "activeWizardStep", "progress", "inputSummary", "data",
        }
        if set(payload) - known_top:
            collector.drop("unsupported_fields", "unsupported_fields_dropped")
        if "id" in payload:
            collector.dropped.add("legacy_client_payload_id")

        title, title_issue = _text(240)(payload.get("title"))
        if title_issue:
            raise VNextError.validation_failed()
        collector.accepted.add("title")
        created_at = _timestamp(payload["createdAt"], collector) if "createdAt" in payload else None
        updated_at = _timestamp(payload["updatedAt"], collector) if "updatedAt" in payload else None
        if created_at or updated_at:
            collector.accepted.add("legacy_timestamps")
        if created_at and updated_at and updated_at < created_at:
            collector.warnings.add("legacy_timestamps_inconsistent")

        workflow: dict[str, object] = {}
        if "activeWizardStep" in payload:
            step = payload["activeWizardStep"]
            if isinstance(step, str) and step in _WORKFLOW_STEPS:
                workflow["active_wizard_step"] = step
            else:
                collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
        if "progress" in payload:
            progress, issue = _number(0, 100)(payload["progress"])
            if issue:
                collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
            else:
                workflow["progress"] = progress
        if workflow:
            collector.add(
                "workflow_snapshot", "legacy_saved_case.workflow_snapshot", workflow,
                "legacy-workflow-snapshot-v1", limitations=("historical_activity_only",),
            )

        summary = payload.get("inputSummary", {})
        data = payload.get("data", {})
        if not isinstance(summary, Mapping):
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
            summary = {}
        if not isinstance(data, Mapping):
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
            data = {}
        known_data = {
            "inputs", "propertySearch", "valuation", "valuationEvidence", "trend", "loan",
            "holdingCost", "locationInsight", "marketInsight", "journeyContext", "terrainRisk",
            "terrainReference", "riskSummary", "taxOracle", "reportCompleted",
        }
        if set(data) - known_data:
            collector.drop("unsupported_fields", "unsupported_fields_dropped")
        inputs = data.get("inputs", {})
        if not isinstance(inputs, Mapping):
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
            inputs = {}

        summary_values = _select(
            summary,
            {
                "city": _text(160), "district": _text(160), "road": _text(240),
                "budgetMin": _number(0, 1_000_000_000, nullable=True),
                "budgetMax": _number(0, 1_000_000_000),
                "propertyPrice": _number(0, 1_000_000_000), "areaPing": _number(0, 1_000_000),
            },
            collector,
        ) or {}
        input_values = _select(
            inputs,
            {
                "city": _text(160), "district": _text(160), "road": _text(240),
                "building_type": _text(160), "area_ping": _number(0, 1_000_000),
                "building_age_years": _number(0, 1_000), "floor": _number(-100, 1_000),
            },
            collector,
        ) or {}
        address: dict[str, object] = {}
        summary_address = {key: summary_values[key] for key in ("city", "district", "road") if key in summary_values}
        input_address = {key: input_values[key] for key in ("city", "district", "road") if key in input_values}
        if summary_address:
            address["input_summary"] = summary_address
        if input_address:
            address["valuation_inputs"] = input_address
        if address:
            collector.add(
                "address_input", "legacy_saved_case.address_input", address,
                "legacy-address-input-v1",
                limitations=("user_provided", "not_canonical_identity", "requires_resolution"),
            )
            collector.warnings.add("address_requires_resolution")
        else:
            collector.warnings.add("missing_address")
        property_inputs = {
            **{key: value for key, value in summary_values.items() if key not in {"city", "district", "road"}},
            **{key: value for key, value in input_values.items() if key not in {"city", "district", "road"}},
        }
        if property_inputs:
            collector.add(
                "property_inputs", "legacy_saved_case.property_inputs", property_inputs,
                "legacy-property-inputs-v1", status="user_provided",
                limitations=("user_provided", "not_current_valuation"),
            )

        property_search = data.get("propertySearch")
        if isinstance(property_search, Mapping) and "summary" in property_search:
            selected = _select(
                property_search["summary"],
                {
                    "matched_count": _number(0, 10_000_000), "city_count": _number(0, 1000),
                    "district_count": _number(0, 10_000), "road_count": _number(0, 1_000_000),
                    "budget_min": _number(0, 1_000_000_000, nullable=True),
                    "budget_max": _number(0, 1_000_000_000), "period_min": _text(32),
                    "period_max": _text(32), "data_source_label": _text(160),
                    "message": _text(1000), "disclaimer": _text(2000),
                },
                collector,
            )
            if selected:
                collector.add(
                    "property_search_summary", "legacy_saved_case.property_search_summary",
                    selected, "legacy-property-search-summary-v1", status="stale",
                    coverage="partial", quality="limited",
                    limitations=("reference_only", "raw_rows_excluded", "requires_revalidation"),
                )
        elif property_search is not None:
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")

        stale_sections = (
            (
                "valuationEvidence", "valuation_evidence_summary",
                "legacy_saved_case.valuation_evidence_summary", "legacy-valuation-evidence-summary-v1",
                {
                    "status": _enum("trusted", "manual", "partial", "unavailable", "not_assessed"),
                    "source": _text(80), "label": _text(240), "value": _text(240),
                    "range": _text(240), "confidence": _text(120), "reason": _text(1000),
                    "transferable": _boolean,
                },
            ),
            (
                "valuation", "valuation_summary", "legacy_saved_case.valuation_summary",
                "legacy-valuation-summary-v1",
                {
                    "source": _text(80), "data_composition": _text(80),
                    "estimate_data_composition": _text(80), "estimate_source_label": _text(240),
                    "candidate_pool_size": _number(0, 10_000_000), "estimate_level": _text(80),
                    "confidence_reason": _text(1000),
                    "estimate_total_price": _number(0, 1_000_000_000_000),
                    "estimate_unit_price_per_ping": _number(0, 1_000_000_000),
                    "confidence": _enum("high", "medium", "low"),
                    "confidence_score": _number(0, 100),
                },
            ),
            (
                "trend", "trend_snapshot", "legacy_saved_case.trend_snapshot",
                "legacy-trend-snapshot-v1",
                {
                    "source": _text(80), "data_scope": _text(80), "period_min": _text(32),
                    "period_max": _text(32), "effective_period_min": _text(32),
                    "effective_period_max": _text(32), "sample_count": _number(0, 10_000_000),
                    "recent_median_unit_price": _number(0, 1_000_000_000),
                    "trend_annualized_rate": _number(-100, 100),
                    "volatility": _number(0, 100, nullable=True),
                    "confidence_level": _enum("high", "medium", "low"),
                    "confidence_reason": _text(1000),
                },
            ),
            (
                "marketInsight", "market_snapshot", "legacy_saved_case.market_snapshot",
                "legacy-market-snapshot-v1",
                {
                    "city": _text(160), "district": _text(160), "period": _text(32),
                    "average_unit_price": _number(0, 1_000_000_000, nullable=True),
                    "transaction_count": _number(0, 100_000_000, nullable=True),
                    "summary": _text(1000), "source_name": _text(160),
                    "source_updated_at": _text(64), "coverage_status": _text(40),
                    "data_status": _text(40), "caveat": _text(1000), "disclaimer": _text(2000),
                },
            ),
        )
        for key, field_class, fact_type, schema, rules in stale_sections:
            _add_section(
                data, key, collector, rules, field_class, fact_type, schema,
                status="stale", coverage="partial", quality="limited",
                limitations=("legacy_summary_only", "requires_revalidation"),
            )
        if "valuation" not in data and "valuationEvidence" not in data:
            collector.warnings.add("missing_valuation")

        _add_section(
            data, "loan", collector,
            {
                "property_price_wan": _number(0, 1_000_000_000),
                "down_payment_ratio": _number(0, 1), "down_payment_wan": _number(0, 1_000_000_000),
                "loan_amount_wan": _number(0, 1_000_000_000),
                "annual_interest_rate": _number(0, 100), "loan_years": _number(0, 100),
                "grace_period_years": _number(0, 100),
                "monthly_income_wan": _number(0, 1_000_000_000, nullable=True),
                "monthly_payment": _number(0, 1_000_000_000_000),
                "total_payment": _number(0, 1_000_000_000_000),
                "total_interest": _number(0, 1_000_000_000_000),
                "income_burden_ratio": _number(0, 100, nullable=True),
                "affordability_level": _enum("comfortable", "manageable", "tight", "risky", "unknown"),
            },
            "loan_artifact", "legacy_saved_case.loan_artifact", "legacy-loan-artifact-v1",
            limitations=("legacy_calculation_artifact", "not_recalculated"),
        )
        _add_section(
            data, "holdingCost", collector,
            {
                "property_price_wan": _number(0, 1_000_000_000),
                "loan_monthly_payment": _number(0, 1_000_000_000_000),
                "monthly_management_fee": _number(0, 1_000_000_000),
                "monthly_repair_reserve": _number(0, 1_000_000_000),
                "monthly_tax_estimate": _number(0, 1_000_000_000),
                "monthly_insurance": _number(0, 1_000_000_000),
                "monthly_total_holding_cost": _number(0, 1_000_000_000_000),
                "annual_total_holding_cost": _number(0, 1_000_000_000_000),
                "income_burden_ratio": _number(0, 100, nullable=True),
                "affordability_level": _enum("comfortable", "manageable", "tight", "risky", "unknown"),
            },
            "holding_cost_artifact", "legacy_saved_case.holding_cost_artifact",
            "legacy-holding-cost-artifact-v1",
            limitations=("legacy_calculation_artifact", "not_recalculated"),
        )

        location = data.get("locationInsight")
        if isinstance(location, Mapping):
            selected_location = _select(
                location,
                {
                    "radius_m": _number(0, 1_000_000),
                    "location_score": _number(0, 100, nullable=True),
                    "strengths": _strings(12, 240), "weaknesses": _strings(12, 240),
                    "disclaimer": _text(2000),
                },
                collector,
            ) or {}
            for nested_key, nested_rules in {
                "category_scores": {
                    "transit_score": _number(0, 100), "convenience_score": _number(0, 100),
                    "education_score": _number(0, 100), "green_space_score": _number(0, 100),
                    "medical_score": _number(0, 100), "risk_score": _number(0, 100),
                },
                "poi_summary": {
                    "transit_count": _number(0, 1_000_000), "convenience_count": _number(0, 1_000_000),
                    "school_count": _number(0, 1_000_000), "park_count": _number(0, 1_000_000),
                    "medical_count": _number(0, 1_000_000), "risk_facility_count": _number(0, 1_000_000),
                },
                "data_quality": {
                    "status": _enum("good", "limited", "unavailable"),
                    "missing_sources": _strings(12, 160), "warnings": _strings(12, 240),
                },
            }.items():
                if nested_key in location:
                    nested = _select(location[nested_key], nested_rules, collector)
                    if nested:
                        selected_location[nested_key] = nested
            if selected_location:
                collector.add(
                    "location_summary", "legacy_saved_case.location_summary", selected_location,
                    "legacy-location-summary-v1", status="stale", coverage="partial",
                    quality="limited",
                    limitations=("legacy_summary_only", "exact_coordinates_excluded", "requires_revalidation"),
                )
        elif location is not None:
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")

        _add_terrain(data, collector)
        _add_section(
            data, "riskSummary", collector,
            {
                "overallSignal": _enum("green", "yellow", "red", "unknown"),
                "overallLabel": _text(240), "overallScore": _number(0, 100, nullable=True),
                "decisionSuggestion": _text(1000),
                "dataConfidence": _enum("high", "medium", "low", "unknown"),
                "missingChecks": _strings(20, 240), "nextActions": _strings(20, 240),
                "referenceNotes": _strings(12, 500),
            },
            "risk_presentation", "legacy_saved_case.risk_presentation",
            "legacy-risk-presentation-v1",
            limitations=("presentation_artifact_only", "not_authoritative"),
        )
        if "riskSummary" in data:
            collector.warnings.add("risk_presentation_not_authoritative")
        _add_section(
            data, "taxOracle", collector,
            {
                "eligibility_status": _enum("eligible", "manual_review", "not_eligible"),
                "risk_score": _number(0, 10_000), "signal_color": _enum("green", "yellow", "red"),
                "hard_fail_rules": _strings(20, 120), "manual_review_rules": _strings(20, 120),
                "missing_docs": _strings(20, 160), "reminder_timeline": _strings(20, 240),
                "tax_output_boundary": _enum("preliminary_screening_only"),
            },
            "tax_artifact", "legacy_saved_case.tax_artifact", "legacy-tax-artifact-v1",
            limitations=("legacy_calculation_artifact", "not_recalculated"),
        )
        if "reportCompleted" in data:
            report_completed, issue = _boolean(data["reportCompleted"])
            if issue:
                collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")
            else:
                collector.add(
                    "report_activity", "legacy_saved_case.report_activity",
                    {"report_completed": report_completed, "case_status_effect": "none"},
                    "legacy-report-activity-v1",
                    limitations=("historical_activity_only", "does_not_complete_case"),
                )

        journey = data.get("journeyContext")
        if isinstance(journey, Mapping):
            selected_journey = _select(
                journey,
                {
                    "version": _number(1, 1), "priceBasis": _enum("asking", "valuation", "manual"),
                    "activePriceWan": _number(0, 1_000_000_000),
                    "manualPriceWan": _number(0, 1_000_000_000),
                },
                collector,
            ) or {}
            if "propertyContext" in journey:
                context = _select(
                    journey["propertyContext"],
                    {
                        "city": _text(160), "district": _text(160), "road": _text(240),
                        "addressSummary": _text(512), "buildingType": _text(160),
                        "areaPing": _number(0, 1_000_000), "buildingAgeYears": _number(0, 1_000),
                        "floor": _number(-100, 1_000), "askingPriceWan": _number(0, 1_000_000_000),
                        "sourceLabel": _text(160),
                        "selectionStatus": _enum("not_selected", "selected", "partial"),
                    },
                    collector,
                )
                if context:
                    selected_journey["property_context"] = context
            if selected_journey:
                collector.add(
                    "journey_context", "legacy_saved_case.journey_context", selected_journey,
                    "legacy-journey-context-v1",
                    limitations=("user_provided_context", "not_canonical_identity"),
                )
        elif journey is not None:
            collector.drop("corrupt_optional_section", "corrupt_optional_section_dropped")

        if any(item.evidence_status in {"stale", "limited"} for item in collector.evidence):
            collector.warnings.add("legacy_snapshot_requires_revalidation")
        return ParsedLegacyCase(
            title=str(title),
            client_created_at=created_at,
            client_updated_at=updated_at,
            accepted_field_classes=tuple(item for item in _ACCEPTED_ORDER if item in collector.accepted),
            dropped_field_classes=tuple(item for item in _DROPPED_ORDER if item in collector.dropped),
            warnings=tuple(item for item in _WARNING_ORDER if item in collector.warnings),
            evidence=tuple(collector.evidence),
        )
