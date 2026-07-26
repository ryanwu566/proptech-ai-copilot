"""Audit a local PLVR import readiness report without touching a database."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.import_plvr_to_postgres import REPORT_SCHEMA_VERSION, classify_import_readiness


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit a local PLVR import report")
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(report, dict) or report.get("report_schema_version") != REPORT_SCHEMA_VERSION:
            raise ValueError
        quality = classify_import_readiness(report)
        status = quality["quality_status"]
        values: dict[str, Any] = {
            "PLVR_IMPORT_REPORT": status,
            "REPORT_SCHEMA_VERSION": report.get("report_schema_version", ""),
            "QUALITY_REASON_COUNT": len(quality["quality_reason_codes"]),
            "OPERATOR_ATTENTION_REQUIRED": "yes" if quality["operator_attention_required"] else "no",
            "ACCEPTED_ROWS": _safe_int(report.get("accepted_rows")),
            "INSERTED_ROWS": _safe_int(report.get("inserted_rows")),
            "EXCLUDED_ROWS": _safe_int(report.get("excluded_rows")),
            "SKIPPED_DUPLICATE_ROWS": _safe_int(report.get("skipped_duplicate_rows")),
            "SOURCE_PERIOD_MIN": quality["source_period_min"] or "",
            "SOURCE_PERIOD_MAX": quality["source_period_max"] or "",
        }
        for key, value in values.items():
            print(f"{key}={value}")
        return 2 if status == "blocked" else 0
    except Exception:
        print("PLVR_IMPORT_REPORT=invalid")
        return 1


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
