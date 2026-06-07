import json

from scripts import import_plvr_to_postgres as importer
from scripts.import_plvr_to_postgres import _chunks, _safe_error_reason, _write_rows, build_parser, main


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


def test_taichung_main_file_dry_run_has_city_diagnostics(tmp_path, capsys) -> None:
    path = tmp_path / "B_lvr_land_A.csv"
    path.write_text(CSV_TEXT.replace("大安區", "西屯區").replace("和平東路二段", "台灣大道三段"), encoding="utf-8-sig")
    assert main(["--input", str(path), "--city", "台中市", "--dry-run"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["files"][0]["city_hint"] == "台中市"
    assert report["accepted_rows"] == 1
    assert report["accepted_rows_by_city"] == {"台中市": 1}
    assert report["estimated_growth"] == 1
    assert report["inserted_rows_by_city"] == {}


def test_limit_reached_adds_warning(tmp_path, capsys) -> None:
    path = tmp_path / "b_lvr_land_a.csv"
    path.write_text(CSV_TEXT.replace("大安區", "西屯區").replace("和平東路二段", "台灣大道三段"), encoding="utf-8-sig")
    assert main(["--input", str(path), "--city", "臺中市", "--limit", "1", "--dry-run"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["limit_reached"] is True
    assert "可能因 --limit 截斷" in report["limit_warning"]


def test_folder_input_reads_multiple_csv_and_dedupes_batch(tmp_path, capsys) -> None:
    history = tmp_path / "history"
    history.mkdir()
    (history / "a_lvr_land_a.csv").write_text(CSV_TEXT, encoding="utf-8-sig")
    (history / "period_copy.csv").write_text(CSV_TEXT, encoding="utf-8-sig")
    assert main(["--input", str(history), "--city", "台北市", "--dry-run"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["files_processed"] == 2
    assert report["accepted_rows"] == 1
    assert report["skipped_duplicate_rows"] == 1


def test_folder_input_without_city_scope_is_blocked(tmp_path, capsys) -> None:
    history = tmp_path / "history"
    history.mkdir()
    (history / "a_lvr_land_a.csv").write_text(CSV_TEXT, encoding="utf-8-sig")
    assert main(["--input", str(history), "--dry-run"]) == 1
    assert "必須指定 --city 或 --cities" in capsys.readouterr().out


def test_large_import_requires_confirmation(tmp_path, monkeypatch, capsys) -> None:
    path = tmp_path / "a_lvr_land_a.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")
    rows = [{"dedupe_key": f"key-{index}"} for index in range(10_001)]
    report = {
        "read_rows": 10_001,
        "accepted_rows": 10_001,
        "excluded_rows": 0,
        "exclusion_reasons": {},
        "periods": ["2025-01"],
        "cities": ["台北市"],
        "districts": ["大安區"],
        "roads_count": 1,
        "city_counts": {"台北市": 10_001},
        "district_counts": {"大安區": 10_001},
        "road_counts": {"和平東路二段": 10_001},
    }
    monkeypatch.setattr(importer, "normalize_rows", lambda *_args, **_kwargs: (rows, report))
    assert main(["--input", str(path), "--city", "台北市", "--dry-run"]) == 1
    assert '"status": "blocked_large_import"' in capsys.readouterr().out


def test_chunk_write_cli_defaults() -> None:
    args = build_parser().parse_args(["--input", "sample.csv"])
    assert args.chunk_size == 200
    assert args.progress_every == 100
    assert args.statement_timeout == 30
    assert args.max_write_rows is None
    assert [len(chunk) for chunk in _chunks([{"id": index} for index in range(450)], 200)] == [200, 200, 50]


def test_max_write_rows_limits_formal_write(tmp_path, monkeypatch, capsys) -> None:
    path = tmp_path / "a_lvr_land_a.csv"
    path.write_text(CSV_TEXT, encoding="utf-8-sig")
    captured: dict[str, int] = {}
    monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://configured-but-not-used")
    monkeypatch.setattr(
        importer,
        "_write_rows",
        lambda _url, rows, _report, _args, _cities, _districts: captured.update({"rows": len(rows)})
        or {
            "inserted_rows": len(rows),
            "updated_rows": 0,
            "skipped_duplicate_rows": 0,
            "current_db_records_before": 0,
            "current_db_records_after": len(rows),
            "current_db_official_before": 0,
            "current_db_official_after": len(rows),
            "estimated_growth": len(rows),
        },
    )
    assert main(["--input", str(path), "--city", "台北市", "--max-write-rows", "1"]) == 0
    assert captured["rows"] == 1
    assert '"write_rows": 1' in capsys.readouterr().out


class _FakeTransaction:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None


class _BatchCursor:
    def __init__(self) -> None:
        self.query = ""
        self.batch_size = 0
        self.executemany_sizes: list[int] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, query, _params=None) -> None:
        self.query = " ".join(query.split())

    def executemany(self, _query, rows) -> None:
        batch = list(rows)
        self.batch_size = len(batch)
        self.executemany_sizes.append(len(batch))

    def fetchone(self):
        if "select count(*) as inserted_rows from inserted" in self.query:
            return {"inserted_rows": self.batch_size}
        if "count(*) as records_count" in self.query:
            return {"records_count": 0, "official_records_count": 0}
        return None

    def fetchall(self):
        if "select city, count(*) as inserted_rows from inserted" in self.query:
            return [{"city": "台北市", "inserted_rows": self.batch_size}]
        return []


class _BatchConnection:
    def __init__(self) -> None:
        self.cursor_instance = _BatchCursor()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def cursor(self):
        return self.cursor_instance

    def commit(self) -> None:
        return None

    def transaction(self):
        return _FakeTransaction()


def test_write_rows_uses_staging_chunks_and_progress(monkeypatch, capsys) -> None:
    import psycopg

    connection = _BatchConnection()
    connect_kwargs = {}
    def fake_connect(*_args, **kwargs):
        connect_kwargs.update(kwargs)
        return connection
    monkeypatch.setattr(psycopg, "connect", fake_connect)
    args = build_parser().parse_args(
        ["--input", "sample.csv", "--city", "台北市", "--chunk-size", "2", "--progress-every", "2", "--statement-timeout", "30"]
    )
    rows = [
        {
            "transaction_period": "2025-01", "city": "台北市", "district": "大安區", "road": "和平東路二段",
            "address_text": f"和平東路二段{index}號", "building_type": "住宅大樓", "area_ping": 30,
            "building_age_years": 15, "floor": 8, "total_floor": 15, "unit_price_per_ping": 70,
            "total_price": 2100, "lat": None, "lng": None, "source": "official_plvr_opendata",
            "raw_note": "", "dedupe_key": f"key-{index}",
        }
        for index in range(5)
    ]
    report = {"skipped_duplicate_rows": 0, "source_periods": ["2025-01"], "files_processed": 1, "read_rows": 5, "accepted_rows": 5, "excluded_rows": 0}
    result = _write_rows("postgresql://test", rows, report, args, ["台北市"], ["大安區"])
    assert connection.cursor_instance.executemany_sizes == [2, 2, 1]
    assert result["inserted_rows"] == 5
    assert result["inserted_rows_by_city"] == {"台北市": 5}
    assert result["skipped_duplicate_rows_by_city"] == {}
    assert connect_kwargs["prepare_threshold"] is None
    assert connect_kwargs["connect_timeout"] == 10
    output = capsys.readouterr().out
    assert "Writing rows 1-2 / 5" in output
    assert "Writing rows 5-5 / 5" in output


def test_safe_chunk_error_reason_is_concise() -> None:
    error = RuntimeError("prepared statement _pg3_0 already exists\nconnection details omitted")
    reason = _safe_error_reason(error)
    assert "\n" not in reason
    assert "prepared statement" in reason
    assert len(reason) <= 240
