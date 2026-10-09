"""Bounded operator acceptance. Default is config-only; never loads dotenv."""

from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.provider_config_contract import REQUIREMENTS, SOURCES, configuration_status, exact_version, valid_sha

# These suites are deterministic. An additional subprocess socket guard forbids
# outbound requests if a fixture accidentally falls through to a real provider.
OFFLINE_SUITES = {
    "valuation": "tests/test_provider_closure_market_valuation.py",
    "finder": "tests/test_property_search_service.py",
    "trend": "tests/test_valuation_trend_service.py",
    "market": "tests/test_market_segmentation_service.py",
    "places": "tests/test_provider_closure_location.py",
    "plvr": "tests/test_plvr_provider_update.py",
    "wra": "tests/test_provider_artifact_acceptance.py",
    "gsmma": "tests/test_provider_artifact_acceptance.py",
    "ardswc": "tests/test_risk_provider_closure.py",
    "ardswc-landslide": "tests/test_risk_provider_closure.py",
    "ardswc-debris-flow": "tests/test_risk_provider_closure.py",
    "liquefaction": "tests/test_terrain_risk_service.py",
    "nlsc": "tests/test_nlsc_gateway_adapter.py",
    "tdx": "tests/test_tdx_mrt_snapshot.py",
    "ris": "tests/test_ris_village_resolver.py",
    "satellite": "tests/test_satellite_reference.py",
    "maps": "tests/test_map_localization_mobile_search.py",
    "street-view": "tests/test_map_localization_mobile_search.py",
    "hosted": "tests/test_provider_closure_smoke.py",
}


def _release_sha(values: Mapping[str, str]) -> str:
    value = str(values.get("RELEASE_COMMIT_SHA", "")).strip()
    if valid_sha(value):
        return value.lower()
    try:
        value = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=5, check=True).stdout.strip()
        return value if valid_sha(value) else "unconfigured"
    except (OSError, subprocess.SubprocessError):
        return "unconfigured"


def _geocoding(*, key: str, query: str, offline: bool) -> tuple[str, str]:
    from services.adapters.geocoding_adapter import GoogleGeocodingAdapter
    from services.geocoding_acceptance import evaluate_geocoding_acceptance
    from unittest.mock import patch
    import httpx

    adapter = GoogleGeocodingAdapter(api_key=key, timeout_seconds=5)
    if offline:
        fixture = {"status": "OK", "results": [{"place_id": "fixture-only", "formatted_address": query, "types": ["street_address"], "geometry": {"location": {"lat": 25.025, "lng": 121.55}, "location_type": "ROOFTOP"}, "address_components": [{"long_name": "台北市", "types": ["administrative_area_level_1"]}, {"long_name": "大安區", "types": ["administrative_area_level_2"]}, {"long_name": "敦化南路二段", "types": ["route"]}, {"long_name": "100", "types": ["street_number"]}]}]}
        response = httpx.Response(200, json=fixture, request=httpx.Request("GET", "https://fixture.invalid"))
        with patch("services.adapters.geocoding_adapter.httpx.get", return_value=response):
            location = adapter.search(query, [])
    else:
        location = adapter.search(query, [])
    if location is None:
        reason = getattr(adapter, "last_reason_code", "provider_error")
        return ("no_data" if reason == "no_match" else "fail"), reason
    acceptance = evaluate_geocoding_acceptance(query, location, "google_geocoding")
    return ("pass", "success") if acceptance["accepted_for_analysis"] else ("unaccepted", "geocoding_unaccepted")


def _routes(*, key: str, origin: tuple[float, float], destination: tuple[float, float], offline: bool) -> tuple[str, str]:
    import httpx
    from services.adapters.routes_adapter import GoogleRoutesAdapter, RoutesAdapterError

    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={"routes": [{"duration": "900s", "distanceMeters": 6000}]}))) if offline else None
    adapter = GoogleRoutesAdapter(api_key=key, timeout_seconds=4, client=client)
    try:
        route = adapter.compute_route(origin, destination, "transit")
        return ("pass", "success") if route["source"] == "google_routes" else ("fail", "invalid_provider_result")
    except RoutesAdapterError as error:
        return "fail", error.reason_code
    finally:
        adapter.close()
        if client is not None:
            client.close()


def _offline_suite(capability: str) -> bool:
    suite = OFFLINE_SUITES.get(capability)
    if not suite or not (ROOT / suite).is_file():
        return False
    code = "import socket,sys,ipaddress; original=socket.socket.connect\ndef guarded(self,address):\n try: allowed=ipaddress.ip_address(address[0]).is_loopback\n except ValueError: allowed=False\n if not allowed: raise RuntimeError('offline_network_forbidden')\n return original(self,address)\nsocket.socket.connect=guarded\nimport pytest; sys.exit(pytest.main(['-q',sys.argv[1]]))"
    result = subprocess.run([sys.executable, "-c", code, suite], cwd=ROOT, capture_output=True, timeout=180, env={**os.environ, "VALUATION_DEMO_MODE": "false"})
    return result.returncode == 0


def _valid_endpoint(endpoint: tuple[float, float]) -> bool:
    try:
        lat, lng = endpoint
        return math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180
    except (TypeError, ValueError):
        return False


def run(*, capability: str, mode: str = "config-only", environ: Mapping[str, str] | None = None, allow_live: bool = False, confirmed_environment: str | None = None, request_budget: int | None = None, query: str = "台北市大安區敦化南路二段100號", origin: tuple[float, float] | None = None, destination: tuple[float, float] | None = None, manifest: Path | None = None, artifact: Path | None = None, dataset_version: str | None = None, scenario: str = "24h-350mm", fixtures: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    values = os.environ if environ is None else environ
    config = configuration_status(capability, values)
    version = dataset_version or values.get("GSMMA_GEOLOGICAL_SENSITIVITY_DATASET_VERSION", "") if capability == "gsmma" else "v1" if capability == "wra" else "113" if capability == "ardswc" else "not_checked"
    result = {"capability": capability, "release_sha": _release_sha(values), "release_scope": "local_checkout", "provider_source": SOURCES[capability], "config_status": config, "dataset_version": version if exact_version(version) else "not_checked", "freshness": "not_checked", "test_mode": mode, "result": "ready_for_production_acceptance", "provider_status": "not_checked", "reason_code": "config_contract_valid", "checked_at": datetime.now(UTC).isoformat(), "network_requests": 0, "production_readiness": "unproven"}
    if capability in {"active-fault", "tax-legal"}:
        return {**result, "result": "manual_verification_only", "reason_code": "manual_verification_required"}
    if mode == "config-only":
        if any(value != "present" for value in config.values()):
            result.update(result="configuration_required", reason_code="configuration_required")
        return result
    if mode == "bounded-live":
        if not allow_live or confirmed_environment not in {"preview", "production"} or type(request_budget) is not int or request_budget != 1 or capability not in {"geocoding", "routes"} or any(value != "present" for value in config.values()) or capability == "routes" and (origin is None or destination is None):
            return {**result, "result": "configuration_required", "reason_code": "live_contract_required"}
        if capability == "geocoding" and (not isinstance(query, str) or not query.strip() or len(query) > 500) or capability == "routes" and (not _valid_endpoint(origin) or not _valid_endpoint(destination)):
            return {**result, "result": "fail", "provider_status": "unavailable", "reason_code": "invalid_input"}
        result["network_requests"] = 1
    elif mode != "offline-fixture":
        raise ValueError("unsupported test mode")
    try:
        offline = mode == "offline-fixture"
        if capability == "geocoding":
            state, reason = _geocoding(key="offline-fixture" if offline else values["GOOGLE_MAPS_API_KEY"], query=query, offline=offline)
        elif capability == "routes":
            state, reason = _routes(key="offline-fixture" if offline else values["GOOGLE_MAPS_API_KEY"], origin=origin or (25.03, 121.47), destination=destination or (25.0478, 121.517), offline=offline)
        elif capability in {"wra", "gsmma"} and manifest is not None and artifact is not None:
            from services.provider_artifact_acceptance import validate_gsmma_artifact, validate_wra_artifact
            # Bounded reads, using the real runtime artifact validator and index.
            if manifest.stat().st_size > 1_000_000 or artifact.stat().st_size > 512_000_000:
                raise ValueError("artifact size limit")
            details = validate_wra_artifact(manifest.read_bytes(), artifact.read_bytes(), scenario=scenario, fixtures=fixtures or ()) if capability == "wra" else validate_gsmma_artifact(manifest.read_bytes(), artifact.read_bytes(), dataset_version=version, fixtures=fixtures or ())
            result.update(artifact_evidence=details, dataset_version=details["dataset_version"])
            state, reason = "pass", "artifact_contract_valid"
        elif manifest is not None or artifact is not None:
            state, reason = "fail", "artifact_inputs_invalid"
        else:
            passed = _offline_suite(capability)
            state, reason = ("pass", "offline_contract_verified") if passed else ("fail", "offline_contract_failed")
        result.update(result=state, provider_status=state, reason_code=reason)
    except Exception:
        result.update(result="fail", provider_status="unavailable", reason_code="acceptance_contract_failed")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capability", choices=sorted(REQUIREMENTS), required=True)
    parser.add_argument("--mode", choices=("config-only", "offline-fixture", "bounded-live"), default="config-only")
    parser.add_argument("--dry-run", action="store_true", help="Alias for config-only, no requests")
    parser.add_argument("--allow-live", action="store_true", help="One Google capability request, no retry; follow runbook budget")
    parser.add_argument("--confirmed-environment", choices=("preview", "production"))
    parser.add_argument("--request-budget", type=int, help="Must equal 1 for live acceptance; no retries")
    parser.add_argument("--query", default="台北市大安區敦化南路二段100號")
    parser.add_argument("--origin", nargs=2, type=float, metavar=("LAT", "LNG"))
    parser.add_argument("--destination", nargs=2, type=float, metavar=("LAT", "LNG"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--artifact", type=Path)
    parser.add_argument("--dataset-version")
    parser.add_argument("--scenario", default="24h-350mm")
    parser.add_argument("--fixtures-json", type=Path)
    args = parser.parse_args(argv)
    try:
        fixtures = None
        if args.fixtures_json:
            if args.fixtures_json.stat().st_size > 20_000:
                raise ValueError("fixture size")
            fixtures = json.loads(args.fixtures_json.read_text(encoding="utf-8"))
            if not isinstance(fixtures, list) or len(fixtures) > 3:
                raise ValueError("fixture contract")
        result = run(capability=args.capability, mode="config-only" if args.dry_run else args.mode, allow_live=args.allow_live, confirmed_environment=args.confirmed_environment, request_budget=args.request_budget, query=args.query, origin=tuple(args.origin) if args.origin else None, destination=tuple(args.destination) if args.destination else None, manifest=args.manifest, artifact=args.artifact, dataset_version=args.dataset_version, scenario=args.scenario, fixtures=fixtures)
    except Exception:
        result = {"capability": args.capability, "result": "fail", "reason_code": "acceptance_input_invalid", "network_requests": 0}
    print(json.dumps(result, sort_keys=True, ensure_ascii=True))
    return 0 if result["result"] in {"pass", "ready_for_production_acceptance", "manual_verification_only"} else 2 if result["result"] == "configuration_required" else 1


if __name__ == "__main__":
    raise SystemExit(main())
