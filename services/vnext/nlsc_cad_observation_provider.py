"""TEST-scoped NLSC CAD observations for Property Identity review.

CAD_009 yields parcel-reference observations from an address query.  CAD_001
yields georeference evidence only, and can run only when a trusted caller has
separately supplied the exact NLSC county code, section code, eight-digit land
number, and CRS.  The two operations are never chained or inferred.

Both providers deliberately use the appendable ``vnext-test`` source at the
IdentityResolutionEngine boundary.  Their true ``nlsc-cadastral`` / NLSC
origin remains explicit provenance, while that official registry entry stays
non-appendable and non-production-accepted.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Protocol

from services.vnext.identity_resolution import (
    CandidateRankingFactors,
    IdentityCandidateType,
    NormalizedResolutionInput,
    ProviderCandidateObservation,
    ProviderResolutionResult,
    ResolutionAttemptStatus,
    ResolutionErrorCategory,
    ResolutionInputType,
)
from services.vnext.property_graph import CoverageStatus, SourceEnvironment


NLSC_SOURCE_ID = "nlsc-cadastral"
OBSERVATION_SOURCE_ID = "vnext-test"
CAD_009_PROVIDER_ID = "nlsc-cad-009-observation"
CAD_009_STRATEGY_ID = "nlsc-cad-009-observation-v1"
CAD_001_PROVIDER_ID = "nlsc-cad-001-georeference"
CAD_001_STRATEGY_ID = "nlsc-cad-001-georeference-v1"

_CODE = re.compile(r"[A-Za-z0-9]{1,32}\Z")
_LAND_NUMBER = re.compile(r"[0-9]{8}\Z")
_MAX_CAD_009_RESULTS = 8


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class _NlscCadAdapter(Protocol):
    @property
    def available(self) -> bool: ...

    def cad_009_address_query_land(
        self,
        query: str,
        max_results: int = 1,
    ) -> Mapping[str, object]: ...

    def cad_001_cadas_map_position(
        self,
        county_code: str,
        section_code: str,
        land_number: str,
        crs: str = "4326",
    ) -> Mapping[str, object]: ...


@dataclass(frozen=True)
class TrustedCad001Query:
    """Explicit CAD_001 codes supplied by a trusted backend context."""

    county_code: str
    section_code: str
    land_number: str
    crs: str = "4326"

    def __post_init__(self) -> None:
        if (
            not isinstance(self.county_code, str)
            or not _CODE.fullmatch(self.county_code)
            or not isinstance(self.section_code, str)
            or not _CODE.fullmatch(self.section_code)
            or not isinstance(self.land_number, str)
            or not _LAND_NUMBER.fullmatch(self.land_number)
            or self.crs not in {"4326", "3826"}
        ):
            raise ValueError("Invalid explicit CAD_001 query.")


def _neutral_factors() -> CandidateRankingFactors:
    # NLSC supplies no confidence or ranking factors in either official CAD
    # contract.  Zero is the engine's neutral floor, not a source confidence.
    return CandidateRankingFactors(
        source_reliability=0.0,
        match_quality=0.0,
        identifier_agreement=0.0,
        geometry_agreement=0.0,
        temporal_validity=0.0,
        coverage_quality=0.0,
    )


def _timestamp(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("invalid retrieval timestamp")
    try:
        selected = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("invalid retrieval timestamp") from None
    if selected.utcoffset() is None:
        raise ValueError("invalid retrieval timestamp")
    return selected


def _provenance(service_code: str, retrieved_at: str) -> Mapping[str, object]:
    return {
        "source": "NLSC",
        "declared_source_id": NLSC_SOURCE_ID,
        "service_code": service_code,
        "retrieved_at": retrieved_at,
        "coverage": "unknown",
        "source_record_id": None,
        "raw_confidence": None,
        "identity_status": "proposed_unverified",
        "human_confirmation_required": True,
    }


def _coverage(
    *,
    scope: str,
    fields: tuple[str, ...],
    provenance: Mapping[str, object],
) -> Mapping[str, object]:
    return {
        "status": "unknown",
        "reason": "official_coverage_not_supplied",
        "subject_scope": scope,
        "fields": list(fields),
        "provenance": dict(provenance),
    }


def _fingerprint(service_code: str, value: Mapping[str, object]) -> str:
    encoded = json.dumps(
        {"service_code": service_code, "value": dict(value)},
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _failure(
    *,
    service_code: str,
    started_at: datetime,
    completed_at: datetime,
    status: ResolutionAttemptStatus,
    category: ResolutionErrorCategory,
    code: str,
    retryable: bool,
) -> ProviderResolutionResult:
    return ProviderResolutionResult(
        status=status,
        started_at=started_at,
        completed_at=completed_at,
        retrieved_at=None,
        coverage_status=CoverageStatus.UNAVAILABLE,
        coverage={
            "status": "unavailable",
            "source": "NLSC",
            "service_code": service_code,
            "source_record_id": None,
            "raw_confidence": None,
            "reason": code,
        },
        candidates=(),
        conflicts=(),
        error_category=category,
        error_code=code,
        error_retryable=retryable,
    )


def _unsupported(
    *,
    service_code: str,
    started_at: datetime,
    completed_at: datetime,
) -> ProviderResolutionResult:
    return _failure(
        service_code=service_code,
        started_at=started_at,
        completed_at=completed_at,
        status=ResolutionAttemptStatus.UNSUPPORTED,
        category=ResolutionErrorCategory.UNSUPPORTED_INPUT,
        code=f"{service_code.lower()}_explicit_input_required",
        retryable=False,
    )


def _adapter_failure(
    *,
    service_code: str,
    started_at: datetime,
    completed_at: datetime,
    result: object,
) -> ProviderResolutionResult:
    error_code = result.get("error_code") if isinstance(result, Mapping) else None
    if error_code == "not_configured":
        return _failure(
            service_code=service_code,
            started_at=started_at,
            completed_at=completed_at,
            status=ResolutionAttemptStatus.UNAVAILABLE,
            category=ResolutionErrorCategory.NOT_CONFIGURED,
            code=f"{service_code.lower()}_not_configured",
            retryable=False,
        )
    if error_code == "timeout":
        return _failure(
            service_code=service_code,
            started_at=started_at,
            completed_at=completed_at,
            status=ResolutionAttemptStatus.TIMEOUT,
            category=ResolutionErrorCategory.TIMEOUT,
            code=f"{service_code.lower()}_timeout",
            retryable=True,
        )
    if error_code == "invalid_input":
        return _unsupported(
            service_code=service_code,
            started_at=started_at,
            completed_at=completed_at,
        )
    if error_code == "transport_error":
        return _failure(
            service_code=service_code,
            started_at=started_at,
            completed_at=completed_at,
            status=ResolutionAttemptStatus.UNAVAILABLE,
            category=ResolutionErrorCategory.TRANSPORT_ERROR,
            code=f"{service_code.lower()}_transport_error",
            retryable=True,
        )
    return _failure(
        service_code=service_code,
        started_at=started_at,
        completed_at=completed_at,
        status=ResolutionAttemptStatus.ERROR,
        category=ResolutionErrorCategory.INVALID_RESPONSE,
        code=f"{service_code.lower()}_invalid_response",
        retryable=False,
    )


def _validated_result(
    result: object,
    *,
    service_code: str,
) -> tuple[datetime, str, list[object]]:
    if (
        not isinstance(result, Mapping)
        or result.get("status") != "available"
        or result.get("source") != "NLSC"
        or result.get("service_code") != service_code
        or result.get("coverage") != "unknown"
        or result.get("source_record_id") is not None
        or result.get("raw_confidence") is not None
        or result.get("error_code") is not None
        or not isinstance(result.get("observations"), list)
        or not result.get("observations")
    ):
        raise ValueError("invalid adapter result")
    retrieved_text = result.get("retrieved_at")
    retrieved_at = _timestamp(retrieved_text)
    return retrieved_at, str(retrieved_text), list(result["observations"])


def _text(value: object, *, maximum: int) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid text")
    selected = " ".join(value.split())
    if not selected or len(selected) > maximum or "\x00" in selected:
        raise ValueError("invalid text")
    return selected


def _cad_009_candidate(
    observation: object,
    *,
    retrieved_at: datetime,
    retrieved_text: str,
) -> ProviderCandidateObservation:
    if not isinstance(observation, Mapping) or set(observation) != {
        "content",
        "location",
        "office_code",
        "section_code",
        "land_number",
    }:
        raise ValueError("invalid CAD_009 observation")
    content = _text(observation.get("content"), maximum=512)
    location = _text(observation.get("location"), maximum=96)
    office = _text(observation.get("office_code"), maximum=32)
    section = _text(observation.get("section_code"), maximum=32)
    land_number = _text(observation.get("land_number"), maximum=8)
    if not _CODE.fullmatch(office) or not _CODE.fullmatch(section) or not _LAND_NUMBER.fullmatch(land_number):
        raise ValueError("invalid CAD_009 cadastral code")
    source_facts: Mapping[str, object] = {
        "content": content,
        "location": location,
        "office_code": office,
        "section_code": section,
        "land_number": land_number,
    }
    provenance = _provenance("CAD_009", retrieved_text)
    coverage = _coverage(
        scope="parcel_reference",
        fields=("content", "location", "office_code", "section_code", "land_number"),
        provenance=provenance,
    )
    fingerprint = _fingerprint("CAD_009", source_facts)
    return ProviderCandidateObservation(
        observation_id=f"nlsc-cad009:{fingerprint}",
        candidate_type=IdentityCandidateType.PARCEL,
        normalized_key=f"nlsc-cad009:{fingerprint}",
        normalized_identity={
            "kind": "parcel_reference_observation",
            **source_facts,
            "provenance": provenance,
        },
        display_identity=content,
        source_record_id=None,
        retrieved_at=retrieved_at,
        ranking_factors=_neutral_factors(),
        coverage_status=CoverageStatus.UNKNOWN,
        coverage=coverage,
    )


def _number(value: object) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("invalid coordinate")
    selected = float(value)
    if not math.isfinite(selected):
        raise ValueError("invalid coordinate")
    return selected


def _point(value: object, *, expected_crs: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping) or set(value) != {"x", "y", "crs"}:
        raise ValueError("invalid point")
    if value.get("crs") != expected_crs:
        raise ValueError("invalid point CRS")
    return {"x": _number(value.get("x")), "y": _number(value.get("y")), "crs": expected_crs}


def _cad_001_candidate(
    observation: object,
    *,
    query: TrustedCad001Query,
    retrieved_at: datetime,
    retrieved_text: str,
) -> ProviderCandidateObservation:
    if not isinstance(observation, Mapping) or set(observation) != {
        "representative_point",
        "bounds",
    }:
        raise ValueError("invalid CAD_001 observation")
    crs_name = f"EPSG:{query.crs}"
    representative = _point(observation.get("representative_point"), expected_crs=crs_name)
    bounds = observation.get("bounds")
    if not isinstance(bounds, Mapping) or set(bounds) != {"lower_left", "upper_right", "crs"}:
        raise ValueError("invalid bounds")
    if bounds.get("crs") != crs_name:
        raise ValueError("invalid bounds CRS")
    lower = bounds.get("lower_left")
    upper = bounds.get("upper_right")
    if not isinstance(lower, Mapping) or set(lower) != {"x", "y"}:
        raise ValueError("invalid lower bound")
    if not isinstance(upper, Mapping) or set(upper) != {"x", "y"}:
        raise ValueError("invalid upper bound")
    normalized_bounds: Mapping[str, object] = {
        "lower_left": {"x": _number(lower.get("x")), "y": _number(lower.get("y"))},
        "upper_right": {"x": _number(upper.get("x")), "y": _number(upper.get("y"))},
        "crs": crs_name,
    }
    parcel_query: Mapping[str, object] = {
        "county_code": query.county_code,
        "section_code": query.section_code,
        "land_number": query.land_number,
        "crs": query.crs,
    }
    source_facts: Mapping[str, object] = {
        "parcel_query": parcel_query,
        "representative_point": representative,
        "bounds": normalized_bounds,
    }
    provenance = _provenance("CAD_001", retrieved_text)
    coverage = _coverage(
        scope="parcel_georeference",
        fields=("representative_point", "bounds"),
        provenance=provenance,
    )
    fingerprint = _fingerprint("CAD_001", source_facts)
    return ProviderCandidateObservation(
        observation_id=f"nlsc-cad001:{fingerprint}",
        candidate_type=IdentityCandidateType.GEO_REFERENCE,
        normalized_key=f"nlsc-cad001:{fingerprint}",
        normalized_identity={
            "kind": "georeference_observation",
            "identity_effect": "does_not_confirm_parcel_identity",
            **source_facts,
            "provenance": provenance,
        },
        display_identity=(
            "NLSC CAD_001 georeference for "
            f"{query.county_code}/{query.section_code}/{query.land_number}"
        ),
        source_record_id=None,
        retrieved_at=retrieved_at,
        ranking_factors=_neutral_factors(),
        coverage_status=CoverageStatus.UNKNOWN,
        coverage=coverage,
    )


class _BaseNlscObservationProvider:
    def __init__(
        self,
        adapter: _NlscCadAdapter,
        *,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._adapter = adapter
        self._clock = clock

    @property
    def source_id(self) -> str:
        return OBSERVATION_SOURCE_ID

    @property
    def source_environment(self) -> SourceEnvironment:
        return SourceEnvironment.TEST

    @property
    def declared_source_id(self) -> str:
        return NLSC_SOURCE_ID

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.utcoffset() is None:
            raise ValueError("Provider clock must be timezone-aware.")
        return value


class NlscCad009ParcelObservationProvider(_BaseNlscObservationProvider):
    """Translate CAD_009 results into unverified parcel candidates."""

    @property
    def provider_id(self) -> str:
        return CAD_009_PROVIDER_ID

    @property
    def strategy_id(self) -> str:
        return CAD_009_STRATEGY_ID

    def resolve(self, resolution_input: NormalizedResolutionInput) -> ProviderResolutionResult:
        started_at = self._now()
        if resolution_input.input_type is not ResolutionInputType.ADDRESS:
            return _unsupported(
                service_code="CAD_009",
                started_at=started_at,
                completed_at=self._now(),
            )
        if not self._adapter.available:
            return _adapter_failure(
                service_code="CAD_009",
                started_at=started_at,
                completed_at=self._now(),
                result={"error_code": "not_configured"},
            )
        query = resolution_input.normalized_input.get("address")
        if not isinstance(query, str):
            return _unsupported(
                service_code="CAD_009",
                started_at=started_at,
                completed_at=self._now(),
            )
        try:
            adapter_result = self._adapter.cad_009_address_query_land(
                query,
                max_results=_MAX_CAD_009_RESULTS,
            )
            completed_at = self._now()
            if not isinstance(adapter_result, Mapping) or adapter_result.get("status") != "available":
                return _adapter_failure(
                    service_code="CAD_009",
                    started_at=started_at,
                    completed_at=completed_at,
                    result=adapter_result,
                )
            retrieved_at, retrieved_text, observations = _validated_result(
                adapter_result,
                service_code="CAD_009",
            )
            candidates = tuple(
                _cad_009_candidate(
                    observation,
                    retrieved_at=retrieved_at,
                    retrieved_text=retrieved_text,
                )
                for observation in observations
            )
            if not started_at <= retrieved_at <= completed_at:
                raise ValueError("retrieval timestamp outside request window")
            coverage = _coverage(
                scope="parcel_reference",
                fields=("content", "location", "office_code", "section_code", "land_number"),
                provenance=_provenance("CAD_009", retrieved_text),
            )
            return ProviderResolutionResult(
                status=ResolutionAttemptStatus.LIMITED,
                started_at=started_at,
                completed_at=completed_at,
                retrieved_at=retrieved_at,
                coverage_status=CoverageStatus.UNKNOWN,
                coverage=coverage,
                candidates=candidates,
                conflicts=(),
            )
        except Exception:
            return _adapter_failure(
                service_code="CAD_009",
                started_at=started_at,
                completed_at=self._now(),
                result={"error_code": "invalid_response"},
            )


class NlscCad001GeoreferenceObservationProvider(_BaseNlscObservationProvider):
    """Translate explicitly authorized CAD_001 output to georeference evidence."""

    def __init__(
        self,
        adapter: _NlscCadAdapter,
        *,
        trusted_query: TrustedCad001Query | None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        super().__init__(adapter, clock=clock)
        self._trusted_query = trusted_query

    @property
    def provider_id(self) -> str:
        return CAD_001_PROVIDER_ID

    @property
    def strategy_id(self) -> str:
        return CAD_001_STRATEGY_ID

    def resolve(self, resolution_input: NormalizedResolutionInput) -> ProviderResolutionResult:
        started_at = self._now()
        query = self._trusted_query
        expected_input = (
            None
            if query is None
            else {
                "jurisdiction": query.county_code,
                "section": query.section_code,
                "lot_number": query.land_number,
            }
        )
        if (
            query is None
            or resolution_input.input_type is not ResolutionInputType.LOT_NUMBER
            or dict(resolution_input.normalized_input) != expected_input
        ):
            return _unsupported(
                service_code="CAD_001",
                started_at=started_at,
                completed_at=self._now(),
            )
        if not self._adapter.available:
            return _adapter_failure(
                service_code="CAD_001",
                started_at=started_at,
                completed_at=self._now(),
                result={"error_code": "not_configured"},
            )
        try:
            adapter_result = self._adapter.cad_001_cadas_map_position(
                query.county_code,
                query.section_code,
                query.land_number,
                query.crs,
            )
            completed_at = self._now()
            if not isinstance(adapter_result, Mapping) or adapter_result.get("status") != "available":
                return _adapter_failure(
                    service_code="CAD_001",
                    started_at=started_at,
                    completed_at=completed_at,
                    result=adapter_result,
                )
            retrieved_at, retrieved_text, observations = _validated_result(
                adapter_result,
                service_code="CAD_001",
            )
            if len(observations) != 1:
                raise ValueError("CAD_001 must return exactly one position")
            candidate = _cad_001_candidate(
                observations[0],
                query=query,
                retrieved_at=retrieved_at,
                retrieved_text=retrieved_text,
            )
            if not started_at <= retrieved_at <= completed_at:
                raise ValueError("retrieval timestamp outside request window")
            coverage = _coverage(
                scope="parcel_georeference",
                fields=("representative_point", "bounds"),
                provenance=_provenance("CAD_001", retrieved_text),
            )
            return ProviderResolutionResult(
                status=ResolutionAttemptStatus.LIMITED,
                started_at=started_at,
                completed_at=completed_at,
                retrieved_at=retrieved_at,
                coverage_status=CoverageStatus.UNKNOWN,
                coverage=coverage,
                candidates=(candidate,),
                conflicts=(),
            )
        except Exception:
            return _adapter_failure(
                service_code="CAD_001",
                started_at=started_at,
                completed_at=self._now(),
                result={"error_code": "invalid_response"},
            )
