"""Phase 3A runtime loader for WRA flood potential processed artifacts.

This module is a *read-only* runtime that loads immutable processed artifacts
from Cloudflare R2 (``processed/wra/flood/v1/{scenario}/``), verifies their
integrity against the manifest ``artifact_sha256``, decodes them into Phase 1
:class:`~services.wra_flood_offline_dataset.FloodFeature` objects (reusing the
existing WKB/gzip/JSON deserialization in :mod:`services.wra_flood_artifact` --
never re-implemented here), builds a Shapely :class:`~shapely.strtree.STRtree`
spatial index, and caches the whole thing per process.

Design constraints (Phase 3A scope):

* Does NOT modify ``WraFloodProvider``, the Terrain Risk runtime, the frontend,
  any database, or create a ``production.json`` / ``latest`` pointer.
* Does NOT rebuild artifacts and does NOT re-implement serialization / WKB
  decode logic; it calls :func:`services.wra_flood_artifact.load_artifact`.
* Credentials come only from environment variables; nothing is hard-coded.
* Only the 10 canonical scenario IDs are accepted; unknown scenarios fail
  closed.  Callers cannot compose arbitrary R2 keys.
* R2 / checksum / parse failures are NEVER converted into a ``no_match`` or any
  "safe" / "low risk" interpretation.  They surface as explicit failure states.

Failure taxonomy (``status`` values):

* ``invalid_scenario``    -- scenario ID is not one of the 10 canonical IDs
* ``source_unavailable``  -- R2 object missing / network / client error
* ``checksum_mismatch``   -- artifact SHA256 != manifest ``artifact_sha256``
* ``artifact_invalid``    -- manifest/artifact could not be parsed/decoded
* ``loaded``              -- scenario loaded (or served from cache) successfully
* ``no_match``            -- a *successful* query that found no intersecting feature
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Optional, Protocol

from shapely.geometry import Point
from shapely.strtree import STRtree

from services.wra_flood_artifact import load_artifact
from services.wra_flood_offline_dataset import FloodFeature

# ---------------------------------------------------------------------------
# Canonical scenarios and immutable release prefix
# ---------------------------------------------------------------------------

#: The only accepted canonical scenario IDs (Phase 2.7 immutable release v1).
CANONICAL_SCENARIOS: tuple[str, ...] = (
    "6h-150mm",
    "6h-250mm",
    "6h-350mm",
    "12h-200mm",
    "12h-300mm",
    "12h-400mm",
    "24h-200mm",
    "24h-350mm",
    "24h-500mm",
    "24h-650mm",
)

_CANONICAL_SET = frozenset(CANONICAL_SCENARIOS)

#: Immutable release prefix (must match Phase 2.7 upload layout).
RELEASE_PREFIX = "processed/wra/flood/v1"

#: Required credential environment variable names (values never logged).
REQUIRED_ENV = (
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT",
    "R2_BUCKET",
    "R2_REGION",
)


# ---------------------------------------------------------------------------
# Failure taxonomy
# ---------------------------------------------------------------------------


class WraFloodRuntimeError(Exception):
    """Base error for runtime loader failures with an explicit status code.

    ``status`` is one of the failure-taxonomy strings.  These errors are never
    silently downgraded to a ``no_match`` result.
    """

    status: str = "artifact_invalid"

    def __init__(self, message: str, *, scenario: Optional[str] = None) -> None:
        super().__init__(message)
        self.scenario = scenario


class InvalidScenarioError(WraFloodRuntimeError):
    status = "invalid_scenario"


class SourceUnavailableError(WraFloodRuntimeError):
    status = "source_unavailable"


class ChecksumMismatchError(WraFloodRuntimeError):
    status = "checksum_mismatch"


class ArtifactInvalidError(WraFloodRuntimeError):
    status = "artifact_invalid"


# ---------------------------------------------------------------------------
# R2 client protocol (only the S3 GET operation is required)
# ---------------------------------------------------------------------------


class R2Client(Protocol):
    """Minimal protocol for the subset of the boto3 S3 client we use."""

    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
        ...


# ---------------------------------------------------------------------------
# Key construction (callers cannot compose arbitrary keys)
# ---------------------------------------------------------------------------


def validate_scenario(scenario: str) -> str:
    """Return the scenario if it is one of the 10 canonical IDs, else fail closed."""

    if not isinstance(scenario, str) or scenario not in _CANONICAL_SET:
        raise InvalidScenarioError(f"unknown scenario: {scenario!r}", scenario=scenario if isinstance(scenario, str) else None)
    return scenario


def manifest_key(scenario: str) -> str:
    """Canonical R2 key for a scenario manifest (validates scenario first)."""

    return f"{RELEASE_PREFIX}/{validate_scenario(scenario)}/manifest.json"


def artifact_key(scenario: str) -> str:
    """Canonical R2 key for a scenario artifact (validates scenario first)."""

    return f"{RELEASE_PREFIX}/{validate_scenario(scenario)}/features.json.gz"


# ---------------------------------------------------------------------------
# Loaded scenario cache entry
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoadedScenario:
    """A fully loaded, cached scenario ready for point queries."""

    scenario: str
    manifest: dict[str, Any]
    artifact_sha256: str
    features: list[FloodFeature]
    geometries: list[Any]
    tree: STRtree
    feature_count: int

    def status(self) -> str:
        return "loaded"


# ---------------------------------------------------------------------------
# Boto3 client factory (lazy; only built for real R2 access)
# ---------------------------------------------------------------------------


def build_default_r2_client() -> R2Client:
    """Construct a boto3 S3 client for Cloudflare R2 from environment variables.

    ``boto3`` is imported lazily so that unit tests (which inject a mock client)
    do not require the dependency to be importable, and so that importing this
    module never constructs a client or reads credentials.
    """

    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        # Only names are surfaced, never values.
        raise SourceUnavailableError(
            "missing required R2 environment variables: " + ", ".join(missing)
        )

    import boto3  # local import: optional at module import time
    from botocore.config import Config

    session = boto3.session.Session()
    return session.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name=os.environ["R2_REGION"],
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"},
            retries={"max_attempts": 5, "mode": "standard"},
        ),
    )


def _bucket_name() -> str:
    bucket = os.environ.get("R2_BUCKET")
    if not bucket:
        raise SourceUnavailableError("missing required R2 environment variable: R2_BUCKET")
    return bucket


# ---------------------------------------------------------------------------
# Low-level R2 GET helpers
# ---------------------------------------------------------------------------


def _get_object_bytes(client: R2Client, bucket: str, key: str) -> bytes:
    """GET an object and return its full body, mapping errors to failure states."""

    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except Exception as exc:  # noqa: BLE001 - normalize to a failure status
        # boto3 raises ClientError (incl. 404 NoSuchKey) and connection errors.
        raise SourceUnavailableError(f"R2 GET failed for {key}: {exc}") from exc

    body = response.get("Body")
    if body is None:
        raise SourceUnavailableError(f"R2 GET returned no body for {key}")
    try:
        return body.read()
    except Exception as exc:  # noqa: BLE001
        raise SourceUnavailableError(f"R2 body read failed for {key}: {exc}") from exc


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Core scenario loader (no cache) -- R2 -> manifest -> artifact -> verify -> tree
# ---------------------------------------------------------------------------


def _load_scenario_uncached(scenario: str, client: R2Client, bucket: str) -> LoadedScenario:
    scenario = validate_scenario(scenario)
    mkey = f"{RELEASE_PREFIX}/{scenario}/manifest.json"
    akey = f"{RELEASE_PREFIX}/{scenario}/features.json.gz"

    # 1. GET + parse manifest.
    manifest_bytes = _get_object_bytes(client, bucket, mkey)
    try:
        manifest = json.loads(manifest_bytes.decode("utf-8"))
    except Exception as exc:  # noqa: BLE001
        raise ArtifactInvalidError(f"manifest JSON parse failed for {scenario}: {exc}", scenario=scenario) from exc
    if not isinstance(manifest, dict):
        raise ArtifactInvalidError(f"manifest is not a JSON object for {scenario}", scenario=scenario)

    expected_sha = manifest.get("artifact_sha256")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        raise ArtifactInvalidError(
            f"manifest missing/invalid artifact_sha256 for {scenario}", scenario=scenario
        )
    manifest_scenario = manifest.get("scenario")
    if manifest_scenario is not None and manifest_scenario != scenario:
        raise ArtifactInvalidError(
            f"manifest scenario mismatch: key={scenario} manifest={manifest_scenario}", scenario=scenario
        )

    # 2. GET artifact bytes.
    artifact_bytes = _get_object_bytes(client, bucket, akey)

    # 3. Verify checksum BEFORE decoding. Fail closed on mismatch.
    actual_sha = _sha256_bytes(artifact_bytes)
    if actual_sha.lower() != expected_sha.lower():
        raise ChecksumMismatchError(
            f"artifact checksum mismatch for {scenario}: expected {expected_sha}, got {actual_sha}",
            scenario=scenario,
        )

    # 4. Decode using the existing artifact loader (no re-implementation here).
    try:
        _document, features = load_artifact(artifact_bytes)
    except Exception as exc:  # noqa: BLE001 - gzip/json/wkb decode failures
        raise ArtifactInvalidError(f"artifact decode failed for {scenario}: {exc}", scenario=scenario) from exc

    # 5. Build the STRtree over feature geometries.
    geometries = [feature.geometry for feature in features]
    tree = STRtree(geometries)

    return LoadedScenario(
        scenario=scenario,
        manifest=manifest,
        artifact_sha256=actual_sha,
        features=features,
        geometries=geometries,
        tree=tree,
        feature_count=len(features),
    )


# ---------------------------------------------------------------------------
# Process-local cache with single-flight loading
# ---------------------------------------------------------------------------


class WraFloodRuntime:
    """Process-local, thread-safe runtime cache for loaded flood scenarios.

    A single global lock guards the cache dictionary and the per-scenario
    single-flight locks.  Each scenario has its own load lock so that two
    concurrent cold-loads of the *same* scenario download the artifact only
    once (single-flight), while different scenarios can still load in parallel.
    """

    def __init__(self, client_factory=build_default_r2_client, *, bucket: Optional[str] = None) -> None:
        self._client_factory = client_factory
        self._bucket = bucket
        self._cache: dict[str, LoadedScenario] = {}
        self._registry_lock = threading.Lock()
        self._scenario_locks: dict[str, threading.Lock] = {}
        self._client: Optional[R2Client] = None
        # Test/diagnostic counter: how many uncached loads (cold R2 fetches).
        self.cold_load_count = 0

    # -- client lifecycle --------------------------------------------------

    def _get_client(self) -> R2Client:
        # The client is created once per runtime and reused (connection reuse).
        if self._client is None:
            with self._registry_lock:
                if self._client is None:
                    self._client = self._client_factory()
        return self._client

    def _resolve_bucket(self) -> str:
        # Prefer an explicitly injected bucket (tests / controlled config);
        # otherwise fall back to the R2_BUCKET environment variable.
        if self._bucket:
            return self._bucket
        return _bucket_name()

    def _scenario_lock(self, scenario: str) -> threading.Lock:
        with self._registry_lock:
            lock = self._scenario_locks.get(scenario)
            if lock is None:
                lock = threading.Lock()
                self._scenario_locks[scenario] = lock
            return lock

    # -- public API --------------------------------------------------------

    def load_scenario(self, scenario: str) -> LoadedScenario:
        """Load a scenario (cold from R2 or warm from cache).

        Validates the scenario first (fail closed on unknown IDs).  Uses a
        per-scenario single-flight lock so concurrent cold-loads of the same
        scenario only download once.
        """

        scenario = validate_scenario(scenario)

        # Fast path: already cached.
        cached = self._cache.get(scenario)
        if cached is not None:
            return cached

        lock = self._scenario_lock(scenario)
        with lock:
            # Re-check inside the lock: another thread may have loaded it while
            # we waited (single-flight).
            cached = self._cache.get(scenario)
            if cached is not None:
                return cached

            client = self._get_client()
            bucket = self._resolve_bucket()
            loaded = _load_scenario_uncached(scenario, client, bucket)
            self.cold_load_count += 1
            with self._registry_lock:
                self._cache[scenario] = loaded
            return loaded

    def query_point(self, scenario: str, lon: float, lat: float) -> dict[str, Any]:
        """Query a WGS84 point against a scenario, loading it if necessary.

        Uses the STRtree for candidate selection, then exact ``intersects``.
        When several features intersect, the deepest ``Class`` wins (Phase 1
        semantics).  A miss returns ``matched=False`` with NO safe/low-risk
        interpretation.  Invalid scenario / R2 / checksum / decode failures
        raise the corresponding :class:`WraFloodRuntimeError` and are never
        downgraded to ``no_match``.
        """

        loaded = self.load_scenario(scenario)
        return _query_loaded(loaded, lon, lat)

    def is_cached(self, scenario: str) -> bool:
        return scenario in self._cache

    def cached_scenarios(self) -> list[str]:
        return sorted(self._cache.keys())

    def clear_cache(self) -> None:
        """Clear the process-local cache. For tests / controlled refresh only."""

        with self._registry_lock:
            self._cache.clear()
            self._scenario_locks.clear()


def _query_loaded(loaded: LoadedScenario, lon: float, lat: float) -> dict[str, Any]:
    point = Point(float(lon), float(lat))

    # STRtree.query returns integer indices into the geometry list (Shapely 2.x).
    candidate_indices = loaded.tree.query(point)
    hits: list[FloodFeature] = []
    for idx in candidate_indices:
        feature = loaded.features[int(idx)]
        if feature.geometry.intersects(point):
            hits.append(feature)

    if not hits:
        # A plain miss. Deliberately NO 'safe' / 'low_risk' / 'risk' keys.
        return {
            "status": "no_match",
            "scenario": loaded.scenario,
            "matched": False,
            "matched_count": 0,
        }

    # Deepest Class wins (largest canonical range).
    primary = max(hits, key=lambda feature: feature.class_value)
    props = primary.properties or {}
    return {
        "status": "loaded",
        "scenario": loaded.scenario,
        "matched": True,
        "matched_count": len(hits),
        "class": primary.class_value,
        "canonical_depth": primary.canonical_depth,
        "flood_dept_raw": primary.flood_dept_raw,
        "flood_dept_malformed": bool(primary.flood_dept_malformed),
        "city_name": props.get("city_name"),
        "town_name": props.get("town_name"),
    }


# ---------------------------------------------------------------------------
# Module-level default runtime + convenience functions
# ---------------------------------------------------------------------------

_default_runtime: Optional[WraFloodRuntime] = None
_default_runtime_lock = threading.Lock()


def get_runtime() -> WraFloodRuntime:
    """Return the process-wide default runtime (lazily constructed)."""

    global _default_runtime
    if _default_runtime is None:
        with _default_runtime_lock:
            if _default_runtime is None:
                _default_runtime = WraFloodRuntime()
    return _default_runtime


def load_scenario(scenario: str) -> LoadedScenario:
    """Load a scenario using the process-wide default runtime."""

    return get_runtime().load_scenario(scenario)


def query_point(scenario: str, lon: float, lat: float) -> dict[str, Any]:
    """Query a point using the process-wide default runtime."""

    return get_runtime().query_point(scenario, lon, lat)


def clear_cache() -> None:
    """Clear the process-wide default runtime cache. Tests / controlled refresh only."""

    if _default_runtime is not None:
        _default_runtime.clear_cache()
