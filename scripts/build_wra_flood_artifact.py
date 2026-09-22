"""Build a processed WRA flood artifact from an operator-provided SHP ZIP.

This offline builder never downloads data, never contacts Cloudflare R2, never
touches a database, and never modifies the Terrain Risk runtime.  It reads a
local ZIP the operator has already obtained, validates it, and writes a compact
deterministic artifact plus a manifest under ``<output-dir>/<scenario>/``.

Raw SHP/ZIP inputs and the processed artifact must never be committed to git;
they belong in the ``proptech-government-data`` R2 bucket.

Example:

    python scripts/build_wra_flood_artifact.py \\
        --input-zip C:\\Projects\\_wra-flood-test\\flood_350mm_24hr.zip \\
        --scenario 24h-350mm \\
        --source-url "https://gic.wra.gov.tw/gis/gic/API/Google/DownLoad.aspx?fname=flood_350mm_24hr&filetype=SHP" \\
        --output-dir C:\\Projects\\_wra-flood-test\\processed
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from services.wra_flood_artifact import build_processed_artifact, write_build_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Build a processed WRA flood artifact from a local SHP ZIP")
    parser.add_argument("--input-zip", required=True, help="local operator-provided SHP ZIP path")
    parser.add_argument("--scenario", required=True, help="scenario id, e.g. 24h-350mm")
    parser.add_argument("--source-url", required=True, help="official WRA download URL for provenance")
    parser.add_argument("--output-dir", required=True, help="local output directory for the artifact + manifest")
    parser.add_argument("--expected-sha256", default=None, help="optional expected source ZIP SHA256")
    parser.add_argument("--area-tolerance-pct", type=float, default=0.01, help="max allowed area difference percent")
    parser.add_argument("--write", action="store_true", help="write artifact + manifest (otherwise summary only)")
    parser.add_argument(
        "--verify-point",
        action="append",
        default=None,
        metavar="LON,LAT,LABEL",
        help="verify a WGS84 point against freshly built features; repeatable",
    )
    args = parser.parse_args()

    zip_path = Path(args.input_zip)
    zip_bytes = zip_path.read_bytes()

    result = build_processed_artifact(
        zip_bytes,
        scenario=args.scenario,
        source_url=args.source_url,
        expected_source_sha256=args.expected_sha256,
        area_tolerance_pct=args.area_tolerance_pct,
    )

    verifications = []
    if args.verify_point:
        from services.wra_flood_artifact import verify_point_against_features

        for spec in args.verify_point:
            parts = spec.split(",")
            lon = float(parts[0])
            lat = float(parts[1])
            label = parts[2] if len(parts) > 2 else f"{lon},{lat}"
            outcome = verify_point_against_features(lon, lat, result.features)
            verifications.append({"label": label, "result": outcome})

    summary = {
        "scenario": args.scenario,
        "artifact_size_bytes": len(result.artifact_bytes),
        "manifest": result.manifest,
        "written": False,
    }
    if verifications:
        summary["verifications"] = verifications
    if args.write:
        paths = write_build_outputs(result, Path(args.output_dir), args.scenario)
        summary["written"] = True
        summary["output"] = {name: str(path) for name, path in paths.items()}

    print(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
