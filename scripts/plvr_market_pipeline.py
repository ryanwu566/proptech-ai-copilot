"""Operator CLI for the official PLVR file pipeline.

The CLI does not accept credentials or database URLs on the command line. The
default commands are discovery/configuration checks; imports require an
explicit operator-approved staging path and remain outside the frontend tree.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
from pathlib import Path
import tempfile
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.official_plvr_market_pipeline import (
    DISCOVERY_STATUSES,
    aggregate_transactions,
    discover_official_release,
    download_official_archive,
    extract_zip_archive,
    inspect_zip_archive,
    load_source_registry,
    normalize_rows,
    parse_csv_rows,
    resolve_public_resource,
    safe_release_evidence,
    validate_schema,
)


def discover(registry_path: Path) -> dict[str, object]:
    try:
        sources = load_source_registry(registry_path)
    except (OSError, ValueError):
        return {"status": "configuration_required", "source_count": 0}
    enabled = [source for source in sources if source.enabled]
    if not enabled:
        return {"status": "configuration_required", "source_count": 0}
    return {
        "status": "configuration_required",
        "source_count": len(enabled),
        "message": "Operator must resolve and validate the current official release before download.",
    }


def run_canary(registry_path: Path, source_id: str, max_parse_rows: int, output_report: Path, retain_staging: bool) -> dict[str, object]:
    sources = load_source_registry(registry_path)
    source = next((item for item in sources if item.source_id == source_id), None)
    if source is None:
        return {"status": "configuration_required", "reason_code": "source_id_unknown"}
    try:
        resource_url, strategy = resolve_public_resource(source)
    except ValueError:
        return {"status": "resource_unavailable", "reason_code": "registry_resource_invalid"}
    staging_root = Path(tempfile.mkdtemp(prefix="plvr-canary-"))
    archive_path = staging_root / "official-release.zip"
    report: dict[str, object] = {"status": "resource_unavailable", "source_id": source.source_id, "dataset_name": source.dataset_name, "resource_strategy": strategy, "official_host": source.official_hosts[0] if source.official_hosts else None}
    try:
        signatures = tuple(value.encode("latin-1").decode("unicode_escape").encode("latin-1") for value in source.expected_archive_signature)
        download = download_official_archive(resource_url, archive_path, allowed_hosts=source.official_hosts, accepted_content_types=source.accepted_content_types, expected_archive_signatures=signatures)
        report.update({key: download.get(key) for key in ("status", "reason_code", "content_type", "bytes", "sha256") if key in download})
        if download.get("status") != "downloaded":
            return _write_canary_report(output_report, report)
        archive_info = inspect_zip_archive(archive_path)
        extract_root = staging_root / "extracted"
        members = extract_zip_archive(archive_path, extract_root)
        names = sorted(path.name for path in members)
        manifest_names = [name for name in names if "manifest" in name.lower()]
        schema_names = [name for name in names if "schema" in name.lower()]
        transaction_files = [path for path in members if path.suffix.lower() == ".csv" and "schema" not in path.name.lower() and "manifest" not in path.name.lower()]
        report.update({"archive_status": archive_info["status"], "archive_file_count": archive_info["file_count"], "manifest_files": manifest_names, "schema_files": schema_names, "transaction_files": [path.name for path in transaction_files]})
        if not transaction_files or not schema_names or not manifest_names:
            report.update({"status": "schema_changed", "reason_code": "manifest_or_schema_missing"})
            return _write_canary_report(output_report, report)
        transaction_file = transaction_files[0]
        with transaction_file.open("r", encoding="utf-8-sig", newline="") as handle:
            headers = next(csv.reader(handle), [])
        schema_report = validate_schema(headers)
        report.update({"manifest_found": bool(manifest_names), "schema_files_found": schema_names, "schema_validation": schema_report.status, "encoding": "utf-8-sig"})
        if schema_report.status != "valid":
            report.update({"status": "schema_changed", "reason_code": "transaction_schema_invalid"})
            return _write_canary_report(output_report, report)
        rows = itertools.islice(parse_csv_rows(transaction_file, max_rows=max_parse_rows), max_parse_rows)
        normalized, summary = normalize_rows(rows, source_id=source.source_id, release_id=str(download.get("sha256") or "unknown"))
        report.update({"status": "canary_passed" if normalized else "validation_failed", "rows_parsed": summary.parsed_rows, "rows_normalized": summary.accepted_rows, "rows_quarantined": summary.quarantined_rows, "duplicate_rows": summary.duplicate_rows, "cancelled_rows": summary.cancelled_rows})
        return _write_canary_report(output_report, report)
    except ValueError as exc:
        report.update({"status": "archive_invalid", "reason_code": str(exc)})
        return _write_canary_report(output_report, report)
    finally:
        if retain_staging:
            report["staging_retained"] = False
        else:
            import shutil
            shutil.rmtree(staging_root, ignore_errors=True)


def _write_canary_report(path: Path, report: dict[str, object]) -> dict[str, object]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=True, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded official PLVR market pipeline")
    parser.add_argument("command", choices=("discover", "canary", "validate", "status", "verify"))
    parser.add_argument("--registry", type=Path, default=ROOT / "config" / "official-market-sources.json")
    parser.add_argument("--input", type=Path, default=None, help="Operator staging CSV path outside the repository")
    parser.add_argument("--source-id", default=None)
    parser.add_argument("--release-id", default=None)
    parser.add_argument("--source-updated-at", default=None)
    parser.add_argument("--source", default=None)
    parser.add_argument("--max-parse-rows", type=int, default=200)
    parser.add_argument("--output-report", type=Path, default=ROOT / ".local" / "market-canary-report.json")
    parser.add_argument("--retain-staging", action="store_true")
    args = parser.parse_args()
    if args.command == "canary":
        if not args.source:
            result = {"status": "configuration_required", "reason_code": "source_id_required"}
        else:
            result = run_canary(args.registry, args.source, max(1, min(args.max_parse_rows, 200)), args.output_report, args.retain_staging)
    elif args.command == "validate":
        if not args.input or not args.source_id or not args.release_id:
            result = {"status": "configuration_required", "message": "Validation requires an operator staging path and release metadata."}
        else:
            try:
                transactions, summary = normalize_rows(parse_csv_rows(args.input), source_id=args.source_id, release_id=args.release_id)
                aggregates = aggregate_transactions(transactions, source_name="Official PLVR OpenData", source_release_id=args.release_id, source_updated_at=args.source_updated_at)
                result = {"status": "validated", "aggregate_count": len(aggregates), **safe_release_evidence(source_id=args.source_id, release_id=args.release_id, schema_version=None, archive_sha256=None, input_rows=summary.input_rows, accepted_rows=summary.accepted_rows, quarantined_rows=summary.quarantined_rows, source_updated_at=args.source_updated_at)}
            except (OSError, ValueError):
                result = {"status": "validation_failed", "message": "The staged release did not pass bounded validation."}
    else:
        result = discover(args.registry) if args.command == "discover" else {
        "status": "configuration_required",
        "message": "No production release is claimed without operator data launch.",
        }
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    if args.command == "canary":
        return 0 if result["status"] == "canary_passed" else 1
    return 0 if result["status"] in DISCOVERY_STATUSES or result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
