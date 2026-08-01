from scripts.validate_pilot_evidence_migration import validate


def test_disposable_sqlite_migration_and_isolation_validation_passes() -> None:
    result = validate()
    assert result["status"] == "pass"
    assert result["foreign_keys"] == "pass"
    assert result["participant_isolation"] == "pass"
    assert result["fixture_exclusion"] == "pass"
