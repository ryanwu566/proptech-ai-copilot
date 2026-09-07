"""Supabase Auth JWT verification and canonical principal mapping."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any, Callable, Mapping
from urllib.parse import urlsplit
from uuid import UUID

import jwt
from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.vnext.errors import VNextError


SUPABASE_URL_ENV = "SUPABASE_URL"
SUPABASE_JWT_ISSUER_ENV = "SUPABASE_JWT_ISSUER"
SUPABASE_JWT_AUDIENCE_ENV = "SUPABASE_JWT_AUDIENCE"
DEFAULT_SUPABASE_AUDIENCE = "authenticated"
ALLOWED_JWT_ALGORITHMS = frozenset({"RS256", "ES256"})
MAX_BEARER_TOKEN_LENGTH = 16_384
SUPABASE_BEARER_SCHEME = HTTPBearer(
    auto_error=False,
    scheme_name="SupabaseBearer",
    description="Supabase Auth access token",
    bearerFormat="JWT",
)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    """The small, verified identity surface needed by the backend."""

    user_id: UUID
    token_subject: str
    issuer: str
    token_issued_at: datetime | None = None


SigningKeyResolver = Callable[[str], Any]


def _normalized_issuer(value: str) -> str:
    candidate = value.strip().rstrip("/")
    parsed = urlsplit(candidate)
    local_http = parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}
    if (
        parsed.scheme not in {"http", "https"}
        or (parsed.scheme != "https" and not local_http)
        or not parsed.netloc
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or not parsed.path.endswith("/auth/v1")
    ):
        raise ValueError("Supabase JWT issuer is invalid")
    return candidate


def _issuer_from_environment(environ: Mapping[str, str]) -> str:
    configured = environ.get(SUPABASE_JWT_ISSUER_ENV, "").strip()
    if configured:
        return _normalized_issuer(configured)
    project_url = environ.get(SUPABASE_URL_ENV, "").strip().rstrip("/")
    if not project_url:
        raise ValueError("Supabase JWT verification is not configured")
    return _normalized_issuer(f"{project_url}/auth/v1")


class SupabaseJWTVerifier:
    """Verify Supabase access tokens using the project's asymmetric JWKS.

    Production construction uses the Auth JWKS endpoint with a bounded timeout
    and five-minute cache. Tests inject an in-memory public-key resolver and do
    not need live Supabase credentials or committed signing secrets.
    """

    def __init__(
        self,
        *,
        issuer: str,
        audience: str = DEFAULT_SUPABASE_AUDIENCE,
        signing_key_resolver: SigningKeyResolver | None = None,
    ) -> None:
        self.issuer = _normalized_issuer(issuer)
        self.audience = audience.strip()
        if not self.audience:
            raise ValueError("Supabase JWT audience is invalid")
        if signing_key_resolver is None:
            client = jwt.PyJWKClient(
                f"{self.issuer}/.well-known/jwks.json",
                cache_jwk_set=True,
                lifespan=300,
                timeout=5,
            )
            signing_key_resolver = lambda token: client.get_signing_key_from_jwt(token).key
        self._signing_key_resolver = signing_key_resolver

    @classmethod
    def from_environment(
        cls,
        environ: Mapping[str, str] | None = None,
    ) -> "SupabaseJWTVerifier":
        values = environ if environ is not None else os.environ
        issuer = _issuer_from_environment(values)
        audience = values.get(SUPABASE_JWT_AUDIENCE_ENV, DEFAULT_SUPABASE_AUDIENCE)
        return cls(issuer=issuer, audience=audience)

    def verify(self, token: str) -> AuthenticatedPrincipal:
        if (
            not token
            or len(token) > MAX_BEARER_TOKEN_LENGTH
            or token.count(".") != 2
            or any(character.isspace() for character in token)
        ):
            raise VNextError.authentication_required()
        try:
            header = jwt.get_unverified_header(token)
            algorithm = header.get("alg")
            key_id = header.get("kid")
            if algorithm not in ALLOWED_JWT_ALGORITHMS or not isinstance(key_id, str) or not key_id:
                raise ValueError("unsupported JWT header")
            signing_key = self._signing_key_resolver(token)
            claims = jwt.decode(
                token,
                signing_key,
                algorithms=[algorithm],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["aud", "exp", "iss", "sub"]},
            )
            if claims.get("role") == "service_role":
                raise ValueError("privileged JWT is not a request principal")
            token_subject = str(claims["sub"])
            user_id = UUID(token_subject)
            issued_at = claims.get("iat")
            token_issued_at = (
                datetime.fromtimestamp(int(issued_at), tz=timezone.utc)
                if issued_at is not None
                else None
            )
        except VNextError:
            raise
        except Exception:
            # Signature, lifetime, issuer/audience, JWKS availability, claim
            # shape, and UUID errors intentionally share one client response.
            raise VNextError.authentication_required() from None
        return AuthenticatedPrincipal(
            user_id=user_id,
            token_subject=token_subject,
            issuer=self.issuer,
            token_issued_at=token_issued_at,
        )


def bearer_token(request: Request) -> str:
    values = request.headers.getlist("authorization")
    if len(values) != 1:
        raise VNextError.authentication_required()
    authorization = values[0]
    if authorization != authorization.strip():
        raise VNextError.authentication_required()
    scheme, separator, token = authorization.partition(" ")
    if separator != " " or scheme.lower() != "bearer" or not token or " " in token or "\t" in token:
        raise VNextError.authentication_required()
    return token


@lru_cache(maxsize=1)
def get_supabase_jwt_verifier() -> SupabaseJWTVerifier:
    try:
        return SupabaseJWTVerifier.from_environment()
    except Exception:
        # Missing or malformed configuration is an unavailable verification
        # boundary, never a reason to synthesize an authenticated principal.
        raise VNextError.authentication_required() from None


def require_authenticated_principal(
    request: Request,
    _credentials: HTTPAuthorizationCredentials | None = Security(SUPABASE_BEARER_SCHEME),
    verifier: SupabaseJWTVerifier = Depends(get_supabase_jwt_verifier),
) -> AuthenticatedPrincipal:
    principal = verifier.verify(bearer_token(request))
    request.state.authenticated_principal = principal
    return principal
