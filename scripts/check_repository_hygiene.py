"""Fail only on high-confidence secret markers in tracked source files."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


PATTERNS = (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"), re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"), re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"))
BLOCKED_NAMES = {".env", ".env.example"}


def scan(root: Path = Path(".")) -> dict[str, object]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, check=False)
    paths = [Path(item) for item in result.stdout.decode(errors="ignore").split("\0") if item and Path(item).name not in BLOCKED_NAMES]
    findings = 0
    for path in paths:
        try:
            text = (root / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        findings += sum(1 for pattern in PATTERNS if pattern.search(text))
    return {"status": "pass" if findings == 0 else "failed", "finding_count": findings}


if __name__ == "__main__":
    result = scan()
    print(f"REPOSITORY_HYGIENE={result['status']}")
    raise SystemExit(0 if result["status"] == "pass" else 1)
