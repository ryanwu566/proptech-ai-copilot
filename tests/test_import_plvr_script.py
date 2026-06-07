from scripts.import_plvr_to_postgres import main


CSV_TEXT = """鄉鎮市區,土地區段位置建物區段門牌,交易年月日,移轉層次,總樓層數,建物型態,建築完成年月,建物移轉總面積平方公尺,總價元,單價元平方公尺
大安區,台北市大安區和平東路二段100號,1140105,八層,十五層,住宅大樓,1000101,99.17,24000000,242008
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
