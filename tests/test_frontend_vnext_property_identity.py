from __future__ import annotations

import re
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
WORKFLOW = (FRONTEND / "components" / "vnext-property-identity-workflow.tsx").read_text(encoding="utf-8")
CLIENT = (FRONTEND / "lib" / "vnext-identity-client.ts").read_text(encoding="utf-8")
CONTRACT = (FRONTEND / "lib" / "vnext-identity-contract.ts").read_text(encoding="utf-8")
AUTH = (FRONTEND / "lib" / "vnext-auth-session.ts").read_text(encoding="utf-8")
CSP = (FRONTEND / "next.config.mjs").read_text(encoding="utf-8")
AUTH_GATE = (FRONTEND / "components" / "vnext-auth-gate.tsx").read_text(encoding="utf-8")
LIVE_ROUTE = (FRONTEND / "components" / "property-identity-live-route.tsx").read_text(encoding="utf-8")


def test_slice_8_is_an_isolated_route_without_homepage_imports() -> None:
    page = FRONTEND / "app" / "vnext" / "property-identity" / "page.tsx"
    assert page.is_file()
    assert "VNextPropertyIdentityWorkflow" in page.read_text(encoding="utf-8")
    assert "hero-intro" not in WORKFLOW
    assert "case-storage" not in WORKFLOW


def test_client_calls_only_the_approved_identity_surface() -> None:
    for path in (
        "/v1/property-resolutions",
        "/confirm",
        "/reject",
        "/v1/properties/",
        "/graph",
        "/evidence",
        "/v1/cases",
        "/attach-resolution",
        "/v1/workspaces/",
    ):
        assert path in CLIENT
    assert "legacy-case-imports" not in CLIENT
    assert "listing_url" not in CLIENT
    assert "x-user-id" not in CLIENT.lower()
    assert "x-workspace-role" not in CLIENT.lower()


def test_browser_auth_uses_only_publishable_session_configuration() -> None:
    assert "NEXT_PUBLIC_SUPABASE_URL" in AUTH
    assert "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY" in AUTH
    assert "createClient(config.url, config.key" in AUTH
    assert "client.auth.getSession()" in AUTH
    assert "client.auth.refreshSession()" in AUTH
    assert "client.auth.signInWithPassword(" in AUTH
    assert 'client.auth.signOut({ scope: "local" })' in AUTH
    assert "window.localStorage" not in AUTH
    assert '["RS256", "ES256"].includes(String(header.alg))' in AUTH
    assert "payload.iss !== issuer" in AUTH
    assert 'payload.role !== "authenticated"' in AUTH
    assert "sb_publishable_" in AUTH
    assert "Authorization" in CLIENT and "Bearer ${session.accessToken}" in CLIENT
    assert "from(" not in AUTH
    assert "rpc(" not in AUTH
    assert "getSupabaseAuthConnectSource" in CSP
    assert "url.username || url.password" in CSP
    assert "${supabaseAuthConnectSource}" in CSP


def test_production_auth_deployment_contract_and_browser_boundary() -> None:
    manifest = json.loads((ROOT / "config" / "hosted-environment-manifest.json").read_text(encoding="utf-8"))
    public_frontend = {
        item["name"] for item in manifest["variables"]
        if item["scope"] == "frontend" and item["visibility"] == "public"
    }
    assert public_frontend == {
        "NEXT_PUBLIC_API_BASE_URL", "NEXT_PUBLIC_SUPABASE_URL", "NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY"
    }
    browser_source = AUTH + CLIENT + AUTH_GATE + LIVE_ROUTE
    for forbidden in ("sb_secret_", "SUPABASE_SERVICE_ROLE_KEY", "DATABASE_URL", "signInWithOAuth", "signUp("):
        assert forbidden not in browser_source
    assert "console." not in browser_source
    assert "captureException" not in browser_source
    assert "Authorization" not in AUTH_GATE + LIVE_ROUTE
    assert 'redirect: "error"' in CLIENT


def test_runtime_contracts_fail_closed_without_any() -> None:
    assert "class VNextContractError" in CONTRACT
    assert "Invalid VNext response" in CONTRACT
    assert "unknown" in CONTRACT and "unavailable" in CONTRACT
    assert '"confirmed", "rejected"' in CONTRACT
    assert '"blocking"' in CONTRACT
    assert not re.search(r"\bany\b", CONTRACT)
    assert not re.search(r"\bany\b", CLIENT)


def test_all_signed_input_types_are_explicit_and_listing_url_is_absent() -> None:
    for kind in ("address", "lot_number", "building_number", "coordinates", "map_click"):
        assert f'kind: "{kind}"' in CLIENT
    assert "listing_url" not in WORKFLOW
    assert "EPSG:4326" in CLIENT and "EPSG:4326" in WORKFLOW


def test_human_confirmation_requires_selection_review_intent_and_reason() -> None:
    assert "selectedCandidateId" in WORKFLOW
    assert "reviewed" in WORKFLOW
    assert "confirmIntent" in WORKFLOW
    assert "confirmationReason.trim().length < 8" in WORKFLOW
    assert "hasBlockingConflict" in WORKFLOW
    assert "selectedCandidateConfirmable" in WORKFLOW
    assert 'selectedCandidate.source.environment === "production"' in WORKFLOW
    assert 'workspace?.role === "owner" || workspace?.role === "admin"' in WORKFLOW
    assert "candidate.confidence * 100" in WORKFLOW
    assert "checked={selectedCandidateId === candidate.candidate_id}" in WORKFLOW


def test_command_retries_are_bounded_and_double_submission_is_guarded() -> None:
    assert "pendingRef.current" in WORKFLOW
    assert "newIdempotencyKey" in WORKFLOW
    assert "VNextOutcomeUnknownError" in WORKFLOW
    assert "setConfirmAttempt(null)" in WORKFLOW
    assert "setAttachAttempt(null)" in WORKFLOW
    assert '`${command}:${crypto.randomUUID()}`' in CLIENT
    assert "commandSavedRefreshFailed" in WORKFLOW


def test_confirmation_and_case_attachment_remain_separate() -> None:
    confirmation_body = WORKFLOW.split("async function confirmCandidate", 1)[1].split("async function rejectResolution", 1)[0]
    assert "attachResolution" not in confirmation_body
    assert "createCase" not in confirmation_body
    assert "await refreshResolution" in confirmation_body
    assert "createdCaseReplay" in WORKFLOW
    assert 'caught.code === "version_conflict"' in WORKFLOW
    assert "setCaseAttached(true)" in WORKFLOW
