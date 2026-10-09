"""Build-only identity writer; never reads credentials or runtime RELEASE_COMMIT_SHA."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from services.production_identity import SHA


def write_identity(output: Path, *, root: Path = ROOT, commit: str | None = None) -> dict:
    source = 'ci-build-argument'
    if commit is None:
        commit = os.getenv('RENDER_GIT_COMMIT')
        source = 'render-checkout'
    if not commit:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=root, capture_output=True,
                                text=True, check=True, timeout=5).stdout.strip()
        source = 'git-checkout'
    commit = commit.lower()
    if not SHA.fullmatch(commit):
        raise ValueError('build_commit_invalid')
    # Digest code/config/manifests, never environment, data or generated identity.
    digest = hashlib.sha256()
    for directory in ('backend', 'services', 'config', 'database'):
        for path in sorted((root / directory).rglob('*')):
            if (path.is_file() and path.suffix in {'.py', '.json', '.sql', '.txt'}
                and '__pycache__' not in path.parts and path.name != 'build-identity.json'):
                digest.update(path.relative_to(root).as_posix().encode())
                digest.update(b'\0')
                digest.update(path.read_bytes())
                digest.update(b'\0')
    payload = {'schema_version': 'backend-build-v1', 'service': 'proptech-api',
               'commit_sha': commit, 'source': source,
               'build_timestamp': datetime.now(UTC).isoformat(),
               'build_id': 'sha256:' + digest.hexdigest()}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, sort_keys=True) + '\n', encoding='utf-8')
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'backend/build-identity.json')
    parser.add_argument('--commit', help='CI checkout SHA for Docker builds without .git')
    args = parser.parse_args()
    write_identity(args.output, commit=args.commit)
    print('BACKEND_BUILD_IDENTITY=written')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
