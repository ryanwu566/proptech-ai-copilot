"""Tests for the safe PLVR dedupe_key v2 backfill tool."""

from __future__ import annotations

from scripts import backfill_dedupe_key_v2 as backfill
from services.plvr_import_service import OFFICIAL_SOURCE, build_dedupe_key


def official_row(**overrides: object) -> dict[str, object]:
    """Return one representative persisted official transaction row."""
    row: dict[str, object] = {
        "id": 1,
        "transaction_period": "2025-05",
        "city": "台中市",
        "district": "西屯區",
        "address_text": "臺灣大道三段100號",
        "building_type": "住宅大樓",
        "area_ping": 30.5,
        "total_price": 1800.0,
        "unit_price_per_ping": 59.02,
        "source": OFFICIAL_SOURCE,
        "dedupe_key": "old-key",
    }
    row.update(overrides)
    return row


def test_make_report_only_processes_official_rows() -> None:
    report, candidates = backfill.make_report(
        [
            official_row(),
            official_row(id=2, source="real_price_sample"),
            official_row(id=3, source="mock_fallback"),
        ]
    )

    assert report["rows_scanned"] == 1
    assert report["rows_needing_update"] == 1
    assert len(candidates) == 1


def test_make_report_detects_already_v2() -> None:
    row = official_row(dedupe_key="")
    row["dedupe_key"] = build_dedupe_key(row)

    report, candidates = backfill.make_report([row])

    assert report["rows_already_v2"] == 1
    assert report["rows_needing_update"] == 0
    assert candidates == []


def test_duplicate_rebuilt_keys_are_reported_and_not_updated() -> None:
    first = official_row(id=1, dedupe_key="old-a")
    second = official_row(id=2, dedupe_key="old-b")

    report, candidates = backfill.make_report([first, second])

    assert report["potential_duplicate_groups_after_v2"] == 1
    assert report["rows_skipped_due_to_potential_duplicates"] == 2
    assert candidates == []


def test_same_transaction_v2_key_is_stable() -> None:
    first = official_row(city="臺中市")
    second = official_row(city="台中市", dedupe_key="another-old-key")

    assert build_dedupe_key(first) == build_dedupe_key(second)


def test_same_serial_in_different_cities_has_different_v2_key() -> None:
    first = official_row(city="台中市")
    second = official_row(city="台南市")

    assert build_dedupe_key(first, transaction_id="ABC-001") != build_dedupe_key(
        second, transaction_id="ABC-001"
    )


def test_tainan_variants_normalize_to_same_key() -> None:
    first = official_row(city="臺南市")
    second = official_row(city="台南市")

    assert build_dedupe_key(first) == build_dedupe_key(second)


def test_dry_run_wins_over_confirm_update(monkeypatch, capsys) -> None:
    captured: dict[str, object] = {}

    def fake_run_backfill(database_url: str, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": "completed"}

    monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://redacted")
    monkeypatch.setattr(backfill, "run_backfill", fake_run_backfill)

    assert backfill.main(["--confirm-update", "--dry-run"]) == 0
    assert captured["will_update"] is False
    assert '"status": "dry_run"' in capsys.readouterr().out


def test_confirm_update_is_required(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run_backfill(database_url: str, **kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": "dry_run"}

    monkeypatch.setenv("VALUATION_DATABASE_URL", "postgresql://redacted")
    monkeypatch.setattr(backfill, "run_backfill", fake_run_backfill)

    assert backfill.main([]) == 0
    assert captured["will_update"] is False

    assert backfill.main(["--confirm-update"]) == 0
    assert captured["will_update"] is True


def test_missing_database_url_exits_without_scanning(monkeypatch, capsys) -> None:
    monkeypatch.delenv("VALUATION_DATABASE_URL", raising=False)

    assert backfill.main(["--confirm-update"]) == 0
    assert "未掃描或更新任何資料" in capsys.readouterr().out
