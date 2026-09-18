"""TEST-ENVIRONMENT-ONLY TGOS identity observation provider seam.

This module adapts the existing backend-only TGOS geocoding adapter
(``services.adapters.tgos_geocoding_adapter``) into the existing
``IdentityResolutionProvider`` protocol so that a TGOS address observation can
flow:

    legacy TGOS adapter output
        -> ProviderResolutionResult
        -> ProviderCandidateObservation
        -> coverage / provenance / quality metadata
        -> IdentityResolutionEngine

Deliberate boundaries (Slice A):

* This provider is a thin translation seam. It reuses the current TGOS HTTP
  adapter rather than duplicating HTTP logic, and it never calls TGOS itself in
  tests: an ``adapter`` collaborator is injected and faked offline.
* The engine-facing protocol ``source_id`` is ``vnext-test``. That is the only
  currently-appendable TEST source in ``DATA_SOURCE_REGISTRY``; using it lets an
  observation reach the engine as a *candidate that still requires human
  confirmation* WITHOUT promoting ``tgos-address`` to ``request_appendable`` or
  ``production_accepted``. The true official origin (``tgos-address`` / provider
  ``tgos``) is preserved as provenance inside every candidate and coverage
  payload, never as authority.
* ``TGOS_SOURCE_ID`` (``tgos-address``) is exposed only as declared provenance.
  A caller that (incorrectly) presents ``tgos-address`` as the engine-facing
  ``source_id`` is rejected by the engine's ``_source_definition`` gate, which
  is the intended fail-closed behaviour and is covered by tests.
* This provider only produces observations. It never confirms a candidate,
  materializes a PropertyEntity, creates a ``property_address`` relation, merges
  identities, or resolves conflicts. Ranking and conflict state remain the
  engine's responsibility; human confirmation remains required downstream.

Unknown TGOS facts stay unknown, partial coverage stays partial, and provider
failure never fabricates a successful candidate.
"""

from __future__ import annotations

import hashlib
import json
import math
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


# Declared official provenance. NOT the engine-facing appendable source id; see
# module docstring. tgos-address stays request_appendable=False in the registry.
TGOS_SOURCE_ID = "tgos-address"
# Engine-facing appendable TEST source. Keeps the observation strictly inside
# the test namespace and out of production identity truth.
OBSERVATION_SOURCE_ID = "vnext-test"
PROVIDER_ID = "tgos-address-observation"
STRATEGY_ID = "tgos-address-observation-v1"

# TGOS licence terms are not reviewed/approved for identity reuse (registry:
# tgos-address is prototype_partial, owner_review_required). We therefore state
# the licence status explicitly as unknown rather than implying permission.
_TGOS_LICENSE: Mapping[str, object] = {
    "source": "tgos-address",
    "terms": "TGOS service/application terms",
    "status": "owner_review_required",
    "commercial_use": "owner_review_required",
    "redistribution": "owner_review_required",
    "attribution": "TGOS",
}

_MAX_RESULTS = 8


class _TgosAddressAdapter(Protocol):
    """Structural type for the reused backend-only TGOS geocoding adapter."""

    @property
    def available(self) -> bool: ...

    @property
    def last_error(self) -> str: ...

    def search(self, query: str, regions: list[dict[str, Any]]) -> dict[str, Any] | None: ...


def _aware_now() -> datetime:
    return datetime.now(timezone.utc)


class TgosIdentityObservationProvider:
    """Translate one TGOS address lookup into a ProviderResolutionResult.

    The provider conforms to ``IdentityResolutionProvider`` and is TEST only.
    """

    def __init__(
        self,
        adapter: _TgosAddressAdapter,
        *,
        clock: Callable[[], datetime] = _aware_now,
    ) -> None:
        self._adapter = adapter
        self._clock = clock

    # -- IdentityResolutionProvider protocol -----------------------------------

    @property
    def provider_id(self) -> str:
        return PROVIDER_ID

    @property
    def strategy_id(self) -> str:
        return STRATEGY_ID

    @property
    def source_id(self) -> str:
        # Engine-facing appendable TEST source; official origin is provenance.
        #
        # PRODUCTION PROMOTION MUST NOT reuse ``vnext-test`` as TGOS authority.
        # ``vnext-test`` is a TEST-only transport namespace (SourceType.TEST,
        # environments={test}, readiness=metadata_only). It grants strictly LESS
        # authority than TGOS, never more. A production TGOS provider requires a
        # first-class, authorized provider/source design (or an authorized
        # ``tgos-address`` promoted through the readiness gate) so that persisted
        # resolution attempts/candidates record TGOS as a first-class origin
        # rather than only inside JSON provenance. Do not promote this alias.
        return OBSERVATION_SOURCE_ID

    @property
    def source_environment(self) -> SourceEnvironment:
        return SourceEnvironment.TEST

    @property
    def tgos_source_id(self) -> str:
        """Declared official provenance source id; never engine authority."""

        return TGOS_SOURCE_ID

    # -- Resolution ------------------------------------------------------------

    def resolve(
        self,
        resolution_input: NormalizedResolutionInput,
    ) -> ProviderResolutionResult:
        started_at = self._clock()

        # TGOS address service only answers address-shaped queries. Anything
        # else is unsupported for this provider; do not guess.
        if resolution_input.input_type is not ResolutionInputType.ADDRESS:
            return self._failure(
                started_at,
                status=ResolutionAttemptStatus.UNSUPPORTED,
                category=ResolutionErrorCategory.UNSUPPORTED_INPUT,
                code="tgos_unsupported_input",
                retryable=False,
                reason="tgos_supports_address_only",
            )

        query = str(resolution_input.normalized_input.get("address", "")).strip()
        if not query:
            return self._failure(
                started_at,
                status=ResolutionAttemptStatus.UNSUPPORTED,
                category=ResolutionErrorCategory.UNSUPPORTED_INPUT,
                code="tgos_empty_query",
                retryable=False,
                reason="empty_address",
            )

        # Credentials absent -> unavailable, never a fabricated candidate.
        if not self._adapter.available:
            return self._failure(
                started_at,
                status=ResolutionAttemptStatus.UNAVAILABLE,
                category=ResolutionErrorCategory.NOT_CONFIGURED,
                code="tgos_not_configured",
                retryable=False,
                reason="credentials_not_configured",
            )

        try:
            item = self._adapter.search(query, [])
        except Exception:
            # Do not retain raw provider detail. Fail closed as a transport error.
            return self._failure(
                started_at,
                status=ResolutionAttemptStatus.ERROR,
                category=ResolutionErrorCategory.TRANSPORT_ERROR,
                code="tgos_transport_error",
                retryable=True,
                reason="provider_exception",
            )

        # None means the adapter could not produce a usable result. Distinguish a
        # genuine no-match from an unavailable/timeout by inspecting last_error.
        if item is None:
            return self._empty_or_unavailable(started_at)

        # One coherent retrieval instant for both the result and the candidate.
        completed_at = self._clock()
        observation = self._observation(item, query, observed_at=completed_at)
        if observation is None:
            # Malformed provider payload: fail closed, never invent a candidate.
            return self._failure(
                started_at,
                status=ResolutionAttemptStatus.ERROR,
                category=ResolutionErrorCategory.INVALID_RESPONSE,
                code="tgos_malformed_result",
                retryable=False,
                reason="malformed_result",
            )

        coverage_status, coverage = observation[1], observation[2]
        # A single geocoder answer is a plausible observation, but TGOS returns
        # only best-match rooftop/geometric points, not a verified identity.
        status = (
            ResolutionAttemptStatus.AVAILABLE
            if coverage_status is CoverageStatus.KNOWN
            else ResolutionAttemptStatus.LIMITED
        )
        return ProviderResolutionResult(
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            retrieved_at=completed_at,
            coverage_status=coverage_status,
            coverage=coverage,
            candidates=(observation[0],),
            conflicts=(),
        )

    # -- Helpers ---------------------------------------------------------------

    def _observation(
        self,
        item: Mapping[str, Any],
        query: str,
        *,
        observed_at: datetime,
    ) -> tuple[ProviderCandidateObservation, CoverageStatus, Mapping[str, object]] | None:
        if not isinstance(item, Mapping):
            return None
        center = item.get("center")
        formatted = item.get("formatted_address")
        if not isinstance(center, Mapping) or not isinstance(formatted, str):
            return None
        latitude = center.get("lat")
        longitude = center.get("lng")
        if not _is_number(latitude) or not _is_number(longitude):
            return None
        formatted_address = formatted.strip()
        if not formatted_address or len(formatted_address) > 512 or "\x00" in formatted_address:
            return None

        metadata = item.get("geocoding_metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        location_type = str(metadata.get("location_type", "") or "")
        partial_match = bool(metadata.get("partial_match", False))

        city = str(item.get("city", "") or "")
        district = str(item.get("district", "") or "")
        road = str(item.get("road", "") or "")
        if (
            len(location_type) > 80
            or "\x00" in location_type
            or any(len(value) > 240 or "\x00" in value for value in (city, district, road))
        ):
            return None

        # Coverage reflects what TGOS actually said. Rooftop + full match =>
        # known; anything less stays partial. Never upgrade unknown to known.
        if location_type == "ROOFTOP" and not partial_match:
            coverage_status = CoverageStatus.KNOWN
        else:
            coverage_status = CoverageStatus.PARTIAL

        # Provenance is preserved on the candidate; the engine-facing source id
        # remains the TEST namespace. This records the TRUE origin without
        # granting it authority. License metadata travels with the provenance so
        # it survives into the engine-visible candidate and coverage, rather
        # than living only as a dead module constant.
        provenance: Mapping[str, object] = {
            "provider": "tgos",
            "declared_source_id": TGOS_SOURCE_ID,
            "location_type": location_type or "unknown",
            "partial_match": partial_match,
            "query": query,
            "license": dict(_TGOS_LICENSE),
        }
        source_facts: Mapping[str, object] = {
            "kind": "address",
            "formatted_address": formatted_address,
            "city": city,
            "district": district,
            "road": road,
            "latitude": float(latitude),
            "longitude": float(longitude),
            "crs": "EPSG:4326",
        }
        normalized_identity: Mapping[str, object] = {
            **source_facts,
            "provenance": provenance,
        }
        coverage: Mapping[str, object] = {
            "geography": {
                "kind": "point",
                "value": formatted_address,
                "status": "known" if coverage_status is CoverageStatus.KNOWN else "partial",
            },
            "subject_scope": "address",
            "fields": ["formatted_address", "latitude", "longitude"],
            "provenance": provenance,
        }

        factors = CandidateRankingFactors(
            source_reliability=0.7,   # official geocoder, but unreviewed for identity
            match_quality=1.0 if not partial_match else 0.5,
            identifier_agreement=0.0,  # TGOS supplies no parcel/building identifier
            geometry_agreement=1.0 if location_type == "ROOFTOP" else 0.5,
            temporal_validity=0.0,     # TGOS supplies no effective/observation date
            coverage_quality=1.0 if coverage_status is CoverageStatus.KNOWN else 0.5,
        )

        raw_record_id = item.get("id")
        record_id = raw_record_id.strip() if isinstance(raw_record_id, str) else ""
        if len(record_id) > 16_384 or "\x00" in record_id:
            return None
        source_record_id = record_id if record_id and len(record_id) <= 240 else None

        # Collision-safe observation id. Prefer the provider's own stable record
        # id; otherwise derive a deterministic, bounded SHA-256 fingerprint of
        # stable source facts. Request query and license are not ID inputs.
        # Never truncate the raw display string (long addresses sharing a
        # prefix would collide) or use a process-local or random ID.
        observation_id = _observation_id(
            record_id or None,
            {**source_facts, "location_type": location_type, "partial_match": partial_match},
        )

        observation = ProviderCandidateObservation(
            observation_id=observation_id,
            candidate_type=IdentityCandidateType.ADDRESS,
            # NOTE (production): this normalized_key is the TGOS display address
            # only. It is NOT a stable identity key. Full-width/half-width,
            # traditional/simplified and whitespace variants of the same address
            # would split identical observations or falsely group different
            # ones. Production promotion still requires a first-class TGOS
            # normalization strategy (NFKC + Taiwan token canonicalization)
            # before this value is used for identity matching or dedupe.
            normalized_key=f"tgos-address:{formatted_address}"[:512],
            normalized_identity=normalized_identity,
            display_identity=formatted_address[:512],
            source_record_id=source_record_id,
            retrieved_at=observed_at,
            ranking_factors=factors,
            coverage_status=coverage_status,
            coverage=coverage,
        )
        return observation, coverage_status, coverage

    def _empty_or_unavailable(self, started_at: datetime) -> ProviderResolutionResult:
        error = str(getattr(self._adapter, "last_error", "") or "")
        if error:
            # The legacy TGOS adapter collapses timeout and other transport
            # failures into a recorded ``last_error`` with a ``None`` result and
            # does not expose a machine-readable timeout signal. Rather than
            # guess a subtype from a localized message, we honestly report
            # UNAVAILABLE (retryable). Absence is never inferred as a no-match.
            return self._failure(
                started_at,
                status=ResolutionAttemptStatus.UNAVAILABLE,
                category=ResolutionErrorCategory.PROVIDER_UNAVAILABLE,
                code="tgos_unavailable",
                retryable=True,
                reason="provider_unavailable",
            )
        # No error and no item: a genuine, scoped no-match. No candidate.
        completed_at = self._clock()
        return ProviderResolutionResult(
            status=ResolutionAttemptStatus.NO_MATCH,
            started_at=started_at,
            completed_at=completed_at,
            retrieved_at=completed_at,
            coverage_status=CoverageStatus.KNOWN,
            coverage={
                "subject_scope": "address",
                "result": "no_match",
                "provenance": {
                    "provider": "tgos",
                    "declared_source_id": TGOS_SOURCE_ID,
                    "license": dict(_TGOS_LICENSE),
                },
            },
            candidates=(),
            conflicts=(),
        )

    def _failure(
        self,
        started_at: datetime,
        *,
        status: ResolutionAttemptStatus,
        category: ResolutionErrorCategory,
        code: str,
        retryable: bool,
        reason: str,
    ) -> ProviderResolutionResult:
        completed_at = self._clock()
        return ProviderResolutionResult(
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            retrieved_at=None,
            coverage_status=CoverageStatus.UNAVAILABLE,
            coverage={
                "reason": reason,
                "provenance": {
                    "provider": "tgos",
                    "declared_source_id": TGOS_SOURCE_ID,
                    "license": dict(_TGOS_LICENSE),
                },
            },
            candidates=(),
            conflicts=(),
            error_category=category,
            error_code=code,
            error_retryable=retryable,
        )


def _is_number(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(value)
    except OverflowError:
        return False


def _observation_id(
    source_record_id: str | None,
    source_facts: Mapping[str, object],
) -> str:
    """Deterministic, bounded, collision-safe observation id.

    Prefer the provider's stable ``source_record_id``. Hash a long record ID
    without truncation. Without one, hash bounded source facts that omit the
    request query and license. Distinct long addresses retain distinct IDs.

    NOTE (production): ``source_facts`` here are built from the TGOS
    display string without NFKC/Taiwan-token normalization. Distinct Unicode
    encodings of the same address would still fingerprint differently. A
    first-class TGOS normalization strategy (NFKC + token canonicalization) is
    required before production promotion; see the normalized-key note below.
    """

    if source_record_id is not None:
        selected = source_record_id.strip()
        # Only use the readable prefixed form when it fits WITHOUT truncation;
        # truncation would reintroduce the collision risk we are removing.
        if selected and len(selected) + len("tgos:") <= 120:
            return f"tgos:{selected}"
    fingerprint_input = (
        {"source_record_id": source_record_id}
        if source_record_id is not None
        else source_facts
    )
    canonical = json.dumps(
        fingerprint_input,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    digest = hashlib.sha256(canonical).hexdigest()
    return f"tgos:sha256:{digest}"  # 13 + 64 = 77 chars, within the 120 bound
