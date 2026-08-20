from __future__ import annotations

from io import BytesIO
import json
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from pyproj import CRS, Transformer
import shapefile

from services.parcel_geometry import (
    MAX_COORDINATES,
    MAX_UPLOAD_BYTES,
    NlscCadastralProvider,
    ParcelGeometryError,
    PointReferenceProvider,
    UploadedParcelProvider,
    assess_location_geometry_consistency,
    resolve_parcel_geometry,
    select_parcel_geometry,
    spatial_intersection,
)


SQUARE = [[[121.55, 25.03], [121.55, 25.031], [121.551, 25.031], [121.551, 25.03], [121.55, 25.03]]]


def geojson_bytes(geometry_type: str = "Polygon", coordinates=None) -> bytes:
    return json.dumps({"type": geometry_type, "coordinates": coordinates or SQUARE}).encode()


def make_shapefile_zip(*, epsg: int | None = 4326, missing: str | None = None, traversal: bool = False) -> bytes:
    shp, shx, dbf = BytesIO(), BytesIO(), BytesIO()
    writer = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shapefile.POLYGON)
    writer.field("id", "N")
    ring = SQUARE[0]
    if epsg and epsg != 4326:
        transformer = Transformer.from_crs(4326, epsg, always_xy=True)
        ring = [transformer.transform(x, y) for x, y in ring]
    writer.poly([ring]); writer.record(1); writer.close()
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as output:
        for extension, body in ((".shp", shp.getvalue()), (".shx", shx.getvalue()), (".dbf", dbf.getvalue())):
            if missing != extension:
                output.writestr(f"parcel{extension}", body)
        if epsg is not None:
            output.writestr("parcel.prj", CRS.from_epsg(epsg).to_wkt())
        if traversal:
            output.writestr("../../outside.txt", "not extracted")
    return archive.getvalue()


def upload(filename: str, data: bytes, **coordinates):
    return UploadedParcelProvider().resolve(filename=filename, data=data, **coordinates)


def assert_error(code: str, filename: str, data: bytes) -> None:
    with pytest.raises(ParcelGeometryError) as caught:
        upload(filename, data)
    assert caught.value.code == code


def test_geojson_polygon_is_user_geometry_with_computed_area_and_real_timings() -> None:
    evidence = upload("parcel.geojson", geojson_bytes(), latitude=25.0305, longitude=121.5505)
    assert evidence["status"] == "user_provided"
    assert evidence["source"] == "uploaded_geojson"
    assert evidence["geometry_type"] == "Polygon"
    assert evidence["legal_boundary"] is False
    assert evidence["area_semantics"] == "computed_geometry_area"
    assert 9_000 < evidence["area_m2"] < 13_000
    assert evidence["location_geometry_consistency"] == "CONSISTENT"
    assert evidence["timing_ms"]["parse_ms"] < 500
    assert evidence["timing_ms"]["geometry_validation_ms"] >= 0


def test_geojson_multipolygon_and_feature_collection_assembly_are_deterministic() -> None:
    second = [[[121.552, 25.03], [121.552, 25.031], [121.553, 25.031], [121.553, 25.03], [121.552, 25.03]]]
    multi = upload("parcel.geojson", geojson_bytes("MultiPolygon", [SQUARE, second]))
    collection = {"type": "FeatureCollection", "features": [
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": SQUARE}},
        {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": second}},
    ]}
    merged = upload("parcel.json", json.dumps(collection).encode())
    assert multi["geometry_type"] == merged["geometry_type"] == "MultiPolygon"
    assert multi["bbox"] == merged["bbox"] == [121.55, 25.03, 121.553, 25.031]


def test_geojson_rejects_non_polygon_and_irrecoverable_geometry() -> None:
    assert_error("NO_POLYGON_FOUND", "line.geojson", geojson_bytes("LineString", [[121.5, 25], [121.6, 25.1]]))
    assert_error("INVALID_GEOMETRY", "flat.geojson", geojson_bytes("Polygon", [[[121.5, 25], [121.5, 25], [121.5, 25], [121.5, 25]]]))


def test_self_intersection_is_repaired_with_honest_marker() -> None:
    bowtie = [[[121.55, 25.03], [121.551, 25.031], [121.551, 25.03], [121.55, 25.031], [121.55, 25.03]]]
    evidence = upload("repair.geojson", geojson_bytes("Polygon", bowtie))
    assert evidence["geometry_validity"] == "REPAIRED"
    assert "repaired" in evidence["limitation"].lower()


def test_geojson_guards_feature_count_and_non_taiwan_or_swapped_coordinates() -> None:
    feature = {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": SQUARE}}
    too_many = {"type": "FeatureCollection", "features": [feature] * 1001}
    assert_error("INVALID_GEOMETRY", "many.geojson", json.dumps(too_many).encode())
    assert_error("INVALID_GEOMETRY", "swapped.geojson", geojson_bytes("Polygon", [[[25, 121], [25, 121.1], [25.1, 121.1], [25.1, 121], [25, 121]]]))
    assert_error("INVALID_GEOMETRY", "other-country.geojson", geojson_bytes("Polygon", [[[-74, 40], [-74, 40.1], [-73.9, 40.1], [-73.9, 40], [-74, 40]]]))


def test_geojson_accepts_exact_feature_limit_but_rejects_excessive_coordinates() -> None:
    feature = {"type": "Feature", "properties": {}, "geometry": {"type": "Polygon", "coordinates": SQUARE}}
    at_limit = upload("limit.geojson", json.dumps({"type": "FeatureCollection", "features": [feature] * 1000}).encode())
    assert at_limit["geometry_type"] == "Polygon"

    side = MAX_COORDINATES // 4 + 1
    ring = []
    for index in range(side): ring.append([121.55, 25.03 + index / side * 0.001])
    for index in range(side): ring.append([121.55 + index / side * 0.001, 25.031])
    for index in range(side): ring.append([121.551, 25.031 - index / side * 0.001])
    for index in range(side): ring.append([121.551 - index / side * 0.001, 25.03])
    ring.append(ring[0])
    assert_error("INVALID_GEOMETRY", "complex.geojson", geojson_bytes("Polygon", [ring]))


def test_kml_polygon_and_multigeometry_parse_under_target() -> None:
    kml = b"""<kml xmlns='http://www.opengis.net/kml/2.2'><Placemark><MultiGeometry>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>121.55,25.03 121.55,25.031 121.551,25.031 121.551,25.03 121.55,25.03</coordinates></LinearRing></outerBoundaryIs></Polygon>
      <Polygon><outerBoundaryIs><LinearRing><coordinates>121.552,25.03 121.552,25.031 121.553,25.031 121.553,25.03 121.552,25.03</coordinates></LinearRing></outerBoundaryIs></Polygon>
    </MultiGeometry></Placemark></kml>"""
    evidence = upload("parcel.kml", kml)
    assert evidence["source"] == "uploaded_kml"
    assert evidence["geometry_type"] == "MultiPolygon"
    assert evidence["timing_ms"]["parse_ms"] < 750


@pytest.mark.parametrize("payload", [b"<kml><Polygon>", b"<kml><Polygon><outerBoundaryIs><coordinates>bad</coordinates></outerBoundaryIs></Polygon></kml>"])
def test_kml_malformed_coordinates_and_xml_recover(payload: bytes) -> None:
    assert_error("PARSE_FAILED", "parcel.kml", payload)


def test_kml_external_entity_is_rejected() -> None:
    payload = b'<!DOCTYPE kml [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><kml><Polygon><outerBoundaryIs><coordinates>&xxe;</coordinates></outerBoundaryIs></Polygon></kml>'
    assert_error("PARSE_FAILED", "parcel.kml", payload)


def test_shapefile_wgs84_and_epsg3826_normalize_without_legal_claim() -> None:
    wgs84 = upload("parcel.zip", make_shapefile_zip())
    twd97 = upload("parcel.zip", make_shapefile_zip(epsg=3826))
    for evidence, crs in ((wgs84, "EPSG:4326"), (twd97, "EPSG:3826")):
        assert evidence["source"] == "uploaded_shapefile"
        assert evidence["crs_original"] == crs
        assert evidence["crs_normalized"] == "EPSG:4326"
        assert evidence["legal_boundary"] is False
        assert evidence["timing_ms"]["parse_ms"] < 1500
        assert abs(evidence["centroid"]["lng"] - 121.5505) < 0.0001


@pytest.mark.parametrize("missing", [".shx", ".dbf"])
def test_shapefile_requires_sidecars(missing: str) -> None:
    assert_error("MISSING_SHAPEFILE_COMPONENTS", "parcel.zip", make_shapefile_zip(missing=missing))


def test_shapefile_unknown_crs_and_zip_traversal_are_rejected() -> None:
    assert_error("UNKNOWN_CRS", "parcel.zip", make_shapefile_zip(epsg=None))
    assert_error("PARSE_FAILED", "parcel.zip", make_shapefile_zip(traversal=True))


@pytest.mark.parametrize("unsafe_name", ["/absolute/parcel.shp", "C:/parcel.shp", "folder/../../parcel.shp"])
def test_zip_rejects_absolute_drive_and_parent_paths(unsafe_name: str) -> None:
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as output:
        output.writestr(unsafe_name, "unsafe")
    assert_error("PARSE_FAILED", "parcel.zip", archive.getvalue())


def test_zip_rejects_oversized_decompression_before_reading_members() -> None:
    archive = BytesIO()
    with ZipFile(archive, "w", ZIP_DEFLATED) as output:
        output.writestr("parcel.shp", b"0" * (50 * 1024 * 1024 + 1))
    assert len(archive.getvalue()) < MAX_UPLOAD_BYTES
    assert_error("FILE_TOO_LARGE", "parcel.zip", archive.getvalue())


def test_file_limit_empty_and_format_errors_are_structured() -> None:
    assert_error("FILE_TOO_LARGE", "parcel.geojson", b"x" * (MAX_UPLOAD_BYTES + 1))
    assert_error("PARSE_FAILED", "parcel.geojson", b"")
    assert_error("UNSUPPORTED_FORMAT", "parcel.txt", b"polygon")
    assert_error("PARSE_FAILED", "fake.zip", b"not a zip")


def test_point_fallback_disabled_official_and_provider_precedence() -> None:
    point = PointReferenceProvider().resolve(latitude=25.03, longitude=121.55)
    uploaded = upload("parcel.geojson", geojson_bytes())
    disabled = NlscCadastralProvider().resolve(latitude=25.03, longitude=121.55)
    official = {**uploaded, "status": "verified_official", "source": "nlsc", "legal_boundary": True}
    assert point["status"] == "point_reference_only" and point["can_spatial_intersect"] is False
    assert disabled["status"] == "unavailable" and disabled["legal_boundary"] is False
    assert select_parcel_geometry(official=disabled, uploaded=uploaded, latitude=25.03, longitude=121.55) is uploaded
    assert select_parcel_geometry(official=official, uploaded=uploaded) is official
    assert select_parcel_geometry(latitude=25.03, longitude=121.55)["status"] == "point_reference_only"


def test_official_provider_failure_does_not_discard_valid_user_geometry() -> None:
    class FailedOfficialProvider:
        def resolve(self, **_):
            raise TimeoutError("official provider unavailable")

    uploaded = upload("parcel.geojson", geojson_bytes())
    assert resolve_parcel_geometry(official_provider=FailedOfficialProvider(), uploaded=uploaded) is uploaded


def test_location_geometry_consistency_handles_inside_near_far_and_missing() -> None:
    geometry = {"type": "Polygon", "coordinates": SQUARE}
    assert assess_location_geometry_consistency(geometry, latitude=25.0305, longitude=121.5505) == "CONSISTENT"
    assert assess_location_geometry_consistency(geometry, latitude=25.0305, longitude=121.5512) == "CONSISTENT"
    assert assess_location_geometry_consistency(geometry, latitude=22.63, longitude=120.3) == "POSSIBLE_MISMATCH"
    assert assess_location_geometry_consistency(geometry, latitude=None, longitude=None) == "NOT_CHECKED"


def test_spatial_engine_outside_intersects_inside_touch_multipolygon_and_no_geometry() -> None:
    parcel = {"type": "Polygon", "coordinates": SQUARE}
    outside = {"type": "Polygon", "coordinates": [[[121.56, 25.03], [121.56, 25.031], [121.561, 25.031], [121.561, 25.03], [121.56, 25.03]]]}
    crossing = {"type": "Polygon", "coordinates": [[[121.5505, 25.029], [121.5505, 25.032], [121.552, 25.032], [121.552, 25.029], [121.5505, 25.029]]]}
    inside = {"type": "Polygon", "coordinates": [[[121.5502, 25.0302], [121.5502, 25.0308], [121.5508, 25.0308], [121.5508, 25.0302], [121.5502, 25.0302]]]}
    touch = {"type": "Polygon", "coordinates": [[[121.551, 25.03], [121.551, 25.031], [121.552, 25.031], [121.552, 25.03], [121.551, 25.03]]]}
    assert spatial_intersection(parcel, outside)["intersects"] is False
    assert spatial_intersection(parcel, crossing)["intersection_area_m2"] > 0
    contained = spatial_intersection(parcel, inside)
    assert contained["intersects"] is True and 0 < contained["intersection_ratio"] < 1
    touched = spatial_intersection(parcel, touch)
    assert touched["intersects"] is True and touched["intersection_area_m2"] == 0
    multi = {"type": "MultiPolygon", "coordinates": [SQUARE, outside["coordinates"]]}
    assert spatial_intersection(multi, crossing)["claim_type"] == "GEOMETRIC_INTERSECTION"
    unavailable = spatial_intersection(parcel, None)
    assert unavailable == {"claim_type": "NO_GEOMETRY_AVAILABLE", "geometry_available": False, "timing_ms": unavailable["timing_ms"]}
    assert "intersects" not in unavailable


def test_spatial_timing_is_measured_not_manufactured() -> None:
    result = spatial_intersection({"type": "Polygon", "coordinates": SQUARE}, {"type": "Polygon", "coordinates": SQUARE})
    assert 0 <= result["timing_ms"]["spatial_intersection_ms"] < 500
