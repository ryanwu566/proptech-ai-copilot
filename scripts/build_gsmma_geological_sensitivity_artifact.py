"""Build local immutable GSMMA geological-sensitivity processed outputs.

This operator command performs no downloads and no uploads. RAR/7z packages
must be extracted with an approved external tool and mapped to their local
extracted directories before this command runs.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.gsmma_geological_sensitivity_artifact import (
    PackageInput,
    build_processed_artifact,
    write_build_outputs,
)


def _package_inputs(path: Path) -> list[PackageInput]:
    try:
        rows = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        raise ValueError(f"package mapping JSON could not be read: {type(exc).__name__}") from exc
    if not isinstance(rows, list) or not rows:
        raise ValueError("package mapping JSON must be a non-empty array")
    inputs: list[PackageInput] = []
    allowed = {"index_no", "path", "shapefile_path", "encoding", "expected_sha256"}
    for position, row in enumerate(rows, start=1):
        if not isinstance(row, dict) or set(row) - allowed:
            raise ValueError(f"invalid package mapping at position {position}")
        if not isinstance(row.get("index_no"), str) or not isinstance(row.get("path"), str):
            raise ValueError(f"package mapping {position} requires string index_no and path")
        inputs.append(
            PackageInput(
                index_no=row["index_no"],
                path=Path(row["path"]),
                shapefile_path=row.get("shapefile_path"),
                encoding=row.get("encoding"),
                expected_sha256=row.get("expected_sha256"),
            )
        )
    return inputs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, required=True, help="Operator-downloaded official UTF-8 CSV index")
    parser.add_argument("--package-map", type=Path, required=True, help="JSON array mapping index rows to ZIPs/extracted directories")
    parser.add_argument("--dataset-version", required=True, help="Immutable release version; never defaults to latest")
    parser.add_argument("--source-vintage", required=True, help="Auditable official source vintage")
    parser.add_argument("--output-dir", type=Path, required=True, help="Local processed-output root")
    parser.add_argument("--expected-index-sha256", help="Optional expected SHA256 for the official CSV bytes")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    index_bytes = args.index.read_bytes()
    index_sha = hashlib.sha256(index_bytes).hexdigest()
    if args.expected_index_sha256 and index_sha.lower() != args.expected_index_sha256.lower():
        raise ValueError(
            f"source index SHA256 mismatch: expected {args.expected_index_sha256}, got {index_sha}"
        )
    result = build_processed_artifact(
        index_bytes,
        _package_inputs(args.package_map),
        dataset_version=args.dataset_version,
        source_vintage=args.source_vintage,
    )
    paths = write_build_outputs(result, args.output_dir)
    summary: dict[str, Any] = {
        "artifact_sha256": result.manifest["artifact_sha256"],
        "dataset_version": result.manifest["dataset_version"],
        "feature_count": result.manifest["feature_count"],
        "output_files": {name: str(path) for name, path in sorted(paths.items())},
        "quality_status": result.manifest["quality_status"],
        "rejected_feature_count": result.manifest["rejected_feature_count"],
        "source_index_sha256": index_sha,
        "upload_performed": False,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
