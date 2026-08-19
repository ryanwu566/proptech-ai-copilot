"""Static trust-boundary checks for property case evidence."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (ROOT / "frontend_next/lib/property-case-evidence.ts").read_text(encoding="utf-8")
CASE_MODEL = (ROOT / "frontend_next/lib/property-case.ts").read_text(encoding="utf-8")
REPORT = (ROOT / "frontend_next/components/property-comparison-report.tsx").read_text(encoding="utf-8")


def test_evidence_has_explicit_status_and_source_allowlists() -> None:
    for value in ("trusted", "manual", "partial", "unavailable", "not_assessed"):
        assert value in EVIDENCE
    for value in ("official_valuation", "manual_user_input", "loan_reference", "holding_reference", "location_reference", "terrain_reference", "tax_reference", "none"):
        assert value in EVIDENCE


def test_only_actionable_official_valuation_is_transferable() -> None:
    assert "getTrustedValuationEvidence" in EVIDENCE
    assert "transferable: true" in EVIDENCE
    assert "result_origin !== \"official\"" in EVIDENCE
    assert "is_actionable !== true" in EVIDENCE
    assert "comparables.length < 3" in EVIDENCE
    assert "source === \"official_plvr_opendata\"" in EVIDENCE
    assert "valuationTransferConfirmed === true" in CASE_MODEL
    assert "confirmedValuationPrice" in CASE_MODEL


def test_evidence_and_storage_do_not_expose_raw_provider_fields() -> None:
    for source in (EVIDENCE, REPORT):
        for forbidden in ("raw_payload", "provider raw", "source_details", "StationUID", "token", "secret", "SQL", "database URL"):
            assert forbidden not in source


def test_partial_and_official_report_paths_are_separate() -> None:
    assert 'copy("comparison.insufficientData")' in REPORT or "目前為部分資料摘要" in REPORT
    assert "comparisonStatus === \"ready\"" in REPORT
    assert 'copy("comparison.partialNote")' in REPORT or "不會被視為 0、低風險或完成" in REPORT
