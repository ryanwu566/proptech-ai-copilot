"""Generate a dependency-manifest SBOM without contacting a package registry."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def generate() -> dict[str, object]:
    package = json.loads((ROOT / "frontend_next/package.json").read_text(encoding="utf-8"))
    python_requirements = []
    for line in (ROOT / "backend/requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            python_requirements.append(line.split(";", 1)[0])
    components = [{"type": "library", "name": name, "version": str(version)} for name, version in sorted({**package.get("dependencies", {}), **package.get("devDependencies", {})}.items())]
    components.extend({"type": "library", "name": item.split("<", 1)[0].split(">=", 1)[0], "version": "declared"} for item in sorted(python_requirements))
    return {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1, "metadata": {"component": {"type": "application", "name": "proptech-ai-copilot"}}, "components": components}


if __name__ == "__main__":
    print(json.dumps(generate(), ensure_ascii=True, sort_keys=True))
