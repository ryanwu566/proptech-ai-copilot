"""The loopback probe must not accept HTTP success as data acceptance."""
import io
import json
from pathlib import Path
import runpy
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts/ops/professor_local_api_acceptance.py'


def run_probe(payload, http_status=200):
    class Response(io.BytesIO):
        status = http_status
    class Opener:
        def open(self, req, timeout):
            return Response(json.dumps(payload).encode())
    with patch('urllib.request.build_opener', return_value=Opener()), \
            patch.object(Path, 'write_text'), patch.object(Path, 'mkdir'):
        return runpy.run_path(str(SCRIPT))['results']


def test_malformed_success_response_is_blocked_and_probe_continues():
    results = run_probe([])
    assert len(results) == 11
    assert all(r['status'] == 'BLOCKED' for r in results)


def test_degraded_health_http_200_never_passes():
    results = run_probe({'status': 'degraded', 'readiness': 'not_ready'})
    for name in ['health', 'readiness', 'demographics_village', 'demographics_location']:
        assert next(r for r in results if r['name'] == name)['status'] == 'BLOCKED'
    assert next(r for r in results if r['name'] == 'valuation_estimate')['status'] == 'PARTIAL'

    assert all(r['status'] == 'BLOCKED' for r in run_probe({}, http_status=503))
