"""Personal Saved Cases. No providers, workspace role mapping, or DB fallback.

Repository transactions MUST serialize ACL checks and CAS writes for each case,
commit activity with the mutation, and roll back on any exception. A later SQL
adapter must run under DatabasePrincipalContext and implement this same protocol.
"""
from __future__ import annotations

from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from typing import ContextManager, Literal, Protocol
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from services.vnext.auth import AuthenticatedPrincipal
from services.vnext.errors import ErrorCode, VNextError

MAX_IMPORT_BYTES = 262_144
MAX_COMMAND_RECEIPTS = 2048
COMMAND_REPLAY_WINDOW = timedelta(hours=24)
IDEMPOTENCY_PATTERN = r"^[A-Za-z0-9._:-]{16,128}$"
MemberRole = Literal["editor", "viewer"]
CaseRole = Literal["owner", "editor", "viewer"]
Scope = Literal["owned", "shared"]
_CREDENTIAL_KEYS = frozenset({"token", "idtoken", "privatekey", "secretkey", "accesstoken", "refreshtoken", "authorization", "password", "apikey", "servicekey", "servicerolekey", "secret", "clientsecret", "cookie", "session", "credentials", "bearertoken", "jwt"})
_CREDENTIAL_VALUE = re.compile(r"(?i)\bbearer\s+\S+|\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+|\bsb_(?:secret|publishable)_[A-Za-z0-9_-]+|[?&](?:key|api_key|token|access_token|signature)=[^&#\s]+|https?://[^/\s]+:[^/@\s]+@")


def validate_safe_json(value: object, depth: int = 0) -> object:
    """Reject unsafe imports as a whole. Never strip or rewrite evidence/notes."""
    if depth > 24:
        raise ValueError("JSON nesting exceeds limit")
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str) or len(key) > 200:
                raise ValueError("Invalid JSON key")
            normalized = re.sub(r"[^a-z]", "", key.lower())
            if (normalized in _CREDENTIAL_KEYS
                    or normalized.endswith("token") and normalized not in {"identitytoken", "evidencetoken"}
                    or normalized.endswith(("apikey", "secretkey", "privatekey", "password"))):
                raise ValueError("Credential fields cannot be stored")
            validate_safe_json(child, depth + 1)
    elif isinstance(value, list):
        if len(value) > 2000:
            raise ValueError("JSON list exceeds limit")
        for child in value:
            validate_safe_json(child, depth + 1)
    elif isinstance(value, str):
        if _CREDENTIAL_VALUE.search(value):
            raise ValueError("Credential values cannot be stored")
    elif value is not None and type(value) not in (bool, int, float):
        raise ValueError("Not JSON")
    elif isinstance(value, float) and not math.isfinite(value):
        raise ValueError("Non-finite JSON")
    return value


class StrictRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CreateCase(StrictRequest):
    snapshot: dict
    user_authored: dict = Field(default_factory=dict)
    import_key: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")
    explicit_consent: StrictBool

    @model_validator(mode="after")
    def validate_import(self):
        if self.explicit_consent is not True:
            raise ValueError("Explicit consent required")
        snapshot = self.snapshot
        if (type(snapshot.get("version")) is not int or snapshot.get("version") != 1 or snapshot.get("workflowMode") != "buying_wizard"
                or not isinstance(snapshot.get("id"), str) or not 1 <= len(snapshot["id"]) <= 160
                or not isinstance(snapshot.get("title"), str) or not 1 <= len(snapshot["title"]) <= 500
                or not isinstance(snapshot.get("data"), dict) or not isinstance(snapshot["data"].get("inputs"), dict)
                or not isinstance(snapshot.get("inputSummary"), dict)):
            raise ValueError("Invalid saved snapshot")
        for key in ("createdAt", "updatedAt"):
            raw = snapshot.get(key)
            if not isinstance(raw, str) or len(raw) > 40 or datetime.fromisoformat(raw.replace("Z", "+00:00")).tzinfo is None:
                raise ValueError("Timestamp with timezone required")
        validate_safe_json([snapshot, self.user_authored, self.import_key])
        if len(json.dumps([snapshot, self.user_authored], ensure_ascii=False, allow_nan=False).encode()) > MAX_IMPORT_BYTES:
            raise ValueError("Import exceeds limit")
        return self


class VersionedRequest(StrictRequest):
    expected_revision: int = Field(strict=True, ge=1)


class MetadataUpdate(VersionedRequest):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    notes: str | None = Field(default=None, max_length=8000)

    @model_validator(mode="after")
    def bounded(self):
        if not self.model_fields_set.intersection({"title", "notes"}):
            raise ValueError("No changes")
        if any(getattr(self, key) is None for key in self.model_fields_set.intersection({"title", "notes"})):
            raise ValueError("Null metadata not supported")
        validate_safe_json([self.title, self.notes])
        return self


class MembershipUpdate(VersionedRequest):
    member_id: UUID
    role: MemberRole | None  # null revokes; owner is never a membership role


class MonitoringUpdate(VersionedRequest):
    cadence: Literal["off", "daily", "weekly"]
    refresh_policy: Literal["manual_only"] = "manual_only"


class MonitoringPreferences(BaseModel):
    cadence: Literal["off", "daily", "weekly"] = "off"
    refresh_policy: Literal["manual_only"] = "manual_only"
    execution_status: Literal["not_configured"] = "not_configured"
    delivery_status: Literal["not_configured"] = "not_configured"


class Activity(BaseModel):
    revision: int
    actor_id: UUID
    kind: Literal["case_imported", "metadata_updated", "membership_updated", "monitoring_updated"]
    occurred_at: datetime
    # No evidence, note text, tokens, email, or provider payloads in history.


@dataclass
class CaseRecord:
    id: UUID
    owner_id: UUID
    import_key: str
    import_digest: str
    snapshot: dict
    user_authored: dict
    title: str
    notes: str
    created_at: datetime
    updated_at: datetime
    revision: int = 1
    members: dict[UUID, MemberRole] = field(default_factory=dict)
    monitoring: MonitoringPreferences = field(default_factory=MonitoringPreferences)


class CaseView(BaseModel):
    id: UUID
    owner_id: UUID
    role: CaseRole
    revision: int
    title: str
    notes: str
    created_at: datetime
    updated_at: datetime
    snapshot: dict
    user_authored: dict
    members: dict[UUID, MemberRole]
    monitoring: MonitoringPreferences
    sharing: Literal["private", "members_only"]


class CaseSummary(BaseModel):
    id: UUID
    role: CaseRole
    revision: int
    title: str
    updated_at: datetime
    sharing: Literal["private", "members_only"]


@dataclass(frozen=True)
class CommandReceipt:
    actor_id: UUID
    method: str
    route: str
    key_hash: str
    request_fingerprint: str
    case_id: UUID
    revision: int
    created_at: datetime
    expires_at: datetime


class CaseTransaction(Protocol):
    # Serialize actor/key admission before case writes. Store only committed
    # references, never raw keys/bodies; retain >=24h, cap live rows per actor,
    # prune expired rows in bounded batches, fail closed at capacity.
    def find_command(self, actor_id: UUID, method: str, route: str, key_hash: str, now: datetime) -> CommandReceipt | None: ...
    def append_command(self, receipt: CommandReceipt) -> None: ...
    def get(self, case_id: UUID) -> CaseRecord | None: ...
    def find_import(self, owner_id: UUID, import_key: str) -> CaseRecord | None: ...
    def list_accessible(self, user_id: UUID, *, scope: Scope, offset: int, limit: int) -> list[CaseRecord]: ...
    def insert(self, value: CaseRecord) -> None: ...
    def replace(self, value: CaseRecord, *, expected_revision: int) -> bool: ...
    def append_activity(self, case_id: UUID, event: Activity) -> None: ...
    def list_activity(self, case_id: UUID, *, offset: int, limit: int) -> list[Activity]: ...


class CaseRepository(Protocol):
    def transaction(self, principal: AuthenticatedPrincipal) -> ContextManager[CaseTransaction]: ...


def persistence_pending() -> VNextError:
    return VNextError(ErrorCode.MAINTENANCE, details={"reason_code": "persistence_pending"})


class UnavailableCaseRepository:
    @contextmanager
    def transaction(self, principal):
        raise persistence_pending()
        yield  # pragma: no cover - makes this a contextmanager, no memory fallback


class CaseService:
    def __init__(self, repository: CaseRepository):
        self.repository = repository

    @contextmanager
    def _transaction(self, principal):
        try:
            with self.repository.transaction(principal) as transaction:
                yield transaction
        except VNextError:
            raise
        except Exception:
            raise VNextError(ErrorCode.MAINTENANCE) from None

    @staticmethod
    def _role(principal, row):
        if row is None:
            raise VNextError.not_found()
        if row.owner_id == principal.user_id:
            return "owner"
        role = row.members.get(principal.user_id)
        if role not in {"editor", "viewer"}:
            raise VNextError.not_found()
        return role

    def _view(self, principal, row):
        role = self._role(principal, row)
        return CaseView(id=row.id, owner_id=row.owner_id, role=role, revision=row.revision,
                        title=row.title, notes=row.notes, created_at=row.created_at, updated_at=row.updated_at,
                        snapshot=deepcopy(row.snapshot), user_authored=deepcopy(row.user_authored),
                        members=deepcopy(row.members) if role == "owner" else {},
                        monitoring=row.monitoring.model_copy(deep=True), sharing="members_only" if row.members else "private")

    @staticmethod
    def _command_identity(request, key):
        if not isinstance(key, str) or re.fullmatch(IDEMPOTENCY_PATTERN, key) is None:
            raise VNextError.validation_failed()
        canonical = json.dumps(request.model_dump(mode="json"), sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        return hashlib.sha256(key.encode()).hexdigest(), hashlib.sha256(canonical.encode()).hexdigest()

    def _replay(self, principal, transaction, receipt, fingerprint):
        row = transaction.get(receipt.case_id)
        self._role(principal, row)  # Never let a receipt bypass current access.
        if receipt.request_fingerprint != fingerprint:
            raise VNextError.idempotency_conflict()
        if row.id != receipt.case_id or row.revision < receipt.revision:
            raise VNextError(ErrorCode.MAINTENANCE)
        # As with existing parcel-set commands, replay the resource reference
        # using its current authorized projection, never old ACLs/private bodies.
        return self._view(principal, row)

    @staticmethod
    def _receipt(principal, method, route, key_hash, fingerprint, result, now):
        return CommandReceipt(principal.user_id, method, route, key_hash, fingerprint,
                              result.id, result.revision, now, now + COMMAND_REPLAY_WINDOW)

    def create(self, principal, request: CreateCase, *, idempotency_key: str) -> CaseView:
        key_hash, fingerprint = self._command_identity(request, idempotency_key)
        digest = hashlib.sha256(json.dumps([request.snapshot, request.user_authored], sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        with self._transaction(principal) as transaction:
            now = datetime.now(timezone.utc)
            receipt = transaction.find_command(principal.user_id, "POST", "/v1/saved-cases", key_hash, now)
            previous = None if receipt else transaction.find_import(principal.user_id, request.import_key)
            if receipt:
                result = self._replay(principal, transaction, receipt, fingerprint)
            elif previous:
                if previous.owner_id != principal.user_id:
                    raise VNextError.permission_denied()
                self._role(principal, previous)
                if previous.import_digest != digest:
                    raise VNextError.idempotency_conflict()
                result = self._view(principal, previous)
            else:
                row = CaseRecord(uuid4(), principal.user_id, request.import_key, digest,
                                 deepcopy(request.snapshot), deepcopy(request.user_authored), request.snapshot["title"], "", now, now)
                transaction.insert(row)
                transaction.append_activity(row.id, Activity(revision=1, actor_id=principal.user_id, kind="case_imported", occurred_at=now))
                result = self._view(principal, row)
            if not receipt:
                transaction.append_command(self._receipt(principal, "POST", "/v1/saved-cases", key_hash, fingerprint, result, now))
        return result  # only acknowledge after commit

    def list(self, principal, *, scope: Scope, offset: int, limit: int) -> list[CaseSummary]:
        if scope not in {"owned", "shared"} or not 0 <= offset <= 10000 or not 1 <= limit <= 100:
            raise VNextError.validation_failed()
        with self._transaction(principal) as transaction:
            rows = transaction.list_accessible(principal.user_id, scope=scope, offset=offset, limit=limit)
            result = []
            for row in rows:
                role = self._role(principal, row)
                if scope == "owned" and role != "owner" or scope == "shared" and role == "owner":
                    raise VNextError.permission_denied()
                result.append(CaseSummary(id=row.id, role=role, revision=row.revision, title=row.title, updated_at=row.updated_at,
                                          sharing="members_only" if row.members else "private"))
        return result

    def open(self, principal, case_id):
        with self._transaction(principal) as transaction:
            result = self._view(principal, transaction.get(case_id))
        return result

    def activity(self, principal, case_id, *, offset, limit):
        if not 0 <= offset <= 10000 or not 1 <= limit <= 100:
            raise VNextError.validation_failed()
        with self._transaction(principal) as transaction:
            row = transaction.get(case_id)
            self._role(principal, row)
            result = deepcopy(transaction.list_activity(case_id, offset=offset, limit=limit))
        return result

    def _update(self, principal, case_id, request, *, idempotency_key, kind, owner_only, mutate):
        key_hash, fingerprint = self._command_identity(request, idempotency_key)
        method, suffix = {"metadata_updated": ("PATCH", "metadata"), "membership_updated": ("PUT", "membership"), "monitoring_updated": ("PUT", "monitoring")}[kind]
        route = f"/v1/saved-cases/{case_id}/{suffix}"
        with self._transaction(principal) as transaction:
            now = datetime.now(timezone.utc)
            receipt = transaction.find_command(principal.user_id, method, route, key_hash, now)
            row = transaction.get(case_id)
            role = self._role(principal, row)
            if role == "viewer" or owner_only and role != "owner":
                raise VNextError.permission_denied()
            if receipt:
                if receipt.case_id != case_id:
                    raise VNextError(ErrorCode.MAINTENANCE)
                result = self._replay(principal, transaction, receipt, fingerprint)
            else:
                result = self._apply_update(transaction, principal, row, request, mutate, kind)
                transaction.append_command(self._receipt(principal, method, route, key_hash, fingerprint, result, now))
        return result

    def _apply_update(self, transaction, principal, row, request, mutate, kind):
        if row.revision != request.expected_revision:
            raise VNextError.version_conflict()
        mutate(row)
        row.revision += 1
        row.updated_at = datetime.now(timezone.utc)
        if not transaction.replace(row, expected_revision=request.expected_revision):
            raise VNextError.version_conflict()
        transaction.append_activity(row.id, Activity(revision=row.revision, actor_id=principal.user_id, kind=kind, occurred_at=row.updated_at))
        result = self._view(principal, row)
        return result

    def metadata(self, principal, case_id, request: MetadataUpdate, *, idempotency_key: str):
        def mutate(row):
            for key in request.model_fields_set & {"title", "notes"}:
                setattr(row, key, getattr(request, key))
        return self._update(principal, case_id, request, idempotency_key=idempotency_key, kind="metadata_updated", owner_only=False, mutate=mutate)

    def membership(self, principal, case_id, request: MembershipUpdate, *, idempotency_key: str):
        def mutate(row):
            if request.member_id == row.owner_id:
                raise VNextError.permission_denied()
            if request.role is None:
                row.members.pop(request.member_id, None)
            else:
                if request.member_id not in row.members and len(row.members) >= 50:
                    raise VNextError.validation_failed()
                row.members[request.member_id] = request.role
        return self._update(principal, case_id, request, idempotency_key=idempotency_key, kind="membership_updated", owner_only=True, mutate=mutate)

    def monitoring(self, principal, case_id, request: MonitoringUpdate, *, idempotency_key: str):
        def mutate(row):
            row.monitoring = MonitoringPreferences(cadence=request.cadence)
        return self._update(principal, case_id, request, idempotency_key=idempotency_key, kind="monitoring_updated", owner_only=True, mutate=mutate)


_SERVICE = CaseService(UnavailableCaseRepository())


def get_case_service() -> CaseService:
    from services.professor_userdb import enabled, get_repository, PostgresCaseRepository, PrivateCaseService
    if enabled():
        return PrivateCaseService(PostgresCaseRepository(get_repository()))
    return _SERVICE
