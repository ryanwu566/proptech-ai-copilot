"""Active consumer repository for deterministic pre-existing VNext API suites."""
from datetime import datetime, timezone
from services.vnext.accounts import Account, AccountAuthorizer


def active_account_authorizer():
    class ActiveRepository:
        def get_account(self, *, principal):
            now = datetime.now(timezone.utc)
            return Account(principal.user_id, "active", "consumer", now, now)
    return AccountAuthorizer(ActiveRepository())
