"""Static CLI boundaries for Phase 2C authoritative acquisition."""

from __future__ import annotations

from pathlib import Path

from scripts import acquire_official_plvr_artifacts as acquire
from scripts import build_plvr_clean_shadow as build


ROOT = Path(__file__).resolve().parents[1]


def test_acquisition_defaults_to_inventory_not_download() -> None:
    args = acquire.build_parser().parse_args(["--season", "115S2"])

    assert args.download is False
    assert args.season == ["115S2"]


def test_acquisition_requires_explicit_scope() -> None:
    assert acquire.main([]) == 2


def test_shadow_reconciliation_is_opt_in_and_uses_env_name_only() -> None:
    args = build.build_parser().parse_args(
        ["--since", "2023-09", "--until", "2026-08", "--as-of-date", "2026-08-11"]
    )

    assert args.reconcile_production is False
    assert args.database_url_env == "VALUATION_DATABASE_URL"


def test_raw_and_processed_artifacts_are_gitignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")

    assert "data/raw/" in ignore
    assert "data/processed/" in ignore
    assert "*.zip" in ignore


def test_phase_2c_sources_do_not_define_production_mutation_sql() -> None:
    sources = "\n".join(
        (ROOT / path).read_text(encoding="utf-8").lower()
        for path in (
            "services/plvr_clean_shadow_rebuild.py",
            "scripts/acquire_official_plvr_artifacts.py",
            "scripts/build_plvr_clean_shadow.py",
        )
    )

    for statement in (
        "update real_price_transactions",
        "delete from real_price_transactions",
        "insert into real_price_transactions",
        "truncate real_price_transactions",
        "drop table real_price_transactions",
        "alter table real_price_transactions",
        "delete from market_district_period_aggregates",
    ):
        assert statement not in sources
