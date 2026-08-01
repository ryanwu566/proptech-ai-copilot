"""Create a route-to-client-chunk report from a Next production build.

The report is intentionally derived from build manifests and static assets only.
It does not print source contents or inspect environment files.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PUBLIC_ROUTE_NAMES = {
    "/": "homepage",
    "/cases/[caseId]": "property_case",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _asset_sizes(static_root: Path) -> dict[str, int]:
    return {str(path.relative_to(static_root)).replace("\\", "/"): path.stat().st_size for path in static_root.rglob("*") if path.is_file()}


def _route_files(manifest: dict[str, Any], route: str) -> list[str]:
    pages = manifest.get("pages", {})
    files = pages.get(route, []) if isinstance(pages, dict) else []
    return [str(item) for item in files if isinstance(item, str)]


def analyze(build_root: Path = ROOT / "frontend_next/.next") -> dict[str, Any]:
    static_root = build_root / "static"
    if not static_root.is_dir():
        return {"status": "not_run", "reason": "frontend_build_missing", "routes": {}}
    manifest = _read_json(build_root / "build-manifest.json")
    app_paths = _read_json(build_root / "server/app-paths-manifest.json")
    sizes = _asset_sizes(static_root)
    shared = [str(item) for item in manifest.get("rootMainFiles", []) if isinstance(item, str)]
    polyfills = [str(item) for item in manifest.get("polyfillFiles", []) if isinstance(item, str)]
    routes: dict[str, Any] = {}
    for route, name in PUBLIC_ROUTE_NAMES.items():
        files = _route_files(manifest, route)
        manifest_route = "/page" if route == "/" else f"{route}/page"
        server_module = app_paths.get(manifest_route, "") if isinstance(app_paths, dict) else ""
        files = sorted(set(files))
        route_bytes = sum(sizes.get(item.removeprefix("static/"), sizes.get(item, 0)) for item in files)
        routes[name] = {
            "route": route,
            "client_files": files,
            "client_bytes": route_bytes,
            "server_module": server_module,
            "status": "identified" if files else ("server_route_only" if server_module else "route_not_present"),
        }
    all_js = {name: size for name, size in sizes.items() if name.endswith(".js")}
    largest = max(all_js.items(), key=lambda item: item[1], default=(None, 0))
    return {
        "status": "pass",
        "build_id": _read_json(build_root / "build-manifest.json").get("buildId", "unknown"),
        "shared_files": shared,
        "polyfill_files": polyfills,
        "largest_client_chunk": {"file": largest[0], "bytes": largest[1]},
        "all_javascript_bytes": sum(all_js.values()),
        "routes": routes,
        "static_javascript_files": len(all_js),
        "static_asset_count": len(sizes),
        "content_checks": {
            "admin_markers_in_public_assets": _marker_files(static_root, ("PILOT_ADMIN_TOKEN", "X-Pilot-Admin", "/pilot/admin", "approve-publication")),
            "road_catalog_markers_in_public_assets": _marker_files(static_root, ("road-display-catalog", "taiwan_roads", "road-phonetics")),
            "test_fixture_markers_in_public_assets": _marker_files(static_root, ("test_fixture", "e2e-session", "mock_tax_cases")),
        },
    }


def _marker_files(root: Path, markers: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for path in root.rglob("*.js"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if any(marker in text for marker in markers):
            matches.append(str(path.relative_to(root)).replace("\\", "/"))
    return matches


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT / "frontend_next/.next")
    args = parser.parse_args()
    result = analyze(args.root)
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
