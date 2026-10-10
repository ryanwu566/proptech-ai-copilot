"""Opt-in offline inspection of a read-only gcloud JSON service export.

Owner command: gcloud run services describe SERVICE --region REGION --format=json
Keep the export private: it can contain environment values. Only bounded
categories are returned. This does not verify the load balancer/WAF or bypass.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from services.guardrail_evidence import read_bounded_json


def inspect_export(export):
    annotations = export.get("metadata", {}).get("annotations", {})
    containers = export.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
    commands = [item for container in containers if isinstance(container, dict) for item in container.get("command", []) + container.get("args", [])]
    # Exact arguments only. Shell command strings require owner review.
    checks = {"restricted_ingress": "PASS" if annotations.get("run.googleapis.com/ingress") == "internal-and-cloud-load-balancing" else "FAIL",
              "default_url_disabled": "PASS" if str(annotations.get("run.googleapis.com/default-url-disabled", "")).lower() == "true" else "FAIL",
              "proxy_headers_disabled": "PASS" if "--no-proxy-headers" in commands and "--proxy-headers" not in commands else "UNKNOWN"}
    return {"schema_version": "cloud-run-export-check-v1", "scope": "offline_export_only", "checks": checks,
            "controls": {"trusted_ingress": "BLOCKED", "edge_waf": "BLOCKED"}, "live_configuration": "UNKNOWN"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = inspect_export(read_bounded_json(args.export))
    except (OSError, ValueError, TypeError, AttributeError):
        result = {"state": "FAIL", "reason": "invalid_cloud_export"}
    print(json.dumps(result, sort_keys=True))
    return 0 if all(value == "PASS" for value in result.get("checks", {}).values()) and "checks" in result else 1


if __name__ == "__main__":
    raise SystemExit(main())
