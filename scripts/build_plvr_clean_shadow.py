"""Build and optionally reconcile a local authoritative PLVR clean shadow."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_clean_shadow_rebuild import (
    ReadOnlyProductionRepository,
    ShadowRebuildError,
    build_clean_shadow,
    load_clean_rows,
    reconcile_shadow_rows,
    replacement_readiness_gate,
)


DEFAULT_RAW_ROOT = ROOT / "data" / "raw" / "plvr" / "phase2c"
DEFAULT_PROCESSED_ROOT = ROOT / "data" / "processed" / "plvr" / "phase2c"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a local clean PLVR shadow; production remains SELECT-only.")
    parser.add_argument("--manifest", type=Path, default=DEFAULT_RAW_ROOT / "source_manifest.json")
    parser.add_argument("--shadow-db", type=Path, default=DEFAULT_PROCESSED_ROOT / "clean-shadow.sqlite3")
    parser.add_argument("--summary-output", type=Path, default=DEFAULT_PROCESSED_ROOT / "clean-shadow-summary.json")
    parser.add_argument("--since", required=True, help="Inclusive YYYY-MM rebuild start")
    parser.add_argument("--until", required=True, help="Inclusive YYYY-MM rebuild end")
    parser.add_argument("--as-of-date", required=True, type=date.fromisoformat)
    parser.add_argument("--normalized-at", type=datetime.fromisoformat)
    parser.add_argument("--reconcile-production", action="store_true")
    parser.add_argument("--database-url-env", default="VALUATION_DATABASE_URL")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = build_clean_shadow(
            args.manifest,
            args.shadow_db,
            since=args.since,
            until=args.until,
            as_of=args.as_of_date,
            allowed_shadow_root=DEFAULT_PROCESSED_ROOT,
            normalized_at=args.normalized_at,
        )
        reconciliation = None
        if args.reconcile_production:
            database_url = os.getenv(args.database_url_env, "").strip()
            if not database_url:
                raise ShadowRebuildError("production_read_runtime_not_configured")
            repository = ReadOnlyProductionRepository(database_url)
            reconciliation = reconcile_shadow_rows(
                load_clean_rows(args.shadow_db),
                repository.iter_transactions(),
                as_of_period=args.until,
            )
            report["production_reconciliation"] = reconciliation
        report["gate"] = replacement_readiness_gate(report, reconciliation)
        _write_summary(args.summary_output, report)
    except (OSError, ValueError, ShadowRebuildError) as error:
        print("SHADOW_REBUILD_STATUS=blocked")
        print(f"REASON_CODE={error if isinstance(error, ShadowRebuildError) else 'shadow_runtime_unavailable'}")
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def _write_summary(path: Path, report: dict[str, object]) -> None:
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


if __name__ == "__main__":
    raise SystemExit(main())
