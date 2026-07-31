"""Contract tests for verified official source metadata."""

from services.official_data_registry import OFFICIAL_DATA_PROVIDERS, provider_registry, public_source_status


def test_registry_contains_only_verified_public_source_metadata() -> None:
    assert OFFICIAL_DATA_PROVIDERS
    assert {item.domain for item in OFFICIAL_DATA_PROVIDERS} == {"terrain", "tax"}
    for item in OFFICIAL_DATA_PROVIDERS:
        assert item.provider_id
        assert item.agency
        assert item.source_url.startswith("https://")
        assert item.documentation_url.startswith("https://")
        assert item.authentication_mode == "none"
        assert item.runtime_status == "not_checked"


def test_status_distinguishes_metadata_from_runtime_availability() -> None:
    status = public_source_status("terrain")
    assert status["status"] == "not_checked"
    assert status["credentials_required"] is False
    assert all(row["runtime_status"] == "not_checked" for row in status["sources"])
    assert provider_registry("tax")
