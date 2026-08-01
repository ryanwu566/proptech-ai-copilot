"""Generate a bounded, non-secret release evidence JSON document.

All inputs are explicit categorical or release metadata arguments. The script
does not read environment files, provider settings, databases, or URLs.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path

SAFE_VALUE = re.compile(r"^[A-Za-z0-9._:-]{1,120}$")
ALLOWED_STATUS = {"generated", "ci_verified", "preview_verified", "production_verified", "pending", "not_run"}


def _safe(value: str, default: str = "pending") -> str:
    value = str(value or "").strip()
    return value if SAFE_VALUE.fullmatch(value) else default


def build_evidence(*, release_id: str, commit: str, schema_version: str, local_status: str = "pending", ci_status: str = "pending", preview_status: str = "pending", production_status: str = "pending", owner_actions: list[str] | None = None) -> dict[str, object]:
    statuses = (local_status, ci_status, preview_status, production_status)
    if any(status not in ALLOWED_STATUS for status in statuses):
        raise ValueError("evidence status is not allowlisted")
    return {
        "schema_version": "production-release-evidence-v1",
        "generated_at": datetime.now(UTC).isoformat(),
        "release_id": _safe(release_id),
        "commit": _safe(commit),
        "schema_compatibility": _safe(schema_version),
        "validation": {
            "local": local_status,
            "ci": ci_status,
            "preview": preview_status,
            "production": production_status,
        },
        "owner_actions": [_safe(item) for item in (owner_actions or [])],
        "privacy": {"secrets_included": False, "raw_payloads_included": False, "customer_data_included": False},
    }


def write_evidence(output: Path, **kwargs: object) -> dict[str, object]:
    payload = build_evidence(**kwargs)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_name(f".{output.name}.tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--release-id", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--schema-version", required=True)
    parser.add_argument("--local-status", choices=sorted(ALLOWED_STATUS), default="pending")
    parser.add_argument("--ci-status", choices=sorted(ALLOWED_STATUS), default="pending")
    parser.add_argument("--preview-status", choices=sorted(ALLOWED_STATUS), default="pending")
    parser.add_argument("--production-status", choices=sorted(ALLOWED_STATUS), default="pending")
    parser.add_argument("--owner-action", action="append", default=[])
    args = parser.parse_args()
    write_evidence(args.output, release_id=args.release_id, commit=args.commit, schema_version=args.schema_version, local_status=args.local_status, ci_status=args.ci_status, preview_status=args.preview_status, production_status=args.production_status, owner_actions=args.owner_action)
    print("RELEASE_EVIDENCE=written")
    print("RELEASE_EVIDENCE_SECRETS_INCLUDED=no")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
