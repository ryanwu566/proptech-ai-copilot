from __future__ import annotations

from datetime import date
import gzip
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
import shapefile
from shapely.geometry import mapping, Polygon

from services.location_insight_service import analyze_location
from services.nlsc_village_boundary_runtime import NlscVillageBoundaryRuntime
from services.ris_demographics_insight import build_demographics_insight
from services.ris_population_query import RisPopulationQueryUnavailable
from services.ris_village_resolver import RisVillageResolver


def _artifact() -> bytes:
    features = [
        {
            "type": "Feature",
            "properties": {
                "county_name": "縣A",
                "town_name": "鎮A",
                "village_name": "甲里",
                "village_code": "A1",
            },
            "geometry": mapping(Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])),
        },
        {
            "type": "Feature",
            "properties": {
                "county_name": "縣A",
                "town_name": "鎮A",
                "village_name": "乙里",
                "village_code": "B1",
            },
            "geometry": mapping(Polygon([(1, 0), (2, 0), (2, 1), (1, 1), (1, 0)])),
        },
        {
            "type": "Feature",
            "properties": {
                "county_name": "縣B",
                "town_name": "鎮B",
                "village_name": "",
                "village_code": "SPECIALS01",
            },
            "geometry": mapping(Polygon([(10, 0), (11, 0), (11, 1), (10, 1), (10, 0)])),
        },
    ]
    return json.dumps({"type": "FeatureCollection", "features": features}).encode()


def _runtime(*, calls: list[int] | None = None) -> NlscVillageBoundaryRuntime:
    data = _artifact()
    loader = (lambda: calls.append(1) or data) if calls is not None else lambda: data
    return NlscVillageBoundaryRuntime(
        artifact_loader=loader,
        expected_sha256=hashlib.sha256(data).hexdigest(),
        demographic_codes={"A1", "B1"},
    )


def _row(month: str, *, population: int = 20, households: int = 8, ratios: bool = True) -> dict[str, object]:
    return {
        "statistic_yyymm": month,
        "statistic_month": date(int(month[:-2]) + 1911, int(month[-2:]), 1),
        "district_code": "A1",
        "site_id": "縣A鎮A",
        "village": "完全不同的顯示名稱",
        "household_count": households,
        "total_population": population,
        "child_ratio": 0.1 if ratios else None,
        "working_age_ratio": 0.8 if ratios else None,
        "elderly_ratio": 0.1 if ratios else None,
        "average_household_size": 2.5 if ratios else None,
        "source_provider": "RIS",
        "source_dataset": "ODRP014",
    }


class FakeQuery:
    def __init__(self, *, latest=None, history=None, error: Exception | None = None):
        self.latest_row = latest if latest is not None else _row("11507")
        self.history_rows = history if history is not None else [_row("11506"), _row("11507")]
        self.error = error
        self.latest_codes: list[str] = []
        self.history_calls: list[tuple[str, int]] = []

    def latest(self, district_code: str):
        if self.error:
            raise self.error
        self.latest_codes.append(district_code)
        return self.latest_row

    def history(self, district_code: str, *, limit: int):
        if self.error:
            raise self.error
        self.history_calls.append((district_code, limit))
        return self.history_rows


def test_urban_point_resolves_unique_polygon() -> None:
    result = _runtime().resolve(latitude=0.5, longitude=0.5)
    assert result["status"] == "resolved"
    assert result["village_code"] == "A1"


def test_rural_or_mountain_style_point_resolves_unique_polygon() -> None:
    result = _runtime().resolve(latitude=0.5, longitude=1.5)
    assert result["status"] == "resolved"
    assert result["village_code"] == "B1"


def test_ocean_point_is_unresolved() -> None:
    assert _runtime().resolve(latitude=20, longitude=125)["status"] == "unresolved"


def test_shared_boundary_is_ambiguous() -> None:
    result = _runtime().resolve(latitude=0.5, longitude=1.0)
    assert result["status"] == "ambiguous"
    assert result["reason"] == "multiple_intersecting_polygons"


def test_blank_special_geometry_is_unresolved() -> None:
    result = _runtime().resolve(latitude=0.5, longitude=10.5)
    assert result["status"] == "unresolved"
    assert result["reason"] == "non_demographic_boundary_geometry"


def test_villcode_is_used_as_primary_district_code_without_name_join() -> None:
    query = FakeQuery()
    result = RisVillageResolver(boundary_runtime=_runtime(), demographics_query=query).resolve(latitude=0.5, longitude=0.5)
    assert result["location"]["district_code"] == "A1"
    assert query.latest_codes == ["A1"]


def test_no_name_fuzzy_fallback_is_attempted() -> None:
    query = FakeQuery(latest=None)
    result = RisVillageResolver(boundary_runtime=_runtime(), demographics_query=query).resolve(latitude=0.5, longitude=0.5)
    assert result["location"]["village"] == "甲里"
    assert result["demographics"]["status"] == "available"
    assert query.latest_codes == ["A1"]


def test_latest_and_thirteen_month_history_are_summarized() -> None:
    history = [_row(f"114{month:02d}", population=month) for month in range(1, 13)] + [_row("11501", population=20)]
    result = RisVillageResolver(boundary_runtime=_runtime(), demographics_query=FakeQuery(history=history)).resolve(latitude=0.5, longitude=0.5)
    demographics = result["demographics"]
    assert demographics["observed_month_count"] == 13
    assert demographics["first_month"] == "11401"
    assert demographics["last_month"] == "11501"
    assert demographics["population_change"] == 19
    assert demographics["has_month_gaps"] is False


def test_zero_population_preserves_null_ratios() -> None:
    result = build_demographics_insight(_row("11507", population=0, ratios=False), [_row("11507", population=0, ratios=False)])
    assert result["total_population"] == 0
    assert result["child_ratio"] is None
    assert result["average_household_size"] is None
    assert result["population_change_ratio"] is None


def test_no_data_does_not_fail_location_identity() -> None:
    query = FakeQuery(latest=None)
    query.latest_row = None
    result = RisVillageResolver(boundary_runtime=_runtime(), demographics_query=query).resolve(latitude=0.5, longitude=0.5)
    assert result["location"]["status"] == "resolved"
    assert result["demographics"]["status"] == "no_data"


def test_database_unavailable_does_not_fail_location_identity() -> None:
    query = FakeQuery(error=RisPopulationQueryUnavailable())
    result = RisVillageResolver(boundary_runtime=_runtime(), demographics_query=query).resolve(latitude=0.5, longitude=0.5)
    assert result["location"]["status"] == "resolved"
    assert result["demographics"] == {"status": "no_data", "reason": "demographics_unavailable"}


def test_location_insight_still_succeeds_when_demographics_unavailable() -> None:
    result = analyze_location(
        latitude=0.5,
        longitude=0.5,
        village_resolver=type("UnavailableResolver", (), {"resolve": lambda self, **_: (_ for _ in ()).throw(RuntimeError("unavailable"))})(),
        nearby_fetcher=lambda *args: {"source": "unavailable", "categories": [], "category_score_map": {}, "nearest_places": []},
    )
    assert result["resolved_location"] is not None
    assert result["demographics"]["status"] == "no_data"


def test_process_local_artifact_and_strtree_cache_load_once() -> None:
    calls: list[int] = []
    runtime = _runtime(calls=calls)
    runtime.resolve(latitude=0.5, longitude=0.5)
    runtime.resolve(latitude=0.5, longitude=1.5)
    assert calls == [1]
    assert runtime.loaded is True


def test_checksum_mismatch_is_unavailable() -> None:
    runtime = NlscVillageBoundaryRuntime(artifact_loader=_artifact, expected_sha256="0" * 64)
    assert runtime.resolve(latitude=0.5, longitude=0.5)["status"] == "unavailable"


def test_gzip_artifact_loads_through_runtime() -> None:
    data = _artifact()
    compressed = gzip.compress(data, mtime=0)
    runtime = NlscVillageBoundaryRuntime(
        artifact_loader=lambda: compressed,
        expected_sha256=hashlib.sha256(compressed).hexdigest(),
        demographic_codes={"A1", "B1"},
    )
    assert runtime.resolve(latitude=0.5, longitude=0.5)["village_code"] == "A1"


def test_corrupted_gzip_artifact_is_rejected() -> None:
    data = gzip.compress(_artifact(), mtime=0)[:-8]
    runtime = NlscVillageBoundaryRuntime(
        artifact_loader=lambda: data,
        expected_sha256=hashlib.sha256(data).hexdigest(),
    )
    assert runtime.resolve(latitude=0.5, longitude=0.5)["status"] == "unavailable"
    assert runtime.load_error == "EOFError"


def test_malformed_schema_is_rejected() -> None:
    data = gzip.compress(b'{"type":"NotAFeatureCollection"}', mtime=0)
    runtime = NlscVillageBoundaryRuntime(
        artifact_loader=lambda: data,
        expected_sha256=hashlib.sha256(data).hexdigest(),
    )
    assert runtime.resolve(latitude=0.5, longitude=0.5)["status"] == "unavailable"
    assert runtime.load_error == "VillageBoundaryArtifactError"


def test_concurrent_cold_load_is_single_flight() -> None:
    data = _artifact()
    calls: list[int] = []
    runtime = NlscVillageBoundaryRuntime(
        artifact_loader=lambda: calls.append(1) or data,
        expected_sha256=hashlib.sha256(data).hexdigest(),
        demographic_codes={"A1", "B1"},
    )
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: runtime.resolve(latitude=0.5, longitude=0.5)["status"], range(4)))
    assert results == ["resolved"] * 4
    assert calls == [1]


def test_builder_rejects_duplicate_village_code(tmp_path) -> None:
    from scripts.build_nlsc_village_artifact import ArtifactBuildError, build_feature_collection

    base = tmp_path / "duplicate"
    writer = shapefile.Writer(str(base))
    for field in ("VILLCODE", "COUNTYNAME", "TOWNNAME", "VILLNAME"):
        writer.field(field, "C", size=32)
    writer.poly([[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]])
    writer.record("A1", "縣A", "鎮A", "甲里")
    writer.poly([[[2, 0], [3, 0], [3, 1], [2, 1], [2, 0]]])
    writer.record("A1", "縣A", "鎮A", "乙里")
    writer.close()
    base.with_suffix(".prj").write_text("GEOGCS[\"WGS 84\"]", encoding="utf-8")
    with pytest.raises(ArtifactBuildError, match="invalid PRJ"):
        build_feature_collection(tmp_path)


def test_runtime_has_no_request_time_download_or_tgos_dependency() -> None:
    runtime = _runtime()
    assert runtime.resolve(latitude=0.5, longitude=0.5)["source"] == "nlsc_village_boundary"
    assert "tgos" not in type(runtime).__module__
