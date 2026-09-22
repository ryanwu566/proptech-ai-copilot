"""Tests for RIS population normalization (pure, offline)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from services.ris_population_dataset import (
    RisNormalizationError,
    normalize_row,
    normalize_rows,
    roc_yyymm_to_gregorian,
    summarize_identity,
)

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "ris_odrp014_sample.json"


def _load_rows() -> list[dict]:
    fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    return fixture["page_1"]["responseData"] + fixture["page_2"]["responseData"]


def _row_by_village(village: str) -> dict:
    for row in _load_rows():
        if row["village"] == village:
            return copy.deepcopy(row)
    raise AssertionError(f"village {village!r} not found in fixture")


# --- ROC date conversion -------------------------------------------------

def test_roc_11507_to_2026_07() -> None:
    assert roc_yyymm_to_gregorian("11507") == "2026-07"


def test_roc_two_digit_year() -> None:
    assert roc_yyymm_to_gregorian("9901") == "2010-01"


@pytest.mark.parametrize("bad", ["", "1", "ab12", "11513"])
def test_roc_invalid_inputs(bad: str) -> None:
    with pytest.raises(RisNormalizationError):
        roc_yyymm_to_gregorian(bad)


# --- Age aggregation -----------------------------------------------------

def test_age_buckets_for_liuhou() -> None:
    n = normalize_row(_row_by_village("留侯里"))
    # child at 000: m1 f1 = 2
    assert n["age_0_14"] == 2
    # working at 030: m2 f3 = 5
    assert n["age_15_64"] == 5
    # elderly at 070 (m1 f1) + 100up (m1 f0) = 3
    assert n["age_65_plus"] == 3


def test_100up_included_in_65_plus() -> None:
    row = _row_by_village("留侯里")
    baseline = normalize_row(row)["age_65_plus"]
    # Zero out the 100up bucket; 65+ must drop by exactly the removed count.
    row["people_age_100up_m"] = "0"
    row["people_age_100up_f"] = "0"
    reduced = normalize_row(row)["age_65_plus"]
    assert baseline - reduced == 1  # only the 1 in 100up_m was removed


# --- Ratios --------------------------------------------------------------

def test_ratios_for_liuhou() -> None:
    n = normalize_row(_row_by_village("留侯里"))
    assert n["total_population"] == 10
    assert n["child_ratio"] == pytest.approx(0.2)
    assert n["working_age_ratio"] == pytest.approx(0.5)
    assert n["elderly_ratio"] == pytest.approx(0.3)


def test_average_household_size() -> None:
    n = normalize_row(_row_by_village("留侯里"))
    assert n["household_count"] == 3
    assert n["average_household_size"] == pytest.approx(10 / 3)


# --- Zero-denominator -> None (not 0) ------------------------------------

def _zero_population_row() -> dict:
    row = _row_by_village("樂華村")
    for key, value in list(row.items()):
        if key.startswith("people"):
            row[key] = "0"
    row["household_no"] = "0"
    return row


def test_zero_total_population_ratios_are_none() -> None:
    n = normalize_row(_zero_population_row())
    assert n["total_population"] == 0
    assert n["child_ratio"] is None
    assert n["working_age_ratio"] is None
    assert n["elderly_ratio"] is None


def test_zero_household_average_is_none() -> None:
    row = _row_by_village("樂華村")
    row["household_no"] = "0"
    n = normalize_row(row)
    assert n["average_household_size"] is None


# --- Negative rejection --------------------------------------------------

def test_negative_population_rejected() -> None:
    row = _row_by_village("留侯里")
    row["people_total"] = "-1"
    with pytest.raises(RisNormalizationError, match="negative"):
        normalize_row(row)


def test_negative_age_bucket_rejected() -> None:
    row = _row_by_village("留侯里")
    row["people_age_030_m"] = "-2"
    with pytest.raises(RisNormalizationError, match="negative"):
        normalize_row(row)


def test_non_integer_rejected() -> None:
    row = _row_by_village("留侯里")
    row["people_total"] = "N/A"
    with pytest.raises(RisNormalizationError):
        normalize_row(row)


def test_missing_identity_rejected() -> None:
    row = _row_by_village("留侯里")
    row["village"] = ""
    with pytest.raises(RisNormalizationError):
        normalize_row(row)


# --- Consistency checks -> audit reasons (no silent mutation) ------------

def test_sex_total_consistency_ok() -> None:
    n = normalize_row(_row_by_village("留侯里"))
    assert n["male_population"] + n["female_population"] == n["total_population"]
    assert n["audit_reasons"] == []


def test_sex_total_mismatch_recorded_not_mutated() -> None:
    row = _row_by_village("留侯里")
    row["people_total"] = "11"  # m5 + f5 = 10 != 11
    n = normalize_row(row)
    assert n["total_population"] == 11  # reported value preserved, not rewritten
    assert any("sex_total_mismatch" in reason for reason in n["audit_reasons"])


def test_age_bucket_overflow_recorded() -> None:
    row = _row_by_village("留侯里")
    row["people_total"] = "5"  # bucket sum is 10 > 5
    n = normalize_row(row)
    assert any("age_bucket_overflow" in reason for reason in n["audit_reasons"])


# --- Identity summary ----------------------------------------------------

def test_identity_summary_unique() -> None:
    normalized = normalize_rows(_load_rows())
    summary = summarize_identity(normalized)
    assert summary["row_count"] == 3
    assert summary["unique_district_codes"] == 3
    assert summary["duplicate_district_code_count"] == 0
    assert summary["duplicate_composite_key_count"] == 0
    assert summary["null_identity_rows"] == 0


def test_identity_summary_detects_duplicate_district_code() -> None:
    rows = _load_rows()
    dup = copy.deepcopy(rows[0])  # same district_code / site_id / village
    normalized = normalize_rows(rows + [dup])
    summary = summarize_identity(normalized)
    assert summary["duplicate_district_code_count"] == 1
    assert summary["duplicate_composite_key_count"] == 1
    assert summary["row_count"] == 4


def test_identity_summary_city_district_coverage() -> None:
    normalized = normalize_rows(_load_rows())
    summary = summarize_identity(normalized)
    # site_id is a city+district label; 3 distinct labels in the fixture.
    assert summary["district_label_count"] == 3
    assert summary["city_label_count"] >= 1


# --- Fixture / generator drift guard -------------------------------------

def test_generator_output_matches_committed_fixture() -> None:
    """The committed JSON fixture must equal the generator's build() output.

    Guards against the deterministic static fixture drifting away from its
    generator (provenance / rebuildability).
    """

    import importlib.util

    generator_path = FIXTURE_PATH.parent / "build_ris_odrp014_sample.py"
    spec = importlib.util.spec_from_file_location("build_ris_odrp014_sample", generator_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    committed = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    assert module.build() == committed
