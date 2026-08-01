from pathlib import Path


ROOT = Path(__file__).parents[1]
STATIC = ROOT / "frontend_next/.next/static"
MAX_STATIC_BYTES = 6 * 1024 * 1024


def test_competition_bundle_budget_is_defined_and_respected_when_build_output_exists():
    assert MAX_STATIC_BYTES == 6 * 1024 * 1024
    if not STATIC.exists():
        return
    total = sum(path.stat().st_size for path in STATIC.rglob("*") if path.is_file())
    assert total <= MAX_STATIC_BYTES
