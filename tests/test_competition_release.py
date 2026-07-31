from pathlib import Path


ROOT = Path(__file__).parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_competition_surface_is_explicit_and_reuses_existing_contracts():
    source = read("frontend_next/components/competition-taxoracle-demo.tsx")
    assert "api.runTaxOracleCase" in source
    assert "api.holdingCostCalculate" in source
    assert "offline" in source.lower()
    assert "window.print" in source
    assert "rule_version" in source
    assert "missing" in source


def test_capability_matrix_has_truthful_non_fabricated_states():
    source = read("frontend_next/lib/competition-release.ts")
    assert "market validation pending" in source
    assert "professional review pending" in source
    assert "customer-validation" in source
    assert "accuracy" in source


def test_public_policy_and_docs_are_present():
    page = read("frontend_next/app/page.tsx")
    assert '"Privacy" as AppPage' in page
    assert '"Terms" as AppPage' in page
    assert (ROOT / "docs/competition-release.md").exists()
    assert (ROOT / "docs/competition-evidence-pack.md").exists()


def test_competition_does_not_change_protected_backend_or_formula_modules():
    changed = {line for line in read("frontend_next/components/competition-taxoracle-demo.tsx").splitlines() if "backend/" in line or "rules/" in line}
    assert not changed
