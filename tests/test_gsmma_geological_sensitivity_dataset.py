from __future__ import annotations

import pytest
from pyproj import CRS
from shapely.geometry import MultiPolygon, Point, Polygon

from services.gsmma_geological_sensitivity_dataset import (
    CrsInvalidError,
    UnsupportedDatasetError,
    normalize_feature,
    parse_index_csv,
    resolve_source_crs,
    summarize_normalization,
)


HEADERS = (
    "No.,地質敏感區類型,地質敏感區編號,地質敏感區名稱,公告日期,文號,"
    "座標系統1,座標系統2,下載連結\n"
)


def _csv(*rows: str, bom: bool = False) -> bytes:
    text = HEADERS + "\n".join(rows) + "\n"
    return (("\ufeff" if bom else "") + text).encode("utf-8")


@pytest.mark.parametrize(
    ("official", "canonical"),
    [
        ("地質遺跡地質敏感區", "geological_heritage_sensitive_area"),
        ("地下水補注地質敏感區", "groundwater_recharge_sensitive_area"),
        ("活動斷層地質敏感區", "active_fault_sensitive_area"),
        ("山崩與地滑地質敏感區", "landslide_sensitive_area"),
    ],
)
def test_index_preserves_official_category_and_adds_canonical_category(
    official: str, canonical: str
) -> None:
    records = parse_index_csv(
        _csv(f"1,{official},F0001,測試區,103年1月20日,經地字第123號,TWD97 TM2 121,,https://example.gov.tw/a.zip")
    )

    assert records[0].official_category == official
    assert records[0].canonical_category == canonical
    assert records[0].announcement_date == "2014-01-20"
    assert records[0].announcement_no == "經地字第123號"


def test_index_accepts_utf8_bom_without_corrupting_official_headers() -> None:
    records = parse_index_csv(
        _csv(
            "7,活動斷層地質敏感區,F0007,測試斷層,2024-06-27,經授地字第7號,TWD97 TM2 121,,https://example.gov.tw/f.zip",
            bom=True,
        )
    )

    assert records[0].source_index_no == "7"
    assert records[0].official_name == "測試斷層"


def test_index_rejects_non_utf8_instead_of_guessing_legacy_encoding() -> None:
    with pytest.raises(UnsupportedDatasetError, match="UTF-8"):
        parse_index_csv(HEADERS.encode("cp950") + b"\xff\xfe")


def test_index_sorting_is_deterministic_and_whitespace_is_normalized() -> None:
    records = parse_index_csv(
        _csv(
            " 2 ,山崩與地滑地質敏感區,L0002, 第二區 ,2024/06/28, 文號2 , TWD97 , ,https://example.gov.tw/2.zip ",
            "1,山崩與地滑地質敏感區,L0001,第一區,2024-06-27,文號1,TWD97,,https://example.gov.tw/1.zip",
        )
    )

    assert [record.source_index_no for record in records] == ["1", "2"]
    assert records[1].official_name == "第二區"
    assert records[1].declared_crs_values == ("TWD97",)


def test_index_rejects_unknown_category() -> None:
    with pytest.raises(UnsupportedDatasetError, match="category"):
        parse_index_csv(
            _csv("1,未知類型,X1,未知,2024-06-27,文號,TWD97,,https://example.gov.tw/x.zip")
        )


def test_index_rejects_missing_required_header() -> None:
    payload = HEADERS.replace("文號,", "").encode("utf-8")
    with pytest.raises(UnsupportedDatasetError, match="missing required index fields"):
        parse_index_csv(payload)


def test_index_rejects_conflicting_duplicate_identifier() -> None:
    with pytest.raises(UnsupportedDatasetError, match="duplicate"):
        parse_index_csv(
            _csv(
                "1,活動斷層地質敏感區,F0001,甲,2024-06-27,文號1,TWD97 TM2 121,,https://example.gov.tw/a.zip",
                "2,活動斷層地質敏感區,F0001,乙,2024-06-28,文號2,TWD97 TM2 121,,https://example.gov.tw/b.zip",
            )
        )


@pytest.mark.parametrize(
    ("epsg", "declaration"),
    [
        (3825, "TWD97 TM2 119"),
        (3826, "TWD97 TM2 121"),
        (3827, "TWD67 TM2 119"),
        (3828, "TWD67 TM2 121"),
    ],
)
def test_crs_is_resolved_per_package(epsg: int, declaration: str) -> None:
    resolved = resolve_source_crs(CRS.from_epsg(epsg).to_wkt(), (declaration,))
    assert resolved.to_epsg() == epsg


def test_crs_family_declaration_accepts_specific_prj_central_meridian() -> None:
    resolved = resolve_source_crs(CRS.from_epsg(3826).to_wkt(), ("TWD97",))
    assert resolved.to_epsg() == 3826


@pytest.mark.parametrize(
    ("prj", "declared", "message"),
    [
        ("", ("TWD97",), "missing"),
        ("not wkt", ("TWD97",), "parse"),
        (CRS.from_epsg(3826).to_wkt(), (), "missing"),
        (CRS.from_epsg(3826).to_wkt(), ("TWD67 TM2 121",), "conflicts"),
        (CRS.from_epsg(3857).to_wkt(), ("EPSG:3857",), "unsupported"),
    ],
)
def test_crs_missing_ambiguous_or_contradictory_fails_closed(
    prj: str, declared: tuple[str, ...], message: str
) -> None:
    with pytest.raises(CrsInvalidError, match=message):
        resolve_source_crs(prj, declared)


def _record():
    return parse_index_csv(
        _csv(
            "1,活動斷層地質敏感區,F0001,測試區,2024-06-27,經地字第1號,TWD97 TM2 121,,https://example.gov.tw/a.zip"
        )
    )[0]


def _normalize(geometry):
    return normalize_feature(
        geometry,
        {"OBJECTID": 7, "備註": "原始值"},
        _record(),
        source_crs=CRS.from_epsg(3826),
        dataset_version="2024-06-27",
        source_package_sha256="a" * 64,
    )


def test_polygon_is_transformed_to_wgs84_and_preserves_audit_metadata() -> None:
    result = _normalize(
        Polygon([(250000, 2770000), (250100, 2770000), (250100, 2770100), (250000, 2770000)])
    )

    assert result.feature is not None
    assert result.feature.geometry.geom_type == "Polygon"
    lon, lat = result.feature.geometry.exterior.coords[0]
    assert lon == pytest.approx(121.0, abs=1e-7)
    assert lat == pytest.approx(25.03812167, abs=1e-7)
    assert result.feature.source_crs == "EPSG:3826"
    assert result.feature.target_crs == "EPSG:4326"
    assert result.feature.official_category == "活動斷層地質敏感區"
    assert result.feature.canonical_category == "active_fault_sensitive_area"
    assert result.feature.original_attributes == {"OBJECTID": 7, "備註": "原始值"}


def test_valid_multipolygon_is_accepted() -> None:
    first = Polygon([(250000, 2770000), (250010, 2770000), (250010, 2770010), (250000, 2770000)])
    second = Polygon([(250020, 2770020), (250030, 2770020), (250030, 2770030), (250020, 2770020)])
    result = _normalize(MultiPolygon([first, second]))
    assert result.feature is not None
    assert result.feature.geometry.geom_type == "MultiPolygon"


def test_invalid_bow_tie_is_repaired_and_counted() -> None:
    result = _normalize(
        Polygon([(250000, 2770000), (250100, 2770100), (250100, 2770000), (250000, 2770100), (250000, 2770000)])
    )
    features, quarantine, stats = summarize_normalization([result])

    assert len(features) == 1
    assert quarantine == []
    assert stats.invalid_geometry_count == 1
    assert stats.repaired_geometry_count == 1
    assert stats.accepted_feature_count == 1


def test_non_polygonal_repair_remnants_are_counted() -> None:
    result = _normalize(
        Polygon(
            [
                (250000, 2770000),
                (250100, 2770100),
                (250200, 2770000),
                (250100, 2770100),
                (250100, 2770000),
                (250000, 2770000),
            ]
        )
    )
    features, quarantine, stats = summarize_normalization([result])

    assert len(features) == 1
    assert quarantine == []
    assert stats.discarded_repair_part_count == 1


@pytest.mark.parametrize(
    ("geometry", "counter"),
    [
        (Polygon(), "empty_geometry_count"),
        (Point(250000, 2770000), "unsupported_geometry_count"),
    ],
)
def test_empty_and_unsupported_geometry_are_quarantined(geometry, counter: str) -> None:
    result = _normalize(geometry)
    features, quarantine, stats = summarize_normalization([result])

    assert features == []
    assert len(quarantine) == 1
    assert stats.rejected_feature_count == 1
    assert getattr(stats, counter) == 1


def test_stats_preserve_category_crs_and_geometry_distributions() -> None:
    polygon = Polygon([(250000, 2770000), (250010, 2770000), (250010, 2770010), (250000, 2770000)])
    features, quarantine, stats = summarize_normalization([_normalize(polygon), _normalize(Point(0, 0))])

    assert len(features) == 1
    assert len(quarantine) == 1
    assert stats.input_feature_count == 2
    assert stats.official_category_distribution == {"活動斷層地質敏感區": 2}
    assert stats.canonical_category_distribution == {"active_fault_sensitive_area": 2}
    assert stats.source_crs_distribution == {"EPSG:3826": 2}
    assert stats.geometry_type_distribution == {"Point": 1, "Polygon": 1}
