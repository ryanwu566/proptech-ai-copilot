"""Bounded persistent process isolation for Earth Engine preview generation."""

from __future__ import annotations

import asyncio
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date
import math
import multiprocessing
import queue
import threading
import time
from typing import Any, Callable, Literal
from uuid import uuid4

from services.satellite_reference import (
    AOI_RADIUS_M,
    CLOUD_FILTER_PERCENT,
    DATASET_ID,
    MAX_PROVIDER_IMAGE_BYTES,
    WINDOW_DAYS,
    EarthEngineCredentialUnavailable,
    EarthEngineFeatureDisabled,
    EarthEngineImageGenerationError,
    EarthEngineInitializationUnavailable,
    EarthEngineProviderError,
    EarthEngineProviderTimeout,
    SatelliteQuery,
)


PROTOCOL_VERSION = 1
MAX_LIVE_WORKERS = 2
MAX_QUEUED_REQUESTS = 2
MAX_ADMITTED_REQUESTS = MAX_LIVE_WORKERS + MAX_QUEUED_REQUESTS
STARTUP_TIMEOUT_SECONDS = 20.0
_STOP_GRACE_SECONDS = 0.25
_POLL_SECONDS = 0.025
_CLEANUP_RESERVE_SECONDS = 0.5
_READY_OUTCOMES = {"ready", "credential_unavailable", "initialization_unavailable"}
_RESULT_OUTCOMES = {
    "available",
    "credential_unavailable",
    "image_generation_failed",
    "provider_error",
}


@dataclass(frozen=True)
class SatelliteWorkerRequest:
    version: int
    generation: int
    request_id: str
    latitude: float
    longitude: float
    window_start: str
    window_end: str


@dataclass(frozen=True)
class SatelliteWorkerResult:
    version: int
    generation: int
    request_id: str
    outcome: Literal[
        "available",
        "credential_unavailable",
        "image_generation_failed",
        "provider_error",
    ]
    image_bytes: bytes | None


@dataclass(frozen=True)
class SatelliteWorkerReady:
    version: int
    generation: int
    outcome: Literal["ready", "credential_unavailable", "initialization_unavailable"]


@dataclass
class RequestControl:
    """Thread-safe request expiry/cancellation marker shared with executor work."""

    deadline: float
    _stale: threading.Event = field(default_factory=threading.Event, init=False, repr=False)

    def mark_stale(self) -> None:
        self._stale.set()

    def is_stale(self) -> bool:
        return self._stale.is_set() or time.monotonic() >= self.deadline


@dataclass
class _WorkerSlot:
    index: int
    generation: int
    process: Any
    connection: Any
    request_id: str | None = None


def _valid_worker_request(message: object, generation: int) -> bool:
    if type(message) is not SatelliteWorkerRequest:
        return False
    request = message
    try:
        interval = (date.fromisoformat(request.window_end) - date.fromisoformat(request.window_start)).days
    except (TypeError, ValueError):
        return False
    return (
        request.version == PROTOCOL_VERSION
        and request.generation == generation
        and isinstance(request.request_id, str)
        and 0 < len(request.request_id) <= 128
        and isinstance(request.latitude, (int, float))
        and not isinstance(request.latitude, bool)
        and math.isfinite(request.latitude)
        and -90 <= request.latitude <= 90
        and isinstance(request.longitude, (int, float))
        and not isinstance(request.longitude, bool)
        and math.isfinite(request.longitude)
        and -180 <= request.longitude <= 180
        and interval == WINDOW_DAYS
    )


def _earth_engine_worker_entry(
    connection: Any,
    project: str,
    generation: int,
    _slot_index: int,
) -> None:
    """Initialize once, then process one fixed request at a time."""

    from services.adapters.earth_engine_adapter import EarthEngineSatelliteAdapter

    adapter = EarthEngineSatelliteAdapter(project=project)
    try:
        adapter.initialize()
    except EarthEngineCredentialUnavailable:
        connection.send(SatelliteWorkerReady(PROTOCOL_VERSION, generation, "credential_unavailable"))
        connection.close()
        return
    except (EarthEngineInitializationUnavailable, BaseException):
        try:
            connection.send(SatelliteWorkerReady(PROTOCOL_VERSION, generation, "initialization_unavailable"))
        finally:
            connection.close()
        return

    connection.send(SatelliteWorkerReady(PROTOCOL_VERSION, generation, "ready"))
    try:
        while True:
            try:
                message = connection.recv()
            except EOFError:
                return
            if message == ("shutdown", PROTOCOL_VERSION, generation):
                return
            if not _valid_worker_request(message, generation):
                return

            query = SatelliteQuery(
                latitude=float(message.latitude),
                longitude=float(message.longitude),
                dataset=DATASET_ID,
                window_start=message.window_start,
                window_end=message.window_end,
                aoi_radius_m=AOI_RADIUS_M,
                cloud_filter_percent=CLOUD_FILTER_PERCENT,
                rgb_bands=("B4", "B3", "B2"),
                excluded_scl_classes=(3, 8, 9, 10, 11),
                dimensions=(512, 512),
                image_format="jpg",
            )
            try:
                image_bytes = adapter.fetch_initialized(query).image_bytes
                result = SatelliteWorkerResult(
                    PROTOCOL_VERSION,
                    generation,
                    message.request_id,
                    "available",
                    image_bytes,
                )
            except EarthEngineCredentialUnavailable:
                result = SatelliteWorkerResult(
                    PROTOCOL_VERSION,
                    generation,
                    message.request_id,
                    "credential_unavailable",
                    None,
                )
            except EarthEngineImageGenerationError:
                result = SatelliteWorkerResult(
                    PROTOCOL_VERSION,
                    generation,
                    message.request_id,
                    "image_generation_failed",
                    None,
                )
            except BaseException:
                result = SatelliteWorkerResult(
                    PROTOCOL_VERSION,
                    generation,
                    message.request_id,
                    "provider_error",
                    None,
                )
            connection.send(result)
    finally:
        connection.close()


class EarthEngineWorkerManager:
    """Own exactly two bounded Earth Engine worker slots for one fixed project."""

    def __init__(
        self,
        *,
        context: Any | None = None,
        worker_target: Callable[..., None] = _earth_engine_worker_entry,
        worker_target_args: tuple[Any, ...] = (),
        startup_timeout_seconds: float = STARTUP_TIMEOUT_SECONDS,
        replacement_timeout_seconds: float | None = None,
    ) -> None:
        self._context = context or multiprocessing.get_context("spawn")
        self._worker_target = worker_target
        self._worker_target_args = worker_target_args
        self._startup_timeout_seconds = startup_timeout_seconds
        self._replacement_timeout_seconds = replacement_timeout_seconds or startup_timeout_seconds
        self._lock = threading.RLock()
        self._state = "stopped"
        self._unavailable_reason = "provider_error"
        self._project: str | None = None
        self._slots: dict[int, _WorkerSlot] = {}
        self._idle_slots: queue.Queue[_WorkerSlot] = queue.Queue(maxsize=MAX_LIVE_WORKERS)
        self._shutdown_event = threading.Event()
        self._startup_thread: threading.Thread | None = None
        self._replacement_thread: threading.Thread | None = None
        self._replacement_events: queue.Queue[tuple[int, int]] = queue.Queue()
        self._replacement_attempts: set[tuple[int, int]] = set()
        self._admission_slots = threading.BoundedSemaphore(MAX_ADMITTED_REQUESTS)
        self._admitted_requests = 0
        self._executor: ThreadPoolExecutor | None = None

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def unavailable_reason(self) -> str:
        with self._lock:
            return self._unavailable_reason

    @property
    def live_worker_count(self) -> int:
        with self._lock:
            return sum(slot.process.is_alive() for slot in self._slots.values())

    @property
    def available_admission_slots(self) -> int:
        with self._lock:
            return MAX_ADMITTED_REQUESTS - self._admitted_requests

    def start(self, *, enabled: bool, project: str) -> None:
        """Capture configuration and start one non-blocking bounded readiness controller."""

        with self._lock:
            if self._state != "stopped":
                return
            self._shutdown_event.clear()
            self._replacement_attempts.clear()
            self._drain_replacements_locked()
            self._project = project.strip()
            if not enabled:
                self._state = "unavailable"
                self._unavailable_reason = "feature_disabled"
                return
            if not self._project:
                self._state = "unavailable"
                self._unavailable_reason = "credential_unavailable"
                return
            self._admission_slots = threading.BoundedSemaphore(MAX_ADMITTED_REQUESTS)
            self._admitted_requests = 0
            self._executor = ThreadPoolExecutor(
                max_workers=MAX_LIVE_WORKERS,
                thread_name_prefix="earth-engine-reference",
            )
            self._state = "starting"
            self._unavailable_reason = "provider_error"
            self._startup_thread = threading.Thread(
                target=self._startup_controller,
                name="earth-engine-startup",
                daemon=True,
            )
            self._startup_thread.start()

    async def fetch(
        self,
        *,
        latitude: float,
        longitude: float,
        window_start: str,
        window_end: str,
        deadline: float,
    ) -> bytes:
        """Admit and execute one request within its original absolute deadline."""

        self._raise_if_unavailable()
        if not self._admission_slots.acquire(blocking=False):
            raise EarthEngineProviderError("Earth Engine request capacity is unavailable")
        with self._lock:
            self._admitted_requests += 1
            executor = self._executor
        control = RequestControl(deadline=deadline)
        future: Future[bytes] | None = None
        wrapped: asyncio.Future[bytes] | None = None
        try:
            if executor is None or control.is_stale():
                raise EarthEngineProviderTimeout("Earth Engine operation timed out")
            future = executor.submit(
                self._execute_request,
                latitude=latitude,
                longitude=longitude,
                window_start=window_start,
                window_end=window_end,
                deadline=deadline,
                control=control,
            )
            wrapped = asyncio.wrap_future(future, loop=asyncio.get_running_loop())
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                control.mark_stale()
                future.cancel()
                raise EarthEngineProviderTimeout("Earth Engine operation timed out")
            done, _ = await asyncio.wait({wrapped}, timeout=remaining)
            if not done:
                control.mark_stale()
                future.cancel()
                await self._await_containment(wrapped)
                raise EarthEngineProviderTimeout("Earth Engine operation timed out")
            return wrapped.result()
        except asyncio.CancelledError:
            control.mark_stale()
            if future is not None:
                future.cancel()
            if wrapped is not None:
                await self._await_containment(wrapped)
            raise
        finally:
            with self._lock:
                self._admitted_requests -= 1
            self._admission_slots.release()

    async def _await_containment(self, wrapped: asyncio.Future[bytes]) -> None:
        if wrapped.cancelled() or wrapped.done():
            return
        try:
            await asyncio.wait_for(
                asyncio.shield(wrapped),
                timeout=_CLEANUP_RESERVE_SECONDS,
            )
        except (asyncio.TimeoutError, asyncio.CancelledError, Exception):
            return

    def _execute_request(
        self,
        *,
        latitude: float,
        longitude: float,
        window_start: str,
        window_end: str,
        deadline: float,
        control: RequestControl,
    ) -> bytes:
        """Send one request once and accept only its exact bounded response."""

        self._raise_if_unavailable()
        if control.is_stale() or deadline != control.deadline:
            raise EarthEngineProviderTimeout("Earth Engine operation timed out")

        slot = self._acquire_slot(deadline, control)
        request_id = uuid4().hex
        request = SatelliteWorkerRequest(
            version=PROTOCOL_VERSION,
            generation=slot.generation,
            request_id=request_id,
            latitude=latitude,
            longitude=longitude,
            window_start=window_start,
            window_end=window_end,
        )
        with self._lock:
            if (
                self._state != "available"
                or self._slots.get(slot.index) is not slot
                or control.is_stale()
            ):
                self._release_slot(slot)
                raise EarthEngineProviderTimeout("Earth Engine operation timed out")
            slot.request_id = request_id

        try:
            slot.connection.send(request)
        except BaseException as exc:
            self._retire_slot(slot, replace=True)
            raise EarthEngineProviderError("Earth Engine worker communication failed") from exc

        while True:
            remaining = deadline - time.monotonic()
            if control.is_stale() or remaining <= _CLEANUP_RESERVE_SECONDS:
                self._retire_slot(slot, replace=True)
                raise EarthEngineProviderTimeout("Earth Engine operation timed out")
            try:
                if slot.connection.poll(min(_POLL_SECONDS, remaining - _CLEANUP_RESERVE_SECONDS)):
                    result = slot.connection.recv()
                    break
            except (EOFError, OSError) as exc:
                self._retire_slot(slot, replace=True)
                raise EarthEngineProviderError("Earth Engine worker exited without a result") from exc
            if not slot.process.is_alive():
                self._retire_slot(slot, replace=True)
                raise EarthEngineProviderError("Earth Engine worker exited without a result")

        if not self._valid_result(result, slot, request_id):
            self._retire_slot(slot, replace=True)
            raise EarthEngineProviderError("Earth Engine worker protocol was rejected")

        self._release_slot(slot)
        if result.outcome == "available":
            return result.image_bytes
        if result.outcome == "credential_unavailable":
            raise EarthEngineCredentialUnavailable("Application Default Credentials are unavailable")
        if result.outcome == "image_generation_failed":
            raise EarthEngineImageGenerationError("Earth Engine thumbnail generation failed")
        raise EarthEngineProviderError("Earth Engine query failed")

    def shutdown(self) -> None:
        """Idempotently stop controller threads, workers, and every parent pipe."""

        with self._lock:
            if self._state == "stopped" and not self._slots:
                return
            self._state = "closing"
            self._shutdown_event.set()
            controller_threads = [self._startup_thread, self._replacement_thread]
            executor = self._executor

        for thread in controller_threads:
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout=_CLEANUP_RESERVE_SECONDS)

        with self._lock:
            slots = list(self._slots.values())
            self._slots.clear()
            self._drain_idle_locked()
        cleanup_error: EarthEngineProviderError | None = None
        for slot in slots:
            try:
                self._stop_slot(slot, graceful=True)
            except EarthEngineProviderError as exc:
                if cleanup_error is None:
                    cleanup_error = exc
                with self._lock:
                    self._slots[slot.index] = slot
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)

        with self._lock:
            self._drain_replacements_locked()
            self._replacement_attempts.clear()
            self._startup_thread = None
            self._replacement_thread = None
            self._executor = None
            self._project = None
            self._state = "unavailable" if self._slots else "stopped"
        if cleanup_error is not None:
            raise cleanup_error

    def _startup_controller(self) -> None:
        deadline = time.monotonic() + self._startup_timeout_seconds
        try:
            for index in range(MAX_LIVE_WORKERS):
                if self._shutdown_event.is_set():
                    return
                slot = self._spawn_slot(index=index, generation=1)
                with self._lock:
                    if self._state != "starting":
                        self._stop_slot(slot, graceful=False)
                        return
                    self._slots[index] = slot

            with self._lock:
                slots = list(self._slots.values())
            outcome = self._await_pool_ready(slots, deadline)
            if outcome != "ready":
                reason = "credential_unavailable" if outcome == "credential_unavailable" else "provider_error"
                self._mark_unavailable_and_cleanup(reason)
                return
            with self._lock:
                if self._state != "starting" or self._shutdown_event.is_set():
                    return
                for slot in slots:
                    self._idle_slots.put_nowait(slot)
                self._state = "available"
        except BaseException:
            self._mark_unavailable_and_cleanup("provider_error")

    def _spawn_slot(self, *, index: int, generation: int) -> _WorkerSlot:
        parent_connection, child_connection = self._context.Pipe(duplex=True)
        process = self._context.Process(
            target=self._worker_target,
            args=(
                child_connection,
                self._project,
                generation,
                index,
                *self._worker_target_args,
            ),
            daemon=True,
        )
        try:
            process.start()
        except BaseException:
            parent_connection.close()
            child_connection.close()
            raise
        child_connection.close()
        return _WorkerSlot(index, generation, process, parent_connection)

    def _await_pool_ready(self, slots: list[_WorkerSlot], deadline: float) -> str:
        pending = {slot.index: slot for slot in slots}
        while pending and not self._shutdown_event.is_set():
            if time.monotonic() >= deadline:
                return "initialization_unavailable"
            for index, slot in list(pending.items()):
                if not slot.process.is_alive():
                    return "initialization_unavailable"
                try:
                    if not slot.connection.poll(0):
                        continue
                    message = slot.connection.recv()
                except (EOFError, OSError):
                    return "initialization_unavailable"
                if (
                    type(message) is not SatelliteWorkerReady
                    or message.version != PROTOCOL_VERSION
                    or message.generation != slot.generation
                    or message.outcome not in _READY_OUTCOMES
                ):
                    return "initialization_unavailable"
                if message.outcome != "ready":
                    return message.outcome
                pending.pop(index)
            if pending:
                self._shutdown_event.wait(
                    timeout=min(_POLL_SECONDS, max(0, deadline - time.monotonic()))
                )
        return "ready" if not pending else "initialization_unavailable"

    def _await_ready(self, slot: _WorkerSlot, deadline: float) -> str:
        while not self._shutdown_event.is_set():
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return "initialization_unavailable"
            try:
                if slot.connection.poll(min(_POLL_SECONDS, remaining)):
                    message = slot.connection.recv()
                    if (
                        type(message) is SatelliteWorkerReady
                        and message.version == PROTOCOL_VERSION
                        and message.generation == slot.generation
                        and message.outcome in _READY_OUTCOMES
                    ):
                        return message.outcome
                    return "initialization_unavailable"
            except (EOFError, OSError):
                return "initialization_unavailable"
            if not slot.process.is_alive():
                return "initialization_unavailable"
        return "initialization_unavailable"

    def _raise_if_unavailable(self) -> None:
        with self._lock:
            state = self._state
            reason = self._unavailable_reason
        if state == "available":
            return
        if reason == "feature_disabled":
            raise EarthEngineFeatureDisabled("Earth Engine satellite reference is disabled")
        if reason == "credential_unavailable":
            raise EarthEngineCredentialUnavailable("Application Default Credentials are unavailable")
        raise EarthEngineProviderError("Earth Engine worker capacity is unavailable")

    def _acquire_slot(self, deadline: float, control: RequestControl) -> _WorkerSlot:
        while True:
            remaining = deadline - time.monotonic()
            if control.is_stale() or remaining <= _CLEANUP_RESERVE_SECONDS:
                raise EarthEngineProviderTimeout("Earth Engine operation timed out")
            try:
                return self._idle_slots.get(timeout=min(_POLL_SECONDS, remaining - _CLEANUP_RESERVE_SECONDS))
            except queue.Empty:
                self._raise_if_unavailable()

    @staticmethod
    def _valid_result(result: object, slot: _WorkerSlot, request_id: str) -> bool:
        if type(result) is not SatelliteWorkerResult:
            return False
        if (
            result.version != PROTOCOL_VERSION
            or result.generation != slot.generation
            or result.request_id != request_id
            or result.outcome not in _RESULT_OUTCOMES
        ):
            return False
        if result.outcome == "available":
            return (
                isinstance(result.image_bytes, bytes)
                and 0 < len(result.image_bytes) <= MAX_PROVIDER_IMAGE_BYTES
            )
        return result.image_bytes is None

    def _release_slot(self, slot: _WorkerSlot) -> None:
        with self._lock:
            slot.request_id = None
            if self._state == "available" and self._slots.get(slot.index) is slot:
                self._idle_slots.put_nowait(slot)

    def _retire_slot(self, slot: _WorkerSlot, *, replace: bool) -> None:
        with self._lock:
            if self._slots.get(slot.index) is not slot:
                return
        try:
            self._stop_slot(slot, graceful=False)
        except EarthEngineProviderError:
            with self._lock:
                self._state = "unavailable"
                self._unavailable_reason = "provider_error"
                self._slots[slot.index] = slot
                self._drain_idle_locked()
                self._drain_replacements_locked()
            raise
        with self._lock:
            if self._slots.get(slot.index) is slot:
                self._slots.pop(slot.index, None)
        if replace:
            self._schedule_replacement(slot.index, slot.generation)

    def _schedule_replacement(self, index: int, retired_generation: int) -> None:
        event = (index, retired_generation)
        with self._lock:
            if self._state != "available" or self._shutdown_event.is_set() or event in self._replacement_attempts:
                return
            stale_attempts = {
                attempt for attempt in self._replacement_attempts if attempt[0] == index
            }
            self._replacement_attempts.difference_update(stale_attempts)
            self._replacement_attempts.add(event)
            self._replacement_events.put_nowait(event)
            if self._replacement_thread is None or not self._replacement_thread.is_alive():
                self._start_replacement_controller_locked()

    def _start_replacement_controller_locked(self) -> None:
        self._replacement_thread = threading.Thread(
            target=self._replacement_controller,
            name="earth-engine-replacement",
            daemon=True,
        )
        self._replacement_thread.start()

    def _replacement_controller(self) -> None:
        current_thread = threading.current_thread()
        try:
            while not self._shutdown_event.is_set():
                try:
                    index, retired_generation = self._replacement_events.get_nowait()
                except queue.Empty:
                    return
                slot: _WorkerSlot | None = None
                try:
                    slot = self._spawn_slot(index=index, generation=retired_generation + 1)
                    with self._lock:
                        if self._state != "available" or self._shutdown_event.is_set():
                            self._stop_slot(slot, graceful=False)
                            return
                        self._slots[index] = slot
                    outcome = self._await_ready(
                        slot,
                        time.monotonic() + self._replacement_timeout_seconds,
                    )
                    if outcome != "ready":
                        reason = "credential_unavailable" if outcome == "credential_unavailable" else "provider_error"
                        self._mark_unavailable_and_cleanup(reason)
                        return
                    with self._lock:
                        if self._state != "available" or self._shutdown_event.is_set():
                            return
                        self._idle_slots.put_nowait(slot)
                except BaseException:
                    if slot is not None:
                        self._stop_slot(slot, graceful=False)
                    self._mark_unavailable_and_cleanup("provider_error")
                    return
        finally:
            with self._lock:
                if self._replacement_thread is current_thread:
                    self._replacement_thread = None
                    if (
                        self._state == "available"
                        and not self._shutdown_event.is_set()
                        and not self._replacement_events.empty()
                    ):
                        self._start_replacement_controller_locked()

    def _mark_unavailable_and_cleanup(self, reason: str) -> None:
        with self._lock:
            if self._state == "closing":
                return
            self._state = "unavailable"
            self._unavailable_reason = reason
            slots = list(self._slots.values())
            self._slots.clear()
            self._drain_idle_locked()
            self._drain_replacements_locked()
        for slot in slots:
            try:
                self._stop_slot(slot, graceful=False)
            except EarthEngineProviderError:
                with self._lock:
                    self._slots[slot.index] = slot

    @staticmethod
    def _stop_slot(slot: _WorkerSlot, *, graceful: bool) -> None:
        process = slot.process
        lifecycle_error: BaseException | None = None
        if graceful and process.is_alive():
            try:
                slot.connection.send(("shutdown", PROTOCOL_VERSION, slot.generation))
            except (EOFError, OSError, BrokenPipeError):
                pass
        try:
            if process.is_alive():
                process.join(timeout=_STOP_GRACE_SECONDS if graceful else 0)
            if process.is_alive():
                process.terminate()
                process.join(timeout=_STOP_GRACE_SECONDS)
            if process.is_alive() and hasattr(process, "kill"):
                process.kill()
                process.join(timeout=_STOP_GRACE_SECONDS)
        except (EOFError, OSError, BrokenPipeError, ValueError) as exc:
            lifecycle_error = exc
        try:
            slot.connection.close()
        except (EOFError, OSError, BrokenPipeError) as exc:
            if lifecycle_error is None:
                lifecycle_error = exc
        if process.is_alive():
            raise EarthEngineProviderError("Earth Engine worker could not be stopped") from lifecycle_error
        try:
            process.close()
        except ValueError as exc:
            if lifecycle_error is None:
                lifecycle_error = exc
        if lifecycle_error is not None:
            raise EarthEngineProviderError("Earth Engine worker cleanup failed") from lifecycle_error

    def _drain_idle_locked(self) -> None:
        while True:
            try:
                self._idle_slots.get_nowait()
            except queue.Empty:
                return

    def _drain_replacements_locked(self) -> None:
        while True:
            try:
                self._replacement_events.get_nowait()
            except queue.Empty:
                return


_MANAGER_LOCK = threading.Lock()
_MANAGER: EarthEngineWorkerManager | None = None


def get_earth_engine_worker_manager() -> EarthEngineWorkerManager:
    """Return the process-local manager without starting Earth Engine work."""

    global _MANAGER
    if _MANAGER is None:
        with _MANAGER_LOCK:
            if _MANAGER is None:
                _MANAGER = EarthEngineWorkerManager()
    return _MANAGER
