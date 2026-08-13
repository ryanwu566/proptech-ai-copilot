"""Capture and reconcile PLVR production rows under a SELECT-only contract."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_clean_shadow_rebuild import manifest_checksum
from services.plvr_coverage_closure import build_coverage_report
from services.plvr_production_reconciliation import (
    DEFAULT_PAGE_SIZE,
    ReadOnlyPostgresProductionSource,
    ReconciliationError,
    capture_production_snapshot,
    reconcile_snapshots,
    reconciliation_gate,
    safe_reconciliation_artifacts,
)
from services.production_config import database_url, load_runtime_configuration


DEFAULT_RUNTIME_ROOT = ROOT / "data" / "processed" / "plvr" / "phase2c5"
DEFAULT_RAW_ROOT = ROOT / "data" / "raw" / "plvr" / "phase2c5"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Reconcile an authoritative PLVR shadow with production using SELECT only."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_RAW_ROOT / "source_manifest.json")
    parser.add_argument("--shadow-db", type=Path, default=DEFAULT_RUNTIME_ROOT / "clean-shadow.sqlite3")
    parser.add_argument("--shadow-summary", type=Path, default=DEFAULT_RUNTIME_ROOT / "clean-shadow-summary.json")
    parser.add_argument("--snapshot-db", type=Path, default=DEFAULT_RUNTIME_ROOT / "production-snapshot.sqlite3")
    parser.add_argument("--reconciliation-db", type=Path, default=DEFAULT_RUNTIME_ROOT / "reconciliation.sqlite3")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_RUNTIME_ROOT / "reconciliation-summary.json")
    parser.add_argument("--since", default="2023-09")
    parser.add_argument("--until", default="2026-08")
    parser.add_argument(
        "--database-url-env",
        choices=("DATABASE_URL", "PILOT_EVIDENCE_DATABASE_URL"),
        default="",
    )
    parser.add_argument("--production-access", default="select-only")
    parser.add_argument("--page-size", type=int, default=DEFAULT_PAGE_SIZE)
    parser.add_argument("--main-sha", default="")
    parser.add_argument("--safe-artifacts-dir", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.production_access != "select-only":
            raise ReconciliationError("production_access_must_be_select_only")
        manifest = _read_json(args.manifest)
        if manifest.get("manifest_sha256") != manifest_checksum(manifest):
            raise ReconciliationError("artifact_manifest_checksum_mismatch")
        shadow_summary = _read_json(args.shadow_summary)
        coverage = build_coverage_report(manifest, since=args.since, until=args.until)
        config = load_runtime_configuration()
        configured_database_url = (
            os.getenv(args.database_url_env, "").strip()
            if args.database_url_env
            else database_url()
        )
        database_source = args.database_url_env or config.database_source
        if not configured_database_url:
            raise ReconciliationError("production_read_runtime_not_configured")
        main_sha = args.main_sha.strip() or _current_head()
        source = ReadOnlyPostgresProductionSource(configured_database_url)
        capture_production_snapshot(
            source,
            args.snapshot_db,
            allowed_root=DEFAULT_RUNTIME_ROOT,
            main_sha=main_sha,
            clean_manifest_sha256=str(manifest["manifest_sha256"]),
            clean_shadow_sha256=str(shadow_summary.get("shadow_dataset_sha256") or ""),
            page_size=args.page_size,
        )
        report = reconcile_snapshots(
            args.shadow_db,
            args.snapshot_db,
            args.reconciliation_db,
            allowed_root=DEFAULT_RUNTIME_ROOT,
            coverage_report=coverage,
            since=args.since,
            expected_release_ceiling=str(coverage["expected_release_ceiling"]),
            main_sha=main_sha,
            clean_manifest_sha256=str(manifest["manifest_sha256"]),
        )
        gate, blockers = reconciliation_gate(shadow_summary, report)
        report["production_runtime"] = {
            "database_source": database_source,
            "database_status": "configured",
        }
        report["gate"] = gate
        report["blockers"] = blockers
        _write_summary(args.summary_output, report)
        if args.safe_artifacts_dir:
            _write_safe_artifacts(args.safe_artifacts_dir, report)
    except Exception as error:
        print("PLVR_RECONCILIATION_STATUS=blocked")
        print(f"REASON_CODE={_safe_reason(error)}")
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ReconciliationError("local_reconciliation_input_invalid")
    return value


def _write_summary(path: Path, report: Mapping[str, Any]) -> None:
    resolved_root = DEFAULT_RUNTIME_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
        raise ReconciliationError("local_output_outside_allowed_root")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        temporary.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_safe_artifacts(root: Path, report: Mapping[str, Any]) -> None:
    resolved_root = root.resolve()
    repository_artifacts = (ROOT / "artifacts").resolve()
    if resolved_root != repository_artifacts:
        raise ReconciliationError("safe_artifact_output_outside_repository_artifacts")
    root.mkdir(parents=True, exist_ok=True)
    for filename, payload in safe_reconciliation_artifacts(report).items():
        path = root / filename
        temporary = path.with_suffix(path.suffix + ".partial")
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def _current_head() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _safe_reason(error: Exception) -> str:
    if isinstance(error, ReconciliationError):
        return str(error)
    return "local_reconciliation_runtime_unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
