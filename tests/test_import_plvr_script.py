from scripts.import_plvr_to_postgres import main


CSV_TEXT = """鄉鎮市區,交易標的,土地位置建物門牌,交易年月日,移轉層次,總樓層數,建物型態,建築完成年月,建物移轉總面積平方公尺,總價元,單價元平方公尺
The villages and towns urban district,transaction sign,land sector position building sector house number plate,transaction year month and day,shifting level,total floor number,building state,construction to complete the years,building shifting total area,total price NTD,the unit price
大安區,房地(土地+建物),和平東路二段100號,1140105,八層,十五層,住宅大樓,1000101,99.17,24000000,242008
"""


def test_dry_run_does_not_require_database_url(tmp_path, monkeypatch, capsys) -> None:
    path = tmp_path / "a_lvr_land_a.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
    assert main(["--input", str(path), "--city", "台北市", "--dry-run"]) == 0
    assert '"status": "dry_run"' in capsys.readouterr().out


def test_missing_database_url_exits_friendly(tmp_path, monkeypatch, capsys) -> None:
    path = tmp_path / "a_lvr_land_a.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
    assert main(["--input", str(path), "--city", "台北市"]) == 0
    assert "未設定 VALUATION_DATABASE_URL" in capsys.readouterr().out


def test_replace_scope_requires_filter(tmp_path, capsys) -> None:
    path = tmp_path / "a_lvr_land_a.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")
    assert main(["--input", str(path), "--replace-scope", "--dry-run"]) == 1
    assert "必須搭配" in capsys.readouterr().out


def test_daan_official_direct_csv_dry_run_is_recognized(tmp_path, capsys) -> None:
    path = tmp_path / "a_lvr_land_a.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")
    assert main(["--input", str(path), "--city", "台北市", "--district", "大安區", "--limit", "1000", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "找不到可辨識" not in output
    assert '"accepted_rows": 1' in output


def test_new_taipei_filename_city_hint_overrides_wrong_external_hint(tmp_path, capsys) -> None:
    path = tmp_path / "f_lvr_land_a.csv"
    path.write_text(CSV_TEXT.replace("大安區", "板橋區").replace("和平東路二段", "文化路二段"), encoding="utf-8-sig")
    assert main(["--input", str(path), "--city", "台北市", "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert '"city_hint": "新北市"' in output
