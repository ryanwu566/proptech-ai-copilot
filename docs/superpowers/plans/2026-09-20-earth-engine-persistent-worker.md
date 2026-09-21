# Earth Engine Persistent Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace per-request disposable Earth Engine processes with two bounded reusable workers so the real satellite-reference endpoint can return a validated JPEG within the existing eight-second deadline.

**Architecture:** A process-local manager owns four-request admission, a two-thread request executor, exactly two persistent spawned-worker slots, strict request/result IPC, startup/replacement controllers, and the fixed project snapshot. Workers initialize Earth Engine once, process one request at a time, omit the collection-size round trip, and are terminated on timeout, cancellation, crash, or protocol violation.

**Tech Stack:** Python 3.12+, FastAPI lifespan, `multiprocessing` spawn context and pipes, `threading`, `concurrent.futures.ThreadPoolExecutor`, asyncio, Google Earth Engine Python API, pytest.

**Spec:** `docs/superpowers/specs/2026-09-20-earth-engine-persistent-worker-design.md`

## Global Constraints

- Keep the branch local: no push, merge, or rebase.
- Keep spec, plan, tests, and implementation uncommitted until final delivery; do not create task-by-task commits.
- Maximum two live Earth Engine workers and exactly four admitted requests: two active plus two queued.
- Preserve the 8.0-second absolute request deadline and 20.0-second worker-readiness deadline.
- Preserve dataset `COPERNICUS/S2_SR_HARMONIZED`, trailing 90 days, exact 500 m circle, cloud threshold 35, SCL exclusions 3/8/9/10/11, median B4/B3/B2, 512×512 maximum, 250,000 provider bytes, and 365,000 response bytes.
- Application retries, Earth Engine SDK retries, and thumbnail HTTP retries remain zero.
- No export, batch task, persistence, credential file, API key, caller project, caller Earth Engine expression, or provider URL exposure.
- Preserve the exact disclaimer: `Satellite reference imagery — not cadastral or statutory evidence.`
- `available` means only that the bounded pipeline produced and validated a reference JPEG.
- Remove `collection.size().getInfo()` without replacing it with an inferred or placeholder scene count.

## Review Focus

1. Cancellation that races executor dequeue must never send IPC; Task 3 adds a barrier-based race test and an exact-once admission-release assertion.
2. Two simultaneous worker failures must never create a third live process; Task 2 asserts live-worker count through replacement scheduling.
3. Replacement failure must clean the still-healthy worker and every pipe; Task 2 asserts zero child processes and closed connections.
4. Startup controller shutdown must not race worker readiness into `available`; Task 4 asserts `closing/stopped` wins and unrelated health remains available.
5. Expired credentials must refresh once, while Earth Engine initialization failures remain provider failures; Task 1 tests the two categories independently.

---

### Task 1: Split Worker Initialization and Remove Scene Count

**Files:**
- Modify: `services/adapters/earth_engine_adapter.py`
- Modify: `services/satellite_reference.py`
- Modify: `tests/test_satellite_reference.py`

**Interfaces:**
- Produces: `EarthEngineSatelliteAdapter.initialize() -> None`
- Produces: `EarthEngineSatelliteAdapter.fetch_initialized(query: SatelliteQuery) -> SatelliteAdapterResult`
- Produces: `EarthEngineInitializationUnavailable`
- Changes: `SatelliteAdapterResult` contains `image_bytes: bytes` and no scene count.

- [ ] **Step 1: Add RED tests for initialization success, credentials, retries, and concurrency**

Add tests that use a valid fake credential object and a fake `ee.data.setMaxRetries` recorder:

```python
def test_adapter_initializes_once_sets_zero_retries_and_reuses_state_concurrently():
    # Two concurrent initialize() calls on one adapter.
    # Assert auth_default, credential refresh, and ee.Initialize each run once.
    # Assert setMaxRetries(0) occurs before Initialize.

def test_adapter_maps_adc_refresh_failure_to_credential_unavailable():
    # credentials.valid is False and refresh raises a secret-bearing error.
    # Assert safe EarthEngineCredentialUnavailable with no secret text.

def test_adapter_maps_ee_initialize_failure_to_initialization_unavailable():
    # Valid credentials, Initialize raises a provider/network error.
    # Assert EarthEngineInitializationUnavailable, not credential_unavailable.
```

- [ ] **Step 2: Run the new initialization tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_satellite_reference.py -k "initializes_once or adc_refresh_failure or ee_initialize_failure"
```

Expected: failures because the split initialization API and failure class do not exist.

- [ ] **Step 3: Implement the minimal thread-safe initialization seam**

Add an instance lock and state to the adapter. `initialize()` must validate the fixed project, discover ADC, refresh only invalid credentials, call `ee.data.setMaxRetries(0)`, initialize the fixed project once, and classify credential versus Earth Engine initialization failures. `fetch()` remains a compatibility wrapper that calls `initialize()` then `fetch_initialized()`.

```python
def initialize(self) -> None:
    if self._initialized:
        return
    with self._initialize_lock:
        if self._initialized:
            return
        credentials, _ = self._auth_default_callable()()
        if hasattr(credentials, "valid") and not credentials.valid:
            credentials.refresh(self._auth_request_factory_callable()())
        self._ee.data.setMaxRetries(0)
        self._ee.Initialize(credentials=credentials, project=self._project)
        self._initialized = True
```

Keep imports lazy and never initialize at module import.

- [ ] **Step 4: Add RED tests proving scene count is absent and preview success is count-free**

Update the fake collection so `size()` raises if called. Assert `fetch_initialized()` still produces a valid JPEG and the service returns `status="available"`. Remove tests whose only contract is `limited_observation_coverage` or `no_usable_imagery_in_window` from an explicit count.

```python
def test_adapter_does_not_issue_collection_size_request():
    adapter.initialize()
    result = adapter.fetch_initialized(fixed_query())
    assert result.image_bytes == jpeg_with_dimensions(512, 512)
    assert not any(call[0] == "size" for call in fake_ee.calls)
```

- [ ] **Step 5: Run scene-count tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_satellite_reference.py -k "scene_count or collection_size or fixed_collection"
```

Expected: current implementation calls `collection.size().getInfo()` or expects `scene_count`.

- [ ] **Step 6: Remove the count request and update preview-only success**

Build the collection, median composite, thumbnail, and JPEG directly. Return only validated image bytes. In the service, a valid image returns `available`; empty/unusable imagery follows the existing allowlisted image/provider failure path. Do not add any numeric or textual scene-count placeholder.

- [ ] **Step 7: Run the adapter/service focused tests GREEN**

Run:

```powershell
python -m pytest -q tests/test_satellite_reference.py
```

Expected: all updated focused tests pass.

- [ ] **Step 8: Checkpoint without committing**

Run `git diff --check` and keep changes uncommitted per the review instruction.

---

### Task 2: Implement Strict IPC and Persistent Worker Lifecycle

**Files:**
- Create: `services/earth_engine_worker_pool.py`
- Create: `tests/test_earth_engine_worker_pool.py`

**Interfaces:**
- Produces: frozen `SatelliteWorkerRequest`, `SatelliteWorkerResult`, and `SatelliteWorkerReady` DTOs.
- Produces: `EarthEngineWorkerManager.start(enabled: bool, project: str) -> None`
- Produces: `EarthEngineWorkerManager.fetch(latitude: float, longitude: float, window_start: str, window_end: str, deadline: float, control: RequestControl) -> bytes`
- Produces: `EarthEngineWorkerManager.shutdown() -> None`
- Produces: `get_earth_engine_worker_manager() -> EarthEngineWorkerManager`

- [ ] **Step 1: Add RED tests for closed IPC and bounded worker ownership**

Use top-level picklable fake worker entrypoints and manager dependency injection. Tests must assert:

```python
def test_manager_owns_exactly_two_worker_slots_and_never_starts_a_third(): ...
def test_request_dto_contains_only_version_generation_id_coordinate_and_dates(): ...
def test_result_with_wrong_request_id_or_generation_is_rejected(): ...
def test_manager_captures_project_once_and_never_accepts_per_request_project(): ...
```

- [ ] **Step 2: Run IPC/ownership tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_earth_engine_worker_pool.py -k "worker_slots or request_dto or wrong_request or captures_project"
```

Expected: module and manager interfaces are absent.

- [ ] **Step 3: Implement DTOs, worker entrypoint, slots, and startup controller**

Implement versioned frozen data-only messages. The child imports the adapter, initializes once, sends one allowlisted readiness message, and then processes requests sequentially. The manager starts one owned startup-controller thread, records `starting`, returns immediately, and changes to `available` only after both slots report ready within 20 seconds.

```python
@dataclass(frozen=True)
class SatelliteWorkerRequest:
    version: int
    generation: int
    request_id: str
    latitude: float
    longitude: float
    window_start: str
    window_end: str
```

No IPC object may contain a project, dataset, bands, geometry, callable, environment, provider URL, credential, or exception.

- [ ] **Step 4: Add RED tests for crash, timeout, replacement, and shutdown**

Add deterministic fake workers for success, crash, hang, initialization failure, and replacement failure:

```python
def test_crashed_worker_is_joined_and_replaced_once_without_request_replay(): ...
def test_timeout_kills_worker_before_one_bounded_replacement(): ...
def test_failed_replacement_cleans_other_worker_and_all_pipes(): ...
def test_shutdown_is_idempotent_and_leaves_no_workers(): ...
```

Assertions include maximum live count two, old PID gone, zero replay count, one replacement attempt for the generation, zero workers after failed replacement, and zero workers after shutdown.

- [ ] **Step 5: Run lifecycle tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_earth_engine_worker_pool.py -k "crashed or timeout or replacement or shutdown"
```

Expected: lifecycle and containment behavior is missing.

- [ ] **Step 6: Implement containment and bounded capacity restoration**

Poll each assigned private pipe in short bounded intervals. On timeout, cancellation, EOF, crash, or protocol mismatch: retire the generation, terminate/join/kill as needed, close the pipe, fail the request, and schedule at most one manager-owned replacement attempt for that generation. Never replay the request. If replacement fails, transition `unavailable`, terminate the remaining worker, close all pipes, and stop with zero workers.

- [ ] **Step 7: Run all worker-pool tests GREEN**

Run:

```powershell
python -m pytest -q tests/test_earth_engine_worker_pool.py
```

- [ ] **Step 8: Checkpoint without committing**

Run `git diff --check`; keep changes uncommitted.

---

### Task 3: Integrate Admission, Absolute Deadline, and Cancellation Races

**Files:**
- Modify: `services/satellite_reference.py`
- Modify: `tests/test_satellite_reference.py`
- Modify: `tests/test_earth_engine_worker_pool.py`

**Interfaces:**
- Consumes: singleton `EarthEngineWorkerManager` and `RequestControl` from Task 2.
- Produces: `fetch_satellite_reference(latitude: float, longitude: float, adapter: SatelliteAdapter | None = None, now: datetime | None = None, timeout_seconds: float = 8.0)` with no per-request project.

- [ ] **Step 1: Add RED tests for four-slot admission and queued cancellation**

Add tests with barriers/events that occupy two active executor calls, queue two more, and submit a fifth. Cancel one queued request before releasing the barrier.

```python
def test_two_active_two_queued_and_fifth_fails_closed(): ...
def test_cancelled_queued_request_never_acquires_worker_or_sends_ipc(): ...
def test_expired_queued_request_never_acquires_worker_or_sends_ipc(): ...
def test_admission_slot_is_released_exactly_once_in_cancel_race(): ...
```

- [ ] **Step 2: Run admission/cancellation tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_earth_engine_worker_pool.py tests/test_satellite_reference.py -k "two_active or cancelled_queued or expired_queued or released_exactly_once"
```

- [ ] **Step 3: Move admission and executor ownership into the manager**

Remove satellite-service global semaphores/executor/process functions. Manager `fetch` acquires the four-slot semaphore non-blocking, creates one absolute deadline at request entry, submits to its two-thread executor, and owns exact-once release in the async caller's `finally` block.

- [ ] **Step 4: Implement the queued cancellation protocol**

Use one thread-safe `RequestControl` per admitted request. On asyncio cancellation or wait timeout, mark it stale and call `future.cancel()`. The executor callable checks the flag/deadline before worker acquisition and immediately before IPC. If already active, it contains the assigned worker before completing. Await containment before releasing admission.

- [ ] **Step 5: Preserve final response deadline and byte cap**

After base64 encoding and response construction, re-check the original deadline and the 365,000-byte serialized cap. Discard the image and return the bounded timeout/image-failure response if either bound is exceeded.

- [ ] **Step 6: Run focused and deadline tests GREEN**

Run:

```powershell
python -m pytest -q tests/test_satellite_reference.py tests/test_earth_engine_worker_pool.py
```

- [ ] **Step 7: Checkpoint without committing**

Run `git diff --check`; keep changes uncommitted.

---

### Task 4: Integrate Optional FastAPI Lifecycle

**Files:**
- Modify: `backend/api_main.py`
- Modify: `backend/api/routes_satellite_reference.py`
- Modify: `tests/test_satellite_reference.py`
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: manager `start`, availability state, fixed configuration snapshot, and `shutdown`.
- Produces: non-blocking optional capability startup and bounded teardown.

- [ ] **Step 1: Add RED tests for non-blocking startup and truthful failure mapping**

```python
def test_fastapi_serves_health_while_earth_engine_manager_is_starting(): ...
def test_satellite_route_fails_closed_while_manager_is_starting(): ...
def test_adc_startup_failure_maps_to_credential_unavailable(): ...
def test_ee_initialization_failure_maps_to_provider_error(): ...
def test_route_does_not_reread_project_per_request(): ...
```

Use a fake manager/startup controller; do not invoke live Earth Engine in unit tests.

- [ ] **Step 2: Run lifecycle/API tests and verify RED**

Run:

```powershell
python -m pytest -q tests/test_satellite_reference.py tests/test_api.py -k "manager_is_starting or startup_failure or does_not_reread"
```

- [ ] **Step 3: Wire startup before yield without awaiting readiness**

At lifespan entry, snapshot the feature flag and project once and call manager `start`. Yield immediately. In teardown, call manager `shutdown` in a `finally` path while preserving existing database-pool cleanup. The route delegates configuration and availability decisions to the manager and never reads a project per request.

- [ ] **Step 4: Add RED shutdown/startup race test**

Assert a readiness callback arriving during shutdown cannot transition the manager from `closing/stopped` back to `available`, and no child survives.

- [ ] **Step 5: Implement state-transition guards and run lifecycle tests GREEN**

Run:

```powershell
python -m pytest -q tests/test_satellite_reference.py tests/test_api.py tests/test_earth_engine_worker_pool.py -k "lifespan or manager or startup or shutdown"
```

- [ ] **Step 6: Checkpoint without committing**

Run `git diff --check`; keep changes uncommitted.

---

### Task 5: Documentation, Regression, Live Acceptance, and Independent Review

**Files:**
- Modify: `docs/satellite-reference-evidence-v1.md`
- Modify: `docs/superpowers/specs/2026-09-20-earth-engine-persistent-worker-design.md`
- Verify: all changed production and test files

**Interfaces:**
- Consumes: completed implementation from Tasks 1–4.
- Produces: verified local closure evidence and final review findings.

- [ ] **Step 1: Update operational documentation**

Document two persistent workers, two-active/two-queued admission, asynchronous bounded readiness, starting/unavailable behavior, scene-count removal, two remote calls, zero retries, timeout termination, bounded replacement, replacement-failure cleanup, and exact preview-only meaning of `available`.

- [ ] **Step 2: Run focused, concurrency, timeout, lifecycle, shutdown, and API tests**

Run:

```powershell
python -m pytest -q tests/test_satellite_reference.py tests/test_earth_engine_worker_pool.py tests/test_api.py
python -m pytest -q tests/test_satellite_reference.py tests/test_earth_engine_worker_pool.py -k "queue or concurrent or cancel or deadline or timeout or crash or replacement or shutdown"
```

- [ ] **Step 3: Run the full relevant Python regression**

Run:

```powershell
python -m pytest -q
```

Record every failure by name; do not hide unrelated pre-existing failures.

- [ ] **Step 4: Run credential/artifact and diff checks**

Run:

```powershell
git diff --check
rg --files -g '.env' -g '*credential*.json' -g '*credentials*.json' -g '*service-account*.json' -g '*service_account*.json' -g 'application_default_credentials.json'
git status --short --branch
```

Expected: no secret artifact, no whitespace error, only scoped local changes.

- [ ] **Step 5: Run live endpoint acceptance**

Start the real FastAPI app with the approved project and feature flag. Wait only for the bounded manager readiness state, then issue: cold first endpoint, warm second endpoint, two additional sequential warm endpoints, and two concurrent endpoint requests at `25.0375, 121.5645`.

For every accepted response record elapsed time, HTTP/result status, JPEG dimensions, provider JPEG bytes, serialized response bytes, and leakage scans. All accepted responses must complete within eight seconds and expose no provider URL or credential marker.

- [ ] **Step 6: Request one independent review**

Review the complete local diff specifically for worker/process leaks, stale credentials, unbounded queues or replacement, unsafe cancellation, hidden retries, provider URL leakage, weakened deadline semantics, concurrency regressions, and shutdown cleanup.

- [ ] **Step 7: Fix all Critical/Important findings test-first**

For each finding, add a failing regression test, verify RED, make the smallest fix, and rerun the focused and full relevant regression suites. Do not implement optional scope.

- [ ] **Step 8: Final verification and commit decision**

Use `superpowers:verification-before-completion`. Keep all work local. Decide final commit structure from the resulting scoped diff and existing history; do not push, merge, rebase, or rewrite the earlier specification commit.
