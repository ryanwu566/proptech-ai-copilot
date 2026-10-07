"""E9 descriptive comparison contracts replacing retired weighted commercial UI."""
from tests.e9_model_probe import probe_models


def test_commercial_comparison_preserves_explicit_order():
    result = probe_models()["two"]
    assert result["status"] == "ready"
    assert [case["caseId"] for case in result["cases"]] == ["case-b", "case-a"]


def test_comparison_keeps_price_concepts_and_unavailable_evidence_separate():
    price = probe_models()["two"]["cases"][0]["price"]
    assert price["asking"]["value"] == 2480
    assert price["marketMedianTotal"]["value"] == 1850
    assert price["valuationEstimate"]["value"] is None
    assert price["valuationEstimate"]["status"] == "unavailable"


def test_commercial_comparison_does_not_produce_ranking_or_overall_scores():
    result = probe_models()["four"]
    for key in ("ranking", "winner", "bestCaseId", "topCandidate", "score"):
        assert key not in result
        assert all(key not in case for case in result["cases"])


def test_commercial_selection_permits_four_and_rejects_fifth():
    result = probe_models()
    assert result["four"]["status"] == "ready"
    assert result["five"] == "too_many"
    assert result["duplicate"] == "duplicate"
