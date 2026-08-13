"""Validate committed Phase 2D design artifacts without external access."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.plvr_cutover_plan import validate_cutover_design


ARTIFACTS = ROOT / "artifacts"


def main() -> int:
    result = validate_cutover_design(
        _read("plvr_cutover_plan.json"),
        _read("plvr_cutover_validation_gates.json"),
        _read("plvr_cutover_failure_matrix.json"),
        _read("plvr_cutover_approval_matrix.json"),
    )
    print(f"PLVR_CUTOVER_DESIGN_VALIDATION={result['status']}")
    print(f"ERROR_COUNT={len(result['error_codes'])}")
    print("PRODUCTION_CONNECTION_ATTEMPTED=no")
    print("PRODUCTION_MUTATION_CAPABILITY=no")
    return 0 if result["status"] == "pass" else 2


def _read(filename: str) -> dict:
    return json.loads((ARTIFACTS / filename).read_text(encoding="utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
