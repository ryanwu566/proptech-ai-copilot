"""Parse safe coverage reconcile counters for the GitHub Actions workflow."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ALLOWED_COVERAGE_STATUSES = {"covered", "not_covered", "coverage_unknown"}
COUNT_FIELDS = ("covered_region_count", "not_covered_region_count", "unknown_region_count")


def _read_count(payload: dict[str, Any], field_name: str) -> int:
    if field_name not in payload:
        raise ValueError
    value = payload[field_name]
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError
    return value


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if len(args) != 1:
            return 2
        with Path(args[0]).open(encoding="utf-8") as handle:
            payload = json.load(handle)
        if not isinstance(payload, dict):
            return 2
        if payload.get("coverage_status") not in ALLOWED_COVERAGE_STATUSES:
            return 2
        counts = [_read_count(payload, field_name) for field_name in COUNT_FIELDS]
        print("{} {} {}".format(*counts))
        return 0
    except BaseException:
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
