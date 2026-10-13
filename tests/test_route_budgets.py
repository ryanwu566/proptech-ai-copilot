from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.analyze_next_bundle import EVIDENCE_NAME, SUPPORTED_ROUTES, analyze, build_fingerprint
from scripts.check_route_budgets import ROUTE_BUDGETS, measure, route_limit


@pytest.mark.parametrize("route", ["/places", "/cases/[caseId]/commute-planner"])
def test_my_places_requires_own_fixed_budget_and_missing_is_not_zero(tmp_path, route):
    assert route in SUPPORTED_ROUTES
    budget = ROUTE_BUDGETS[route]
    assert budget["required"] is True
    assert budget["baseline_source"].startswith("supplemental-feature-my-places")
    assert budget["baseline_client_bytes"] > 0
    assert budget["headroom_percent"] == 20
    assert budget["headroom_cap_bytes"] == 300_000
    result = measure(build_fixture(tmp_path))
    assert result["status"] == "fail"
    assert result["routes"][route]["status"] == "route_not_present"
    assert result["routes"][route]["client_bytes"] is None


def test_decision_room_requires_attribution_and_a_fixed_supplemental_budget(tmp_path):
    route = "/cases/[caseId]/decision-room"
    assert route in SUPPORTED_ROUTES
    budget = ROUTE_BUDGETS[route]
    assert budget["required"] is True
    assert budget["baseline_source"].startswith("supplemental-feature-")
    assert budget["headroom_percent"] == 20
    assert budget["headroom_cap_bytes"] == 300_000
    result = measure(build_fixture(tmp_path))
    assert result["status"] == "fail"
    assert result["routes"][route]["status"] == "route_not_present"
    assert result["routes"][route]["client_bytes"] is None


@pytest.mark.parametrize("kind", ["child", "timeout", "os", "value"])
def test_measurement_failure_diagnostics_are_fail_closed_and_private(monkeypatch, capsys, kind) -> None:
    import subprocess
    import sys
    from scripts import analyze_next_bundle as analyzer

    private = "token=secret-value provider-response saved-address env-value"
    child = {"failure_stage": "route_view_validation", "exception_type": "TimeoutError",
             "current_route": "/cases/[caseId]/risk", "error_code": "timeout"}
    stderr = private + "\nROUTE_ASSET_DIAGNOSTIC=" + json.dumps(child) + "\n" + private * 1000
    errors = {
        "child": subprocess.CalledProcessError(7, ["node"], stderr=stderr),
        "timeout": subprocess.TimeoutExpired("node", 240, stderr=stderr.encode()),
        "os": OSError(private), "value": ValueError(private),
    }

    def fail(_root):
        raise errors[kind]

    monkeypatch.setattr(analyzer, "measure_browser", fail)
    monkeypatch.setattr(sys, "argv", ["analyze_next_bundle.py", "--measure-browser"])
    assert analyzer.main() == 1
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["status"] == "fail" and result["routes"] == {}
    diagnostic = result["diagnostic"]
    assert diagnostic["exception_type"] == type(errors[kind]).__name__
    assert diagnostic["child_exit_code"] == (7 if kind == "child" else None)
    assert len(diagnostic["child_stderr_tail"]) <= 1024
    for secret in private.split():
        assert secret not in output
    if kind in {"child", "timeout"}:
        assert diagnostic["failure_stage"] == "route_view_validation"
        assert diagnostic["current_route"] == "/cases/[caseId]/risk"
        assert diagnostic["child_exception_type"] == "TimeoutError"


def test_untrusted_child_diagnostic_fields_are_redacted() -> None:
    import subprocess
    from scripts.analyze_next_bundle import measurement_diagnostic

    stderr = 'ROUTE_ASSET_DIAGNOSTIC={"failure_stage":"token-secret","exception_type":"address-secret","current_route":"/cases/private-address","error_code":"provider-secret"}'
    diagnostic = measurement_diagnostic(subprocess.CalledProcessError(1, ["node"], stderr=stderr))
    assert "secret" not in json.dumps(diagnostic)
    assert diagnostic["current_route"] is None


@pytest.mark.parametrize("output", ["[]", "null", '{"routes":{"/":{"client_files":[1]}}}'])
def test_malformed_child_output_fails_with_child_output_stage(tmp_path, monkeypatch, capsys, output) -> None:
    import subprocess
    import sys
    from scripts import analyze_next_bundle as analyzer

    class InvalidOutputProcess:
        returncode = 0
        def communicate(self, *args, **kwargs):
            return output, ""

    root = build_fixture(tmp_path)
    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: InvalidOutputProcess())
    monkeypatch.setattr(sys, "argv", ["analyzer", "--measure-browser", "--root", str(root)])
    assert analyzer.main() == 1
    result = json.loads(capsys.readouterr().out)
    assert result["diagnostic"]["failure_stage"] == "child_output"
    assert result["diagnostic"]["exception_type"] == "ValueError"
    assert not (root / EVIDENCE_NAME).exists()


def test_hard_timeout_retains_reaped_exit_and_sanitized_final_stderr(tmp_path, monkeypatch) -> None:
    import os
    import subprocess
    from scripts.analyze_next_bundle import measure_browser, measurement_diagnostic

    record = 'ROUTE_ASSET_DIAGNOSTIC={"failure_stage":"route_networkidle","current_route":"/cases/[caseId]/risk"}\n'
    class TimedOutProcess:
        pid = 424242
        returncode = -15
        def communicate(self, *args, **kwargs):
            if kwargs.get("timeout") == 240:
                raise subprocess.TimeoutExpired("node", 240, stderr=b"private initial log")
            return "", "private cleanup log\n" + record

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: TimedOutProcess())
    if os.name == "nt":
        monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: None)
    else:
        monkeypatch.setattr(os, "killpg", lambda *args: None)
    with pytest.raises(subprocess.TimeoutExpired) as failure:
        measure_browser(build_fixture(tmp_path))
    diagnostic = measurement_diagnostic(failure.value)
    assert diagnostic["child_exit_code"] == -15
    assert diagnostic["failure_stage"] == "route_networkidle"
    assert diagnostic["current_route"] == "/cases/[caseId]/risk"
    assert "private" not in json.dumps(diagnostic)


def build_fixture(tmp_path: Path) -> Path:
    root = tmp_path / ".next"
    (root / "static/chunks").mkdir(parents=True)
    (root / "server/app/preferences").mkdir(parents=True)
    (root / "BUILD_ID").write_text("fixture-build")
    (root / "static/chunks/shared.js").write_bytes(b"s" * 100)
    (root / "static/chunks/home.js").write_bytes(b"h" * 200)
    (root / "static/chunks/preferences.js").write_bytes(b"p" * 300)
    (root / "build-manifest.json").write_text(json.dumps({"rootMainFiles": ["static/chunks/shared.js"]}))
    (root / "react-loadable-manifest.json").write_text("{}")
    (root / "app-build-manifest.json").write_text(json.dumps({"pages": {
        "/layout": [],
        "/page": ["static/chunks/home.js", "static/chunks/shared.js"],
        "/preferences/page": ["static/chunks/preferences.js"],
    }}))
    (root / "server/app-paths-manifest.json").write_text(json.dumps({"/page": "app/page.js", "/preferences/page": "app/preferences/page.js"}))
    for route in ("page", "preferences/page"):
        (root / "server/app" / (route + "_client-reference-manifest.js")).write_text(
            'globalThis.__RSC_MANIFEST["/' + route + '"] = {"entryCSSFiles":{"app/layout":[]}};')
    return root


def test_independent_route_chunk_does_not_increase_homepage_bytes(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    before = analyze(root)["routes"]["/"]["client_bytes"]
    (root / "static/chunks/preferences.js").write_bytes(b"p" * 30_000)
    after = analyze(root)
    assert before == after["routes"]["/"]["client_bytes"] == 300
    assert after["routes"]["/preferences"]["client_bytes"] == 30_100


def test_shared_chunk_increases_homepage_bytes_and_is_deduplicated(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    before = analyze(root)["routes"]["/"]["client_bytes"]
    (root / "static/chunks/shared.js").write_bytes(b"s" * 150)
    assert analyze(root)["routes"]["/"]["client_bytes"] == before + 50


def test_inherited_layout_js_and_css_are_required_assets(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "static/chunks/layout.js").write_bytes(b"l" * 500)
    (root / "static/chunks/layout.css").write_bytes(b"c" * 600)
    manifest = json.loads((root / "app-build-manifest.json").read_text())
    manifest["pages"]["/layout"] = ["static/chunks/layout.js", "static/chunks/layout.css"]
    (root / "app-build-manifest.json").write_text(json.dumps(manifest))
    assert analyze(root)["routes"]["/"]["client_bytes"] == 1400


def test_per_route_client_reference_css_is_required(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "server/app").mkdir(exist_ok=True)
    (root / "static/chunks/layout.css").write_bytes(b"c" * 600)
    (root / "server/app/page_client-reference-manifest.js").write_text(
        'globalThis.__RSC_MANIFEST["/page"] = {"entryCSSFiles":{"app/layout":[{"path":"static/chunks/layout.css","inlined":false}]}};')
    assert analyze(root)["routes"]["/"]["client_bytes"] == 900


def test_global_largest_chunk_protects_even_unrelated_routes(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "static/chunks/unrelated.js").write_bytes(b"x" * 900_001)
    result = measure(root)
    assert result["routes"]["/"]["status"] == "pass"
    assert result["status"] == "fail"
    assert result["global_budget"]["largest_client_chunk_bytes"] == 900_001


def test_global_total_protects_even_unrequested_static_assets(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "static/unrequested.bin").write_bytes(b"x" * 8_000_001)
    result = measure(root)
    assert result["routes"]["/"]["status"] == "pass"
    assert result["status"] == "fail"
    assert result["global_budget"]["total_static_bytes"] > 8_000_000


def test_incomplete_app_manifest_requires_measurement_not_zero(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "app-build-manifest.json").unlink()
    result = measure(root)
    assert result["status"] == "fail"
    assert result["routes"]["/"]["client_bytes"] is None
    assert result["routes"]["/"]["status"] == "attribution_required"


def test_missing_referenced_asset_fails_closed(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "static/chunks/shared.js").unlink()
    assert measure(root)["status"] == "fail"


def test_absent_scenario_is_not_a_zero_byte_pass(tmp_path: Path) -> None:
    result = measure(build_fixture(tmp_path))
    assert result["routes"]["/cases/[caseId]/scenarios"]["status"] == "route_not_present"
    assert result["routes"]["/cases/[caseId]/scenarios"]["client_bytes"] is None


def test_static_root_compatibility_for_release_gate(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    assert measure(root / "static") == measure(root)


def browser_evidence(root: Path) -> None:
    (root / "app-build-manifest.json").unlink(missing_ok=True)
    evidence = {"schema_version": "route-assets-v2", "fingerprint": build_fingerprint(root), "routes": {
        route: {"status": "measured", "client_files": files,
                "samples_per_viewport": 2, "viewports": [390, 1440], "navigation_paths": [route]}
        for route, files in {
            "/": ["static/chunks/shared.js", "static/chunks/home.js"],
            "/preferences": ["static/chunks/shared.js", "static/chunks/preferences.js"],
        }.items()
    }}
    (root / EVIDENCE_NAME).write_text(json.dumps(evidence))


def test_browser_fallback_counts_observed_assets_and_required_shared(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    browser_evidence(root)
    result = analyze(root)
    assert result["status"] == "pass"
    assert result["routes"]["/"]["measurement_method"] == "local_production_browser"
    assert result["routes"]["/"]["client_bytes"] == 300
    assert result["routes"]["/preferences"]["client_bytes"] == 400


def test_runtime_route_cache_writes_do_not_invalidate_build_evidence(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    browser_evidence(root)
    cache = root / "server/route-cache/APP_PAGE/runtime/index.html"
    cache.parent.mkdir(parents=True)
    cache.write_text("runtime response cache")
    assert analyze(root)["routes"]["/"]["client_bytes"] == 300
    cache.write_text("updated runtime response cache")
    assert analyze(root)["status"] == "pass"


def test_prerendered_build_output_change_still_invalidates_browser_evidence(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    html = root / "server/app/index.html"
    html.write_text("built page")
    browser_evidence(root)
    html.write_text("changed built page")
    assert analyze(root)["routes"]["/"]["status"] == "attribution_required"


def test_browser_fallback_remeasured_independent_assets_leave_homepage_unchanged(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    browser_evidence(root)
    before = analyze(root)["routes"]["/"]["client_bytes"]
    (root / "static/chunks/preferences.js").write_bytes(b"p" * 500)
    browser_evidence(root)
    assert analyze(root)["routes"]["/"]["client_bytes"] == before
    assert analyze(root)["routes"]["/preferences"]["client_bytes"] == 600


def test_browser_fallback_remeasured_shared_asset_increases_homepage(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    browser_evidence(root)
    (root / "static/chunks/shared.js").write_bytes(b"s" * 200)
    browser_evidence(root)
    assert analyze(root)["routes"]["/"]["client_bytes"] == 400


def test_stale_browser_evidence_fails_closed_after_rebuild(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    browser_evidence(root)
    (root / "BUILD_ID").write_text("new-build")
    assert analyze(root)["status"] == "fail"
    assert analyze(root)["routes"]["/"]["client_bytes"] is None


def test_stale_browser_evidence_fails_after_asset_content_change_same_size(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    browser_evidence(root)
    (root / "static/chunks/home.js").write_bytes(b"changed" * 28 + b"tail")
    assert (root / "static/chunks/home.js").stat().st_size == 200
    assert analyze(root)["routes"]["/"]["status"] == "attribution_required"


def test_browser_evidence_expires_after_server_redirect_or_view_change(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "server/app").mkdir(exist_ok=True)
    page = root / "server/app/page.js"
    page.write_text("redirect('/preferences')")
    browser_evidence(root)
    page.write_text("redirect('/compare')")
    assert analyze(root)["routes"]["/"]["status"] == "attribution_required"


def test_partial_browser_evidence_cannot_pass(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    browser_evidence(root)
    evidence = json.loads((root / EVIDENCE_NAME).read_text())
    evidence["routes"]["/"]["samples_per_viewport"] = 1
    (root / EVIDENCE_NAME).write_text(json.dumps(evidence))
    assert measure(root)["status"] == "fail"


def test_conditional_css_font_references_require_browser_attribution(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "static/media").mkdir()
    (root / "static/media/font.woff2").write_bytes(b"f" * 400)
    css = b"@font-face{src:url(../media/font.woff2)}"
    (root / "static/chunks/home.css").write_bytes(css)
    manifest = json.loads((root / "app-build-manifest.json").read_text())
    manifest["pages"]["/page"] += ["static/chunks/home.css", "static/chunks/home.css"]
    (root / "app-build-manifest.json").write_text(json.dumps(manifest))
    assert analyze(root)["routes"]["/"]["status"] == "attribution_required"
    browser_evidence(root)
    evidence = json.loads((root / EVIDENCE_NAME).read_text())
    evidence["routes"]["/"]["client_files"] += ["static/chunks/home.css", "static/media/font.woff2", "static/media/font.woff2"]
    (root / EVIDENCE_NAME).write_text(json.dumps(evidence))
    assert analyze(root)["routes"]["/"]["client_bytes"] == 300 + len(css) + 400


def test_lazy_import_manifest_requires_browser_graph(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "react-loadable-manifest.json").write_text('{"lazy-map":{"files":["static/chunks/map.js"]}}')
    assert analyze(root)["routes"]["/"]["status"] == "attribution_required"


def test_route_over_budget_fails_when_global_limits_pass(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "static/chunks/home.css").write_bytes(b"c" * route_limit(ROUTE_BUDGETS["/"]))
    manifest = json.loads((root / "app-build-manifest.json").read_text())
    manifest["pages"]["/page"].append("static/chunks/home.css")
    (root / "app-build-manifest.json").write_text(json.dumps(manifest))
    result = measure(root)
    assert result["global_budget"]["status"] == "pass"
    assert result["routes"]["/"]["status"] == "fail"


def test_all_requested_routes_have_bounded_baseline_budgets() -> None:
    assert set(ROUTE_BUDGETS) == set(SUPPORTED_ROUTES)
    assert ROUTE_BUDGETS["/"]["headroom_percent"] == 10
    assert ROUTE_BUDGETS["/"]["headroom_cap_bytes"] == 200_000
    for route, budget in ROUTE_BUDGETS.items():
        assert 0 < route_limit(budget) - budget["baseline_client_bytes"] <= budget["headroom_cap_bytes"]
        if route != "/":
            assert budget["headroom_percent"] == 20
            assert budget["headroom_cap_bytes"] == 300_000


def test_cli_exits_nonzero_for_failed_budget(tmp_path: Path) -> None:
    import subprocess
    import sys

    root = build_fixture(tmp_path)
    (root / "static/unrelated.bin").write_bytes(b"x" * 8_000_001)
    completed = subprocess.run([sys.executable, "scripts/check_route_budgets.py", "--root", str(root)],
                               capture_output=True, text=True, check=False)
    assert completed.returncode == 1
    assert json.loads(completed.stdout)["global_budget"]["status"] == "fail"


def test_browser_hard_timeout_cleans_up_owned_process_tree(tmp_path: Path, monkeypatch) -> None:
    import os
    import signal
    import subprocess

    import pytest
    from scripts.analyze_next_bundle import measure_browser

    root = build_fixture(tmp_path)
    calls = []

    class TimedOutProcess:
        pid = 424242

        def communicate(self, *args, **kwargs):
            calls.append("communicate")
            if kwargs.get("timeout") == 240:
                raise subprocess.TimeoutExpired("owned-node", kwargs["timeout"], stderr="ROUTE_ASSET_BROWSER_PID=424243\n")
            return "", ""

    monkeypatch.setattr(subprocess, "Popen", lambda *args, **kwargs: TimedOutProcess())
    if os.name == "nt":
        monkeypatch.setattr(subprocess, "run", lambda command, **kwargs: calls.append(command))
    else:
        monkeypatch.setattr(os, "killpg", lambda pid, sig: calls.append((pid, sig)))
    with pytest.raises(subprocess.TimeoutExpired):
        measure_browser(root)
    expected = (["communicate", ["taskkill", "/PID", "424242", "/T", "/F"], "communicate"] if os.name == "nt" else
                ["communicate", (424242, signal.SIGTERM), "communicate", (424243, signal.SIGKILL), "communicate"])
    assert calls == expected


def test_missing_reference_manifest_cannot_drop_required_css(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    (root / "server/app/page_client-reference-manifest.js").unlink()
    assert analyze(root)["routes"]["/"]["status"] == "attribution_required"


def test_missing_root_layout_metadata_requires_browser_attribution(tmp_path: Path) -> None:
    root = build_fixture(tmp_path)
    manifest = json.loads((root / "app-build-manifest.json").read_text())
    del manifest["pages"]["/layout"]
    (root / "app-build-manifest.json").write_text(json.dumps(manifest))
    assert analyze(root)["routes"]["/"]["status"] == "attribution_required"
