"""Run the Phase 2E cutover rehearsal against an explicit local PostgreSQL target."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_cutover_rehearsal import (
    DEFAULT_BATCH_SIZE,
    RehearsalError,
    run_phase2e_rehearsal,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rehearse the PLVR generation cutover in plvr_cutover_dryrun only."
    )
    parser.add_argument("--artifact-root", type=Path, required=True)
    parser.add_argument("--green-shadow", type=Path, required=True)
    parser.add_argument("--green-summary", type=Path, required=True)
    parser.add_argument("--blue-snapshot", type=Path, required=True)
    parser.add_argument(
        "--schema",
        type=Path,
        default=ROOT / "database" / "plvr_phase2e_rehearsal.sql",
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "artifacts" / "plvr_source_manifest.json",
    )
    parser.add_argument(
        "--residual-summary",
        type=Path,
        default=ROOT / "artifacts" / "plvr_residual_resolution_summary.json",
    )
    parser.add_argument(
        "--gate-artifact",
        type=Path,
        default=ROOT / "artifacts" / "plvr_cutover_validation_gates.json",
    )
    parser.add_argument(
        "--aggregate-attribution",
        type=Path,
        default=ROOT / "artifacts" / "plvr_aggregate_delta_attribution.json",
    )
    parser.add_argument("--output-dir", type=Path, default=ROOT / "artifacts")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        summary = run_phase2e_rehearsal(
            schema_path=args.schema,
            manifest_path=args.manifest,
            artifact_root=args.artifact_root,
            green_shadow_path=args.green_shadow,
            green_summary_path=args.green_summary,
            blue_snapshot_path=args.blue_snapshot,
            residual_summary_path=args.residual_summary,
            gate_artifact_path=args.gate_artifact,
            aggregate_attribution_path=args.aggregate_attribution,
            output_dir=args.output_dir,
            batch_size=args.batch_size,
        )
    except RehearsalError as error:
        print("PHASE_2E_REHEARSAL=blocked")
        print(f"REASON_CODE={error}")
        print("PRODUCTION_CONNECTION_ATTEMPTS=0")
        return 2
    except (OSError, ValueError):
        print("PHASE_2E_REHEARSAL=blocked")
        print("REASON_CODE=isolated_rehearsal_runtime_failed")
        print("PRODUCTION_CONNECTION_ATTEMPTS=0")
        return 2

    print("PHASE_2E_REHEARSAL=pass")
    print(f"GREEN_TRANSACTIONS={summary['green_metrics']['transaction_count']}")
    print(f"GREEN_AGGREGATES={summary['green_metrics']['aggregate_count']}")
    print(f"HARD_GATES={summary['hard_gates_passed']}/{summary['hard_gates_total']}")
    print(
        "GOLDEN_REGIONS="
        f"{summary['golden_regions_passed']}/{summary['golden_regions_total']}"
    )
    print(f"DUAL_READ={summary['dual_read_status']}")
    print(f"ROLLBACK={summary['rollback_acceptance']['status']}")
    print("PRODUCTION_CONNECTION_ATTEMPTS=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
