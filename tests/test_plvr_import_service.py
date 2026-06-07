from services.plvr_import_service import is_sale_transaction_csv, normalize_row, normalize_rows, parse_floor, parse_road, roc_date_to_period


VALID_ROW = {
    "鄉鎮市區": "大安區",
    "土地區段位置建物區段門牌": "台北市大安區和平東路二段100號",
    "交易年月日": "1140105",
    "移轉層次": "八層",
    "總樓層數": "十五層",
    "建物型態": "住宅大樓",
    "建築完成年月": "1000101",
    "建物移轉總面積平方公尺": "99.17",
    "總價元": "24000000",
    "單價元平方公尺": "242008",
}


def test_normalize_official_row_converts_units_and_dates() -> None:
    row, reason = normalize_row(VALID_ROW, city_hint="台北市")
    assert reason is None
    assert row is not None
    assert row["transaction_period"] == "2025-01"
    assert row["road"] == "和平東路二段"
    assert 29.9 < row["area_ping"] < 30.1
    assert row["unit_price_per_ping"] > 70
    assert row["source"] == "official_plvr_opendata"


def test_missing_unit_price_is_calculated_from_total_and_area() -> None:
    row, reason = normalize_row({**VALID_ROW, "單價元平方公尺": ""}, city_hint="台北市")
    assert reason is None
    assert row is not None
    assert row["unit_price_per_ping"] == round(row["total_price"] / row["area_ping"], 2)


def test_quality_control_reports_exclusions() -> None:
    rows, report = normalize_rows([VALID_ROW, {**VALID_ROW, "總價元": "0"}], city_hint="台北市")
    assert len(rows) == 1
    assert report["exclusion_reasons"]["invalid_total_price"] == 1


def test_common_parsers() -> None:
    assert roc_date_to_period("1131201") == "2024-12"
    assert roc_date_to_period("20250101") == "2025-01"
    assert parse_floor("十五層") == 15
    assert parse_road("新北市板橋區文化路二段188號") == "文化路二段"
    assert parse_road("台北市大同區市民大道一段100號") == "市民大道一段"


def test_candidate_detection_excludes_schema(tmp_path) -> None:
    sale = tmp_path / "a_lvr_land_a.csv"
    sale.write_text(",".join(VALID_ROW) + "\n" + ",".join(VALID_ROW.values()), encoding="utf-8-sig")
    schema = tmp_path / "schema.csv"
    schema.write_text(sale.read_text(encoding="utf-8-sig"), encoding="utf-8-sig")
    assert is_sale_transaction_csv(sale) is True
    assert is_sale_transaction_csv(schema) is False
