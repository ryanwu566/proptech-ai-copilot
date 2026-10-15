"""Server identity adapter; transport peers are ephemeral, never persisted."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
import os
import re
import secrets
from uuid import UUID

_PEER_KEY = secrets.token_bytes(32)


def peer_key() -> bytes:
    from services.production_guardrails import production_like
    raw = os.getenv("API_USAGE_PEER_HMAC_KEY", "")
    if raw:
        if not re.fullmatch(r"[a-fA-F0-9]{64}", raw):
            raise RuntimeError("Invalid API usage identity configuration.")
        return bytes.fromhex(raw)
    if production_like(os.environ) or os.getenv("API_USAGE_DATABASE_URL", "").strip():
        raise RuntimeError("Invalid API usage identity configuration.")
    # Development only; never used for durable anonymous accounting.
    return _PEER_KEY


@dataclass(frozen=True)
class UsagePrincipal:
    key: str
    principal_class: str
    principal_id: str = ""
    tier: str = "anonymous"


def verified_principal(identity: object) -> UsagePrincipal | None:
    # A mapping/string/header claim cannot satisfy this server-owned contract.
    from services.vnext.auth import AuthenticatedPrincipal
    if not isinstance(identity, AuthenticatedPrincipal) or not isinstance(identity.user_id, UUID):
        return None
    opaque = str(identity.user_id)
    # No tier is selected from user-editable claims. Paid is a policy seam only.
    return UsagePrincipal(f"user:{opaque}", "authenticated", opaque, "free")


def principal_from_scope(scope: dict) -> UsagePrincipal:
    state = scope.get("state") or {}
    verified = verified_principal(state.get("authenticated_principal"))
    if verified is not None:
        return verified
    client = scope.get("client")
    peer = str(client[0])[:256] if client else "unknown"
    opaque = hmac.new(peer_key(), b"proptech-peer-v1:" + peer.encode("utf-8", errors="replace"), hashlib.sha256).hexdigest()
    return UsagePrincipal(f"anon:{opaque}", "anonymous", opaque)
