"""Attribute production client assets using Next manifests or local browser evidence.

No environment files or source contents are emitted. Incomplete attribution is
an error, never a zero-byte measurement. Browser measurement is explicit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import signal
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SUPPORTED_ROUTES = ("/", "/login", "/signup", "/account", "/preferences", "/places", "/compare", "/cases/[caseId]", *(
    f"/cases/[caseId]/{section}" for section in
    ("overview", "market", "location", "risk", "finance", "report", "scenarios", "decision-room", "commute-planner")
))
EVIDENCE_NAME = "route-assets-v2.json"
FAILURE_STAGES = {
    "input", "module_resolution", "fixture_loading", "build_id", "server_start",
    "server_readiness", "chromium_launch", "chromium_connect", "browser_context",
    "route_navigation", "route_view_validation", "route_networkidle", "route_assets",
    "process_cleanup", "browser_subprocess", "child_output", "build_fingerprint", "evidence_write",
    "route_manifest", "bundle_analysis",
}
CHILD_EXCEPTIONS = {"Error", "TypeError", "SyntaxError", "RangeError", "TimeoutError"}
CHILD_ERROR_CODES = {
    "timeout", "MODULE_NOT_FOUND", "ERR_REQUIRE_ESM", "ERR_UNKNOWN_FILE_EXTENSION",
    "ENOENT", "EACCES", "EADDRINUSE", "server_failed", "server_readiness_timeout",
    "unexpected_destination", "fixture_not_hydrated", "incomplete_route_load", "unstable_route_assets",
}


def measurement_diagnostic(error: Exception, stage: str = "browser_subprocess") -> dict[str, Any]:
    """Only emit a closed vocabulary, never arbitrary child logs or error messages.

    Regex redaction cannot safely recognize provider payloads or saved addresses.
    The stderr tail therefore contains only validated structural diagnostics.
    """
    stderr = getattr(error, "stderr", None) or ""
    if isinstance(stderr, bytes):
        stderr = stderr.decode(errors="replace")
    child: dict[str, Any] = {}
    for line in stderr.splitlines():
        if line.startswith("ROUTE_ASSET_DIAGNOSTIC=") and len(line) <= 2048:
            try:
                candidate = json.loads(line.split("=", 1)[1])
            except ValueError:
                continue
            if not isinstance(candidate, dict):
                continue
            child = {
                key: value for key, allowed in (
                    ("failure_stage", FAILURE_STAGES), ("exception_type", CHILD_EXCEPTIONS),
                    ("error_code", CHILD_ERROR_CODES), ("current_route", SUPPORTED_ROUTES),
                    ("observed_route", SUPPORTED_ROUTES),
                ) if isinstance((value := candidate.get(key)), str) and value in allowed
            }
    return {
        "failure_stage": child.get("failure_stage", getattr(error, "failure_stage", stage)),
        "exception_type": type(error).__name__,
        "child_exception_type": child.get("exception_type"),
        "child_exit_code": getattr(error, "returncode", None),
        "error_code": child.get("error_code", str(error) if str(error) in {
            "route_manifest_missing_or_invalid", "build_changed_during_measurement", "invalid_browser_evidence",
        } else None),
        "current_route": child.get("current_route"),
        "child_stderr_tail": json.dumps(child, sort_keys=True)[:1024] if child else ("[redacted]" if stderr else ""),
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def _asset_sizes(static_root: Path) -> dict[str, int]:
    return {path.relative_to(static_root).as_posix(): path.stat().st_size
            for path in static_root.rglob("*") if path.is_file()}


def _asset_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("invalid_static_asset_path")
    name = unquote(urlsplit(value).path).removeprefix("/_next/").removeprefix("static/")
    if not name or name.startswith("/") or ".." in name.split("/") or "\\" in name:
        raise ValueError("invalid_static_asset_path")
    return name


def build_fingerprint(build_root: Path) -> str:
    """Bind cached requests to asset contents, route inventory and measurement code."""
    digest = hashlib.sha256()
    paths = [build_root / "BUILD_ID", build_root / "build-manifest.json",
             build_root / "app-build-manifest.json", build_root / "react-loadable-manifest.json",
             build_root / "server/app-paths-manifest.json"]
    paths += sorted((build_root / "static").rglob("*"))
    # Next 16 creates response-cache files on first production requests. They
    # are runtime state, not build inputs. Keep compiled/prerendered app output
    # and all other server manifests bound to the evidence.
    paths += sorted(path for path in (build_root / "server").rglob("*")
                    if not path.is_relative_to(build_root / "server/route-cache"))
    paths += [build_root / "routes-manifest.json", build_root / "prerender-manifest.json"]
    paths += [Path(__file__), ROOT / "scripts/measure_route_assets.cjs",
              build_root.parent / "lib/workspace/e9-test-fixtures.ts"]
    for path in paths:
        if path.is_file():
            label = path.relative_to(build_root).as_posix() if path.is_relative_to(build_root) else path.name
            digest.update(label.encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
    return digest.hexdigest()


def _manifest_files(build_root: Path, manifest_route: str) -> list[str] | None:
    """Webpack's eager app lists are usable only without unattributed lazy imports.

    Turbopack entryJSFiles/clientModules describe references, not the full loaded
    graph. Do not union every client reference or guess async dependency edges.
    """
    manifest = _read_json(build_root / "app-build-manifest.json")
    files = manifest.get("pages", {}).get(manifest_route) if isinstance(manifest.get("pages"), dict) else None
    if not isinstance(files, list) or not files or not all(isinstance(item, str) for item in files):
        return None
    loadable_path = build_root / "react-loadable-manifest.json"
    try:
        loadable = json.loads(loadable_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if loadable != {}:
        return None
    shared = _read_json(build_root / "build-manifest.json")
    if not isinstance(shared.get("rootMainFiles"), list) or not shared["rootMainFiles"]:
        return None
    if shared.get("polyfillFiles"):
        return None  # Conditional legacy-browser scripts need observed attribution.
    pages = manifest["pages"]
    if "/layout" not in pages:
        return None
    segments = manifest_route.removesuffix("/page").strip("/").split("/") if manifest_route != "/page" else []
    for depth in range(len(segments) + 1):
        layout = "/" + "/".join([*segments[:depth], "layout"])
        layout_files = pages.get(layout, [])
        if not isinstance(layout_files, list) or not all(isinstance(item, str) for item in layout_files):
            return None
        files = files + layout_files
    # CSS entry files may be recorded only in the per-route client manifest.
    reference = build_root / "server/app" / (manifest_route.strip("/") + "_client-reference-manifest.js")
    if not reference.is_file():
        return None
    if reference.is_file():
        try:
            source = reference.read_text(encoding="utf-8")
            assignment = re.search(r"__RSC_MANIFEST\[[^\n]*?\]\s*=\s*(\{)", source)
            if not assignment:
                return None
            client_manifest, _ = json.JSONDecoder().raw_decode(source[assignment.start(1):])
            for entries in client_manifest["entryCSSFiles"].values():
                for entry in entries:
                    if isinstance(entry, str):
                        files.append(entry)
                    elif isinstance(entry, dict) and entry.get("inlined") is False and isinstance(entry.get("path"), str):
                        files.append(entry["path"])
                    elif not isinstance(entry, dict) or entry.get("inlined") is not True:
                        return None
        except (OSError, ValueError, KeyError, TypeError, AttributeError):
            return None
    result = files + shared["rootMainFiles"]
    for asset in result:
        try:
            name = _asset_name(asset)
            if name.endswith(".css"):
                css = (build_root / "static" / name).read_text(encoding="utf-8")
                if any(not match.group(1).startswith("data:") for match in
                       re.finditer(r"url\(\s*['\"]?([^)'\"\s]+)", css)):
                    return None  # Selectors and font ranges determine actual requests.
        except (OSError, ValueError, TypeError):
            return None
    return result


def _with_css_assets(files: list[str], static_root: Path) -> list[str]:
    return sorted({_asset_name(item) for item in files})


def _marker_files(root: Path, markers: tuple[str, ...]) -> list[str]:
    matches = []
    for path in root.rglob("*.js"):
        text = path.read_text(encoding="utf-8", errors="ignore")
        if any(marker in text for marker in markers):
            matches.append(path.relative_to(root).as_posix())
    return sorted(matches)


def analyze(build_root: Path = ROOT / "frontend_next/.next") -> dict[str, Any]:
    build_root = build_root.parent if build_root.name == "static" else build_root
    static_root = build_root / "static"
    if not static_root.is_dir():
        return {"status": "not_run", "reason": "frontend_build_missing", "routes": {}}
    app_paths = _read_json(build_root / "server/app-paths-manifest.json")
    if not app_paths or "/page" not in app_paths:
        return {"status": "fail", "reason": "route_manifest_missing_or_invalid", "routes": {}}
    sizes = _asset_sizes(static_root)
    evidence = _read_json(build_root / EVIDENCE_NAME)
    evidence_valid = (evidence.get("schema_version") == "route-assets-v2"
                      and evidence.get("fingerprint") == build_fingerprint(build_root))
    routes: dict[str, Any] = {}
    for route in SUPPORTED_ROUTES:
        manifest_route = "/page" if route == "/" else f"{route}/page"
        entry: dict[str, Any] = {"route": route, "client_files": [], "client_bytes": None}
        routes[route] = entry
        if manifest_route not in app_paths:
            entry["status"] = "route_not_present"
            continue
        files = _manifest_files(build_root, manifest_route)
        method = "next_app_build_manifest"
        if files is None:
            measured_routes = evidence.get("routes", {})
            measured = measured_routes.get(route, {}) if evidence_valid and isinstance(measured_routes, dict) else {}
            if (not isinstance(measured, dict) or measured.get("status") != "measured"
                    or measured.get("samples_per_viewport") != 2
                    or measured.get("viewports") != [390, 1440]
                    or not isinstance(measured.get("client_files"), list)
                    or not measured["client_files"]):
                entry.update(status="attribution_required", reason="app_manifest_loaded_graph_incomplete_or_browser_evidence_stale")
                continue
            files = measured["client_files"]
            method = "local_production_browser"
            entry["navigation_paths"] = measured.get("navigation_paths", [])
        try:
            names = (_with_css_assets(files, static_root) if method == "next_app_build_manifest"
                     else sorted({_asset_name(item) for item in files}))
            missing = [name for name in names if name not in sizes]
            if missing:
                raise ValueError("referenced_asset_missing")
        except (OSError, ValueError, TypeError):
            entry.update(status="attribution_failed", reason="invalid_or_missing_client_asset")
            continue
        entry.update(status="measured", measurement_method=method,
                     client_files=[f"static/{name}" for name in names],
                     client_bytes=sum(sizes[name] for name in names))
    javascript = {name: size for name, size in sizes.items() if name.endswith(".js")}
    largest = max(javascript.items(), key=lambda item: item[1], default=(None, 0))
    return {
        "schema_version": "next-bundle-v2",
        "status": "pass" if all(item["status"] in {"measured", "route_not_present"} for item in routes.values()) else "fail",
        "build_id": (build_root / "BUILD_ID").read_text().strip() if (build_root / "BUILD_ID").is_file() else "unknown",
        "fingerprint": build_fingerprint(build_root), "routes": routes,
        "largest_client_chunk": {"file": largest[0], "bytes": largest[1]},
        "total_static_bytes": sum(sizes.values()), "all_javascript_bytes": sum(javascript.values()),
        "static_javascript_files": len(javascript), "static_asset_count": len(sizes),
        "content_checks": {
            "admin_markers_in_public_assets": _marker_files(static_root, ("PILOT_ADMIN_TOKEN", "X-Pilot-Admin", "/pilot/admin", "approve-publication")),
            "road_catalog_markers_in_public_assets": _marker_files(static_root, ("road-display-catalog", "taiwan_roads", "road-phonetics")),
            "test_fixture_markers_in_public_assets": _marker_files(static_root, ("test_fixture", "e2e-session", "mock_tax_cases")),
        },
    }


def measure_browser(build_root: Path) -> None:
    state = {"stage": "route_manifest"}
    try:
        _measure_browser(build_root, state)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        error.failure_stage = state["stage"]
        raise


def _measure_browser(build_root: Path, state: dict[str, str]) -> None:
    paths = _read_json(build_root / "server/app-paths-manifest.json")
    routes = [route for route in SUPPORTED_ROUTES if ("/page" if route == "/" else f"{route}/page") in paths]
    if "/" not in routes:
        raise ValueError("route_manifest_missing_or_invalid")
    state["stage"] = "build_fingerprint"
    before = build_fingerprint(build_root)
    state["stage"] = "browser_subprocess"
    process = subprocess.Popen(["node", str(ROOT / "scripts/measure_route_assets.cjs")],
                               stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, start_new_session=os.name != "nt")
    try:
        output, error = process.communicate(json.dumps({"frontend_root": str(build_root.parent.resolve()), "routes": routes}), timeout=240)
    except subprocess.TimeoutExpired as expired:
        # Terminating only Node bypasses its finally and leaves Next/Chromium alive.
        # Kill exclusively this owned process tree/group on the hard deadline.
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True, check=False)
        else:
            # Playwright's Chromium owns a separate process group on POSIX.
            # Its PID is reported by our trusted launcher, never by page content.
            stderr = expired.stderr or ""
            if isinstance(stderr, bytes):
                stderr = stderr.decode(errors="replace")
            browser_groups = [int(pid) for pid in re.findall(r"^ROUTE_ASSET_BROWSER_PID=(\d+)$", stderr, re.MULTILINE)]
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            for group in browser_groups:
                if group > 1 and group != os.getpgrp():
                    try:
                        os.killpg(group, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
        final_output, final_error = process.communicate()
        expired.output = final_output
        expired.stderr = final_error or expired.stderr
        expired.returncode = getattr(process, "returncode", None)
        raise
    if process.returncode:
        raise subprocess.CalledProcessError(process.returncode, process.args, output=output, stderr=error)
    state["stage"] = "child_output"
    evidence = json.loads(output)
    if not isinstance(evidence, dict) or not isinstance(evidence.get("routes"), dict):
        raise ValueError("invalid_browser_evidence")
    if any(not isinstance(entry, dict) or not isinstance(entry.get("client_files"), list)
           or not all(isinstance(item, str) for item in entry["client_files"])
           for entry in evidence["routes"].values()):
        raise ValueError("invalid_browser_evidence")
    state["stage"] = "build_fingerprint"
    if build_fingerprint(build_root) != before:
        raise ValueError("build_changed_during_measurement")
    evidence.update(schema_version="route-assets-v2", fingerprint=before)
    state["stage"] = "evidence_write"
    (build_root / EVIDENCE_NAME).write_text(json.dumps(evidence, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--root", type=Path, default=ROOT / "frontend_next/.next")
    parser.add_argument("--measure-browser", action="store_true", help="Explicit local production fallback; blocks all provider/API requests")
    args = parser.parse_args()
    stage = "browser_subprocess"
    try:
        if args.measure_browser:
            measure_browser(args.root)
        stage = "bundle_analysis"
        result = analyze(args.root)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        result = {"status": "fail", "reason": "local_browser_measurement_failed", "routes": {},
                  "diagnostic": measurement_diagnostic(error, stage)}
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
