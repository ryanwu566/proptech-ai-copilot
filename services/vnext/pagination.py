"""Signed opaque cursor support for bounded VNext read endpoints."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from uuid import UUID

from services.vnext.errors import VNextError

CURSOR_SIGNING_KEY_ENV = "VNEXT_CURSOR_SIGNING_KEY"
CURSOR_VERSION = 1
MAX_CURSOR_LENGTH = 1024


@dataclass(frozen=True)
class CursorPosition:
    """Validated position fields carried by a route-bound cursor."""

    fields: Mapping[str, str | None]


def _encode_part(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode_part(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.b64decode(value + padding, altchars=b"-_", validate=True)


class CursorCodec:
    """Encode signed, versioned cursors without SQL, secrets, or tenant data."""

    def __init__(self, signing_key: bytes) -> None:
        if len(signing_key) < 32:
            raise ValueError("cursor signing key must contain at least 32 bytes")
        self._signing_key = bytes(signing_key)

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "CursorCodec":
        values = environ if environ is not None else os.environ
        key = values.get(CURSOR_SIGNING_KEY_ENV, "").encode("utf-8")
        return cls(key)

    def encode(
        self,
        *,
        kind: str,
        fields: Mapping[str, str | None],
    ) -> str:
        if not kind or len(kind) > 80 or not fields or len(fields) > 8:
            raise VNextError.validation_failed()
        payload = {
            "v": CURSOR_VERSION,
            "kind": kind,
            "fields": dict(fields),
        }
        if any(
            not isinstance(name, str)
            or not name
            or len(name) > 40
            or value is not None
            and (not isinstance(value, str) or len(value) > 160)
            for name, value in payload["fields"].items()
        ):
            raise VNextError.validation_failed()
        encoded = json.dumps(
            payload,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        signature = hmac.new(self._signing_key, encoded, hashlib.sha256).digest()
        cursor = f"{_encode_part(encoded)}.{_encode_part(signature)}"
        if len(cursor) > MAX_CURSOR_LENGTH:
            raise VNextError.validation_failed()
        return cursor

    def decode(
        self,
        cursor: str,
        *,
        kind: str,
        expected_fields: frozenset[str],
    ) -> CursorPosition:
        if not cursor or len(cursor) > MAX_CURSOR_LENGTH or cursor.count(".") != 1:
            raise VNextError.validation_failed()
        try:
            encoded_part, signature_part = cursor.split(".")
            encoded = _decode_part(encoded_part)
            signature = _decode_part(signature_part)
            expected = hmac.new(self._signing_key, encoded, hashlib.sha256).digest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("invalid signature")
            payload = json.loads(encoded)
        except Exception:
            raise VNextError.validation_failed() from None
        if (
            not isinstance(payload, dict)
            or set(payload) != {"v", "kind", "fields"}
            or payload["v"] != CURSOR_VERSION
            or payload["kind"] != kind
            or not isinstance(payload["fields"], dict)
            or set(payload["fields"]) != expected_fields
        ):
            raise VNextError.validation_failed()
        fields: dict[str, str | None] = {}
        for name, value in payload["fields"].items():
            if value is not None and (not isinstance(value, str) or len(value) > 160):
                raise VNextError.validation_failed()
            fields[str(name)] = value
        return CursorPosition(fields=fields)


def cursor_datetime(value: str | None) -> datetime | None:
    if value is None:
        return None
    try:
        selected = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        raise VNextError.validation_failed() from None
    if selected.utcoffset() is None:
        raise VNextError.validation_failed()
    return selected


def cursor_uuid(value: str | None) -> UUID:
    if value is None:
        raise VNextError.validation_failed()
    try:
        return UUID(value)
    except (TypeError, ValueError):
        raise VNextError.validation_failed() from None
