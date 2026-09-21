# Earth Engine Persistent Worker Architecture Design

**Status:** Approved and implemented locally

**Date:** 2026-09-20

**Scope:** Earth Engine Satellite Reference V1 provider execution only

## 1. Purpose

Replace the per-request disposable Earth Engine process with the smallest safe
process-local persistent-worker architecture that can reuse Earth Engine
initialization while preserving the existing eight-second absolute request
deadline, concurrency bounds, security boundary, and truth boundary.

Earth Engine remains an optional bounded capability. Its initialization or
runtime failure must never prevent unrelated FastAPI routes from serving.

## 2. Problem Statement

The existing endpoint creates a new spawned child process for every accepted
request. Each child imports the Earth Engine client, discovers Application
Default Credentials (ADC), initializes Earth Engine, builds and executes the
fixed Sentinel-2 query, downloads one JPEG, returns an allowlisted result, and
exits. Measured complete cold provider execution is slower than the eight-second
absolute request deadline. A cache inside the current child cannot help because
the child is destroyed after one request.

The current design provides strong timeout containment, but it makes every
request cold. The replacement must reuse initialization without allowing a
timed-out provider call to survive indefinitely or allowing process, queue, or
retry growth.

## 3. Goals

- Maintain at most two live Earth Engine worker processes in one FastAPI
  process.
- Reuse one successful Earth Engine initialization for sequential requests in
  each worker.
- Process at most one request at a time in each worker.
- Admit at most four requests: two active and two queued.
- Preserve the eight-second absolute request deadline, including admission
  queueing, worker acquisition, IPC, provider work, JPEG validation, and result
  return.
- Terminate and join a timed-out or unhealthy worker before accepting any late
  result from it.
- Restore lost capacity with at most one bounded replacement attempt for each
  worker-loss lifecycle event, without replaying the failed request.
- Remove the explicit collection-size round trip from the critical path.
- Keep credentials, provider URLs, and Earth Engine client state in the worker.
- Start and stop workers through the FastAPI lifespan without making successful
  Earth Engine readiness a prerequisite for the rest of the application.

## 4. Non-Goals

- Increasing the request deadline.
- Adding application retries, provider retries, request replay, or backoff.
- Adding Redis, Celery, an external daemon, another cloud service, or a durable
  job queue.
- Adding exports, Earth Engine batch tasks, Drive or Cloud Storage delivery, or
  background imagery work.
- Persisting credentials, provider responses, provider URLs, or preview images.
- Accepting caller-selected datasets, bands, dates, geometry, reducers,
  visualization expressions, projects, or Earth Engine expressions.
- Claiming scene count, temporal completeness, cloud-free completeness,
  coverage completeness, current imagery, or legal/cadastral truth.

## 5. Frozen Product Contract

The implementation must preserve all of the following values and behaviors:

| Contract | Frozen value |
|---|---|
| Worker processes | Maximum two live per FastAPI process |
| Admission | Maximum two active plus two queued |
| Absolute request deadline | 8.0 seconds |
| Dataset | `COPERNICUS/S2_SR_HARMONIZED` |
| Date window | Fixed trailing 90 days |
| Area of interest | Exact 500 m circular buffer |
| Scene metadata cloud filter | `CLOUDY_PIXEL_PERCENTAGE <= 35` |
| SCL exclusions | `3, 8, 9, 10, 11` |
| Composite | Median |
| RGB bands | `B4`, `B3`, `B2` |
| Maximum preview dimensions | 512 by 512 pixels |
| Provider JPEG limit | 250,000 bytes |
| Serialized API response limit | 365,000 bytes |
| Application retries | Zero |
| Earth Engine SDK retries | Zero |
| HTTP thumbnail retries | Zero |
| Exports | Zero |
| Batch jobs | Zero |
| Persistence | Zero |
| Caller-provided Earth Engine expressions | Zero |

The exact disclaimer remains:

> Satellite reference imagery — not cadastral or statutory evidence.

## 6. Current Execution Audit

`fetch_satellite_reference` submits admitted work to a dedicated two-thread
executor. A four-slot bounded semaphore admits two executing and two queued
requests. Each executor task acquires a two-slot process semaphore and calls
`_run_in_terminated_process`, which creates a new process using the `spawn`
context.

The parent establishes a monotonic deadline before executor submission. The
deadline therefore includes executor queue time. Before starting or waiting for
the child, the implementation reserves approximately 0.5 seconds for process
termination. On timeout, the parent terminates, joins, and if necessary kills
the child. The child is also closed after a successful response.

The disposable child owns the imported Earth Engine module, ADC credentials,
Earth Engine global state, HTTP session, generated query graph, temporary
thumbnail URL, and JPEG bytes. No state survives to serve another request.

## 7. Earth Engine State Reuse

Each persistent worker owns one Earth Engine client session for exactly one
server-selected project. A worker processes requests sequentially, so its
process-global Earth Engine state is never mutated concurrently.

Worker initialization performs these steps once:

1. Import the Earth Engine client inside the worker.
2. Discover ADC with `google.auth.default()`.
3. Refresh credentials once when they are not valid; classify discovery or
   refresh failure as `credential_unavailable`.
4. Set Earth Engine SDK maximum retries to zero before initialization.
5. Call `ee.Initialize(credentials=credentials, project=fixed_project)` and
   classify its provider/network/service/protocol failures separately as
   `initialization_unavailable`.
6. Publish an allowlisted readiness outcome to the parent.

Google-auth may refresh an expired access token as part of normal credential
use. That protocol action is not an application request retry. The application
does not catch a failed operation and submit it again.

Sequential reuse is permitted because the project never changes, only one
request executes in the worker at a time, and the Earth Engine client retains
credentials, API resources, and its HTTP session in process state. Concurrent
requests within one Earth Engine worker are prohibited.

## 8. Optional Capability Startup

FastAPI lifespan startup creates the worker manager and starts one
lifecycle-controlled startup controller. The manager captures the feature flag
and `EARTH_ENGINE_PROJECT` once, records `starting`, and begins one bounded
attempt to initialize two workers. The lifespan then yields immediately; it
does not wait for Earth Engine readiness before the application serves traffic.

The startup controller owns a fixed 20-second pool-readiness deadline. This
startup deadline is separate from, and does not change, the eight-second
request deadline. The controller is manager-owned, process-local, singular,
and joined during shutdown. It is not an unbounded detached task.

Worker readiness is optional application state:

- If both workers initialize, the manager records `available`.
- If a worker reports an initialization failure, exits, or misses the startup
  deadline, the manager terminates and joins all partially started workers and
  records an allowlisted unavailable reason.
- While the manager is `starting`, satellite requests fail closed immediately
  with the existing bounded provider-unavailable semantics and never enter the
  admission queue.
- Earth Engine readiness success is never a prerequisite for FastAPI startup.
  Initialization failure is not raised out of the startup controller, and
  unrelated routes remain available throughout the attempt and afterward.
- If the feature is disabled, no Earth Engine process starts.
- If the project is absent, no Earth Engine process starts and the existing
  credential-unavailable response remains in force.

The endpoint never starts an unbounded initialization attempt on demand. When
the manager is unavailable, satellite requests fail closed quickly while
unrelated routes remain unaffected.

## 9. Components

### 9.1 Worker Manager

A process-local manager is the sole owner of exactly two fixed worker slots,
the four-slot admission bound, the two-thread request executor, worker
generation state, replacement state, worker lifecycle locks, the fixed
`EARTH_ENGINE_PROJECT` snapshot, and shutdown state. It exposes bounded
`start`, `fetch`, and `shutdown` operations.

Routes and services do not create a second semaphore, executor, process pool,
worker manager, generation registry, or replacement controller. They do not
re-read or pass a different project value per request. The manager lifecycle's
project snapshot is the only project used by its workers.

The manager state is one of `stopped`, `starting`, `available`, `unavailable`,
or `closing`. Only `available` accepts provider work. State transitions are
serialized under one manager lock.

### 9.2 Worker Slot

Each slot owns one process, one private duplex pipe, one generation number, and
at most one in-flight request identifier. A slot cannot be assigned twice.

A replacement process is not started until the prior process is confirmed dead
and joined. The slot generation increments on replacement, making responses
from an older connection invalid even if their request identifiers collide.

### 9.3 Worker Process

The worker initializes Earth Engine once, then runs a blocking command loop. It
accepts only the closed request DTO defined below. For each request it builds the
fixed query locally, performs thumbnail creation and download, validates the
JPEG, and returns one closed result DTO. It never handles two requests
concurrently.

### 9.4 FastAPI Lifespan Integration

The existing lifespan starts the manager's bounded startup controller before
`yield` but does not await readiness. Its teardown path calls manager shutdown,
which joins or stops both startup and replacement control-plane work. Earth
Engine startup errors are recorded, not raised. Existing database-pool cleanup
remains intact even when Earth Engine shutdown reports an internal cleanup
failure.

## 10. Strict IPC Contract

IPC messages contain only primitive values in fixed, versioned tuple or frozen
dataclass shapes. The receiver validates the message kind, field count, field
types, slot generation, and request identifier before using it.

### 10.1 Parent-to-Worker Request

`SatelliteWorkerRequest` contains only:

- protocol version,
- slot generation,
- opaque server-generated request identifier,
- latitude,
- longitude,
- server-computed window start,
- server-computed window end.

The worker validates finite coordinate ranges and an exact 90-day interval. All
other processing values are constants in worker code. The request contains no
dataset name, bands, arbitrary geometry, Earth Engine expression, callable,
provider URL, credentials, environment dictionary, or serialized exception.

### 10.2 Worker-to-Parent Result

`SatelliteWorkerResult` contains only:

- protocol version,
- slot generation,
- matching request identifier,
- one outcome from `available`, `credential_unavailable`,
  `image_generation_failed`, or `provider_error`,
- JPEG bytes only when the outcome is `available`.

Worker readiness uses a separate closed result shape with protocol version,
slot generation, and exactly one outcome: `ready`, `credential_unavailable`,
or `initialization_unavailable`. ADC discovery or credential-refresh failure
maps to `credential_unavailable`. An Earth Engine provider, network, service,
or protocol failure during `ee.Initialize` maps to
`initialization_unavailable`, which becomes the existing public
`provider_error` unavailable response. Missing or unusable server project
configuration retains the current public credential/configuration-unavailable
semantics and is handled before workers start.

No result contains a provider URL, credentials, bearer token, raw exception,
stack trace, project identifier, or Earth Engine object.

The parent accepts a result only when its protocol version, slot generation,
and request identifier exactly match the slot's current assignment. A mismatch
is a protocol violation: the result is discarded, the worker is terminated and
joined, and the request fails closed.

When a worker times out, its pipe and generation are retired with the worker.
Consequently, a late response cannot be consumed by a later request.

## 11. Request Flow and Admission

1. The route validates finite latitude and longitude and consults the sole
   manager's lifecycle snapshot and availability state. It does not re-read or
   pass a per-request project value.
2. The service establishes the monotonic eight-second absolute deadline, then
   computes the fixed trailing 90-day response/query window.
3. Before executor submission, the request attempts to acquire one of exactly
   four admission slots without blocking. Failure returns the existing bounded
   unavailable provider-error response.
4. The service submits to the existing two-thread executor without replacing
   or extending the deadline established at service entry.
5. Executor queue time consumes the same deadline. At most two executor tasks
   can become active, leaving at most two admitted tasks queued.
6. The executor callable re-checks the request's cancellation/expiry control
   before worker acquisition. A cancelled or expired request returns without
   acquiring a worker.
7. An active task acquires one idle worker slot using only its remaining time,
   then re-checks cancellation and the deadline immediately before IPC. If the
   request became stale, the worker returns to idle without receiving it.
8. The parent sends one validated IPC request and waits for the matching result
   using the remaining deadline minus the fixed cleanup reserve.
9. A valid JPEG result is returned to the service; the worker slot becomes idle.
10. The service base64-encodes the bytes, builds the allowlisted response, and
   enforces both the serialized response-byte cap and the original absolute
   deadline before returning. If response construction exhausts the deadline,
   the image is discarded and the service returns the bounded timeout response.
11. The admission slot is released exactly once by the async request owner on
    every path, including queue cancellation, deadline expiry, and worker
    containment.

No failed request is replayed or moved to another worker.

Each admitted request has a small thread-safe control object containing its
absolute deadline and a cancellation/expiry flag. If the client cancels or the
deadline expires while its future is still queued, the async owner marks the
control object stale and cancels the queued future when possible. A callable
that wins the queue race must still perform both mandatory re-checks above. A
stale request cannot acquire a worker, send IPC, or begin a provider operation.

## 12. Scene Count and Success Semantics

Scene count is **not required** for the preview contract. The implementation
removes `collection.size().getInfo()` and does not replace it with an inferred,
placeholder, or fake value.

The worker performs only the fixed thumbnail-create call and the bounded JPEG
download. Success requires all of the following:

- Earth Engine accepts thumbnail creation for the fixed query,
- the server downloads a non-empty `image/jpeg` payload,
- the payload is no larger than 250,000 bytes,
- JPEG start and end signatures are valid,
- decoded JPEG dimensions are positive and no larger than 512 by 512.

`status="available"` means only:

> The bounded Earth Engine pipeline successfully produced and validated a
> reference JPEG for this request.

It does not mean or imply a number of contributing scenes, sufficient temporal
coverage, cloud-free completeness, imagery quality, coverage completeness,
currency, parcel identity, cadastral boundary, ownership, zoning, legal status,
or statutory planning truth.

If an empty or unusable collection cannot produce a valid preview, the worker
returns an allowlisted image-generation/provider failure and the service fails
closed with the existing unavailable semantics. No separate provider request is
made to classify zero, one, or multiple scenes. The public response model may
retain `limited` for compatibility, but this worker path does not emit a
scene-count-derived limited status.

## 13. Retry Policy and Remote Calls

Application request retries are zero. The worker submits each accepted request
to Earth Engine once.

Earth Engine SDK retries are zero. Initialization calls
`ee.data.setMaxRetries(0)` before `ee.Initialize`; tests must prove the zero
value is configured before initialization and that one failed operation is not
resubmitted.

The thumbnail downloader uses one redirect-rejecting `urllib` request and has no
retry adapter. Redirects remain rejected. No other HTTP client or retry wrapper
is introduced.

After initialization, one successful request has exactly two provider network
operations in its critical path:

1. Earth Engine thumbnail creation.
2. HTTPS JPEG retrieval from the allowlisted Earth Engine host.

The removed operation is the separate compute-value call generated by
`collection.size().getInfo()`.

## 14. Deadline, Failure, and Replacement Semantics

### Worker Available

The request is sent once and the matching result is accepted only before the
absolute deadline.

### Worker Busy

At most two additional admitted requests wait in the executor queue. Waiting
consumes their eight-second deadline.

### Queue Full

The fifth concurrent request is not submitted. It fails closed immediately and
does not create a thread, process, IPC message, or provider operation.

### Initialization Failure

Initialization failure categories remain truthful and allowlisted:

- ADC discovery or credential refresh failure reports
  `credential_unavailable`.
- Missing or unusable server project configuration retains the existing public
  credential/configuration-unavailable semantics without starting workers.
- Earth Engine provider, network, service, or protocol failure during
  `ee.Initialize` reports `initialization_unavailable` internally and maps to
  the bounded public `provider_error` response.

Raw exceptions, HTTP bodies, tokens, stack traces, provider details, and
credentials remain inside the child. The manager records the capability
unavailable, cleans up partial workers, and lets FastAPI continue serving
unrelated routes.

### Worker Crash or Protocol Violation

EOF, unexpected exit, invalid message shape, generation mismatch, or request-ID
mismatch causes the current request to fail closed. The worker is joined or
terminated, its connection is discarded, and its request is never replayed.

### Provider Timeout or Request Deadline Exceeded

The assigned worker is terminated and joined within the existing cleanup
reserve. If it does not exit after terminate, it is killed and joined. The
request and any late result are discarded. No provider work from that worker is
allowed to continue indefinitely after the response path completes.

### Queued Cancellation or Expiry

If cancellation or deadline expiry occurs while the request is queued, the
async owner cancels its future when possible and marks its control object stale.
The executor callable checks that state before worker acquisition and again
before IPC. Even if cancellation races with executor startup, a stale request
cannot reach a worker or begin an Earth Engine operation. The admission slot is
released exactly once, and no request is replayed.

### Active Client Cancellation

If a client cancellation occurs while a worker owns the request, the manager
uses the same terminate-and-join containment path before releasing capacity.
The cancelled request is never replayed.

### Capacity Restoration

After a worker is confirmed dead, the manager may schedule exactly one bounded
replacement attempt for that slot and lifecycle event. Replacement is control
plane maintenance only: it does not contain or replay user query data.

Replacement rules are:

- no more than two worker processes may be live at once,
- one replacement attempt is guarded by the slot generation and one in-flight
  replacement flag,
- replacement uses the same fixed 20-second readiness bound,
- replacement never delays or changes the failed request result,
- replacement failure marks the manager unavailable,
- no automatic replacement loop follows a failed replacement,
- restoring service after failed replacement requires an explicit manager/app
  restart.

If the one replacement attempt fails, the manager transitions to
`unavailable`, stops accepting Earth Engine requests, terminates and joins every
remaining healthy worker, closes and retires every worker pipe, and leaves zero
Earth Engine worker processes alive. It does not retain a partially usable
one-worker pool and does not start another recovery loop.

The replacement controller itself is process-local and singular. It cannot
create user-visible jobs, run Earth Engine queries, or outlive manager shutdown.

## 15. Shutdown Semantics

Shutdown first marks the manager `closing`, preventing new admission. It then:

1. Cancels pending capacity-restoration work that has not started.
2. Waits only a fixed bounded interval for a started replacement controller.
3. Sends one allowlisted shutdown command to each responsive worker.
4. Joins workers within a fixed grace interval.
5. Terminates and, if necessary, kills and joins stragglers.
6. Closes every pipe and the request executor.
7. Clears slot state and records `stopped`.

Shutdown is idempotent. No worker may remain in `multiprocessing.active_children`
after shutdown completes.

## 16. Security and Privacy Boundaries

- ADC discovery and token refresh occur only inside worker processes.
- No credential JSON, API key, bearer token, or environment dictionary crosses
  IPC or enters the repository.
- The project is captured from `EARTH_ENGINE_PROJECT` during manager startup;
  callers cannot select or override it.
- The temporary provider URL remains worker-local, is host/scheme/query-key
  validated, is used once, and is never returned or logged.
- Child exceptions are converted to allowlisted categorical outcomes.
- Logs may include slot number, generation, request identifier, outcome, and
  bounded timings, but never coordinates, provider URLs, credentials, tokens,
  JPEG data, or raw provider errors.
- The preview remains component-memory-only and is not attached to saved cases
  or durable Evidence.

## 17. Test Strategy

Implementation follows RED→GREEN test-driven development. Before production
code changes, tests must fail for each new behavior:

- manager never owns more than two live workers,
- the fifth concurrent request fails closed before submission,
- the manager is the single owner of admission, executor, worker, generation,
  replacement, and fixed project state,
- FastAPI serves unrelated routes while the bounded startup controller is still
  initializing Earth Engine,
- a warm worker handles sequential requests without repeated initialization,
- each worker initializes exactly once with its fixed project,
- Earth Engine SDK retry count is set to zero before initialization,
- one failed provider request is never replayed,
- the scene-count compute-value call is absent,
- successful JPEG generation returns preview-availability status without a
  scene-count claim,
- ADC/refresh failure and Earth Engine initialization failure map to different
  allowlisted categories while unrelated FastAPI routes remain available,
- worker crash fails the request and triggers at most one bounded replacement,
- replacement failure marks the manager unavailable without looping, cleans up
  the other worker, closes all pipes, and leaves zero workers alive,
- timeout kills and joins the assigned worker and cannot leak worker count,
- stale generation or request-ID results are rejected and cannot cross requests,
- queued cancellation/deadline races cannot acquire a worker or send IPC and
  release admission exactly once,
- active cancellation contains the assigned worker,
- provider URLs, credentials, tokens, projects, coordinates, and raw errors do
  not leak through responses or logs,
- no export, batch task, persistence, retry, or background imagery operation is
  invoked,
- shutdown is idempotent and leaves no child workers.

Regression includes the Earth Engine-focused tests, endpoint/config/security
tests, explicit concurrency/deadline tests, relevant Python regression, a
credential/artifact scan, and `git diff --check`.

## 18. Live Acceptance

Live acceptance uses the existing fixture coordinate `25.0375, 121.5645` and
the configured Earth Engine project. It runs against the actual FastAPI endpoint
with no mocks.

The sequence is:

1. Cold service start and first endpoint request after bounded lifespan startup.
2. Same-service second endpoint request.
3. Two additional sequential warm requests.
4. Two concurrent accepted requests.

For every accepted request, GO requires:

- HTTP 200 with `status="available"`,
- a real server-mediated JPEG,
- dimensions no larger than 512 by 512,
- provider payload no larger than 250,000 bytes,
- serialized API response no larger than 365,000 bytes,
- no provider URL or credential material in the response or logs,
- completion within the same eight-second absolute deadline.

Observed timings may be summarized as a small-sample P50-like value, explicitly
without a statistical reliability claim.

## 19. Files Expected to Change During Implementation

- `services/earth_engine_worker_pool.py`: new process-local manager, worker
  slots, strict IPC DTOs, lifecycle, timeout containment, and replacement.
- `services/adapters/earth_engine_adapter.py`: split once-per-worker
  initialization from request execution, disable SDK retries, and remove the
  scene-count request.
- `services/satellite_reference.py`: dispatch through the persistent manager,
  preserve admission/deadline/response bounds, and define preview-only success.
- `backend/api_main.py`: optional startup and unconditional bounded shutdown in
  FastAPI lifespan.
- `tests/test_earth_engine_worker_pool.py`: worker lifecycle, IPC, concurrency,
  timeout, crash, replacement, and shutdown tests.
- `tests/test_satellite_reference.py`: adapter/service/API/security contract
  updates and scene-count removal tests.
- `docs/satellite-reference-evidence-v1.md`: operational architecture,
  preview-availability semantics, zero-retry policy, and shutdown behavior.

No database, frontend API shape, persistent storage, external infrastructure,
or deployment service is added.

## 20. Acceptance Decision

The implementation is GO only if all automated tests pass and every live
accepted endpoint request described above returns a valid bounded JPEG within
eight seconds. If persistent initialization reuse and scene-count removal still
cannot reliably satisfy the deadline, the deadline remains unchanged and the
result is NO-GO for a separate architecture decision.
