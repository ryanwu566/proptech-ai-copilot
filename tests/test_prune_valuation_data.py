from scripts import prune_valuation_data as prune


def test_retention_cutoff_is_rolling_five_year_window() -> None:
    assert prune.retention_cutoff_period(5, "2026-06") == "2021-07"
    assert prune.retention_cutoff_period(3, "2026-06") == "2023-07"


def test_city_normalization_supports_taiwan_variants() -> None:
    assert prune.normalize_cities("臺中市,台中市,臺南市,台南市,臺北市") == ["台中市", "台南市", "台北市"]


def test_prune_defaults_to_dry_run_without_confirm(monkeypatch, capsys) -> None:
    captured = {}
    monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://configured-but-not-used")
    monkeypatch.setattr(
        prune,
        "inspect_and_prune",
        lambda _url, cutoff, cities, will_delete: captured.update(
            {"cutoff": cutoff, "cities": cities, "will_delete": will_delete}
        )
        or {"status": "dry_run", "will_delete": False},
    )
    assert prune.main(["--before", "2021-01", "--cities", "臺北市,新北市"]) == 0
    assert captured == {"cutoff": "2021-01", "cities": ["台北市", "新北市"], "will_delete": False}
    assert '"status": "dry_run"' in capsys.readouterr().out


def test_confirm_delete_is_required_and_dry_run_wins(monkeypatch) -> None:
    modes: list[bool] = []
    monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://configured-but-not-used")
    monkeypatch.setattr(
        prune,
        "inspect_and_prune",
        lambda _url, _cutoff, _cities, will_delete: modes.append(will_delete)
        or {"status": "deleted" if will_delete else "dry_run"},
    )
    assert prune.main(["--before", "2021-01", "--confirm-delete"]) == 0
    assert prune.main(["--before", "2021-01", "--confirm-delete", "--dry-run"]) == 0
    assert modes == [True, False]


def test_non_official_source_is_blocked(monkeypatch, capsys) -> None:
    monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://configured-but-not-used")
    assert prune.main(["--source", "real_price_sample", "--confirm-delete"]) == 1
    assert "只允許 official_plvr_opendata" in capsys.readouterr().out


def test_missing_database_url_never_deletes(monkeypatch, capsys) -> None:
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)
    assert prune.main(["--confirm-delete"]) == 0
    assert "不會刪除任何資料" in capsys.readouterr().out


class _FakeCursor:
    def __init__(self) -> None:
        self.query = ""
        self.queries: list[str] = []
        self.rowcount = 3

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, _params=None) -> None:
        self.query = " ".join(query.split())
        self.queries.append(self.query)

    def fetchone(self):
        return {"matched_rows": 3}

    def fetchall(self):
        if "group by replace" in self.query:
            return [{"city": "台北市", "rows": 3}]
        return [{"period": "2020-12", "rows": 3}]


class _FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = _FakeCursor()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self):
        return self.cursor_instance


def test_inspect_dry_run_never_issues_delete(monkeypatch) -> None:
    import psycopg

    connection = _FakeConnection()
    monkeypatch.setattr(psycopg, "connect", lambda *_args, **_kwargs: connection)
    report = prune.inspect_and_prune("postgresql://test", "2021-01", ["台北市"], False)
    assert report["status"] == "dry_run"
    assert report["deleted_rows"] == 0
    assert not any(query.startswith("delete ") for query in connection.cursor_instance.queries)


def test_confirmed_prune_deletes_only_official_transactions(monkeypatch) -> None:
    import psycopg

    connection = _FakeConnection()
    monkeypatch.setattr(psycopg, "connect", lambda *_args, **_kwargs: connection)
    report = prune.inspect_and_prune("postgresql://test", "2021-01", ["臺北市"], True)
    delete_queries = [query for query in connection.cursor_instance.queries if query.startswith("delete ")]
    assert report["deleted_rows"] == 3
    assert len(delete_queries) == 1
    assert "real_price_transactions" in delete_queries[0]
    assert "source = %s" in delete_queries[0]
    assert "real_price_sample" not in delete_queries[0]
    assert "community_buildings" not in delete_queries[0]
    assert "valuation_import_runs" not in delete_queries[0]
