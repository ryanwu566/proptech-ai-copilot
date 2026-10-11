"""Opt-in bounded public metadata capture; never requests transaction archives."""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from urllib.parse import urljoin, urlsplit

import requests

from . import lineage as l, semantics as s

REGISTRY = s.ROOT / 'docs/ml/external-official-sources-v1.json'
MAX_BYTES = 1024 * 1024
MAX_SECONDS = 15
MAX_SOURCES = 24


def official_url(url: str) -> bool:
    try:
        parsed = urlsplit(url)
        return (parsed.scheme == 'https' and parsed.port in {None, 443}
                and not parsed.username and not parsed.password
                and bool(parsed.hostname) and parsed.hostname.endswith(('.gov.tw', '.gov.taipei')))
    except (ValueError, TypeError, AttributeError):
        return False


def capture(source: dict, destination: Path) -> dict:
    started = time.monotonic()
    result = {k: source[k] for k in ('source_id', 'official_url', 'purpose', 'license_note')}
    result.update(retrieved_at=datetime.now(timezone.utc).isoformat(),
                  classification='CURRENT_METADATA_ONLY', byte_size=None, sha256=None,
                  retained_path=None, status='UNAVAILABLE')
    url = source['official_url']
    try:
        for _ in range(4):
            if not official_url(url):
                raise ValueError('official_redirect_required')
            with requests.get(url, timeout=(5, 5), allow_redirects=False, stream=True,
                              headers={'User-Agent':'ML0-bounded-official-metadata-research/1'}) as response:
                if time.monotonic() - started > MAX_SECONDS:
                    raise ValueError('elapsed_bound')
                if response.is_redirect:
                    url = urljoin(url, response.headers.get('Location', ''))
                    continue
                response.raise_for_status()
                content_type = response.headers.get('Content-Type', '').lower()
                if not any(x in content_type for x in ('text/html', 'application/pdf', 'application/json')):
                    raise ValueError('metadata_content_type_required')
                data = bytearray()
                for chunk in response.iter_content(8192):
                    data.extend(chunk)
                    if len(data) > MAX_BYTES or time.monotonic() - started > MAX_SECONDS:
                        raise ValueError('capture_bound')
                if not data:
                    raise ValueError('empty_response')
                filename = source['source_id'] + '.bin'
                (destination / filename).write_bytes(data)
                result.update(status='RETAINED', byte_size=len(data), sha256=hashlib.sha256(data).hexdigest(),
                              retained_path=filename, final_url=url, content_type=content_type)
                return result
        raise ValueError('redirect_bound')
    except (requests.RequestException, ValueError, OSError) as exc:
        # No response body, credentials, local path or server diagnostic in public manifest.
        result['failure_class'] = type(exc).__name__
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    destination = args.output.resolve()
    private = (s.ROOT / 'artifacts/ml/external-evidence').resolve()
    if not destination.is_relative_to(private) or destination.exists():
        parser.exit(2, 'new_private_capture_directory_required\n')
    sources = json.loads(REGISTRY.read_text(encoding='utf-8'))['sources']
    if not 1 <= len(sources) <= MAX_SOURCES or any(not official_url(x['official_url']) for x in sources):
        parser.exit(2, 'bounded_official_registry_required\n')
    destination.mkdir(parents=True)
    with ThreadPoolExecutor(max_workers=3) as executor:
        results = list(executor.map(lambda x: capture(x, destination), sources))
    report = {'schema_version':'ml0-metadata-capture-v1', 'sources':results,
              'bounds':{'sources':len(sources), 'bytes_each':MAX_BYTES, 'seconds_each':MAX_SECONDS,
                        'attempts_each':1, 'workers':3, 'redirects_each':3},
              'historical_proofs_recovered':0}
    (destination / 'manifest.json').write_bytes(l.canonical_bytes(report) + b'\n')
    print(json.dumps({'selected':len(sources), 'retained':sum(x['status']=='RETAINED' for x in results)}))


if __name__ == '__main__':
    main()
