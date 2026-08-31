from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest

from services.vnext.errors import VNextError
from services.vnext.pagination import CursorCodec, cursor_datetime, cursor_uuid


def test_signed_cursor_round_trip_and_tamper_rejection() -> None:
    codec = CursorCodec(b"slice-5-test-cursor-key-material-0001")
    cursor = codec.encode(
        kind="property_graph",
        fields={
            "created_at": "2026-08-31T10:00:00+00:00",
            "relation_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        },
    )

    decoded = codec.decode(
        cursor,
        kind="property_graph",
        expected_fields=frozenset({"created_at", "relation_id"}),
    )

    assert cursor_datetime(decoded.fields["created_at"]) == datetime(
        2026, 8, 31, 10, tzinfo=timezone.utc
    )
    assert cursor_uuid(decoded.fields["relation_id"]) == UUID(
        "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    )
    payload, signature = cursor.split(".")
    tampered = f"{payload[:-1]}{'A' if payload[-1] != 'A' else 'B'}.{signature}"
    with pytest.raises(VNextError):
        codec.decode(
            tampered,
            kind="property_graph",
            expected_fields=frozenset({"created_at", "relation_id"}),
        )


def test_cursor_is_bound_to_route_version_and_exact_fields() -> None:
    codec = CursorCodec(b"slice-5-test-cursor-key-material-0001")
    cursor = codec.encode(
        kind="property_graph",
        fields={
            "created_at": "2026-08-31T10:00:00+00:00",
            "relation_id": str(UUID(int=1)),
        },
    )

    with pytest.raises(VNextError):
        codec.decode(
            cursor,
            kind="property_evidence",
            expected_fields=frozenset({"created_at", "relation_id"}),
        )
    with pytest.raises(VNextError):
        codec.decode(
            cursor,
            kind="property_graph",
            expected_fields=frozenset({"created_at"}),
        )


@pytest.mark.parametrize("value", [None, "", "not-a-time", "2026-08-31T10:00:00"])
def test_cursor_datetime_rejects_missing_or_naive_values(value: str | None) -> None:
    if value is None:
        assert cursor_datetime(value) is None
        return
    with pytest.raises(VNextError):
        cursor_datetime(value)
