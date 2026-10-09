"""Byte-bounded ASGI bodies and server-selected capability/peer admission."""
from __future__ import annotations

import asyncio
import threading
from starlette.requests import Request
from starlette.responses import JSONResponse

from services import anti_abuse
from services.observability import normalize_correlation_id
from services.security import security_headers


BODY_SLOTS = threading.BoundedSemaphore(16)


POST_CAPABILITIES = {
    "/map/search": "geocoding", "/map/insight": "metadata", "/map/nearby": "places",
    "/location/resolve": "geocoding", "/location/insight": "location",
    "/commute/address-lookup": "geocoding", "/commute/nearest": "metadata", "/commute/route": "routes",
    "/terrain/satellite-reference": "satellite", "/terrain-risk/analyze": "terrain",
    "/valuation/estimate": "valuation", "/valuation/trend": "trend", "/valuation/property-search": "finder",
    "/parcel-geometry/upload": "parcel", "/parcel-geometry/consistency": "parcel", "/parcel-geometry/spatial-analyze": "parcel",
}


def capability(scope):
    path = scope["path"].rstrip("/")
    method = scope["method"]
    if method == "POST":
        if path in POST_CAPABILITIES:
            return POST_CAPABILITIES[path]
        if path.startswith("/market-insights"):
            if path == "/market-insights/refresh" or path.startswith("/market-insights/coverage/"):
                return "market_ops"
            return "market"
        if path.startswith("/v1/") and any(piece in path for piece in ("resolutions", "planning", "observations")):
            return "identity"
    if method == "GET" and path.startswith(("/roads/", "/demographics/", "/market-insights")):
        return "metadata"
    return None


class AbuseMiddleware:
    def __init__(self, app, *, controls=None):
        self.app = app
        self.controls = controls

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        controls = self.controls or anti_abuse.CONTROLS
        response_started = False
        original_send = send
        async def captured_send(message):
            nonlocal response_started
            if message["type"] == "http.response.start":
                response_started = True
            await original_send(message)
        send = captured_send
        try:
            name = capability(scope)
            if name:
                client = scope.get("client")
                # Never read XFF, Forwarded, X-Real-IP, tokens or query strings.
                peer = str(client[0])[:256] if client else "unknown"
                controls.admit(name, peer)
            limit = 11_000_000 if scope["path"].rstrip("/") == "/parcel-geometry/upload" else 1_000_000
            lengths = [value for key, value in scope["headers"] if key.lower() == b"content-length"]
            if lengths and (len(lengths) != 1 or len(lengths[0]) > 20 or not lengths[0].isdigit()):
                return await self.respond(scope, receive, send, 400, "invalid_body", "Invalid request body.")
            if lengths and int(lengths[0]) > limit:
                return await self.respond(scope, receive, send, 413, "body_too_large", "Request body is too large.")
            if len(scope.get("query_string", b"")) > 8192:
                return await self.respond(scope, receive, send, 414, "query_too_large", "Request query is too large.")
            if scope["method"] in {"GET", "HEAD", "OPTIONS"}:
                return await self.app(scope, receive, send)
            if not BODY_SLOTS.acquire(blocking=False):
                return await self.respond(scope, receive, send, 503, "capacity_exhausted", "Request capacity is temporarily unavailable.", {"Retry-After": "1"})
            try:
                return await self.with_body(scope, receive, send, limit)
            finally:
                BODY_SLOTS.release()
        except anti_abuse.AbuseRejected as error:
            if response_started:
                raise
            await self.respond(scope, receive, send, error.status_code, error.detail["reason_code"], error.detail["message"], error.headers)

    async def with_body(self, scope, receive, send, limit):
        try:
            # Prebuffer at most limit bytes before any framework parser sees them.
            # A deadline also bounds slow or never-ending chunked input.
            body = bytearray()
            async with asyncio.timeout(15):
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > limit:
                        return await self.respond(scope, receive, send, 413, "body_too_large", "Request body is too large.")
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
            replayed = False
            async def replay():
                nonlocal replayed
                if not replayed:
                    replayed = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await receive()
        except TimeoutError:
            return await self.respond(scope, receive, send, 408, "body_timeout", "Request body timed out.")
        await self.app(scope, replay, send)

    @staticmethod
    async def respond(scope, receive, send, status, reason, message, headers=None):
        request = Request(scope)
        correlation = getattr(request.state, "correlation_id", normalize_correlation_id(request.headers.get("X-Correlation-ID")))
        if scope["path"].startswith("/v1"):
            code = "rate_limited" if status == 429 else "maintenance" if status == 503 else "validation_failed"
            content = {"error": {"code": code, "message": message, "request_id": correlation, "retryable": False, "details": {"reason_code": reason}}}
        else:
            content = {"detail": {"reason_code": reason, "message": message}}
        response = JSONResponse(status_code=status, content=content, headers=headers)
        response.headers["X-Correlation-ID"] = correlation
        for key, value in security_headers(private=True).items():
            response.headers.setdefault(key, value)
        await response(scope, receive, send)
