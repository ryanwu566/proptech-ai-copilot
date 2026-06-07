from services.plvr_import_service import build_dedupe_key, city_from_filename, is_sale_transaction_csv, normalize_row, normalize_rows, parse_floor, parse_road, read_csv_rows, roc_date_to_period


VALID_ROW = {
    "鄉鎮市區": "大安區",
    "交易標的": "房地(土地+建物)",
    "土地位置建物門牌": "台北市大安區和平東路二段100號",
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


def test_same_transaction_builds_same_dedupe_key() -> None:
    first, reason = normalize_row(VALID_ROW, city_hint="台北市")
    second, second_reason = normalize_row(dict(VALID_ROW), city_hint="台北市")
    assert reason is None and second_reason is None
    assert first is not None and second is not None
    assert first["dedupe_key"] == second["dedupe_key"]
    assert first["dedupe_key"] == build_dedupe_key(first)


def test_dedupe_key_v2_uses_official_id_and_transaction_facts() -> None:
    row = {
        "source": "official_plvr_opendata", "city": "台北市", "district": "大安區",
        "transaction_period": "2025-01", "address_text": "和平東路二段100號",
        "building_type": "住宅大樓", "area_ping": 30, "total_price": 2400, "unit_price_per_ping": 80,
    }
    assert build_dedupe_key(row, "A-123") == build_dedupe_key(dict(row), "A-123")
    assert build_dedupe_key(row, "A-123") != build_dedupe_key({**row, "city": "台中市"}, "A-123")
    assert build_dedupe_key(row, "A-123") != build_dedupe_key(row, "A-456")
    assert build_dedupe_key({**row, "city": "臺中市"}, "A-123") == build_dedupe_key({**row, "city": "台中市"}, "A-123")
    assert build_dedupe_key({**row, "city": "臺南市"}, "A-123") == build_dedupe_key({**row, "city": "台南市"}, "A-123")


def test_period_filters_are_applied() -> None:
    rows, report = normalize_rows([VALID_ROW], city_hint="台北市", since="2025-02")
    assert rows == []
    assert report["exclusion_reasons"]["filtered_before_since"] == 1


def test_land_only_transaction_is_excluded() -> None:
    row, reason = normalize_row({**VALID_ROW, "交易標的": "土地", "建物移轉總面積平方公尺": "0"}, city_hint="台北市")
    assert row is None
    assert reason == "non_building_transaction"


def test_building_transaction_is_accepted() -> None:
    row, reason = normalize_row(VALID_ROW, city_hint="台北市")
    assert reason is None
    assert row is not None


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


def test_official_second_english_description_row_is_skipped(tmp_path) -> None:
    path = tmp_path / "a_lvr_land_a.csv"
    path.write_text(
        "鄉鎮市區,交易標的,土地位置建物門牌,交易年月日,建物移轉總面積平方公尺,總價元\n"
        "The villages and towns urban district,transaction sign,land sector position building sector house number plate,transaction year month and day,building shifting total area,total price NTD\n"
        "大安區,房地(土地+建物),和平東路二段100號,1140105,99.17,24000000\n",
        encoding="utf-8-sig",
    )
    rows, _ = read_csv_rows(path)
    assert len(rows) == 1
    assert rows[0]["鄉鎮市區"] == "大安區"


def test_official_sale_filename_is_directly_recognized_and_maps_city(tmp_path) -> None:
    path = tmp_path / "A_LVR_LAND_A.CSV"
    path.write_text("not,a,valid,header\n", encoding="utf-8")
    assert is_sale_transaction_csv(path) is True
    assert city_from_filename(path) == "台北市"
    assert city_from_filename(tmp_path / "f_lvr_land_a.csv") == "新北市"
    expected = {"a": "台北市", "f": "新北市", "h": "桃園市", "b": "台中市", "d": "台南市", "e": "高雄市"}
    for code, city in expected.items():
        assert city_from_filename(tmp_path / f"{code}_lvr_land_A.csv") == city
        assert city_from_filename(tmp_path / f"{code.upper()}_lvr_land_a.csv") == city


def test_non_main_detail_filenames_are_excluded(tmp_path) -> None:
    for name in ("B_lvr_land_park.csv", "B_lvr_land_land.csv", "B_lvr_land_build.csv"):
        path = tmp_path / name
        path.write_text(",".join(VALID_ROW) + "\n" + ",".join(VALID_ROW.values()), encoding="utf-8-sig")
        assert is_sale_transaction_csv(path) is False
