"""Loopback-only browser fixture using the real JWT verifier and API dependencies.

No provider, application database, real user or server credential is used.
"""
import os
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
from uuid import UUID

_STARTED = time.monotonic()


def startup_milestone(name):
    if os.environ.get("WAVE1A_STARTUP_DIAGNOSTICS") == "1":
        # Only fixed phase names and elapsed time; never session or configuration.
        sys.stderr.write("WAVE1A_STARTUP " + json.dumps({
            "milestone": name, "elapsed_ms": round((time.monotonic() - _STARTED) * 1000),
        }) + "\n")
        sys.stderr.flush()


startup_milestone("helper_started")
if os.environ.get("WAVE1A_BROWSER_ACCEPTANCE") != "1":
    raise RuntimeError("explicit browser fixture opt-in required")
for name in list(os.environ):
    if name == "DATABASE_URL" or name.endswith("_DATABASE_URL"):
        os.environ.pop(name)
os.environ["EARTH_ENGINE_SATELLITE_REFERENCE_V1"] = "false"
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
startup_milestone("environment_sanitized")

import jwt
startup_milestone("jwt_imported")
from cryptography.hazmat.primitives.asymmetric import rsa
startup_milestone("crypto_imported")
import uvicorn
startup_milestone("uvicorn_imported")
from backend.api_main import app
startup_milestone("app_imported")
from services.vnext.accounts import Account, AccountAuthorizer, get_account_authorizer
from services.vnext.auth import SupabaseJWTVerifier, get_supabase_jwt_verifier
startup_milestone("dependencies_imported")

USER = UUID("11111111-1111-4111-8111-111111111111")
ISSUER = "https://slice8-auth.supabase.co/auth/v1"
KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
STATUS = os.environ["WAVE1A_FIXTURE_ACCOUNT_STATUS"]
assert STATUS in {"active", "suspended"}
startup_milestone("signing_key_created")


class Accounts:
    def get_account(self, *, principal):
        now = datetime.now(timezone.utc)
        return Account(USER, STATUS, "consumer", now, now) if principal.user_id == USER else None


app.dependency_overrides[get_supabase_jwt_verifier] = lambda: SupabaseJWTVerifier(
    issuer=ISSUER, signing_key_resolver=lambda token: KEY.public_key()
)
app.dependency_overrides[get_account_authorizer] = lambda: AccountAuthorizer(Accounts())


@app.get("/__wave1a_fixture/session")
def fixture_session():
    startup_milestone("fixture_session_reached")
    now = datetime.now(timezone.utc)
    token = jwt.encode({"sub": str(USER), "iss": ISSUER, "aud": "authenticated",
                        "role": "authenticated", "iat": now, "exp": now + timedelta(hours=1),
                        "user_metadata": {"platform_role": "platform_admin"}},
                       KEY, algorithm="RS256", headers={"kid": "local-fixture"})
    return {"access_token": token, "refresh_token": "local-fixture-refresh", "token_type": "bearer",
            "expires_in": 3600, "expires_at": int((now + timedelta(hours=1)).timestamp()),
            "user": {"id": str(USER), "email": "browser-person@example.invalid", "aud": "authenticated",
                     "created_at": now.isoformat()}}


if __name__ == "__main__":
    startup_milestone("server_starting")
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]), log_level="error", access_log=False, lifespan="off")
