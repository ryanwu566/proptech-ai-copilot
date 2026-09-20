# Taipei Planning Read V1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one authenticated, read-only Taipei planning endpoint that normalizes bounded official-document references as user-provided, limited, and unverified evidence without transport or persistence.

**Architecture:** A pure VNext domain module owns closed enums, immutable Taipei UDD portal mappings, bounded text validation, and observation normalization. A strict FastAPI route maps the request and returns one fixed-semantic DTO behind a default-off feature flag and exact `manual_evidence` source-mode gate; configuration and documentation expose value-free status only.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, existing VNext auth/error/configuration infrastructure.

**Spec:** `docs/superpowers/specs/2026-09-20-taipei-planning-read-v1-design.md`

## Global Constraints

- `TAIPEI_PLANNING_READ_V1` defaults off and only existing truthy spellings enable it.
- `TAIPEI_PLANNING_SOURCE_MODE` must equal `manual_evidence`; missing, blank, or unknown modes fail with bounded 503.
- Success is always `LIMITED`, `USER_PROVIDED`, `LIMITED`, `verification_required=true`, and `verification_status=unverified`.
- Invalid or unsupported requests return bounded 422; disabled returns 404; V1 never returns a successful `NOT_AVAILABLE` observation.
- Accepted kinds are only `issued_zoning_certificate` and `official_urban_plan_announcement`.
- Accepted scope is only `Taipei City` plus `urban_plan_non_national_park`.
- The timestamp is named `normalized_at` and means server normalization time only.
- No HTTP/provider/browser/NLSC call, scraping, database access, persistence, audit write, job, upload, migration, frontend change, or new dependency.
- No caller-supplied URL, host, path, authority, provider, credential, user identifier, coordinates, address, or parcel input.
- Keep implementation changes uncommitted until verification and review, then amend commit `2d7d4ac` with `git commit --amend --no-edit`; never create a second commit.
- Do not push or merge.

## Review Focus

- A URI hidden in `reported_document_reference` must fail 422 without echoing the submitted string; covered in Task 2 API validation tests.
- A legitimate announcement reference containing ordinary punctuation or a non-path slash must remain accepted data; covered in Task 1 domain validation tests.
- Supplying `reported_effective_date` must not alter authority, coverage, verification, or announcement limitations; covered in Task 1 normalization tests.
- Global VNext authentication must remain active even though this route has no workspace or repository dependency; covered in Task 2 anonymous-request test.
- Source-mode values must never appear in safe reports or error payloads; covered in Task 3 production configuration and API error tests.

---

### Task 1: Pure planning domain and feature/config gates

**Files:**
- Create: `services/vnext/taipei_planning.py`
- Create: `tests/test_taipei_planning.py`
- Modify: `services/vnext/feature_flags.py`
- Modify: `services/production_config.py`
- Modify: `tests/test_production_config.py`

**Interfaces:**
- Consumes: `Mapping[str, str]`, an injected `Callable[[], datetime]`, and reported manual-reference fields.
- Produces: `DocumentKind`, `AuthorityClass`, `PlanningStatus`, `CoverageStatus`, `VerificationStatus`, `ManualPlanningReference`, `PlanningObservation`, `normalize_manual_reference(reference, clock)`, `taipei_planning_source_mode_status(environ)`, and `VNextFeatureFlags.taipei_planning_read_v1`.

- [ ] **Step 1: Write failing feature and configuration tests**

```python
def test_taipei_planning_flag_defaults_off_and_uses_existing_truthy_values():
    assert VNextFeatureFlags.from_environment({}).taipei_planning_read_v1 is False
    assert VNextFeatureFlags.from_environment({"TAIPEI_PLANNING_READ_V1": "true"}).taipei_planning_read_v1 is True


@pytest.mark.parametrize(
    ("value", "expected"),
    [(None, "not_configured"), ("", "not_configured"), ("manual_evidence", "configured"), ("live_api", "malformed")],
)
def test_taipei_planning_source_mode_is_exact_and_value_free(value, expected):
    environ = {} if value is None else {"TAIPEI_PLANNING_SOURCE_MODE": value}
    report = load_runtime_configuration(environ).safe_report()
    assert report["taipei_planning_source_mode"] == expected
    assert "manual_evidence" not in json.dumps(report)
    assert "live_api" not in json.dumps(report)
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run: `pytest -q tests/test_taipei_planning.py tests/test_production_config.py`

Expected: collection/import failure for the missing planning domain and assertion failures for missing flag/config fields.

- [ ] **Step 3: Implement minimal flag and source-mode status**

```python
TAIPEI_PLANNING_READ_V1_ENV = "TAIPEI_PLANNING_READ_V1"
TAIPEI_PLANNING_SOURCE_MODE_ENV = "TAIPEI_PLANNING_SOURCE_MODE"


def taipei_planning_source_mode_status(values: Mapping[str, str]) -> str:
    raw = values.get(TAIPEI_PLANNING_SOURCE_MODE_ENV)
    if raw is None or not raw.strip():
        return "not_configured"
    return "configured" if raw.strip().lower() == "manual_evidence" else "malformed"
```

Add `taipei_planning_read_v1: bool = False` to `VNextFeatureFlags`, parse it with `_ENABLED`, include it in `enabled()`, and add `taipei_planning_source_mode_status` to `RuntimeConfiguration` and `safe_report()` without changing readiness.

- [ ] **Step 4: Write failing domain normalization and validation tests**

```python
NOW = datetime(2026, 9, 20, 12, tzinfo=timezone.utc)


def test_manual_announcement_is_always_limited_user_provided_and_unverified():
    result = normalize_manual_reference(
        ManualPlanningReference(
            jurisdiction="Taipei City",
            scope="urban_plan_non_national_park",
            document_kind=DocumentKind.OFFICIAL_URBAN_PLAN_ANNOUNCEMENT,
            reported_document_reference="府都規字第1150001號/附件一",
            reported_effective_date=date(2026, 9, 19),
        ),
        clock=lambda: NOW,
    )
    assert (result.status, result.authority_class, result.coverage_status) == (
        PlanningStatus.LIMITED,
        AuthorityClass.USER_PROVIDED,
        CoverageStatus.LIMITED,
    )
    assert result.verification_required is True
    assert result.verification_status is VerificationStatus.UNVERIFIED
    assert result.normalized_at == NOW
    assert "later amendments" in " ".join(result.limitations)


@pytest.mark.parametrize("value", ["https://evil.invalid/x", "www.evil.invalid", "C:\\\\secret", "/etc/passwd", "../../secret", "<b>x</b>", "bad\x00value"])
def test_reported_text_rejects_urls_absolute_paths_traversal_html_and_controls(value):
    with pytest.raises(VNextError) as error:
        normalize_reported_text(value, required=True, maximum=200)
    assert error.value.code is ErrorCode.VALIDATION_FAILED
```

- [ ] **Step 5: Run domain tests and verify RED**

Run: `pytest -q tests/test_taipei_planning.py`

Expected: import failure or missing-symbol failures for the domain contracts.

- [ ] **Step 6: Implement the pure domain module**

```python
class DocumentKind(str, Enum):
    ISSUED_ZONING_CERTIFICATE = "issued_zoning_certificate"
    OFFICIAL_URBAN_PLAN_ANNOUNCEMENT = "official_urban_plan_announcement"


SOURCE_PORTALS = MappingProxyType({
    DocumentKind.ISSUED_ZONING_CERTIFICATE: "https://zone.udd.gov.taipei/new_index1.aspx",
    DocumentKind.OFFICIAL_URBAN_PLAN_ANNOUNCEMENT: "https://udd.gov.taipei/announcement/biwfsm8",
})


def normalize_manual_reference(reference: ManualPlanningReference, *, clock) -> PlanningObservation:
    if reference.jurisdiction != "Taipei City" or reference.scope != "urban_plan_non_national_park":
        raise VNextError.unsupported_input()
    normalized_at = clock()
    if normalized_at.utcoffset() is None:
        raise VNextError.validation_failed()
    return PlanningObservation(
        status=PlanningStatus.LIMITED,
        jurisdiction="Taipei City",
        scope="urban_plan_non_national_park",
        authority_class=AuthorityClass.USER_PROVIDED,
        coverage_status=CoverageStatus.LIMITED,
        verification_required=True,
        verification_status=VerificationStatus.UNVERIFIED,
        normalized_at=normalized_at.astimezone(timezone.utc),
        # fixed source mapping and kind-specific immutable limitations
    )
```

Use a bounded validator that rejects controls, `<`/`>`, `://`, case-insensitive leading `http://`, `https://`, or `www.`, Windows drive/UNC paths, POSIX absolute paths, and traversal path segments while allowing non-path punctuation such as `府都規字第1150001號/附件一`.

- [ ] **Step 7: Run focused tests and verify GREEN**

Run: `pytest -q tests/test_taipei_planning.py tests/test_production_config.py`

Expected: all selected tests pass.

### Task 2: Strict authenticated read-only API

**Files:**
- Create: `backend/api/v1/taipei_planning.py`
- Create: `tests/test_taipei_planning_api.py`
- Modify: `backend/api/v1/router.py`
- Modify: `services/vnext/errors.py`

**Interfaces:**
- Consumes: Task 1 domain contracts, `get_vnext_feature_flags`, `load_runtime_configuration`, existing VNext auth and structured error envelope.
- Produces: `POST /v1/planning/taipei/observe`, `PlanningObservationV1`, `require_taipei_planning_feature()`, and `require_taipei_planning_source_mode()`.

- [ ] **Step 1: Write failing success and fixed-semantics endpoint tests**

```python
def test_manual_certificate_returns_only_fixed_unverified_semantics(client):
    response = client.post("/v1/planning/taipei/observe", json={
        "jurisdiction": "Taipei City",
        "scope": "urban_plan_non_national_park",
        "document_kind": "issued_zoning_certificate",
        "reported_document_reference": "北市都證字第115-001號",
        "reported_zone_label": "第三種住宅區",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "LIMITED"
    assert payload["authority_class"] == "USER_PROVIDED"
    assert payload["coverage_status"] == "LIMITED"
    assert payload["verification_required"] is True
    assert payload["verification_status"] == "unverified"
    assert "normalized_at" in payload
    assert set(payload) == EXPECTED_PLANNING_OBSERVATION_FIELDS
    assert not ({"far", "bcr", "buildability", "ownership", "entitlement", "approval", "parcel_confirmation"} & payload.keys())
```

- [ ] **Step 2: Write failing flag/config and invalid-input API tests**

```python
def test_feature_off_is_bounded_404(client):
    app.dependency_overrides[get_vnext_feature_flags] = lambda: VNextFeatureFlags()
    response = client.post(PATH, json=VALID_CERTIFICATE)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


@pytest.mark.parametrize("mode", [None, "", "live_api", "manual_authoritative_evidence"])
def test_unavailable_source_mode_is_bounded_503(client, monkeypatch, mode):
    if mode is None:
        monkeypatch.delenv("TAIPEI_PLANNING_SOURCE_MODE", raising=False)
    else:
        monkeypatch.setenv("TAIPEI_PLANNING_SOURCE_MODE", mode)
    response = client.post(PATH, json=VALID_CERTIFICATE)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "coverage_unavailable"
    assert mode not in response.text if mode else True
```

Cover New Taipei, ambiguous jurisdiction, national-park scope, unsupported kind, coordinate/address/parcel extras, URL fields, URL values, absolute/traversal paths, controls, HTML, oversized fields, invalid dates, and anonymous authentication as bounded 401/422 responses without input echo.

- [ ] **Step 3: Run endpoint tests and verify RED**

Run: `pytest -q tests/test_taipei_planning_api.py`

Expected: route-not-found and missing-module failures.

- [ ] **Step 4: Implement the strict request/response models and dependencies**

```python
class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PlanningObservationRequest(_StrictModel):
    jurisdiction: Annotated[str, Field(min_length=1, max_length=32)]
    scope: Annotated[str, Field(min_length=1, max_length=64)]
    document_kind: DocumentKind
    reported_document_reference: Annotated[str, Field(min_length=1, max_length=200)]
    reported_plan_identifier: Annotated[str | None, Field(max_length=200)] = None
    reported_zone_code: Annotated[str | None, Field(max_length=80)] = None
    reported_zone_label: Annotated[str | None, Field(max_length=200)] = None
    reported_effective_date: date | None = None


def require_taipei_planning_feature(flags: VNextFeatureFlags = Depends(get_vnext_feature_flags)) -> None:
    if not flags.taipei_planning_read_v1:
        raise VNextError.not_found()


def require_taipei_planning_source_mode() -> None:
    if load_runtime_configuration().taipei_planning_source_mode_status != "configured":
        raise VNextError(ErrorCode.COVERAGE_UNAVAILABLE)
```

Map the domain record to a response model containing only the spec fields, register the route under the existing authenticated VNext router, and add `VNextError.coverage_unavailable()` as a bounded convenience constructor if it improves clarity.

- [ ] **Step 5: Add fail-fast side-effect sentinel tests**

```python
def test_success_performs_no_transport_nlsc_database_or_persistence(client, monkeypatch):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("planning manual seam crossed a forbidden boundary")

    monkeypatch.setattr(httpx.Client, "request", forbidden)
    monkeypatch.setattr(httpx.AsyncClient, "request", forbidden)
    monkeypatch.setattr(backend.db, "get_connection", forbidden)
    monkeypatch.setattr(db_principal, "get_vnext_database_principal_context", forbidden)
    monkeypatch.setattr(NlscGatewayAdapter, "terrain_point", forbidden)
    monkeypatch.setattr(NlscCadGatewayAdapter, "cad_009_address_query_land", forbidden)
    monkeypatch.setattr(NlscTileGatewayAdapter, "fetch_tile", forbidden)
    assert client.post(PATH, json=VALID_CERTIFICATE).status_code == 200
```

If `requests` is installed, patch `requests.sessions.Session.request` with the same sentinel. Assert that no persistence or background-job collaborator is imported or injected into the route; the behavioral sentinel remains the primary proof.

- [ ] **Step 6: Run endpoint and domain tests and verify GREEN**

Run: `pytest -q tests/test_taipei_planning.py tests/test_taipei_planning_api.py tests/test_vnext_auth_api.py`

Expected: all selected tests pass.

### Task 3: Deployment contract and source audit

**Files:**
- Create: `docs/vnext/taipei-planning-read-v1-source-audit.md`
- Modify: `.env.example`
- Modify: `render.yaml`
- Modify: `tests/test_production_deployment_config.py`
- Modify: `backend/api/v1/router.py`
- Test: `tests/test_taipei_planning_api.py`

**Interfaces:**
- Consumes: the exact two environment variable names and fixed portal mappings from Tasks 1 and 2.
- Produces: documented default-off deployment variables, value-free runtime context status, and a Gate 0 audit record.

- [ ] **Step 1: Write failing deployment and runtime-context tests**

```python
def test_render_declares_taipei_planning_as_default_off_manual_mode():
    service = yaml.safe_load(RENDER)["services"][0]
    variables = {item["key"]: item for item in service["envVars"]}
    assert variables["TAIPEI_PLANNING_READ_V1"] == {"key": "TAIPEI_PLANNING_READ_V1", "value": "false"}
    assert variables["TAIPEI_PLANNING_SOURCE_MODE"] == {"key": "TAIPEI_PLANNING_SOURCE_MODE", "value": "manual_evidence"}


def test_vnext_context_reports_planning_flag_without_source_values(client):
    payload = client.get("/v1").json()
    assert payload["features"]["taipei_planning_read_v1"] is True
    assert "manual_evidence" not in json.dumps(payload)
```

- [ ] **Step 2: Run deployment tests and verify RED**

Run: `pytest -q tests/test_production_deployment_config.py tests/test_taipei_planning_api.py`

Expected: missing deployment variables and context feature field.

- [ ] **Step 3: Implement deployment metadata and Gate 0 source audit**

Add these value-only defaults to the Render blueprint and empty/default-off guidance to `.env.example`:

```yaml
- key: TAIPEI_PLANNING_READ_V1
  value: "false"
- key: TAIPEI_PLANNING_SOURCE_MODE
  value: manual_evidence
```

Write the source audit with the official authority, Taipei urban-plan/non-national-park geography, manual lookup keys, formats, legal meaning, update semantics, Open Government Data License v1 attribution, manual certificate/announcement access, availability constraints, no-transport decision, and LUI_002 boundary. Add the planning flag to the `/v1` context response.

- [ ] **Step 4: Run planning, production, and location/identity regression suites**

Run:

```text
pytest -q tests/test_taipei_planning.py tests/test_taipei_planning_api.py tests/test_production_config.py tests/test_production_deployment_config.py
pytest -q tests/test_vnext_identity_resolution.py tests/test_vnext_parcel_hypothesis.py tests/test_vnext_property_api.py tests/test_vnext_nlsc_cad_observation_provider.py
pytest -q tests/test_security_hardening.py tests/test_vnext_auth_api.py tests/test_nlsc_gateway_adapter.py tests/test_nlsc_tile_gateway_adapter.py
```

Expected: all selected tests pass.

### Task 4: Full verification, independent review, and the single amended commit

**Files:**
- Review: every changed file from Tasks 1-3
- Amend: existing commit `2d7d4ac`

**Interfaces:**
- Consumes: complete working-tree diff and all requirements/specification.
- Produces: fresh verification evidence, independent review with no unresolved Critical/Important issue, and exactly one final implementation commit.

- [ ] **Step 1: Run static and complete-suite verification**

Run:

```text
python -m compileall -q backend services tests
git diff --check
pytest -q
```

Expected: exit code 0 for every command and zero pytest failures.

- [ ] **Step 2: Audit prohibited changes and claims**

Run:

```text
git diff --name-only HEAD
git diff --stat HEAD
git status --short
```

Verify there are no migration, frontend, dependency, generated-artifact, credential, transport, persistence, scraping, FAR/BCR/buildability, ownership, entitlement, approval, parcel-confirmation, or LUI_002 authority-promotion changes.

- [ ] **Step 3: Request independent read-only review**

Give the reviewer the full requirements, spec path, base commit `e1ecb70`, current committed head `2d7d4ac`, and working-tree diff. Require explicit inspection for user-provided authority promotion, announcement/certificate current-effect claims, property/case binding, caller URLs, hidden HTTP/scraping, prohibited planning conclusions, LUI_002 promotion, jurisdiction leakage, persistence, and credentials.

- [ ] **Step 4: Fix every Critical or Important review finding test-first**

For each valid finding: add a focused failing regression test, run it to observe RED, implement the smallest fix, then run the focused and full suites to observe GREEN. Re-review affected code if the fix changes architecture or security boundaries.

- [ ] **Step 5: Amend the single commit after fresh verification**

Run:

```text
git add -A
git commit --amend --no-edit
git log --oneline e1ecb70..HEAD
git status --short
```

Expected: exactly one commit named `feat(planning): add Taipei planning read seam` after `e1ecb70`, and a clean working tree. Do not push or merge.
