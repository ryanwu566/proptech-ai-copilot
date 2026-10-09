"""Allowlisted backend build identity. No git or environment SHA fallback at runtime."""
from __future__ import annotations

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Mapping

BUILD_PATH = Path(__file__).resolve().parents[1] / 'backend' / 'build-identity.json'
SHA = re.compile(r'[a-f0-9]{40}\Z')
BUILD_ID = re.compile(r'sha256:[a-f0-9]{64}\Z')


def utc_timestamp(value: object) -> bool:
    if not isinstance(value, str) or len(value) > 40:
        return False
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed.utcoffset() is not None and parsed.utcoffset().total_seconds() == 0
    except ValueError:
        return False


def backend_identity(path: Path = BUILD_PATH, environ: Mapping[str, str] | None = None) -> dict:
    values = os.environ if environ is None else environ
    unknown = {'service': 'proptech-api', 'commit_sha': 'unconfigured',
               'build_timestamp': 'unconfigured', 'build_id': 'unconfigured',
               'identity_source': 'not_built', 'identity_status': 'UNKNOWN',
               'runtime_sha_matches_build': None}
    try:
        if path.stat().st_size > 4096:
            return unknown
        data = json.loads(path.read_text(encoding='utf-8'))
        if (not isinstance(data, dict) or data.get('schema_version') != 'backend-build-v1'
            or not SHA.fullmatch(str(data.get('commit_sha', '')))
            or not BUILD_ID.fullmatch(str(data.get('build_id', '')))
            or not utc_timestamp(data.get('build_timestamp'))
            or data.get('service') != 'proptech-api'
            or data.get('source') not in {'git-checkout', 'render-checkout', 'ci-build-argument'}):
            return unknown
        claimed = values.get('RELEASE_COMMIT_SHA', '').strip().lower()
        return {'service': 'proptech-api', 'commit_sha': data['commit_sha'],
                'build_timestamp': data['build_timestamp'], 'build_id': data['build_id'],
                'identity_source': data['source'], 'identity_status': 'PASS',
                'runtime_sha_matches_build': claimed == data['commit_sha'] if SHA.fullmatch(claimed) else None}
    except (OSError, ValueError, TypeError):
        return unknown
