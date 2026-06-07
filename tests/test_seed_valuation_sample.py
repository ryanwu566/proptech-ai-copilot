from scripts.seed_valuation_sample_to_postgres import seed


def test_seed_without_database_url_exits_friendly(capsys) -> None:
    assert seed("") == 0
    assert "未設定 VALUATION_DATABASE_URL" in capsys.readouterr().out
