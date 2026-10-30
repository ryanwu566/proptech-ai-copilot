"""The image-local smoke helper is offline unless explicitly admitted."""
import json
from types import SimpleNamespace

from scripts.ops import taiwan_imagery_preflight as preflight


def test_preflight_default_is_offline(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "_adapter", lambda *_: (_ for _ in ()).throw(AssertionError("network admitted")))
    assert preflight.main([]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["status"] == "PREPARED_NOT_NETWORK_VERIFIED"
    assert result["provider_calls"] == 0 and result["provider_activated"] is False
    assert result["normal_ca_validation"] is True


def test_explicit_network_check_only_returns_sanitized_metadata(monkeypatch, capsys):
    query = []
    class Adapter:
        def fetch(self, value):
            query.append(value)
            return SimpleNamespace(image_bytes=b"never-print-image", source_type="orthophoto", vintage=None, observation_date=None)
    monkeypatch.setattr(preflight, "_adapter", lambda *_: Adapter())
    assert preflight.main(["--allow-network"]) == 0
    text = capsys.readouterr().out
    result = json.loads(text)
    assert result["status"] == "PASS" and result["output_bytes"] == 17
    assert result["vintage"] is None and result["observation_date"] is None
    assert query[0].dimensions == (512, 512) and query[0].aoi_radius_m == 500
    assert "never-print-image" not in text


def test_unexpected_error_is_redacted(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "_adapter", lambda *_: (_ for _ in ()).throw(RuntimeError("access_token=not-public")))
    assert preflight.main(["--allow-network"]) == 1
    text = capsys.readouterr().out
    assert json.loads(text)["reason_code"] == "provider_error" and "not-public" not in text


def test_csrsr_cannot_skip_license_admission(monkeypatch, capsys):
    monkeypatch.setattr(preflight, "_adapter", lambda *_: (_ for _ in ()).throw(AssertionError("should refuse")))
    assert preflight.main(["--provider", "csrsr_spot", "--allow-network"]) == 1
    assert json.loads(capsys.readouterr().out)["reason_code"] == "licensing_not_accepted"
