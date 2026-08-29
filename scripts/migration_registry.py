"""Deterministic registry for immutable historical PostgreSQL migrations.

The numeric prefix is not a unique historical identifier: two different
``002`` files were operated before a single runner existed, and migration
``011`` has a separate Compact GREEN runbook.  The registry therefore gives
each file a unique logical ID and total order without renaming or rewriting
history.  Execution policy remains explicit so the production runner never
replays a separately operated migration or falsely records it as applied.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
MIGRATION_DIRECTORY = ROOT / "database" / "migrations"
REGISTRY_PATH = ROOT / "database" / "migration_registry.json"

_FILENAME = re.compile(r"^(?P<sequence>\d{3})_[a-z0-9_]+\.sql$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_EXECUTION_POLICIES = frozenset(
    {"legacy_operator", "production_runner", "compact_green_operator"}
)


class MigrationRegistryError(RuntimeError):
    """A bounded registry validation failure safe to surface to operators."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class MigrationRegistration:
    registry_order: int
    logical_id: str
    sequence: int
    filename: str
    execution_policy: str
    sha256: str
    path: Path


def checksum(path: Path) -> str:
    # Git stores these text migrations with LF line endings, while a Windows
    # checkout may materialize CRLF. Hash the canonical Git text so registry
    # and ledger checksums remain stable across operator platforms.
    canonical_bytes = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(canonical_bytes).hexdigest()


def _registration(
    raw: Any,
    *,
    migration_directory: Path,
) -> MigrationRegistration:
    if not isinstance(raw, dict):
        raise MigrationRegistryError("migration_registry_entry_invalid")
    try:
        registry_order = int(raw["registry_order"])
        logical_id = str(raw["logical_id"])
        sequence = int(raw["sequence"])
        filename = str(raw["filename"])
        execution_policy = str(raw["execution_policy"])
        frozen_checksum = str(raw["sha256"])
    except (KeyError, TypeError, ValueError) as exc:
        raise MigrationRegistryError("migration_registry_entry_invalid") from exc

    match = _FILENAME.fullmatch(filename)
    if (
        registry_order < 1
        or not logical_id
        or match is None
        or int(match.group("sequence")) != sequence
        or execution_policy not in _EXECUTION_POLICIES
        or not _SHA256.fullmatch(frozen_checksum)
    ):
        raise MigrationRegistryError("migration_registry_entry_invalid")

    return MigrationRegistration(
        registry_order=registry_order,
        logical_id=logical_id,
        sequence=sequence,
        filename=filename,
        execution_policy=execution_policy,
        sha256=frozen_checksum,
        path=migration_directory / filename,
    )


def load_registry(
    registry_path: Path = REGISTRY_PATH,
    migration_directory: Path = MIGRATION_DIRECTORY,
    *,
    verify_files: bool = True,
) -> tuple[MigrationRegistration, ...]:
    try:
        payload = json.loads(registry_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MigrationRegistryError("migration_registry_unavailable") from exc
    if not isinstance(payload, dict) or payload.get("registry_version") != 1:
        raise MigrationRegistryError("migration_registry_version_invalid")
    raw_migrations = payload.get("migrations")
    if not isinstance(raw_migrations, list) or not raw_migrations:
        raise MigrationRegistryError("migration_registry_empty")

    registrations = tuple(
        _registration(raw, migration_directory=migration_directory)
        for raw in raw_migrations
    )
    logical_ids = [item.logical_id for item in registrations]
    filenames = [item.filename for item in registrations]
    registry_orders = [item.registry_order for item in registrations]
    if len(logical_ids) != len(set(logical_ids)):
        raise MigrationRegistryError("migration_logical_registration_duplicate")
    if len(filenames) != len(set(filenames)):
        raise MigrationRegistryError("migration_file_registration_duplicate")
    if len(registry_orders) != len(set(registry_orders)):
        raise MigrationRegistryError("migration_registry_order_duplicate")

    ordered = tuple(sorted(registrations, key=lambda item: item.registry_order))
    if [item.registry_order for item in ordered] != list(range(1, len(ordered) + 1)):
        raise MigrationRegistryError("migration_registry_order_unstable")

    if verify_files:
        registered_files = {item.filename for item in ordered}
        actual_files = {path.name for path in migration_directory.glob("*.sql")}
        if registered_files != actual_files:
            raise MigrationRegistryError("migration_registry_file_set_mismatch")
        for item in ordered:
            if not item.path.is_file():
                raise MigrationRegistryError("migration_file_missing")
            if checksum(item.path) != item.sha256:
                raise MigrationRegistryError("migration_checksum_drift")
    return ordered


def production_migrations(
    registrations: tuple[MigrationRegistration, ...] | None = None,
) -> tuple[Path, ...]:
    selected = registrations if registrations is not None else load_registry()
    return tuple(
        item.path for item in selected if item.execution_policy == "production_runner"
    )


def next_safe_sequence(
    registrations: tuple[MigrationRegistration, ...] | None = None,
) -> int:
    selected = registrations if registrations is not None else load_registry()
    allocated = {item.sequence for item in selected}
    candidate = max(allocated) + 1
    if candidate in allocated or candidate > 999:
        raise MigrationRegistryError("migration_sequence_allocation_unavailable")
    return candidate


def registry_summary() -> dict[str, object]:
    registrations = load_registry()
    managed_count = sum(
        item.execution_policy == "production_runner" for item in registrations
    )
    return {
        "registry_count": len(registrations),
        "managed_migration_count": managed_count,
        "next_migration_sequence": f"{next_safe_sequence(registrations):03d}",
    }
