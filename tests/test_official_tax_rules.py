"""Offline versioned TaxOracle rule contract tests."""

from services.official_tax_rules import (
    TX_RULE_IDS,
    build_tax_rule_trace,
    compatibility_rule_catalog,
    ingest_tax_rule_snapshot,
    missing_tax_inputs,
    select_tax_rules,
    validate_tax_rule_snapshot,
)


def rule(**overrides: object) -> dict[str, object]:
    result = {
        "rule_id": "HOUSE-001",
        "tax_type": "house_tax",
        "jurisdiction": "fixture-county",
        "official_code": "FIXTURE-001",
        "rule_version": "2026-v1",
        "effective_from": "2026-01-01",
        "effective_to": None,
        "legal_basis": "official fixture legal reference",
        "official_source_url": "https://example.gov.tw/rule",
        "official_agency": "Fixture authority",
        "rate_type": "percentage",
        "rate_value_or_band": 1.0,
        "conditions": ["fixture condition"],
        "required_inputs": ["jurisdiction"],
        "limitation": "fixture only",
    }
    result.update(overrides)
    return result


def test_tx_ids_and_trace_remain_compatible() -> None:
    assert TX_RULE_IDS == tuple(f"TX{i:03d}" for i in range(1, 10))
    catalog = compatibility_rule_catalog()
    assert [row["rule_id"] for row in catalog] == list(TX_RULE_IDS)
    trace = build_tax_rule_trace({"case_id": "fixture", "client_name": "private", "land_value_available": True})
    assert trace["rule_ids"] == list(TX_RULE_IDS)
    assert "client_name" not in trace["used_inputs"]
    assert trace["calculation_kind"] == "preliminary_screening"


def test_exact_jurisdiction_and_effective_date_are_required() -> None:
    records = [rule()]
    selected = select_tax_rules(records, "fixture-county", "2026-06-01")
    assert selected["status"] == "available"
    assert selected["rules"][0]["rule_version"] == "2026-v1"
    missing = select_tax_rules(records, "other-county", "2026-06-01")
    assert missing["status"] == "jurisdiction_data_unavailable"
    assert missing["rules"] == []


def test_missing_inputs_are_not_inferred() -> None:
    result = missing_tax_inputs(("jurisdiction", "assessed_value"), {"jurisdiction": "fixture-county"})
    assert result == {"status": "missing_input", "missing_inputs": ["assessed_value"]}


def test_snapshot_rejects_duplicates_and_bad_ranges() -> None:
    payload = {"rules": [rule(), rule(), rule(effective_from="2027-01-01", effective_to="2026-01-01")]}
    result = validate_tax_rule_snapshot(payload)
    assert result["valid"] is False
    assert result["rejected_count"] == 2


def test_tax_import_is_dry_run(tmp_path) -> None:
    path = tmp_path / "rules.json"
    path.write_text(__import__("json").dumps({"rules": [rule()]}), encoding="utf-8")
    report = ingest_tax_rule_snapshot(path)
    assert report["status"] == "validated"
    assert report["mutation"] == "none"
    assert report["dry_run"] is True
