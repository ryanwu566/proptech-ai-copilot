from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_validation_harnesses_are_present_and_secret_free() -> None:
    scripts = {
        "scripts/analyze_next_bundle.py",
        "scripts/benchmark_local_api.py",
        "scripts/benchmark_pilot_sqlite.py",
        "scripts/run_bounded_load.py",
        "scripts/measure_browser_performance.cjs",
        "scripts/measure_memory_regressions.cjs",
    }
    assert all((ROOT / path).is_file() for path in scripts)
    source = "\n".join((ROOT / path).read_text(encoding="utf-8") for path in scripts)
    assert ".env.example" not in source
    assert "production" in source
    assert "synthetic" in source


def test_browser_harness_checks_public_bundle_boundaries() -> None:
    source = (ROOT / "scripts/analyze_next_bundle.py").read_text(encoding="utf-8")
    assert "admin_markers_in_public_assets" in source
    assert "road_catalog_markers_in_public_assets" in source
    assert "test_fixture_markers_in_public_assets" in source


def test_load_harness_is_bounded_and_local_only() -> None:
    source = (ROOT / "scripts/run_bounded_load.py").read_text(encoding="utf-8")
    assert "ASGITransport" in source
    assert "(1, 5, 10, 20)" in source
    assert "production" not in source.lower()


def test_ci_contains_local_performance_gates_without_secrets() -> None:
    source = (ROOT / ".github/workflows/security-performance.yml").read_text(encoding="utf-8")
    for command in (
        "scripts/analyze_next_bundle.py",
        "scripts/benchmark_local_api.py",
        "scripts/benchmark_pilot_sqlite.py",
        "scripts/run_bounded_load.py",
        "measure_browser_performance.cjs",
        "measure_memory_regressions.cjs",
        "pip-audit",
    ):
        assert command in source
    assert "secrets." not in source
    assert "PILOT_" not in source
