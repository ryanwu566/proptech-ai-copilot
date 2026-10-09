"""Production contracts; local admission never becomes a global cost ceiling."""
from __future__ import annotations

import os
import re
from collections.abc import Mapping
from typing import Protocol

from services.anti_abuse import POLICIES
from services.security import is_serverless_runtime

_HOST = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*\Z")


class SharedAdmission(Protocol):
    """Future atomic shared control boundary, NOT an enabled implementation.

    Reserve before dispatch across workers/revisions, using a server-selected
    capability and fixed account namespace. Return allowed/retry seconds.
    Store failures must reject with 503; failed provider calls consume quota;
    no fallback to a local counter. Requires reviewed atomic transactions,
    bounded deadlines/key retention, least-privilege role, clock and recovery
    tests. Provider quotas remain separate even when this is implemented.
    """
    def reserve(self, *, namespace: str, capability: str, units: int, limit: int,
                window_seconds: int) -> tuple[bool, int]: ...


def production_like(values: Mapping[str, str]) -> bool:
    return values.get("APP_ENV", "development").strip().lower() in {"production", "preview"} or is_serverless_runtime(dict(values))


def allowed_hosts(values: Mapping[str, str]) -> frozenset[str]:
    raw = values.get("API_ALLOWED_HOSTS", "")
    hosts = [item.strip().lower() for item in raw.split(",")]
    if not 1 <= len(hosts) <= 16 or any(len(host) > 253 or not _HOST.fullmatch(host) for host in hosts):
        raise RuntimeError("Invalid production guardrail configuration.")
    return frozenset(hosts)


def assert_guardrail_configuration(environ: Mapping[str, str] | None = None) -> None:
    values = os.environ if environ is None else environ
    # No distributed implementation is registered. Explicit requests cannot
    # silently fall back even in development.
    if values.get("ANTI_ABUSE_ENFORCEMENT_MODE", "local_only") != "local_only":
        raise RuntimeError("Unavailable production guardrail enforcement mode.")
    if not production_like(values):
        return
    allowed_hosts(values)
    for name, policy in POLICIES.items():
        limits = {"REQUESTS": (policy.requests, False), "CONCURRENCY": (policy.concurrency, False),
                  "OPERATIONS": (policy.operations, False), "WINDOW_SECONDS": (policy.window, True),
                  "OPERATION_WINDOW_SECONDS": (policy.operation_window, True)}
        for suffix, (bound, minimum) in limits.items():
            raw = values.get(f"ANTI_ABUSE_{name.upper()}_{suffix}", "").strip()
            if not raw:
                continue
            try:
                value = int(raw)
            except ValueError:
                raise RuntimeError("Invalid production guardrail cost configuration.") from None
            maximum = 3600 if minimum else bound
            if value < 1 or value > maximum:
                raise RuntimeError("Invalid production guardrail cost configuration.")
            if minimum and value < bound:
                raise RuntimeError("Invalid production guardrail cost configuration.")
