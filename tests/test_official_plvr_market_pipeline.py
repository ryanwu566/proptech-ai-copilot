"""Synthetic-only tests for the official PLVR pipeline boundaries."""

from __future__ import annotations

import io
import json
import zipfile
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

import services.official_plvr_market_pipeline as pipeline
from services.official_plvr_market_pipeline import (
    NormalizedTransaction,
    aggregate_transactions,
    classify_transaction,
    inspect_zip_archive,
    load_source_registry,
    normalize_rows,
    normalize_transaction_row,
    parse_manifest,
    parse_roc_date,
    score_comparables,
    sqm_to_ping,
    validate_official_url,
    validate_public_resource_url,
    validate_redirect_chain,
)


ROOT = Path(__file__).resolve().parents[1]


def test_source_registry_is_official_metadata_only() -> None:
    sources = load_source_registry(ROOT / "config" / "official-market-sources.json")
    assert len(sources) == 2
    assert all(source.trust_level == "official" for source in sources)
    assert all("token" not in source.discovery_url.lower() for source in sources)


@pytest.mark.parametrize("url", ["http://plvr.land.moi.gov.tw/x", "https://127.0.0.1/x", "https://evil.example/x", "https://plvr.land.moi.gov.tw/x#secret"])
def test_official_url_allowlist_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError):
        validate_official_url(url, ["plvr.land.moi.gov.tw"])


def test_official_url_allowlist_accepts_official_https() -> None:
    assert validate_official_url("https://plvr.land.moi.gov.tw/public", ["plvr.land.moi.gov.tw"]).startswith("https://")


def test_registry_accepts_query_filename_public_download_route() -> None:
    source = load_source_registry(ROOT / "config" / "official-market-sources.json")[0]
    assert "/Download?" in source.public_resource_url
    assert validate_public_resource_url(source.public_resource_url, source).startswith("https://plvr.land.moi.gov.tw/Download?")


def test_registry_rejects_unexpected_public_resource_query() -> None:
    source = load_source_registry(ROOT / "config" / "official-market-sources.json")[0]
    with pytest.raises(ValueError):
        validate_public_resource_url(source.public_resource_url + "&token=fixture", source)


def test_redirect_chain_must_remain_official() -> None:
    assert validate_redirect_chain(["https://plvr.land.moi.gov.tw/a", "https://download.plvr.land.moi.gov.tw/b"], ["plvr.land.moi.gov.tw"])
    assert not validate_redirect_chain(["https://plvr.land.moi.gov.tw/a", "https://example.invalid/b"], ["plvr.land.moi.gov.tw"])


def test_zip_traversal_is_rejected(tmp_path: Path) -> None:
    archive_path = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../outside.csv", "county,district\n")
    with pytest.raises(ValueError, match="zip_path_traversal"):
        inspect_zip_archive(archive_path)


def test_zip_archive_limits_are_reported(tmp_path: Path) -> None:
    archive_path = tmp_path / "synthetic.zip"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("fixture.csv", "county,district\n")
    assert inspect_zip_archive(archive_path, limits={**pipeline.DEFAULT_LIMITS, "max_files": 2})["status"] == "valid"


def test_manifest_and_schema_change_detection() -> None:
    manifest = parse_manifest(json.dumps({"release_id": "synthetic-release", "schema_version": "v1", "files": []}))
    assert manifest["release_id"] == "synthetic-release"
    report = pipeline.validate_schema(["縣市", "行政區", "交易年月日", "交易總價元", "建物移轉總面積平方公尺", "new_optional"])
    assert report.status == "valid"
    assert "new_optional" in report.unknown_columns


@pytest.mark.parametrize("value,expected", [("112/01/31", date(2023, 1, 31)), ("1120101", date(2023, 1, 1)), ("2024-02-29", date(2024, 2, 29))])
def test_roc_date_normalization(value: str, expected: date) -> None:
    assert parse_roc_date(value) == expected


def test_invalid_roc_date_is_not_silently_repaired() -> None:
    with pytest.raises(ValueError, match="transaction_date_invalid"):
        parse_roc_date("112/02/31")


def test_ping_conversion_uses_exact_constant() -> None:
    assert sqm_to_ping(pipeline.PING_SQM) == pytest.approx(1.0)
    assert sqm_to_ping(0) is None


def test_classification_keeps_sale_presale_rental_separate() -> None:
    assert classify_transaction({"transaction_type": "預售屋"}) == "presale"
    assert classify_transaction({"transaction_type": "租賃"}) == "rental"
    assert classify_transaction({"transaction_type": "房地"}) == "existing_sale"


def test_normalization_canonicalizes_region_without_retaining_address(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "normalize_market_region", lambda county, district: type("R", (), {"valid": True, "county": "Synthetic County", "district": "Synthetic District"})())
    item = normalize_transaction_row({"縣市": "raw county", "行政區": "raw district", "交易年月日": "112/01/01", "交易總價元": "3,305,785", "建物移轉總面積平方公尺": "33.05785", "備註": "裝潢"}, source_id="synthetic", release_id="release")
    assert item.county == "Synthetic County"
    assert item.unit_price_ntd_ping == pytest.approx(330578.5)
    assert "renovation_included" in item.special_transaction_flags
    assert "address_text" not in item.public_trace()


def test_invalid_rows_are_quarantined_and_duplicates_counted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pipeline, "normalize_market_region", lambda county, district: type("R", (), {"valid": True, "county": "Synthetic County", "district": "Synthetic District"})())
    rows = [{"id": "1", "county": "c", "district": "d", "transaction_date": "112/01/01", "total_price": "100", "area_sqm": "10"}] * 2
    rows.append({"county": "c", "district": "d", "transaction_date": "bad", "total_price": "-1", "area_sqm": "0"})
    accepted, summary = normalize_rows(rows, source_id="synthetic", release_id="release")
    assert len(accepted) == 1
    assert summary.duplicate_rows == 1
    assert summary.quarantined_rows == 1


def _item(index: int, price: float, *, period: str = "2024-01") -> NormalizedTransaction:
    return NormalizedTransaction("id-" + str(index), "synthetic", "release", "existing_sale", "Synthetic County", "Synthetic District", date.fromisoformat(period + "-15"), 30.0, price * 30, price, price * pipeline.PING_SQM, building_type="住宅大樓", dedupe_fingerprint="fp-" + str(index), validation_status="valid")


def test_aggregate_is_median_first_with_sample_status() -> None:
    aggregates = aggregate_transactions([_item(1, 100), _item(2, 200), _item(3, 300)], source_name="synthetic official fixture", source_release_id="release", source_updated_at="2024-02-01")
    row = aggregates[0]
    assert row["median_unit_price_ntd_sqm"] == 200
    assert row["mean_unit_price_ntd_sqm"] == 200
    assert row["sample_status"] == "limited"
    assert row["aggregation_version"] == "median-quartiles-v1"


def test_aggregate_does_not_mix_rental_or_presale() -> None:
    rental = _item(1, 100)
    rental.transaction_type = "rental"
    assert aggregate_transactions([rental], source_name="synthetic", source_release_id="r", source_updated_at=None) == []


def test_comparables_are_bounded_and_traceable() -> None:
    target = _item(0, 200)
    candidates = [_item(index, 100 + index) for index in range(20)]
    results = score_comparables(target, candidates, limit=50)
    assert len(results) == 10
    assert all("similarity_reasons" in row and "limitation" in row for row in results)
    assert all("transaction_id" not in row for row in results)


def test_public_aggregate_fields_are_bounded() -> None:
    row = aggregate_transactions([_item(1, 100)], source_name="synthetic", source_release_id="release", source_updated_at=None)[0]
    assert set(row) >= set(pipeline.PUBLIC_AGGREGATE_FIELDS)
    assert "raw_address" not in row


def test_discovery_does_not_call_release_missing() -> None:
    assert pipeline.discover_release(None, None).status == "source_unavailable"
    assert pipeline.discover_release("release", {"release_id": "release"}).status == "already_imported"
    assert pipeline.discover_release("old", {"release_id": "new"}).status == "new_release_available"


def test_official_discovery_without_public_archive_is_resource_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    class Response:
        headers = {"Content-Type": "text/html"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self, _limit: int) -> bytes:
            return b"<html><body>authorized download</body></html>"

    monkeypatch.setattr(pipeline.urllib.request, "urlopen", lambda request, timeout: Response())
    source = replace(load_source_registry(ROOT / "config" / "official-market-sources.json")[0], public_resource_url="", fallback_resource_urls=())
    result = pipeline.discover_official_release(source)
    assert result.status == "resource_unavailable"
    assert result.reason_code == "public_resource_not_discovered"
