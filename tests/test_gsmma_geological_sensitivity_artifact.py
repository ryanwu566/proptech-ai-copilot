from __future__ import annotations

import io
import json
from pathlib import Path
import subprocess
import sys
import zipfile

import pytest
import shapefile
from pyproj import CRS
import services.gsmma_geological_sensitivity_artifact as artifact_module

from services.gsmma_geological_sensitivity_artifact import (
    ArtifactBuildError,
    PackageInput,
    build_processed_artifact,
    load_artifact,
    read_package,
    write_build_outputs,
)
from services.gsmma_geological_sensitivity_dataset import UnsupportedDatasetError


INDEX = (
    "No.,地質敏感區類型,地質敏感區編號,地質敏感區名稱,公告日期,文號,座標系統1,座標系統2,下載連結\n"
    "1,活動斷層地質敏感區,F0001,測試區,2024-06-27,經地字第1號,TWD97 TM2 121,,https://example.gov.tw/f.zip\n"
).encode("utf-8")


def _shapefile_parts(
    *, shape_type: int = shapefile.POLYGON, include_feature: bool = True
) -> dict[str, bytes]:
    shp, shx, dbf = io.BytesIO(), io.BytesIO(), io.BytesIO()
    writer = shapefile.Writer(shp=shp, shx=shx, dbf=dbf, shapeType=shape_type, encoding="utf-8")
    writer.field("OBJECTID", "N", size=8)
    writer.field("NOTE", "C", size=24)
    if include_feature:
        if shape_type == shapefile.POLYGON:
            writer.poly([[[250000, 2770000], [250000, 2770100], [250100, 2770100], [250100, 2770000], [250000, 2770000]]])
        else:
            writer.point(250000, 2770000)
        writer.record(7, "official")
    writer.close()
    return {
        "area.shp": shp.getvalue(),
        "area.shx": shx.getvalue(),
        "area.dbf": dbf.getvalue(),
        "area.prj": CRS.from_epsg(3826).to_wkt().encode("utf-8"),
        "area.cpg": b"UTF-8",
    }


def _zip_bytes(parts: dict[str, bytes] | None = None, *, prefix: str = "official") -> bytes:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, payload in sorted((parts or _shapefile_parts()).items()):
            archive.writestr(f"{prefix}/{name}", payload)
    return output.getvalue()


def _write_package(root: Path, payload: bytes | None = None, name: str = "package.zip") -> Path:
    root.mkdir(parents=True, exist_ok=True)
    path = root / name
    path.write_bytes(payload or _zip_bytes())
    return path


def test_valid_zip_package_is_read_without_extracting_to_disk(tmp_path: Path) -> None:
    package = PackageInput(index_no="1", path=_write_package(tmp_path))
    components = read_package(package)
    assert components.relative_shp_path == "official/area.shp"
    assert components.encoding.lower().replace("-", "") == "utf8"
    assert components.prj.decode("utf-8").startswith("PROJCRS")


@pytest.mark.parametrize("name", ["package.rar", "package.7z"])
def test_rar_and_7z_require_operator_extraction(tmp_path: Path, name: str) -> None:
    package = PackageInput(index_no="1", path=_write_package(tmp_path, b"not used", name))
    with pytest.raises(UnsupportedDatasetError, match="extract"):
        read_package(package)


def test_zip_path_traversal_is_rejected(tmp_path: Path) -> None:
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../area.shp", b"bad")
    package = PackageInput(index_no="1", path=_write_package(tmp_path, output.getvalue()))
    with pytest.raises(ArtifactBuildError, match="unsafe"):
        read_package(package)


def test_zip_case_colliding_sidecars_are_rejected(tmp_path: Path) -> None:
    parts = _shapefile_parts()
    parts["AREA.DBF"] = parts["area.dbf"]
    package = PackageInput(index_no="1", path=_write_package(tmp_path, _zip_bytes(parts)))
    with pytest.raises(ArtifactBuildError, match="duplicate"):
        read_package(package)


def test_multiple_shapefiles_require_explicit_selection(tmp_path: Path) -> None:
    parts = _shapefile_parts()
    parts.update({name.replace("area", "other"): payload for name, payload in _shapefile_parts().items()})
    path = _write_package(tmp_path, _zip_bytes(parts))
    with pytest.raises(ArtifactBuildError, match="multiple"):
        read_package(PackageInput(index_no="1", path=path))
    selected = read_package(PackageInput(index_no="1", path=path, shapefile_path="official/other.shp"))
    assert selected.relative_shp_path == "official/other.shp"


def test_missing_cpg_requires_explicit_encoding(tmp_path: Path) -> None:
    parts = _shapefile_parts()
    parts.pop("area.cpg")
    path = _write_package(tmp_path, _zip_bytes(parts))
    with pytest.raises(ArtifactBuildError, match="encoding"):
        read_package(PackageInput(index_no="1", path=path))
    assert read_package(PackageInput(index_no="1", path=path, encoding="utf-8")).encoding == "utf-8"


def test_operator_extracted_directory_is_supported_without_serializing_root(tmp_path: Path) -> None:
    extracted = tmp_path / "machine-specific-root" / "official"
    extracted.mkdir(parents=True)
    for name, payload in _shapefile_parts().items():
        (extracted / name).write_bytes(payload)

    components = read_package(PackageInput(index_no="1", path=extracted))

    assert components.relative_shp_path == "area.shp"
    assert "machine-specific-root" not in components.relative_shp_path


def test_zip_entry_count_limit_is_enforced(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(artifact_module, "MAX_ARCHIVE_ENTRIES", 5)
    parts = _shapefile_parts()
    parts["extra.txt"] = b"extra"
    path = _write_package(tmp_path, _zip_bytes(parts))
    with pytest.raises(ArtifactBuildError, match="too many entries"):
        read_package(PackageInput(index_no="1", path=path))


def test_zip_expanded_size_and_ratio_limits_are_enforced(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(artifact_module, "MAX_TOTAL_UNCOMPRESSED_BYTES", 100)
    path = _write_package(tmp_path, _zip_bytes())
    with pytest.raises(ArtifactBuildError, match="expanded-size"):
        read_package(PackageInput(index_no="1", path=path))

    monkeypatch.setattr(artifact_module, "MAX_TOTAL_UNCOMPRESSED_BYTES", 512 * 1024 * 1024)
    monkeypatch.setattr(artifact_module, "MAX_COMPRESSION_RATIO", 2)
    with pytest.raises(ArtifactBuildError, match="compression-ratio"):
        read_package(PackageInput(index_no="1", path=path))


def test_build_is_deterministic_across_different_local_roots(tmp_path: Path) -> None:
    payload = _zip_bytes()
    first_path = _write_package(tmp_path / "machine-a" / "temp-one", payload)
    second_path = _write_package(tmp_path / "machine-b" / "temp-two", payload)
    options = {"dataset_version": "2024-06-27", "source_vintage": "2024-06-27"}

    first = build_processed_artifact(INDEX, [PackageInput("1", first_path)], **options)
    second = build_processed_artifact(INDEX, [PackageInput("1", second_path)], **options)

    assert first.artifact_bytes == second.artifact_bytes
    assert first.manifest_bytes == second.manifest_bytes
    assert first.quarantine_bytes == second.quarantine_bytes
    combined = first.artifact_bytes + first.manifest_bytes + first.quarantine_bytes
    assert str(tmp_path).encode() not in combined
    assert b"machine-a" not in combined
    assert b"mtime" not in combined


def test_extracted_package_checksum_covers_auxiliary_source_files(tmp_path: Path) -> None:
    manifests = []
    for name, note in (("first", b"source note one"), ("second", b"source note two")):
        root = tmp_path / name
        root.mkdir()
        for filename, payload in _shapefile_parts().items():
            (root / filename).write_bytes(payload)
        (root / "README.txt").write_bytes(note)
        result = build_processed_artifact(
            INDEX,
            [PackageInput("1", root)],
            dataset_version="2024-06-27",
            source_vintage="2024-06-27",
        )
        manifests.append(result.manifest)

    assert (
        manifests[0]["source_packages"][0]["source_package_sha256"]
        != manifests[1]["source_packages"][0]["source_package_sha256"]
    )


def test_manifest_and_artifact_preserve_normalized_evidence(tmp_path: Path) -> None:
    result = build_processed_artifact(
        INDEX,
        [PackageInput("1", _write_package(tmp_path))],
        dataset_version="2024-06-27",
        source_vintage="2024-06-27",
    )
    document, features = load_artifact(result.artifact_bytes)

    assert result.manifest["schema_version"] == 1
    assert result.manifest["dataset_version"] == "2024-06-27"
    assert result.manifest["quality_status"] == "accepted"
    assert result.manifest["feature_count"] == 1
    assert len(result.manifest["artifact_sha256"]) == 64
    assert document["target_crs"] == "EPSG:4326"
    assert features[0].official_category == "活動斷層地質敏感區"
    assert features[0].canonical_category == "active_fault_sensitive_area"
    assert features[0].original_attributes["NOTE"] == "official"


def test_rejected_feature_sets_review_required_and_writes_quarantine(tmp_path: Path) -> None:
    result = build_processed_artifact(
        INDEX,
        [PackageInput("1", _write_package(tmp_path, _zip_bytes(_shapefile_parts(shape_type=shapefile.POINT))))],
        dataset_version="2024-06-27",
        source_vintage="2024-06-27",
    )
    quarantine = json.loads(__import__("gzip").decompress(result.quarantine_bytes))
    assert result.manifest["quality_status"] == "review_required"
    assert result.manifest["rejected_feature_count"] == 1
    assert quarantine["records"][0]["reason"] == "unsupported_geometry"


def test_empty_source_cannot_be_accepted_as_a_successful_no_match(tmp_path: Path) -> None:
    result = build_processed_artifact(
        INDEX,
        [PackageInput("1", _write_package(tmp_path, _zip_bytes(_shapefile_parts(include_feature=False))))],
        dataset_version="2024-06-27",
        source_vintage="2024-06-27",
    )

    assert result.manifest["feature_count"] == 0
    assert result.manifest["quality_status"] == "review_required"


def test_corrupt_artifact_is_rejected() -> None:
    with pytest.raises(ArtifactBuildError, match="decode"):
        load_artifact(b"not-gzip")


def test_artifact_category_mapping_is_validated(tmp_path: Path) -> None:
    result = build_processed_artifact(
        INDEX,
        [PackageInput("1", _write_package(tmp_path))],
        dataset_version="2024-06-27",
        source_vintage="2024-06-27",
    )
    document = json.loads(__import__("gzip").decompress(result.artifact_bytes))
    document["features"][0]["canonical_category"] = "fabricated_category"
    corrupt = artifact_module._deterministic_gzip(artifact_module._canonical_json(document))

    with pytest.raises(ArtifactBuildError, match="decode"):
        load_artifact(corrupt)


@pytest.mark.parametrize("dataset_version", ["latest", "../escape", "nested/version", "C:drive"])
def test_dataset_version_cannot_select_mutable_or_unsafe_output_paths(
    tmp_path: Path, dataset_version: str
) -> None:
    with pytest.raises(ArtifactBuildError, match="dataset_version"):
        build_processed_artifact(
            INDEX,
            [PackageInput("1", _write_package(tmp_path))],
            dataset_version=dataset_version,
            source_vintage="2024-06-27",
        )


def test_write_outputs_uses_only_dataset_version_subdirectory(tmp_path: Path) -> None:
    result = build_processed_artifact(
        INDEX,
        [PackageInput("1", _write_package(tmp_path / "source"))],
        dataset_version="2024-06-27",
        source_vintage="2024-06-27",
    )
    paths = write_build_outputs(result, tmp_path / "out")
    assert paths["artifact"] == tmp_path / "out" / "2024-06-27" / "features.json.gz"
    assert paths["manifest"].read_bytes() == result.manifest_bytes
    assert paths["quarantine"].read_bytes() == result.quarantine_bytes


def test_operator_cli_builds_local_outputs_without_uploading(tmp_path: Path) -> None:
    index_path = tmp_path / "index.csv"
    index_path.write_bytes(INDEX)
    package_path = _write_package(tmp_path / "sources")
    mapping_path = tmp_path / "packages.json"
    mapping_path.write_text(
        json.dumps([{"index_no": "1", "path": str(package_path)}]),
        encoding="utf-8",
    )
    output_dir = tmp_path / "processed"

    completed = subprocess.run(
        [
            sys.executable,
            "scripts/build_gsmma_geological_sensitivity_artifact.py",
            "--index", str(index_path),
            "--package-map", str(mapping_path),
            "--dataset-version", "2024-06-27",
            "--source-vintage", "2024-06-27",
            "--output-dir", str(output_dir),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["dataset_version"] == "2024-06-27"
    assert summary["quality_status"] == "accepted"
    assert summary["upload_performed"] is False
    assert (output_dir / "2024-06-27" / "manifest.json").exists()
