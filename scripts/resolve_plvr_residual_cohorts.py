"""Resolve Phase 2C.7 residual cohorts from verified local Phase 2C.6 caches."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_residual_resolution import (
    EXPECTED_SNAPSHOT_SHA256,
    ResidualResolutionError,
    resolve_residual_cohorts,
    safe_residual_artifacts,
)


RUNTIME_ROOT = ROOT / "data" / "processed" / "plvr" / "phase2c5"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve PLVR reconciliation residuals from ignored local caches."
    )
    parser.add_argument(
        "--shadow-db", type=Path, default=RUNTIME_ROOT / "clean-shadow.sqlite3"
    )
    parser.add_argument(
        "--snapshot-db",
        type=Path,
        default=RUNTIME_ROOT / "production-snapshot.sqlite3",
    )
    parser.add_argument(
        "--prior-reconciliation-db",
        type=Path,
        default=RUNTIME_ROOT / "reconciliation.sqlite3",
    )
    parser.add_argument(
        "--output-db",
        type=Path,
        default=RUNTIME_ROOT / "residual-resolution.sqlite3",
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=RUNTIME_ROOT / "residual-resolution-summary.json",
    )
    parser.add_argument("--main-sha", required=True)
    parser.add_argument(
        "--expected-snapshot-sha", default=EXPECTED_SNAPSHOT_SHA256
    )
    parser.add_argument("--safe-artifacts-dir", type=Path, default=ROOT / "artifacts")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = resolve_residual_cohorts(
            args.shadow_db,
            args.snapshot_db,
            args.prior_reconciliation_db,
            args.output_db,
            allowed_root=RUNTIME_ROOT,
            main_sha=args.main_sha,
            expected_snapshot_sha256=args.expected_snapshot_sha,
        )
        _write_local_summary(args.summary_output, report)
        _write_safe_artifacts(args.safe_artifacts_dir, report)
    except Exception as error:
        print("PLVR_RESIDUAL_RESOLUTION=blocked")
        print(f"REASON_CODE={_safe_reason(error)}")
        return 2
    print(f"PLVR_RESIDUAL_RESOLUTION={report['gate']}")
    print(f"PRODUCTION_ROWS={report['production_rows']}")
    print(f"CLEAN_ROWS={report['clean_rows']}")
    return 0


def _write_local_summary(path: Path, report: Mapping[str, Any]) -> None:
    resolved_root = RUNTIME_ROOT.resolve()
    resolved_path = path.resolve()
    if resolved_path == resolved_root or resolved_root not in resolved_path.parents:
        raise ResidualResolutionError("local_summary_outside_ignored_root")
    _write_json(path, report)


def _write_safe_artifacts(root: Path, report: Mapping[str, Any]) -> None:
    if root.resolve() != (ROOT / "artifacts").resolve():
        raise ResidualResolutionError("safe_artifact_output_outside_repository_artifacts")
    root.mkdir(parents=True, exist_ok=True)
    for filename, payload in safe_residual_artifacts(report).items():
        _write_json(root / filename, payload)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".partial")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _safe_reason(error: Exception) -> str:
    if isinstance(error, ResidualResolutionError):
        return str(error)
    return "local_residual_resolution_unavailable"


if __name__ == "__main__":
    raise SystemExit(main())
