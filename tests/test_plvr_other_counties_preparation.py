"""Preparation tests for rolling-three-year PLVR imports outside the six cities."""

from __future__ import annotations

import json

import pytest

from scripts.import_plvr_to_postgres import main
from services.plvr_import_service import city_from_filename, is_sale_transaction_csv


CSV_TEXT = """鄉鎮市區,交易標的,土地位置建物門牌,交易年月日,移轉層次,總樓層數,建物型態,建築完成年月,建物移轉總面積平方公尺,總價元,單價元平方公尺
The villages and towns urban district,transaction sign,land sector position building sector house number plate,transaction year month and day,shifting level,total floor number,building state,construction to complete the years,building shifting total area,total price NTD,the unit price
仁愛區,房地(土地+建物),仁愛路100號,1140105,八層,十五層,住宅大樓,1000101,99.17,24000000,242008
"""


OTHER_COUNTY_CODES = {
    "c": "基隆市",
    "o": "新竹市",
    "j": "新竹縣",
    "k": "苗栗縣",
    "n": "彰化縣",
    "m": "南投縣",
    "p": "雲林縣",
    "i": "嘉義市",
    "q": "嘉義縣",
    "t": "屏東縣",
    "g": "宜蘭縣",
    "u": "花蓮縣",
    "v": "台東縣",
    "x": "澎湖縣",
    "w": "金門縣",
    "z": "連江縣",
}


@pytest.mark.parametrize(("code", "city"), OTHER_COUNTY_CODES.items())
def test_other_county_main_filename_maps_case_insensitively(tmp_path, code: str, city: str) -> None:
    lower = tmp_path / f"{code}_lvr_land_a.csv"
    upper = tmp_path / f"{code.upper()}_lvr_land_A.csv"

    assert city_from_filename(lower) == city
    assert city_from_filename(upper) == city


@pytest.mark.parametrize("suffix", ("park", "land", "build"))
def test_other_county_detail_file_is_not_a_sale_main_file(tmp_path, suffix: str) -> None:
    path = tmp_path / f"C_lvr_land_{suffix}.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")

    assert is_sale_transaction_csv(path) is False
    assert city_from_filename(path) == ""


def test_other_county_dry_run_reports_filename_city_hint(tmp_path, capsys) -> None:
    path = tmp_path / "C_lvr_land_A.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")

    assert main(["--input", str(path), "--city", "基隆市", "--dry-run"]) == 0
    report = json.loads(capsys.readouterr().out)

    assert report["files"][0]["city_hint"] == "基隆市"
    assert report["natural_duplicate_check"] == "db_required"
    assert "accepted_rows_by_city" in report
    assert "skipped_natural_duplicate_rows_by_city" in report
    assert "skipped_dedupe_key_duplicate_rows" in report
    assert "limit_reached" in report
    assert "limit_warning" in report
    assert "source_periods" in report
