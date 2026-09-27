"""Read-only runtime for immutable GSMMA geological-sensitivity artifacts."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
import re
import threading
from typing import Any, Optional, Protocol

from shapely.geometry import Point
from shapely.strtree import STRtree

from services.gsmma_geological_sensitivity_artifact import (
    ARTIFACT_SCHEMA,
    DATASET_NAME,
    MANIFEST_SCHEMA,
    SCHEMA_VERSION,
    ArtifactBuildError,
    load_artifact,
)
from services.gsmma_geological_sensitivity_dataset import NormalizedFeature


RELEASE_PREFIX = "processed/gsmma/geological-sensitivity/v1"
DATASET_VERSION_ENV = "GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION"
REQUIRED_R2_ENV = (
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT",
    "R2_BUCKET",
    "R2_REGION",
)
MAX_MATCHED_FEATURES = 1_000
_VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}\Z")


class GeologicalSensitivityRuntimeError(Exception):
    status = "artifact_invalid"

    def __init__(self, message: str, *, dataset_version: str | None = None) -> None:
        super().__init__(message)
        self.dataset_version = dataset_version


class SourceUnavailableError(GeologicalSensitivityRuntimeError):
    status = "source_unavailable"


class ChecksumMismatchError(GeologicalSensitivityRuntimeError):
    status = "checksum_mismatch"


class ArtifactInvalidError(GeologicalSensitivityRuntimeError):
    status = "artifact_invalid"


class UnsupportedDatasetRuntimeError(GeologicalSensitivityRuntimeError):
    status = "unsupported_dataset"


class CrsInvalidRuntimeError(GeologicalSensitivityRuntimeError):
    status = "crs_invalid"


class QueryError(GeologicalSensitivityRuntimeError):
    status = "query_error"


class R2Client(Protocol):
    def get_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:  # noqa: N803
        ...


def validate_dataset_version(version: str) -> str:
    if not isinstance(version, str):
        raise UnsupportedDatasetRuntimeError("dataset version must be a string")
    cleaned = version.strip()
    if cleaned.casefold() == "latest" or not _VERSION_RE.fullmatch(cleaned) or ":" in cleaned:
        raise UnsupportedDatasetRuntimeError(
            f"invalid immutable geological-sensitivity dataset version: {version!r}",
            dataset_version=cleaned or None,
        )
    return cleaned


def manifest_key(version: str) -> str:
    return f"{RELEASE_PREFIX}/{validate_dataset_version(version)}/manifest.json"


def artifact_key(version: str) -> str:
    return f"{RELEASE_PREFIX}/{validate_dataset_version(version)}/features.json.gz"


def build_default_r2_client() -> R2Client:
    missing = [name for name in REQUIRED_R2_ENV if not os.environ.get(name)]
    if missing:
        raise SourceUnavailableError(
            "missing required R2 environment variables: " + ", ".join(missing)
        )
    import boto3
    from botocore.config import Config

    return boto3.session.Session().client(
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


def _get_object_bytes(client: R2Client, bucket: str, key: str, version: str) -> bytes:
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        body = response.get("Body")
        if body is None:
            raise RuntimeError("response has no Body")
        payload = body.read()
        if not isinstance(payload, bytes):
            raise TypeError("object body is not bytes")
        return payload
    except Exception as exc:
        raise SourceUnavailableError(
            f"R2 GET failed for immutable object {key}: {type(exc).__name__}",
            dataset_version=version,
        ) from exc


@dataclass(frozen=True)
class LoadedDataset:
    dataset_version: str
    manifest: dict[str, Any]
    artifact_sha256: str
    source_vintage: str
    features: list[NormalizedFeature]
    geometries: list[Any]
    tree: STRtree


def _parse_manifest(payload: bytes, version: str) -> dict[str, Any]:
    try:
        manifest = json.loads(payload.decode("utf-8"))
    except Exception as exc:
        raise ArtifactInvalidError(
            f"manifest decode failed: {type(exc).__name__}", dataset_version=version
        ) from exc
    if not isinstance(manifest, dict):
        raise ArtifactInvalidError("manifest root is not an object", dataset_version=version)
    if (
        manifest.get("manifest_schema") != MANIFEST_SCHEMA
        or manifest.get("schema_version") != SCHEMA_VERSION
        or manifest.get("dataset") != DATASET_NAME
    ):
        raise UnsupportedDatasetRuntimeError(
            "unsupported geological-sensitivity manifest schema", dataset_version=version
        )
    if manifest.get("dataset_version") != version:
        raise UnsupportedDatasetRuntimeError(
            "manifest dataset version does not match configured version",
            dataset_version=version,
        )
    if manifest.get("quality_status") != "accepted":
        raise UnsupportedDatasetRuntimeError(
            "manifest quality is not accepted", dataset_version=version
        )
    if manifest.get("target_crs") != "EPSG:4326":
        raise CrsInvalidRuntimeError(
            "manifest target CRS must be EPSG:4326", dataset_version=version
        )
    expected_sha = manifest.get("artifact_sha256")
    if not isinstance(expected_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", expected_sha):
        raise ArtifactInvalidError("manifest artifact SHA256 is invalid", dataset_version=version)
    if not isinstance(manifest.get("feature_count"), int) or manifest["feature_count"] < 0:
        raise ArtifactInvalidError("manifest feature count is invalid", dataset_version=version)
    if not isinstance(manifest.get("source_vintage"), str) or not manifest["source_vintage"]:
        raise ArtifactInvalidError("manifest source vintage is invalid", dataset_version=version)
    return manifest


def _load_uncached(version: str, client: R2Client, bucket: str) -> LoadedDataset:
    manifest = _parse_manifest(
        _get_object_bytes(client, bucket, manifest_key(version), version), version
    )
    artifact_bytes = _get_object_bytes(client, bucket, artifact_key(version), version)
    actual_sha = hashlib.sha256(artifact_bytes).hexdigest()
    if actual_sha.lower() != manifest["artifact_sha256"].lower():
        raise ChecksumMismatchError(
            "geological-sensitivity artifact checksum mismatch", dataset_version=version
        )
    try:
        document, features = load_artifact(artifact_bytes)
    except ArtifactBuildError as exc:
        raise ArtifactInvalidError(
            f"artifact decode failed: {exc}", dataset_version=version
        ) from exc
    if (
        document.get("schema") != ARTIFACT_SCHEMA
        or document.get("dataset_version") != version
        or document.get("target_crs") != "EPSG:4326"
    ):
        raise ArtifactInvalidError("artifact metadata mismatch", dataset_version=version)
    if len(features) != manifest["feature_count"]:
        raise ArtifactInvalidError("artifact feature count mismatch", dataset_version=version)
    geometries = [feature.geometry for feature in features]
    return LoadedDataset(
        dataset_version=version,
        manifest=manifest,
        artifact_sha256=actual_sha,
        source_vintage=manifest["source_vintage"],
        features=features,
        geometries=geometries,
        tree=STRtree(geometries),
    )


class GsmmaGeologicalSensitivityRuntime:
    def __init__(
        self,
        client_factory=build_default_r2_client,
        *,
        bucket: str | None = None,
        dataset_version: str | None = None,
    ) -> None:
        self._client_factory = client_factory
        self._bucket = bucket
        self._explicit_version = dataset_version
        self._client: R2Client | None = None
        self._loaded: LoadedDataset | None = None
        self._lock = threading.Lock()
        self.cold_load_count = 0

    def configured_dataset_version(self) -> str:
        value = self._explicit_version
        if value is None:
            value = os.environ.get(DATASET_VERSION_ENV)
        if not value:
            raise SourceUnavailableError(
                f"missing required environment variable: {DATASET_VERSION_ENV}"
            )
        return validate_dataset_version(value)

    def configured_dataset_version_or_none(self) -> str | None:
        value = self._explicit_version
        if value is None:
            value = os.environ.get(DATASET_VERSION_ENV)
        return value.strip() if isinstance(value, str) and value.strip() else None

    def _get_client(self) -> R2Client:
        if self._client is None:
            self._client = self._client_factory()
        return self._client

    def load_dataset(self) -> LoadedDataset:
        version = self.configured_dataset_version()
        cached = self._loaded
        if cached is not None:
            if cached.dataset_version != version:
                raise UnsupportedDatasetRuntimeError(
                    "configured dataset version changed after load", dataset_version=version
                )
            return cached
        with self._lock:
            if self._loaded is not None:
                return self._loaded
            bucket = self._bucket or _bucket_name()
            loaded = _load_uncached(version, self._get_client(), bucket)
            self._loaded = loaded
            self.cold_load_count += 1
            return loaded

    def query_point(self, lon: float, lat: float) -> dict[str, Any]:
        try:
            lon_value, lat_value = float(lon), float(lat)
        except (TypeError, ValueError) as exc:
            raise QueryError("query coordinates must be numeric") from exc
        if (
            not math.isfinite(lon_value)
            or not math.isfinite(lat_value)
            or not -180 <= lon_value <= 180
            or not -90 <= lat_value <= 90
        ):
            raise QueryError("query coordinates are outside WGS84 bounds")
        loaded = self.load_dataset()
        try:
            point = Point(lon_value, lat_value)
            candidate_indices = loaded.tree.query(point)
            hits = [
                loaded.features[int(index)]
                for index in candidate_indices
                if loaded.features[int(index)].geometry.intersects(point)
            ]
        except GeologicalSensitivityRuntimeError:
            raise
        except Exception as exc:
            raise QueryError(
                f"geological-sensitivity spatial query failed: {type(exc).__name__}",
                dataset_version=loaded.dataset_version,
            ) from exc
        if len(hits) > MAX_MATCHED_FEATURES:
            raise QueryError(
                "geological-sensitivity match limit exceeded",
                dataset_version=loaded.dataset_version,
            )
        grouped: dict[tuple[str, ...], dict[str, Any]] = {}
        for feature in hits:
            identity = (
                feature.official_category,
                feature.canonical_category,
                feature.sensitivity_area_no,
                feature.official_name,
                feature.announcement_no,
                feature.announcement_date,
            )
            evidence = grouped.get(identity)
            if evidence is None:
                grouped[identity] = {
                    "official_category": feature.official_category,
                    "canonical_category": feature.canonical_category,
                    "official_name": feature.official_name,
                    "sensitivity_area_no": feature.sensitivity_area_no,
                    "announcement_no": feature.announcement_no,
                    "announcement_date": feature.announcement_date,
                    "source_agency": feature.source_agency,
                    "source_url": feature.source_url,
                    "source_crs": feature.source_crs,
                    "matched_fragment_count": 1,
                }
            else:
                evidence["matched_fragment_count"] += 1
        matches = sorted(
            grouped.values(),
            key=lambda evidence: (
                evidence["canonical_category"],
                evidence["sensitivity_area_no"],
                evidence["announcement_no"],
                evidence["official_name"],
            ),
        )
        common = {
            "dataset_version": loaded.dataset_version,
            "artifact_sha256": loaded.artifact_sha256,
            "source_vintage": loaded.source_vintage,
        }
        if not matches:
            return {
                "status": "no_match",
                "matched": False,
                "matched_count": 0,
                "matches": [],
                **common,
            }
        return {
            "status": "loaded",
            "matched": True,
            "matched_count": len(matches),
            "matches": matches,
            **common,
        }

    def clear_cache(self) -> None:
        with self._lock:
            self._loaded = None


_default_runtime: Optional[GsmmaGeologicalSensitivityRuntime] = None
_default_runtime_lock = threading.Lock()


def get_runtime() -> GsmmaGeologicalSensitivityRuntime:
    global _default_runtime
    if _default_runtime is None:
        with _default_runtime_lock:
            if _default_runtime is None:
                _default_runtime = GsmmaGeologicalSensitivityRuntime()
    return _default_runtime


def load_dataset() -> LoadedDataset:
    return get_runtime().load_dataset()


def query_point(lon: float, lat: float) -> dict[str, Any]:
    return get_runtime().query_point(lon, lat)


def clear_cache() -> None:
    if _default_runtime is not None:
        _default_runtime.clear_cache()
