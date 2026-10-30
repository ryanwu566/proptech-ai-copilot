"""The full developer suite needs native ML; ordinary API installs do not."""
from pathlib import Path

from packaging.requirements import Requirement


ROOT = Path(__file__).resolve().parents[1]


def dependencies(name):
    result = {}
    for line in (ROOT / name).read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("-r "):
            result.update(dependencies(line[3:].strip()))
        elif line:
            requirement = Requirement(line)
            result[requirement.name.lower()] = requirement
    return result


def test_full_suite_uses_the_bounded_ml_profile_without_changing_api_installs():
    ml = dependencies("requirements-ml.txt")
    dev = dependencies("requirements-dev.txt")
    assert "-r requirements-ml.txt" in (ROOT / "requirements-dev.txt").read_text().splitlines()
    for name in ("numpy", "scipy", "scikit-learn", "lightgbm"):
        assert dev[name] == ml[name]
        assert any(spec.operator == ">=" for spec in dev[name].specifier)
        assert any(spec.operator == "<" for spec in dev[name].specifier)
    for manifest in ("requirements.txt", "backend/requirements.txt"):
        runtime = dependencies(manifest)
        assert not {"lightgbm", "scikit-learn", "scipy"} & runtime.keys()
