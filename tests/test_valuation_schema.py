from pathlib import Path


def test_valuation_schema_exists_with_required_tables_and_indexes() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "database" / "valuation_schema.sql"
    schema = schema_path.read_text(encoding="utf-8")
    assert "create table if not exists real_price_transactions" in schema
    assert "create table if not exists community_buildings" in schema
    assert "create table if not exists valuation_import_runs" in schema
    assert "idx_real_price_city_district_road" in schema
    assert "idx_community_name" in schema
    assert "dedupe_key text" in schema
    assert "uq_real_price_source_dedupe_key" in schema
    assert "skipped_duplicate_rows integer" in schema
    assert "input_file_count integer" in schema
    migrations = schema_path.parent / "migrations"
    assert (migrations / "001_add_dedupe_key_to_real_price_transactions.sql").exists()
    assert (migrations / "002_expand_valuation_import_runs.sql").exists()
