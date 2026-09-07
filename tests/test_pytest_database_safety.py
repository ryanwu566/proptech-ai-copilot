"""Regression coverage for the repository-wide hermetic database boundary."""

from __future__ import annotations

import pytest

from conftest import remove_application_database_urls, validate_vnext_rls_test_contract


EXTERNAL_LOOKING_URL = (
    "postgresql://synthetic:unused@db.production.example.invalid/application"
)


def test_application_database_urls_are_removed_from_inherited_environment() -> None:
    environment = {
        "DATABASE_URL": EXTERNAL_LOOKING_URL,
        "PILOT_EVIDENCE_DATABASE_URL": EXTERNAL_LOOKING_URL,
        "VALUATION_DATABASE_URL": EXTERNAL_LOOKING_URL,
        "COMPACT_GREEN_DATABASE_URL": EXTERNAL_LOOKING_URL,
        "PLVR_DRY_RUN_DATABASE_URL": EXTERNAL_LOOKING_URL,
        "VNEXT_DATABASE_URL": EXTERNAL_LOOKING_URL,
        "UNRELATED_SETTING": "preserved",
    }

    removed = remove_application_database_urls(environment)

    assert removed == (
        "COMPACT_GREEN_DATABASE_URL",
        "DATABASE_URL",
        "PILOT_EVIDENCE_DATABASE_URL",
        "PLVR_DRY_RUN_DATABASE_URL",
        "VALUATION_DATABASE_URL",
        "VNEXT_DATABASE_URL",
    )
    assert environment == {"UNRELATED_SETTING": "preserved"}


def test_unconfirmed_vnext_integration_url_is_removed_and_cannot_connect() -> None:
    environment = {"VNEXT_RLS_POSTGRES_URL": EXTERNAL_LOOKING_URL}

    validate_vnext_rls_test_contract(environment)

    assert "VNEXT_RLS_POSTGRES_URL" not in environment


def test_confirmed_vnext_integration_rejects_non_disposable_database_name() -> None:
    environment = {
        "VNEXT_RLS_POSTGRES_URL": EXTERNAL_LOOKING_URL,
        "VNEXT_RLS_POSTGRES_DISPOSABLE": "1",
    }

    with pytest.raises(pytest.UsageError, match="beginning with vnext_rls_test"):
        validate_vnext_rls_test_contract(environment)


def test_confirmed_dedicated_vnext_integration_url_is_allowed() -> None:
    url = "postgresql://test:unused@127.0.0.1:55432/vnext_rls_test_closure"
    environment = {
        "VNEXT_RLS_POSTGRES_URL": url,
        "VNEXT_RLS_POSTGRES_DISPOSABLE": "1",
    }

    validate_vnext_rls_test_contract(environment)

    assert environment["VNEXT_RLS_POSTGRES_URL"] == url
