"""Canonical saved-evidence comparison; responsive UI is exercised by Playwright."""
from tests.e9_model_probe import probe_models


def test_missing_selection_is_not_substituted():
    assert probe_models()["missing"] == "case_not_found"
    assert probe_models()["one"] == "too_few"


def test_compare_url_contains_only_ordered_opaque_ids():
    assert probe_models()["href"] == "/compare?cases=case-b,case-a"


def test_comparison_keeps_saved_finance_without_double_counting():
    finance = probe_models()["two"]["cases"][0]["finance"]
    assert finance["interestRate"]["value"] == 0
    assert finance["monthlyIncome"]["value"] is None
    assert finance["knownMonthlyHousing"]["value"] == 55111


def test_no_match_risk_is_scoped_evidence_and_unknowns_remain_visible():
    case = probe_models()["two"]["cases"][0]
    assert case["risk"][1]["evidence"]["status"] == "no_match"
    assert case["risk"][5]["evidence"]["status"] == "unavailable"
    assert case["risk"][6]["evidence"]["status"] == "unsupported"
    assert any(gap["reason"] == "not_preserved" for gap in case["gaps"])


def test_report_has_all_sections_and_independent_generation_time():
    report = probe_models()["report"]
    assert report["status"] == "ready_with_limits"
    assert len(report["sections"]) == 9
    assert report["generatedAt"] == "2026-10-07T04:00:00Z"
    assert report["evidence"]["savedAt"] == "2026-10-07T03:00:00.000Z"
