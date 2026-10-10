"""Exact Host and Origin admission; forwarding headers confer no authority."""
from __future__ import annotations

import os
from urllib.parse import urlsplit

from backend.api.abuse_middleware import AbuseMiddleware
from services.production_guardrails import allowed_hosts, production_like
from services.security import safe_origin


class IngressMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or not production_like(os.environ):
            return await self.app(scope, receive, send)
        async def reject(status, reason):
            await AbuseMiddleware.respond(scope, receive, send, status, reason, "Request ingress is not allowed.")
        try:
            hosts = allowed_hosts(os.environ)
        except RuntimeError:
            return await reject(503, "guard_unavailable")
        header_hosts = [value for key, value in scope["headers"] if key.lower() == b"host"]
        if len(header_hosts) != 1:
            return await reject(400, "invalid_host")
        try:
            raw = header_hosts[0].decode("ascii")
            parsed = urlsplit("https://" + raw)
            port = parsed.port
            valid = (parsed.hostname in hosts and not parsed.username and not parsed.password
                     and not parsed.path and not parsed.query and not parsed.fragment
                     and not any(char.isspace() for char in raw) and "\\" not in raw
                     and (port is None or 1 <= port <= 65535))
        except (ValueError, UnicodeError):
            valid = False
        if not valid:
            return await reject(400, "invalid_host")
        origins = [value for key, value in scope["headers"] if key.lower() == b"origin"]
        if origins:
            raw = origins[0].decode("latin-1")
            origin = safe_origin(raw)
            approved = {safe_origin(item.strip()) for item in os.getenv("CORS_ALLOWED_ORIGINS", "").split(",")}
            if len(origins) != 1 or not origin or origin not in approved:
                return await reject(403, "invalid_origin")
        if scope["path"].rstrip("/") in {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}:
            return await reject(404, "surface_disabled")
        # No Origin is valid for machines; authentication still belongs to each
        # protected route. Host/CORS are not proof of backend origin protection.
        await self.app(scope, receive, send)
