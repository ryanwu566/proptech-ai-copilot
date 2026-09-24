"""Process-local runtime for a verified NLSC village-boundary artifact."""

from __future__ import annotations

from dataclasses import dataclass
import gzip
import hashlib
import json
from numbers import Integral
import os
from pathlib import Path
from threading import Lock
import time
from typing import Any, Callable

from shapely.geometry import Point, shape
from shapely.geometry.base import BaseGeometry
from shapely.strtree import STRtree


ArtifactLoader = Callable[[], bytes]


@dataclass(frozen=True)
class VillageBoundary:
    county: str
    town: str
    village: str
    village_code: str
    geometry: BaseGeometry
    source_vintage: str | None
    source_provenance: str | None


class VillageBoundaryArtifactError(RuntimeError):
    """The processed boundary artifact failed its bounded contract."""


class NlscVillageBoundaryRuntime:
    """Load one verified artifact per process and resolve points through STRtree."""

    def __init__(
        self,
        *,
        artifact_loader: ArtifactLoader | None = None,
        artifact_path: str | Path | None = None,
        expected_sha256: str | None = None,
        source_vintage: str | None = None,
        source_provenance: str | None = None,
        demographic_codes: set[str] | None = None,
    ) -> None:
        if artifact_loader is not None and artifact_path is not None:
            raise ValueError("provide artifact_loader or artifact_path, not both")
        self._artifact_loader = artifact_loader or self._path_loader(artifact_path)
        self._expected_sha256 = expected_sha256.strip().lower() if expected_sha256 else None
        self._source_vintage = source_vintage
        self._source_provenance = source_provenance
        self._demographic_codes = set(demographic_codes or ())
        self._load_lock = Lock()
        self._loaded = False
        self._load_error = ""
        self._tree: STRtree | None = None
        self._boundaries: tuple[VillageBoundary, ...] = ()
        self._geometry_ids: dict[int, int] = {}
        self._load_metrics: dict[str, float] = {}

    @classmethod
    def from_environment(cls, *, demographic_codes: set[str] | None = None) -> "NlscVillageBoundaryRuntime":
        path = os.getenv("NLSC_VILLAGE_BOUNDARY_ARTIFACT_PATH", "").strip()
        checksum = os.getenv("NLSC_VILLAGE_BOUNDARY_ARTIFACT_SHA256", "").strip() or None
        vintage = os.getenv("NLSC_VILLAGE_BOUNDARY_SOURCE_VINTAGE", "").strip() or None
        provenance = os.getenv("NLSC_VILLAGE_BOUNDARY_SOURCE_PROVENANCE", "").strip() or None
        loader = None
        if not path and os.getenv("NLSC_VILLAGE_BOUNDARY_R2_KEY", "").strip():
            loader = cls._r2_loader()
        return cls(
            artifact_loader=loader,
            artifact_path=path or None,
            expected_sha256=checksum,
            source_vintage=vintage,
            source_provenance=provenance,
            demographic_codes=demographic_codes,
        )

    @staticmethod
    def _r2_loader() -> ArtifactLoader:
        bucket = os.getenv("R2_BUCKET", "proptech-government-data").strip()
        key = os.getenv("NLSC_VILLAGE_BOUNDARY_R2_KEY", "").strip()
        endpoint = os.getenv("R2_ENDPOINT", "").strip()
        region = os.getenv("R2_REGION", "auto").strip() or "auto"

        def load() -> bytes:
            if not endpoint or not os.getenv("R2_ACCESS_KEY_ID", "").strip() or not os.getenv("R2_SECRET_ACCESS_KEY", "").strip():
                raise VillageBoundaryArtifactError("R2 artifact credentials are unavailable")
            import boto3

            client = boto3.client(
                "s3",
                endpoint_url=endpoint,
                aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                region_name=region,
            )
            body = client.get_object(Bucket=bucket, Key=key)["Body"]
            data = body.read() if hasattr(body, "read") else body
            if not isinstance(data, bytes):
                raise VillageBoundaryArtifactError("R2 artifact body is not bytes")
            return data

        return load

    @staticmethod
    def _path_loader(path: str | Path | None) -> ArtifactLoader | None:
        if path is None:
            return None
        selected = Path(path)
        return lambda: selected.read_bytes()

    @property
    def load_error(self) -> str | None:
        self._ensure_loaded()
        return self._load_error or None

    @property
    def loaded(self) -> bool:
        self._ensure_loaded()
        return self._loaded and self._tree is not None

    @property
    def load_metrics(self) -> dict[str, float]:
        self._ensure_loaded()
        return dict(self._load_metrics)

    def resolve(self, *, latitude: float, longitude: float) -> dict[str, Any]:
        if not self._ensure_loaded():
            return self._unavailable("boundary_artifact_unavailable")
        assert self._tree is not None
        point = Point(float(longitude), float(latitude))
        candidates = self._candidate_boundaries(point)
        if not candidates:
            return self._unresolved("zero_polygon")
        if len(candidates) > 1:
            return self._unresolved("multiple_intersecting_polygons", status="ambiguous", candidate_count=len(candidates))
        boundary = candidates[0]
        if not boundary.village and boundary.village_code not in self._demographic_codes:
            return self._unresolved("non_demographic_boundary_geometry")
        return {
            "status": "resolved",
            "county": boundary.county,
            "town": boundary.town,
            "village": boundary.village,
            "village_code": boundary.village_code,
            "district_code": boundary.village_code,
            "source": "nlsc_village_boundary",
            "source_vintage": boundary.source_vintage,
            "reason": "unique_intersection",
        }

    def _candidate_boundaries(self, point: Point) -> list[VillageBoundary]:
        assert self._tree is not None
        selected = self._tree.query(point, predicate="intersects")
        candidates: list[VillageBoundary] = []
        for item in selected:
            index = int(item) if isinstance(item, Integral) else self._geometry_ids.get(id(item))
            if index is not None:
                candidates.append(self._boundaries[index])
        return candidates

    def _ensure_loaded(self) -> bool:
        if self._loaded:
            return self._tree is not None
        with self._load_lock:
            if self._loaded:
                return self._tree is not None
            started = time.perf_counter()
            try:
                if self._artifact_loader is None:
                    raise VillageBoundaryArtifactError("no processed boundary artifact configured")
                data = self._artifact_loader()
                if self._expected_sha256:
                    actual = hashlib.sha256(data).hexdigest()
                    if actual != self._expected_sha256:
                        raise VillageBoundaryArtifactError("boundary artifact checksum mismatch")
                decode_started = time.perf_counter()
                payload = gzip.decompress(data) if data.startswith(b"\x1f\x8b") else data
                self._boundaries = tuple(self._parse(payload))
                tree_started = time.perf_counter()
                if not self._boundaries:
                    raise VillageBoundaryArtifactError("boundary artifact contains no polygon features")
                geometries = [item.geometry for item in self._boundaries]
                self._tree = STRtree(geometries)
                self._geometry_ids = {id(geometry): index for index, geometry in enumerate(geometries)}
                self._load_metrics = {
                    "decode_ms": round((tree_started - decode_started) * 1000, 3),
                    "strtree_build_ms": round((time.perf_counter() - tree_started) * 1000, 3),
                    "cold_load_ms": round((time.perf_counter() - started) * 1000, 3),
                }
            except Exception as exc:
                self._load_error = type(exc).__name__
                self._tree = None
            self._loaded = True
        return self._tree is not None

    def _parse(self, data: bytes) -> list[VillageBoundary]:
        try:
            document = json.loads(data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise VillageBoundaryArtifactError("boundary artifact is not UTF-8 JSON") from exc
        if not isinstance(document, dict) or document.get("type") != "FeatureCollection":
            raise VillageBoundaryArtifactError("boundary artifact must be a FeatureCollection")
        raw_features = document.get("features")
        if not isinstance(raw_features, list):
            raise VillageBoundaryArtifactError("boundary artifact features must be a list")
        parsed: list[VillageBoundary] = []
        for feature in raw_features:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise VillageBoundaryArtifactError("boundary artifact contains an invalid feature")
            properties = feature.get("properties")
            geometry_data = feature.get("geometry")
            if not isinstance(properties, dict) or not isinstance(geometry_data, dict):
                raise VillageBoundaryArtifactError("boundary feature is missing properties or geometry")
            geometry = shape(geometry_data)
            if geometry.is_empty or geometry.geom_type not in {"Polygon", "MultiPolygon"} or not geometry.is_valid:
                raise VillageBoundaryArtifactError("boundary feature geometry is invalid")
            parsed.append(
                VillageBoundary(
                    county=str(properties.get("county_name", "")),
                    town=str(properties.get("town_name", "")),
                    village=str(properties.get("village_name", "")),
                    village_code=str(properties.get("village_code", "")),
                    geometry=geometry,
                    source_vintage=str(properties.get("source_vintage") or self._source_vintage or "") or None,
                    source_provenance=str(properties.get("source_provenance") or self._source_provenance or "") or None,
                )
            )
        return parsed

    @staticmethod
    def _unavailable(reason: str) -> dict[str, Any]:
        return {
            "status": "unavailable",
            "county": None,
            "town": None,
            "village": None,
            "village_code": None,
            "district_code": None,
            "source": "nlsc_village_boundary",
            "source_vintage": None,
            "reason": reason,
        }

    @staticmethod
    def _unresolved(reason: str, *, status: str = "unresolved", candidate_count: int | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "status": status,
            "county": None,
            "town": None,
            "village": None,
            "village_code": None,
            "district_code": None,
            "source": "nlsc_village_boundary",
            "source_vintage": None,
            "reason": reason,
        }
        if candidate_count is not None:
            result["candidate_count"] = candidate_count
        return result


_DEFAULT_RUNTIME: NlscVillageBoundaryRuntime | None = None
_DEFAULT_RUNTIME_LOCK = Lock()


def get_default_village_boundary_runtime() -> NlscVillageBoundaryRuntime:
    global _DEFAULT_RUNTIME
    if _DEFAULT_RUNTIME is None:
        with _DEFAULT_RUNTIME_LOCK:
            if _DEFAULT_RUNTIME is None:
                _DEFAULT_RUNTIME = NlscVillageBoundaryRuntime.from_environment()
    return _DEFAULT_RUNTIME
