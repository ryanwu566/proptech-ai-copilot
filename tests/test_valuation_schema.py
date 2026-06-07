from pathlib import Path


def test_valuation_schema_exists_with_required_tables_and_indexes() -> None:
    schema_path = Path(__file__).resolve().parents[1] / "database" / "valuation_schema.sql"
    schema = schema_path.read_text(encoding="utf-8")
    assert "create table if not exists real_price_transactions" in schema
    assert "create table if not exists community_buildings" in schema
    assert "create table if not exists valuation_import_runs" in schema
    assert "idx_real_price_city_district_road" in schema
    assert "idx_community_name" in schema
