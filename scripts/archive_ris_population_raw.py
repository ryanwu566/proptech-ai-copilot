"""Operator-controlled archival of raw RIS ODRP014 monthly responses to R2.

Local, operator-run only. Credentials come from the environment; nothing is
hardcoded and no secret value is ever printed. Raw archive objects are treated
as immutable: a byte-identical object is skipped, and a same-key object with a
different checksum fails closed (never overwritten).

Environment variables (R2 / S3-compatible):

    R2_ACCESS_KEY_ID
    R2_SECRET_ACCESS_KEY
    R2_ENDPOINT
    R2_BUCKET            (optional; defaults to proptech-government-data)

Usage examples::

    python scripts/archive_ris_population_raw.py --month 11507 --dry-run
    python scripts/archive_ris_population_raw.py --month 11407 --month 11408
    python scripts/archive_ris_population_raw.py --months 11407-11507
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.ris_population_archive import (
    RisArchiveError,
    archive_month,
)
from services.ris_population_dataset import roc_yyymm_to_gregorian
from services.ris_population_provider import (
    DEFAULT_TIMEOUT_SECONDS,
    PAGE_PARAM,
    RisProviderError,
)

DEFAULT_BUCKET = "proptech-government-data"
REQUIRED_ENV = ("R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_ENDPOINT")
DEFAULT_REGION = "auto"
R2_ENV_NAMES = (
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_ENDPOINT",
    "R2_BUCKET",
    "R2_REGION",
)
CHECKPOINT_SCHEMA_VERSION = "ris-phase2d-checkpoint-v1"
CHECKPOINT_PATH = Path(r"C:\Projects\_ris-population-archive\phase2d_checkpoint.json")


def _expand_range(token: str) -> list[str]:
    """Expand a ROC ``START-END`` month range (same or adjacent ROC years)."""

    start, _, end = token.partition("-")
    start, end = start.strip(), end.strip()
    if not (start.isdigit() and end.isdigit()):
        raise ValueError(f"invalid month range {token!r}")
    months = []
    s_year, s_month = int(start[:-2]), int(start[-2:])
    e_year, e_month = int(end[:-2]), int(end[-2:])
    y, m = s_year, s_month
    guard = 0
    while (y, m) <= (e_year, e_month):
        months.append(f"{y}{m:02d}")
        m += 1
        if m > 12:
            m = 1
            y += 1
        guard += 1
        if guard > 240:
            raise ValueError(f"month range {token!r} too large")
    return months


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Archive raw RIS ODRP014 months to R2.")
    parser.add_argument("--month", action="append", default=[], help="ROC yyymm, repeatable (e.g. 11507)")
    parser.add_argument("--months", default=None, help="ROC range START-END (e.g. 11407-11507)")
    parser.add_argument("--bucket", default=os.environ.get("R2_BUCKET", DEFAULT_BUCKET))
    parser.add_argument("--dry-run", action="store_true", help="fetch + plan only; upload nothing")
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT_SECONDS)
    return parser.parse_args(argv)


def resolve_months(args: argparse.Namespace) -> list[str]:
    months: list[str] = list(args.month)
    if args.months:
        months.extend(_expand_range(args.months))
    # de-dup preserving order
    seen: set[str] = set()
    ordered = []
    for m in months:
        m = m.strip()
        if not m.isdigit():
            raise ValueError(f"month must be numeric ROC yyymm, got {m!r}")
        if m not in seen:
            seen.add(m)
            ordered.append(m)
    if not ordered:
        raise ValueError("no months supplied; use --month or --months")
    return ordered


def build_page_fetcher(timeout: float):
    def fetch(url: str, page: int) -> dict:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(url, params={PAGE_PARAM: page}, headers={"Accept": "application/json"})
            resp.raise_for_status()
            return resp.json()

    return fetch


def build_r2_client():
    """Build an S3-compatible client for R2 from environment credentials."""

    missing = [name for name in REQUIRED_ENV if not os.environ.get(name)]
    if missing:
        raise RisArchiveError(
            "missing required R2 environment variables: " + ", ".join(missing)
        )
    import boto3  # imported lazily so --dry-run tests need no boto3

    return boto3.client(
        "s3",
        endpoint_url=os.environ["R2_ENDPOINT"],
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name=os.environ.get("R2_REGION", DEFAULT_REGION),
    )


def clear_r2_environment() -> None:
    for name in R2_ENV_NAMES:
        os.environ.pop(name, None)


def emit_progress(message: str) -> None:
    print(message, flush=True)


def load_checkpoint(path: Path = CHECKPOINT_PATH) -> dict:
    if not path.exists():
        return {"schema_version": CHECKPOINT_SCHEMA_VERSION, "months": {}}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("months"), dict):
        raise RisArchiveError(f"invalid checkpoint structure: {path}")
    if data.get("schema_version") != CHECKPOINT_SCHEMA_VERSION:
        raise RisArchiveError(f"unsupported checkpoint schema: {path}")
    return data


def write_checkpoint_atomic(path: Path, checkpoint: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(path.name + ".tmp")
    try:
        with temp_path.open("w", encoding="utf-8", newline="\n") as handle:
            json.dump(checkpoint, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path.exists():
            temp_path.unlink()


def _checkpoint_entry(yyymm: str, status: str, **values: object) -> dict:
    return {
        "month": yyymm,
        "statistic_month": roc_yyymm_to_gregorian(yyymm),
        "status": status,
        "pages_verified": values.get("pages_verified", 0),
        "manifest_verified": values.get("manifest_verified", False),
        "uploaded_objects": values.get("uploaded_objects", 0),
        "skipped_objects": values.get("skipped_objects", 0),
        "total_bytes": values.get("total_bytes", 0),
        "error": values.get("error"),
    }


def run_archive(
    months: list[str],
    page_fetcher,
    client,
    bucket: str,
    *,
    checkpoint_path: Path = CHECKPOINT_PATH,
    emit=print,
) -> list[dict]:
    checkpoint = load_checkpoint(checkpoint_path)
    results: list[dict] = []
    total = len(months)

    for index, yyymm in enumerate(months, start=1):
        prefix = f"[{index}/{total}]"
        gregorian = roc_yyymm_to_gregorian(yyymm)
        existing = checkpoint["months"].get(yyymm, {})
        if existing.get("status") == "VERIFIED":
            emit(f"{prefix} {gregorian} SKIP checkpoint VERIFIED")
            continue

        checkpoint["months"][yyymm] = _checkpoint_entry(yyymm, "PENDING")
        write_checkpoint_atomic(checkpoint_path, checkpoint)

        def progress(message: str) -> None:
            emit(f"{prefix} {message}")

        try:
            result = archive_month(
                yyymm, page_fetcher, client, bucket, progress=progress
            )
            if result["all_objects_verified"] is not True:
                raise RisArchiveError(f"month {yyymm} did not fully verify")
        except Exception as exc:
            checkpoint["months"][yyymm] = _checkpoint_entry(
                yyymm, "FAILED", error=str(exc)
            )
            write_checkpoint_atomic(checkpoint_path, checkpoint)
            emit(f"{prefix} {gregorian} FAIL: {exc}")
            raise

        checkpoint["months"][yyymm] = _checkpoint_entry(
            yyymm,
            "VERIFIED",
            pages_verified=result["pages"],
            manifest_verified=True,
            uploaded_objects=result["objects_uploaded"],
            skipped_objects=result["objects_skipped"],
            total_bytes=result["total_archived_bytes"] + result["manifest_bytes"],
            error=None,
        )
        write_checkpoint_atomic(checkpoint_path, checkpoint)
        emit(f"{prefix} PASS")
        results.append(result)

    return results


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        months = resolve_months(args)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    page_fetcher = build_page_fetcher(args.timeout)

    client = None
    if not args.dry_run:
        try:
            client = build_r2_client()
        except RisArchiveError as exc:
            # Never print secret values; only which variables are missing.
            print(f"ERROR: {exc}", file=sys.stderr)
            clear_r2_environment()
            return 2

    results = []
    if args.dry_run:
        for month in months:
            try:
                result = archive_month(
                    month, page_fetcher, client, args.bucket, dry_run=True
                )
            except (RisArchiveError, RisProviderError, httpx.HTTPError) as exc:
                print(f"ERROR archiving month {month}: {exc}", file=sys.stderr)
                return 1
            results.append(result)
    else:
        try:
            results = run_archive(
                months,
                page_fetcher,
                client,
                args.bucket,
                checkpoint_path=CHECKPOINT_PATH,
                emit=emit_progress,
            )
        except Exception as exc:  # noqa: BLE001 - operator boundary reports and stops
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        finally:
            clear_r2_environment()

    all_verified = all(r["all_objects_verified"] is True for r in results)

    summary = {
        "bucket": args.bucket,
        "dry_run": args.dry_run,
        "months": [r["yyymm"] for r in results],
        "per_month": [
            {
                "yyymm": r["yyymm"],
                "statistic_month": r["statistic_month"],
                "schema_style": r["schema_style"],
                "pages": r["pages"],
                "total_data_size": r["total_data_size"],
                "objects_uploaded": r["objects_uploaded"],
                "objects_skipped": r["objects_skipped"],
                "objects_planned": r["objects_planned"],
                "total_archived_bytes": r["total_archived_bytes"],
                "all_objects_verified": r["all_objects_verified"],
                "sample_object_keys": r["object_keys"][:2] + [r["manifest_key"]],
            }
            for r in results
        ],
        "all_ris_raw_months_verified": (None if args.dry_run else all_verified),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not args.dry_run and not all_verified:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
