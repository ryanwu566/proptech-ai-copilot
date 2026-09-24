from __future__ import annotations

import pytest

import conftest


def test_missing_ris_test_url_disables_real_database_tests() -> None:
    resolver = getattr(conftest, "resolve_ris_postgres_test_url", None)

    assert callable(resolver)
    assert resolver({"RIS_POSTGRES_TEST_DISPOSABLE": "1"}) is None


def test_disposable_flag_other_than_one_disables_real_database_tests() -> None:
    resolver = getattr(conftest, "resolve_ris_postgres_test_url", None)

    assert callable(resolver)
    assert resolver(
        {
            "RIS_POSTGRES_TEST_URL": "postgresql://user:secret@localhost/ris_population_test_phase3a",
            "RIS_POSTGRES_TEST_DISPOSABLE": "yes",
        }
    ) is None


def test_unsafe_ris_test_database_name_fails_closed() -> None:
    resolver = getattr(conftest, "resolve_ris_postgres_test_url", None)

    assert callable(resolver)
    with pytest.raises(pytest.UsageError, match="ris_population_test"):
        resolver(
            {
                "RIS_POSTGRES_TEST_URL": "postgresql://user:secret@localhost/production",
                "RIS_POSTGRES_TEST_DISPOSABLE": "1",
            }
        )


def test_safe_ris_test_database_name_is_allowed_without_logging_credentials() -> None:
    resolver = getattr(conftest, "resolve_ris_postgres_test_url", None)
    url = "postgresql://user:secret@localhost/ris_population_test_phase3a"

    assert callable(resolver)
    assert resolver(
        {
            "RIS_POSTGRES_TEST_URL": url,
            "RIS_POSTGRES_TEST_DISPOSABLE": "1",
        }
    ) == url


def test_generic_database_urls_are_ignored_as_ris_test_targets() -> None:
    resolver = getattr(conftest, "resolve_ris_postgres_test_url", None)

    assert callable(resolver)
    assert resolver(
        {
            "DATABASE_URL": "postgresql://user:secret@localhost/ris_population_test_trap",
            "POSTGRES_URL": "postgresql://user:secret@localhost/ris_population_test_trap",
            "RIS_POSTGRES_TEST_DISPOSABLE": "1",
        }
    ) is None


def test_ris_database_name_is_asserted_again_immediately_before_migration() -> None:
    assertion = getattr(conftest, "assert_safe_ris_postgres_test_url", None)

    assert callable(assertion)
    assert assertion(
        "postgresql://user:secret@localhost/ris_population_test_phase3a"
    ) == "ris_population_test_phase3a"
    with pytest.raises(pytest.UsageError):
        assertion("postgresql://user:secret@localhost/shared_database")
