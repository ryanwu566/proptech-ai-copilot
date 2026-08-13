from __future__ import annotations

import json
import sqlite3
import subprocess
from pathlib import Path

from services.plvr_residual_resolution import (
    RevisedCleanBucket,
    RevisedProductionBucket,
    _classify_clean,
    _classify_production,
    _create_schema,
    _risk_matrix,
)


ROOT = Path(__file__).resolve().parents[1]


def _attach(connection: sqlite3.Connection, alias: str, path: Path) -> None:
    connection.execute(f"attach database ? as {alias}", (str(path),))


def test_tier_c_one_to_one_is_match_and_one_to_many_is_duplicate(
    tmp_path: Path,
) -> None:
    prior_path = tmp_path / "prior.sqlite3"
    prior = sqlite3.connect(prior_path)
    prior.execute(
        """
        create table production_classification (
            stable_id integer primary key, bucket text, detail text,
            clean_id text, evidence_tier text, geography_matches integer,
            canonical_invalid integer, legacy_supporting integer,
            legacy_duplicate_candidate integer, production_only_reason text
        )
        """
    )
    prior.executemany(
        "insert into production_classification values (?, ?, '', ?, 'C', 1, 0, 0, 0, '')",
        (
            (1, "PROD_PROBABLE_DUPLICATE", "clean-one"),
            (2, "PROD_PROBABLE_DUPLICATE", "clean-many"),
            (3, "PROD_PROBABLE_DUPLICATE", "clean-many"),
        ),
    )
    prior.commit()
    prior.close()

    output = sqlite3.connect(":memory:")
    _attach(output, "prior", prior_path)
    _create_schema(output)
    _classify_production(output)
    rows = {
        int(row[0]): (str(row[1]), str(row[2]))
        for row in output.execute(
            "select row_reference, bucket, subtype from production_resolution"
        )
    }
    output.close()
    assert rows[1] == (
        RevisedProductionBucket.STRONG_FACT_MATCH.value,
        "STRONG_FACT_MATCH_1_TO_1",
    )
    assert rows[2] == rows[3] == (
        RevisedProductionBucket.DUPLICATE.value,
        "STRONG_FACT_DUPLICATE_1_TO_MANY",
    )


def test_clean_side_strong_fact_and_duplicate_reclassification(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "snapshot.sqlite3"
    snapshot = sqlite3.connect(snapshot_path)
    snapshot.execute(
        "create table snapshot_transactions (stable_id integer primary key, canonical_business_fact_hash text)"
    )
    snapshot.commit()
    snapshot.close()

    output = sqlite3.connect(":memory:")
    _attach(output, "snapshot", snapshot_path)
    _create_schema(output)
    clean_rows = []
    for clean_id in ("clean-one", "clean-many", "clean-missing"):
        clean_rows.append(
            (
                clean_id,
                f"source-{clean_id}",
                f"fact-{clean_id}",
                "artifact",
                1,
                "臺北市",
                "台北市",
                "中正區",
                "district",
                "2026-01",
                f"address-{clean_id}",
                1.0,
                10.0,
                100.0,
                20.0,
            )
        )
    output.executemany(
        "insert into clean_aux values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        clean_rows,
    )
    output.executemany(
        "insert into production_resolution values (?, ?, ?, 'C', ?, 0)",
        (
            (1, "STRONG_FACT_MATCH", "STRONG_FACT_MATCH_1_TO_1", "clean-one"),
            (2, "DUPLICATE", "STRONG_FACT_DUPLICATE_1_TO_MANY", "clean-many"),
            (3, "DUPLICATE", "STRONG_FACT_DUPLICATE_1_TO_MANY", "clean-many"),
        ),
    )
    _classify_clean(output)
    rows = {
        str(row[0]): str(row[1])
        for row in output.execute("select clean_id, bucket from clean_resolution")
    }
    output.close()
    assert rows == {
        "clean-one": RevisedCleanBucket.PRESENT_BY_STRONG_FACT.value,
        "clean-many": RevisedCleanBucket.DUPLICATED_IN_PROD.value,
        "clean-missing": RevisedCleanBucket.MISSING_FROM_PROD.value,
    }


def test_committed_residual_artifacts_conserve_every_required_cohort() -> None:
    report = _summary()
    assert sum(report["production_buckets"].values()) == 451_672
    assert sum(report["clean_buckets"].values()) == 517_195
    assert sum(report["production_only_5017"].values()) == 5_017
    assert sum(report["invalid_geography"].values()) == 126_087
    assert report["conflicts"]["production_rows"] == (
        report["conflicts"]["resolved_rows"]
        + report["conflicts"]["materially_unresolved_rows"]
    )
    assert report["aggregate_attribution"]["status_conserved"] is True
    assert report["clean_unclassified_reasons"] == {
        "BOUNDED_FACT_GROUP_AMBIGUITY": 460
    }
    assert (
        report["aggregate_attribution"]["fully_explained_scopes"]
        + report["aggregate_attribution"]["partially_explained_scopes"]
        + report["aggregate_attribution"]["unexplained_scopes"]
        == report["aggregate_attribution"]["mismatched_scopes"]
    )


def test_historical_future_and_materiality_contracts_are_explicit() -> None:
    report = _summary()
    assert report["historical_cohorts"]["historical_109236"]["status"] == "REPRODUCIBLE"
    assert (
        report["historical_cohorts"]["historical_109236"]["reproduced_count"]
        == 109_236
    )
    assert (
        report["historical_cohorts"]["historical_57350"]["status"]
        == "PARTIALLY_REPRODUCIBLE"
    )
    assert report["future_row"] == {
        "artifact_id": "moi-plvr-sale-season-115S1",
        "production_count": 1,
        "publishable_status": "excluded",
        "status": "STRONG_FACT_FUTURE_SOURCE_MATCH",
    }
    assert report["aggregate_attribution"]["unexplained_scopes"] == 0
    assert report["aggregate_attribution"]["scope_percentages"] == {
        "FULLY_EXPLAINED": 98.6908,
        "PARTIALLY_EXPLAINED": 1.3092,
        "UNEXPLAINED": 0.0,
    }
    assert set(
        report["aggregate_attribution"]["attribution_matrix_scope_counts"]
    ) == {
        "PRODUCTION_ONLY_BAD_IMPORT",
        "PRODUCTION_ONLY_OUTSIDE_WINDOW",
        "CLEAN_MISSING_FROM_PROD",
        "STRONG_FACT_DUPLICATE",
        "INVALID_GEOGRAPHY",
        "FUTURE_EXCLUSION",
        "SOURCE_SCOPE_DIFFERENCE",
        "CANONICAL_GEOGRAPHY_SEMANTICS",
        "OTHER_KNOWN",
        "CONFLICTING_IDENTITY",
        "INSUFFICIENT_EVIDENCE",
        "SOURCE_RECORD_NOT_REACQUIRED",
        "UNEXPLAINED",
    }
    assert (
        report["aggregate_attribution"]["materiality"]["result"]
        == "IMMATERIAL_BOUNDED"
    )


def test_cutover_design_and_execution_blockers_are_separate() -> None:
    matrix, design, execution = _risk_matrix(
        {
            "STRONG_FACT_MATCH": 1,
            "DUPLICATE": 1,
            "NOT_IN_CLEAN_SOURCE": 1,
            "CONFLICTING": 1,
            "FUTURE_ANOMALY": 1,
        },
        {"MISSING_FROM_PROD": 1},
        {"production_rows": 1},
        {"INSUFFICIENT_EVIDENCE": 1},
        {},
        {"materiality": {"result": "IMMATERIAL_BOUNDED"}},
        [{"shadow_internally_consistent": True}],
    )
    assert matrix
    assert design == []
    assert execution
    _, design, _ = _risk_matrix(
        {},
        {},
        {"production_rows": 0},
        {},
        {},
        {"materiality": {"result": "MATERIAL_UNEXPLAINED"}},
        [{"shadow_internally_consistent": True}],
    )
    assert design == ["aggregate_unexplained_scopes_material"]


def test_conflicts_are_bounded_with_safe_group_topology() -> None:
    conflicts = _summary()["conflicts"]
    assert conflicts["group_count"] == 193
    assert conflicts["production_rows"] == 458
    assert conflicts["single_artifact_groups"] == 183
    assert conflicts["single_artifact_production_rows"] == 439
    assert conflicts["multi_artifact_groups"] == 10
    assert conflicts["multi_artifact_production_rows"] == 19
    assert sum(item["group_count"] for item in conflicts["group_topology"]) == 193
    assert sum(item["production_rows"] for item in conflicts["group_topology"]) == 458
    assert conflicts["unique_auxiliary_resolutions"] == 0


def test_safe_artifacts_have_no_secret_or_raw_snapshot_surface() -> None:
    paths = (
        ROOT / "artifacts" / "plvr_residual_resolution_summary.json",
        ROOT / "artifacts" / "plvr_revised_reconciliation_buckets.json",
        ROOT / "artifacts" / "plvr_aggregate_delta_attribution.json",
        ROOT / "artifacts" / "plvr_cutover_risk_matrix.json",
    )
    serialized = " ".join(path.read_text(encoding="utf-8").lower() for path in paths)
    for forbidden in (
        "database_url",
        "postgresql://",
        "password",
        "address_text",
        "stable_id",
        "source_row_hash",
        "dedupe_key",
    ):
        assert forbidden not in serialized
    source = (
        ROOT / "services" / "plvr_residual_resolution.py"
    ).read_text(encoding="utf-8").lower()
    assert "psycopg" not in source
    assert "real_price_transactions" not in source


def test_local_resolution_database_is_ignored_and_not_tracked() -> None:
    path = "data/processed/plvr/phase2c5/residual-resolution.sqlite3"
    ignored = subprocess.run(
        ["git", "check-ignore", "--quiet", "--", path],
        cwd=ROOT,
        check=False,
    )
    tracked = subprocess.run(
        ["git", "ls-files", "--", path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert ignored.returncode == 0
    assert tracked.stdout.strip() == ""


def _summary() -> dict:
    return json.loads(
        (ROOT / "artifacts" / "plvr_residual_resolution_summary.json").read_text(
            encoding="utf-8"
        )
    )
