"""Transactional conformance adapter. Never used by production wiring."""
from contextlib import contextmanager
from copy import deepcopy
from threading import RLock

from services.vnext import durable_cases


class MemoryCaseRepository:
    def __init__(self):
        self.rows = {}
        self.events = {}
        self.commands = {}
        self.lock = RLock()

    @contextmanager
    def transaction(self, principal):
        with self.lock:
            original = deepcopy(self.rows)
            original_events = deepcopy(self.events)
            original_commands = deepcopy(self.commands)
            try:
                yield self
            except BaseException:
                self.rows = original
                self.events = original_events
                self.commands = original_commands
                raise

    def find_command(self, actor_id, method, route, key_hash, now):
        receipt = self.commands.get((actor_id, method, route, key_hash))
        return receipt if receipt and receipt.expires_at > now else None

    def append_command(self, receipt):
        # Actor admission is serialized by transaction; never evict live receipts.
        expired = [key for key, row in self.commands.items() if row.actor_id == receipt.actor_id and row.expires_at <= receipt.created_at][:100]
        for key in expired:
            del self.commands[key]
        scope = (receipt.actor_id, receipt.method, receipt.route, receipt.key_hash)
        if scope in self.commands or sum(row.actor_id == receipt.actor_id for row in self.commands.values()) >= durable_cases.MAX_COMMAND_RECEIPTS:
            raise durable_cases.VNextError(durable_cases.ErrorCode.MAINTENANCE)
        self.commands[scope] = receipt

    def get(self, case_id):
        return deepcopy(self.rows.get(case_id))

    def find_import(self, owner_id, import_key):
        return next((deepcopy(r) for r in self.rows.values() if r.owner_id == owner_id and r.import_key == import_key), None)

    def list_accessible(self, user_id, *, scope, offset, limit):
        rows = [r for r in self.rows.values() if (r.owner_id == user_id if scope == "owned" else user_id in r.members)]
        return deepcopy(sorted(rows, key=lambda r: str(r.id))[offset:offset + limit])

    def insert(self, value):
        assert value.id not in self.rows
        assert self.find_import(value.owner_id, value.import_key) is None
        self.rows[value.id] = deepcopy(value)

    def replace(self, value, *, expected_revision):
        if self.rows[value.id].revision != expected_revision:
            return False
        self.rows[value.id] = deepcopy(value)
        return True

    def append_activity(self, case_id, event):
        events = self.events.setdefault(case_id, [])
        assert not any(e.revision == event.revision for e in events)
        events.append(deepcopy(event))

    def list_activity(self, case_id, *, offset, limit):
        return deepcopy(list(reversed(self.events.get(case_id, [])))[offset:offset + limit])


def snapshot():
    return {"id": "case-local", "title": "Original", "createdAt": "2026-10-01T00:00:00Z",
            "updatedAt": "2026-10-02T00:00:00Z", "version": 1, "workflowMode": "buying_wizard",
            "activeWizardStep": "risk", "progress": 30, "inputSummary": {"city": "臺中市"},
            "data": {"inputs": {"city": "臺中市"}, "provider": {"status": "failed", "checked_at": "2026-10-01", "source": "test"},
                     "unknown": None, "notes": "Keep authored text", "checklistReview": {"identityToken": "c1-1234"}}}
