from scripts.seed_valuation_sample_to_postgres import seed


def test_seed_without_database_url_exits_friendly(capsys) -> None:
    assert seed("") == 0
    assert "未設定 VALUATION_DATABASE_URL" in capsys.readouterr().out


class _SeedCursor:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, *_args, **_kwargs):
        return None

    def executemany(self, *_args, **_kwargs):
        return None


class _SeedConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self):
        return _SeedCursor()


def test_seed_disables_prepared_statements(monkeypatch) -> None:
    import psycopg

    captured = {}

    def fake_connect(*_args, **kwargs):
        captured.update(kwargs)
        return _SeedConnection()

    monkeypatch.setattr(psycopg, "connect", fake_connect)
    assert seed("postgresql://test") == 0
    assert captured["prepare_threshold"] is None
    assert captured["connect_timeout"] == 10
