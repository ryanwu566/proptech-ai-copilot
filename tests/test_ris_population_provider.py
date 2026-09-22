"""Tests for the RIS population provider (transport + pagination contract)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import httpx
import pytest

from services.ris_population_provider import (
    RESPONSE_CODE_NO_MORE_DATA,
    RESPONSE_CODE_SUCCESS,
    RisPaginationError,
    RisProviderError,
    RisResponseCodeError,
    RisSchemaError,
    build_dataset_url,
    fetch_population_pages,
    normalize_source_row_schema,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ris_odrp014_sample.json"
ZH_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ris_odrp014_sample_zh.json"


def _load_fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_zh_fixture() -> dict:
    return json.loads(ZH_FIXTURE_PATH.read_text(encoding="utf-8"))


def _fetcher_from_pages(pages: dict[int, dict]):
    """Build a fetcher that returns a fixed payload per 1-based page number."""

    def fetch(url: str, page: int) -> dict:
        if page not in pages:
            # Anything past the defined pages behaves as the terminator.
            return {"responseCode": RESPONSE_CODE_NO_MORE_DATA}
        return copy.deepcopy(pages[page])

    return fetch


def _standard_pages() -> dict[int, dict]:
    fixture = _load_fixture()
    return {1: fixture["page_1"], 2: fixture["page_2"], 3: fixture["page_3"]}


def test_build_dataset_url() -> None:
    assert build_dataset_url("11507") == (
        "https://www.ris.gov.tw/rs-opendata/api/v1/datastore/ODRP014/11507"
    )


def test_build_dataset_url_rejects_non_numeric() -> None:
    with pytest.raises(ValueError):
        build_dataset_url("11507; DROP")


def test_pagination_collects_all_pages() -> None:
    result = fetch_population_pages("11507", _fetcher_from_pages(_standard_pages()))
    assert result["pages_fetched"] == 2
    assert result["total_page"] == 2
    assert result["total_data_size"] == 3
    assert len(result["rows"]) == 3
    # Order preserved: page1 rows then page2 row.
    assert result["rows"][0]["village"] == "留侯里"
    assert result["rows"][-1]["village"] == "樂華村"


def test_terminator_response_code_stops_without_error() -> None:
    # Only page 1 defined; page 2 -> terminator. totalDataSize matches 2 rows.
    fixture = _load_fixture()
    page1 = copy.deepcopy(fixture["page_1"])
    page1["totalPage"] = "1"
    page1["totalDataSize"] = "2"
    result = fetch_population_pages("11507", _fetcher_from_pages({1: page1}))
    assert result["pages_fetched"] == 1
    assert len(result["rows"]) == 2


def test_total_data_size_mismatch_fails_closed() -> None:
    pages = _standard_pages()
    pages[1] = copy.deepcopy(pages[1])
    pages[1]["totalDataSize"] = "999"
    pages[2] = copy.deepcopy(pages[2])
    pages[2]["totalDataSize"] = "999"
    with pytest.raises(RisPaginationError, match="totalDataSize"):
        fetch_population_pages("11507", _fetcher_from_pages(pages))


def test_duplicate_page_fails_closed() -> None:
    fixture = _load_fixture()
    # Server keeps reporting page 1 forever (never advances to totalPage).
    always_page1 = copy.deepcopy(fixture["page_1"])
    always_page1["totalPage"] = "3"

    def fetch(url: str, page: int) -> dict:
        payload = copy.deepcopy(always_page1)
        # Report the same page number regardless of the requested page.
        payload["page"] = "1"
        return payload

    with pytest.raises(RisPaginationError):
        fetch_population_pages("11507", fetch)


def test_invalid_response_code_not_retried() -> None:
    calls = {"n": 0}

    def fetch(url: str, page: int) -> dict:
        calls["n"] += 1
        return {"responseCode": "OD-9999-E", "responseMessage": "boom"}

    with pytest.raises(RisResponseCodeError):
        fetch_population_pages("11507", fetch)
    assert calls["n"] == 1  # no retry on a response-code error


def test_malformed_schema_missing_field() -> None:
    fixture = _load_fixture()
    page1 = copy.deepcopy(fixture["page_1"])
    del page1["responseData"][0]["people_total"]
    with pytest.raises(RisSchemaError, match="missing required fields"):
        fetch_population_pages("11507", _fetcher_from_pages({1: page1}))


def test_malformed_schema_response_data_not_list() -> None:
    fixture = _load_fixture()
    page1 = copy.deepcopy(fixture["page_1"])
    page1["responseData"] = {"not": "a list"}
    with pytest.raises(RisSchemaError, match="must be a list"):
        fetch_population_pages("11507", _fetcher_from_pages({1: page1}))


def test_hard_max_pages_ceiling() -> None:
    fixture = _load_fixture()

    def fetch(url: str, page: int) -> dict:
        payload = copy.deepcopy(fixture["page_1"])
        payload["page"] = str(page)  # advance so it is never a duplicate
        payload["totalPage"] = "9999"  # server claims far more pages than allowed
        return payload

    with pytest.raises(RisPaginationError, match="hard maximum"):
        fetch_population_pages("11507", fetch, max_pages=3)


def test_default_fetcher_retries_transient_then_succeeds(monkeypatch) -> None:
    fixture = _load_fixture()
    page1 = copy.deepcopy(fixture["page_1"])
    page1["totalPage"] = "1"
    page1["totalDataSize"] = "2"
    attempts = {"n": 0}

    class _FlakyClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url, params=None, headers=None):
            attempts["n"] += 1
            if attempts["n"] == 1:
                raise httpx.ConnectError("transient")
            request = httpx.Request("GET", url)
            return httpx.Response(200, json=page1, request=request)

    monkeypatch.setattr(httpx, "Client", _FlakyClient)
    result = fetch_population_pages(
        "11507", fetcher=None, max_retries=2, retry_backoff=0, sleep=lambda _s: None
    )
    assert attempts["n"] == 2  # one failure + one success
    assert len(result["rows"]) == 2


def test_default_fetcher_does_not_retry_4xx(monkeypatch) -> None:
    attempts = {"n": 0}

    class _ClientErrorClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url, params=None, headers=None):
            attempts["n"] += 1
            request = httpx.Request("GET", url)
            return httpx.Response(404, request=request)

    monkeypatch.setattr(httpx, "Client", _ClientErrorClient)
    with pytest.raises(RisResponseCodeError):
        fetch_population_pages(
            "11507", fetcher=None, max_retries=3, retry_backoff=0, sleep=lambda _s: None
        )
    assert attempts["n"] == 1  # 4xx is never retried


def test_default_fetcher_retries_exhausted(monkeypatch) -> None:
    class _AlwaysTimeoutClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def get(self, url, params=None, headers=None):
            raise httpx.TimeoutException("slow")

    monkeypatch.setattr(httpx, "Client", _AlwaysTimeoutClient)
    with pytest.raises(RisProviderError):
        fetch_population_pages(
            "11507", fetcher=None, max_retries=2, retry_backoff=0, sleep=lambda _s: None
        )


def test_success_and_terminator_codes_are_expected_constants() -> None:
    assert RESPONSE_CODE_SUCCESS == "OD-0101-S"
    assert RESPONSE_CODE_NO_MORE_DATA == "OD-0102-S"


# --- Source-schema adapter (Phase 2B) ------------------------------------

def test_adapter_chinese_row_to_canonical() -> None:
    zh = {
        "統計年月": "11504",
        "區域別代碼": "65000010002",
        "區域別": "新北市板橋區",
        "村里": "流芳里",
        "戶數": "661",
        "人口數": "1446",
        "人口數-男": "646",
        "人口數-女": "800",
    }
    canonical = normalize_source_row_schema(zh)
    assert canonical == {
        "statistic_yyymm": "11504",
        "district_code": "65000010002",
        "site_id": "新北市板橋區",
        "village": "流芳里",
        "household_no": "661",
        "people_total": "1446",
        "people_total_m": "646",
        "people_total_f": "800",
    }


def test_adapter_english_row_unchanged() -> None:
    fixture = _load_fixture()
    english_row = fixture["page_1"]["responseData"][0]
    # Adapter must not mutate an already-canonical row.
    assert normalize_source_row_schema(english_row) == english_row


def test_adapter_age_bucket_mapping() -> None:
    zh = {
        "0歲-男": "1",
        "0歲-女": "2",
        "14歲-男": "3",
        "65歲-女": "4",
        "99歲-男": "5",
    }
    canonical = normalize_source_row_schema(zh)
    assert canonical["people_age_000_m"] == "1"
    assert canonical["people_age_000_f"] == "2"
    assert canonical["people_age_014_m"] == "3"
    assert canonical["people_age_065_f"] == "4"
    assert canonical["people_age_099_m"] == "5"


def test_adapter_100up_mapping() -> None:
    canonical = normalize_source_row_schema({"100歲以上-男": "7", "100歲以上-女": "8"})
    assert canonical["people_age_100up_m"] == "7"
    assert canonical["people_age_100up_f"] == "8"


def test_adapter_age_099_maps() -> None:
    canonical = normalize_source_row_schema({"99歲-男": "5"})
    assert canonical["people_age_099_m"] == "5"


def test_adapter_100up_only_via_static_map() -> None:
    canonical = normalize_source_row_schema({"100歲以上-男": "9"})
    assert canonical["people_age_100up_m"] == "9"


def test_adapter_age_100_not_mapped() -> None:
    # "100歲-男" is out of the single-year 0..99 range and must NOT become a
    # canonical age field; it is preserved verbatim as an unknown extra column.
    canonical = normalize_source_row_schema({"100歲-男": "3"})
    assert "people_age_100_m" not in canonical
    assert canonical["100歲-男"] == "3"


def test_adapter_age_101_not_mapped() -> None:
    canonical = normalize_source_row_schema({"101歲-女": "4"})
    assert "people_age_101_f" not in canonical
    assert canonical["101歲-女"] == "4"


def test_adapter_age_999_not_mapped() -> None:
    canonical = normalize_source_row_schema({"999歲-男": "1"})
    assert "people_age_999_m" not in canonical
    assert canonical["999歲-男"] == "1"


def test_adapter_bilingual_same_value_accepted() -> None:
    row = {"區域別代碼": "65000010002", "district_code": "65000010002"}
    assert normalize_source_row_schema(row) == {"district_code": "65000010002"}


def test_adapter_bilingual_conflict_rejected() -> None:
    row = {"區域別代碼": "A", "district_code": "B"}
    with pytest.raises(RisSchemaError, match="schema conflict"):
        normalize_source_row_schema(row)


def test_adapter_unknown_field_preserved() -> None:
    row = {"district_code": "X", "some_future_column": "keep-me"}
    canonical = normalize_source_row_schema(row)
    assert canonical["some_future_column"] == "keep-me"


def test_adapter_rejects_non_mapping() -> None:
    with pytest.raises(RisSchemaError):
        normalize_source_row_schema(["not", "a", "dict"])  # type: ignore[arg-type]


def test_chinese_fixture_pagination_succeeds() -> None:
    zh = _load_zh_fixture()
    pages = {1: zh["page_1"], 2: zh["page_2"], 3: zh["page_3"]}
    result = fetch_population_pages("11504", _fetcher_from_pages(pages))
    assert result["pages_fetched"] == 2
    assert result["total_data_size"] == 3
    assert len(result["rows"]) == 3
    # Rows returned to callers are already canonical English-key rows.
    first = result["rows"][0]
    assert "district_code" in first and "統計年月" not in first
    assert first["village"] == "流芳里"
    assert "people_age_100up_m" in first


def test_chinese_fixture_normalizes_downstream() -> None:
    from services.ris_population_dataset import normalize_row

    zh = _load_zh_fixture()
    pages = {1: zh["page_1"], 2: zh["page_2"], 3: zh["page_3"]}
    result = fetch_population_pages("11504", _fetcher_from_pages(pages))
    # The canonical rows must flow through the unchanged dataset contract.
    normalized = [normalize_row(row) for row in result["rows"]]
    assert normalized[0]["statistic_month"] == "2026-04"
    assert all(n["audit_reasons"] == [] for n in normalized)


def test_chinese_generator_matches_committed_fixture() -> None:
    import importlib.util

    generator_path = ZH_FIXTURE_PATH.parent / "build_ris_odrp014_sample_zh.py"
    spec = importlib.util.spec_from_file_location("build_ris_odrp014_sample_zh", generator_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    committed = json.loads(ZH_FIXTURE_PATH.read_text(encoding="utf-8"))
    assert module.build() == committed
