"""Inventory or acquire an explicit set of official PLVR artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_clean_shadow_rebuild import (
    ArtifactAcquisitionError,
    acquire_artifacts,
    build_artifact_requests,
)


DEFAULT_OUTPUT_DIR = ROOT / "data" / "raw" / "plvr" / "phase2c"
DEFAULT_MANIFEST = DEFAULT_OUTPUT_DIR / "source_manifest.json"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inventory official PLVR artifacts; add --download only after reviewing scope and size."
    )
    parser.add_argument("--season", action="append", default=[], help="Explicit ROC season, for example 115S2")
    parser.add_argument("--history", action="append", default=[], help="Explicit YYYYMMDD official release")
    parser.add_argument("--current-release", default="", help="Explicit YYYYMMDD label for the current sale ZIP")
    parser.add_argument("--download", action="store_true", help="Acquire verified artifacts after inventory review")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument(
        "--expected-sha256",
        action="append",
        default=[],
        metavar="ARTIFACT_ID=SHA256",
        help="Optional immutable checksum binding; may be repeated",
    )
    parser.add_argument("--timeout", type=int, default=180)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.timeout < 1:
        print("ACQUISITION_STATUS=blocked")
        print("REASON_CODE=invalid_timeout")
        return 2
    try:
        checksums = _parse_checksums(args.expected_sha256)
        requests = build_artifact_requests(
            seasons=args.season,
            histories=args.history,
            current_release=args.current_release,
        )
        manifest = acquire_artifacts(
            requests,
            destination=args.output_dir,
            manifest_path=args.manifest,
            download=args.download,
            expected_sha256=checksums,
            timeout=args.timeout,
        )
    except ArtifactAcquisitionError as error:
        print("ACQUISITION_STATUS=blocked")
        print(f"REASON_CODE={error}")
        return 2
    entries = manifest["artifacts"]
    counts: dict[str, int] = {}
    for entry in entries:
        status = str(entry.get("source_status") or "UNKNOWN")
        counts[status] = counts.get(status, 0) + 1
    summary = {
        "mode": "download" if args.download else "inventory",
        "requested_artifacts": len(entries),
        "source_status_counts": dict(sorted(counts.items())),
        "verified_artifacts": sum(entry.get("verification_status") == "VERIFIED" for entry in entries),
        "total_verified_bytes": sum(
            int(entry.get("byte_size") or 0)
            for entry in entries
            if entry.get("verification_status") == "VERIFIED"
        ),
        "manifest_sha256": manifest["manifest_sha256"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if all(entry.get("source_status") != "UNAVAILABLE_AUTHORITATIVE" for entry in entries) else 1


def _parse_checksums(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for value in values:
        artifact_id, separator, checksum = value.partition("=")
        if not separator or not artifact_id.strip() or not checksum.strip():
            raise ArtifactAcquisitionError("invalid_expected_sha256_binding")
        if artifact_id.strip() in parsed:
            raise ArtifactAcquisitionError("duplicate_expected_sha256_binding")
        parsed[artifact_id.strip()] = checksum.strip()
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
