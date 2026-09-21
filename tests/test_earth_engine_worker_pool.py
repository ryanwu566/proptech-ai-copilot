"""Persistent Earth Engine worker isolation and lifecycle tests."""

from __future__ import annotations

import asyncio
from dataclasses import fields
import inspect
import multiprocessing
import os
import threading
import time

import pytest

from services import earth_engine_worker_pool as worker_pool
from services import satellite_reference as satellite


def _successful_worker(connection, project, generation, slot_index, observation_queue=None) -> None:
    if observation_queue is not None:
        observation_queue.put(("start", project, generation, slot_index))
    connection.send(worker_pool.SatelliteWorkerReady(1, generation, "ready"))
    try:
        while True:
            message = connection.recv()
            if isinstance(message, tuple) and message[0] == "shutdown":
                return
            if observation_queue is not None:
                observation_queue.put(("request", message))
            connection.send(
                worker_pool.SatelliteWorkerResult(
                    version=1,
                    generation=generation,
                    request_id=message.request_id,
                    outcome="available",
                    image_bytes=b"bounded-jpeg",
                )
            )
    except EOFError:
        return
    finally:
        connection.close()


def _mismatched_worker(connection, _project, generation, _slot_index) -> None:
    connection.send(worker_pool.SatelliteWorkerReady(1, generation, "ready"))
    try:
        message = connection.recv()
        if isinstance(message, tuple) and message[0] == "shutdown":
            return
        connection.send(
            worker_pool.SatelliteWorkerResult(
                version=1,
                generation=generation + 1,
                request_id=f"stale-{message.request_id}",
                outcome="available",
                image_bytes=b"wrong-request",
            )
        )
    finally:
        connection.close()


def _lifecycle_worker(connection, _project, generation, slot_index, mode, observations, starts) -> None:
    with starts.get_lock():
        starts[slot_index] += 1
    observations.put(("start", slot_index, generation, os.getpid()))
    if mode == "replacement_failure" and slot_index == 0 and generation > 1:
        connection.send(worker_pool.SatelliteWorkerReady(1, generation, "initialization_unavailable"))
        connection.close()
        return

    connection.send(worker_pool.SatelliteWorkerReady(1, generation, "ready"))
    try:
        while True:
            message = connection.recv()
            if isinstance(message, tuple) and message[0] == "shutdown":
                return
            observations.put(("request", slot_index, generation, message.request_id))
            if slot_index == 0 and generation == 1 and mode in {"crash", "replacement_failure"}:
                return
            if slot_index == 0 and generation == 1 and mode == "timeout":
                time.sleep(10)
                return
            connection.send(
                worker_pool.SatelliteWorkerResult(
                    1,
                    generation,
                    message.request_id,
                    "available",
                    b"bounded-jpeg",
                )
            )
    except EOFError:
        return
    finally:
        connection.close()


def _blocking_worker(connection, _project, generation, _slot_index, release_event, observations) -> None:
    connection.send(worker_pool.SatelliteWorkerReady(1, generation, "ready"))
    try:
        while True:
            message = connection.recv()
            if isinstance(message, tuple) and message[0] == "shutdown":
                return
            observations.put((message.latitude, message.request_id, os.getpid()))
            release_event.wait(timeout=5)
            connection.send(
                worker_pool.SatelliteWorkerResult(
                    1,
                    generation,
                    message.request_id,
                    "available",
                    b"bounded-jpeg",
                )
            )
    except EOFError:
        return
    finally:
        connection.close()


def _readiness_worker(connection, _project, generation, _slot_index, outcome, release_event=None) -> None:
    if release_event is not None:
        release_event.wait(timeout=5)
    connection.send(worker_pool.SatelliteWorkerReady(1, generation, outcome))
    if outcome == "ready":
        try:
            while True:
                message = connection.recv()
                if isinstance(message, tuple) and message[0] == "shutdown":
                    return
        except EOFError:
            return
    connection.close()


def _wait_for_state(manager, expected: str, timeout: float = 6.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if manager.state == expected:
            return
        time.sleep(0.01)
    raise AssertionError(f"manager state was {manager.state!r}, expected {expected!r}")


def _wait_until(predicate, timeout: float = 3.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.01)
    raise AssertionError("condition did not become true before timeout")


def test_manager_owns_exactly_two_worker_slots_and_never_starts_a_third() -> None:
    context = multiprocessing.get_context("spawn")
    observations = context.Queue()
    manager = worker_pool.EarthEngineWorkerManager(
        context=context,
        worker_target=_successful_worker,
        worker_target_args=(observations,),
        startup_timeout_seconds=5.0,
    )
    try:
        manager.start(enabled=True, project="fixed-project")
        _wait_for_state(manager, "available")
        manager.start(enabled=True, project="different-project")
        time.sleep(0.05)

        starts = [observations.get(timeout=1), observations.get(timeout=1)]
        assert manager.live_worker_count == 2
        assert sorted(item[3] for item in starts) == [0, 1]
        assert all(item[1] == "fixed-project" for item in starts)
        assert observations.empty()
    finally:
        manager.shutdown()

    assert manager.live_worker_count == 0


def test_request_dto_contains_only_version_generation_id_coordinate_and_dates() -> None:
    assert [field.name for field in fields(worker_pool.SatelliteWorkerRequest)] == [
        "version",
        "generation",
        "request_id",
        "latitude",
        "longitude",
        "window_start",
        "window_end",
    ]
    forbidden = {
        "project",
        "dataset",
        "bands",
        "geometry",
        "expression",
        "url",
        "credentials",
        "environment",
    }
    assert forbidden.isdisjoint(field.name for field in fields(worker_pool.SatelliteWorkerRequest))


def test_result_with_wrong_request_id_or_generation_is_rejected() -> None:
    manager = worker_pool.EarthEngineWorkerManager(
        worker_target=_mismatched_worker,
        startup_timeout_seconds=5.0,
        replacement_timeout_seconds=0.2,
    )
    try:
        manager.start(enabled=True, project="fixed-project")
        _wait_for_state(manager, "available")
        deadline = time.monotonic() + 1.0

        with pytest.raises(satellite.EarthEngineProviderError):
            asyncio.run(
                manager.fetch(
                    latitude=25.0375,
                    longitude=121.5645,
                    window_start="2026-06-22",
                    window_end="2026-09-20",
                    deadline=deadline,
                )
            )
    finally:
        manager.shutdown()


def test_manager_captures_project_once_and_never_accepts_per_request_project() -> None:
    signature = inspect.signature(worker_pool.EarthEngineWorkerManager.fetch)
    assert "project" not in signature.parameters

    context = multiprocessing.get_context("spawn")
    observations = context.Queue()
    manager = worker_pool.EarthEngineWorkerManager(
        context=context,
        worker_target=_successful_worker,
        worker_target_args=(observations,),
        startup_timeout_seconds=5.0,
    )
    try:
        manager.start(enabled=True, project="captured-project")
        _wait_for_state(manager, "available")
        deadline = time.monotonic() + 1.0
        asyncio.run(
            manager.fetch(
                latitude=25.0375,
                longitude=121.5645,
                window_start="2026-06-22",
                window_end="2026-09-20",
                deadline=deadline,
            )
        )

        observed = [observations.get(timeout=1) for _ in range(3)]
        assert [item[1] for item in observed if item[0] == "start"] == [
            "captured-project",
            "captured-project",
        ]
        request = next(item[1] for item in observed if item[0] == "request")
        assert isinstance(request, worker_pool.SatelliteWorkerRequest)
        assert not hasattr(request, "project")
    finally:
        manager.shutdown()


def _lifecycle_manager(mode: str):
    context = multiprocessing.get_context("spawn")
    observations = context.Queue()
    starts = context.Array("i", [0, 0])
    manager = worker_pool.EarthEngineWorkerManager(
        context=context,
        worker_target=_lifecycle_worker,
        worker_target_args=(mode, observations, starts),
        startup_timeout_seconds=5.0,
        replacement_timeout_seconds=2.0,
    )
    manager.start(enabled=True, project="fixed-project")
    _wait_for_state(manager, "available")
    return manager, observations, starts


def test_crashed_worker_is_joined_and_replaced_once_without_request_replay() -> None:
    manager, observations, starts = _lifecycle_manager("crash")
    initial = [observations.get(timeout=1), observations.get(timeout=1)]
    old_pid = next(item[3] for item in initial if item[1] == 0)
    deadline = time.monotonic() + 1.5
    try:
        with pytest.raises(satellite.EarthEngineProviderError):
            asyncio.run(
                manager.fetch(
                    latitude=25.0375,
                    longitude=121.5645,
                    window_start="2026-06-22",
                    window_end="2026-09-20",
                    deadline=deadline,
                )
            )
        request = observations.get(timeout=1)
        assert request[:3] == ("request", 0, 1)
        _wait_until(lambda: starts[0] == 2 or manager.state != "available")
        assert starts[0] == 2, (
            manager.state,
            manager._replacement_attempts,
            manager._replacement_thread,
        )
        replacement = observations.get(timeout=3)
        assert replacement[:3] == ("start", 0, 2)
        _wait_until(lambda: manager.live_worker_count == 2)
        assert list(starts) == [2, 1]
        assert old_pid not in {child.pid for child in multiprocessing.active_children()}
        assert observations.empty()
    finally:
        manager.shutdown()


def test_timeout_kills_worker_before_one_bounded_replacement() -> None:
    manager, observations, starts = _lifecycle_manager("timeout")
    initial = [observations.get(timeout=1), observations.get(timeout=1)]
    old_pid = next(item[3] for item in initial if item[1] == 0)
    deadline = time.monotonic() + 0.8
    started_at = time.monotonic()
    try:
        with pytest.raises(satellite.EarthEngineProviderTimeout):
            asyncio.run(
                manager.fetch(
                    latitude=25.0375,
                    longitude=121.5645,
                    window_start="2026-06-22",
                    window_end="2026-09-20",
                    deadline=deadline,
                )
            )
        assert time.monotonic() - started_at < 1.0
        assert observations.get(timeout=1)[:3] == ("request", 0, 1)
        assert observations.get(timeout=3)[:3] == ("start", 0, 2)
        _wait_until(lambda: manager.live_worker_count == 2)
        assert list(starts) == [2, 1]
        assert old_pid not in {child.pid for child in multiprocessing.active_children()}
    finally:
        manager.shutdown()


def test_unconfirmed_worker_death_fails_closed_without_replacement() -> None:
    """Capacity restoration must never begin until the retired process is confirmed dead."""

    class ResistantProcess:
        pid = 4242

        def __init__(self):
            self.terminate_calls = 0
            self.kill_calls = 0

        def is_alive(self):
            return True

        def join(self, timeout=None):
            return None

        def terminate(self):
            self.terminate_calls += 1

        def kill(self):
            self.kill_calls += 1

        def close(self):
            raise AssertionError("a live process handle must be retained")

    class Connection:
        def close(self):
            return None

    process = ResistantProcess()
    slot = worker_pool._WorkerSlot(0, 1, process, Connection())
    manager = worker_pool.EarthEngineWorkerManager()
    manager._state = "available"
    manager._slots[0] = slot

    with pytest.raises(satellite.EarthEngineProviderError):
        manager._retire_slot(slot, replace=True)

    assert manager.state == "unavailable"
    assert manager._slots == {0: slot}
    assert process.terminate_calls == 1
    assert process.kill_calls == 1
    assert manager._replacement_attempts == set()
    assert manager._replacement_events.empty()
    manager.start(enabled=False, project="fixed-project")
    assert manager._replacement_attempts == set()
    assert manager._replacement_events.empty()


def test_broken_graceful_shutdown_pipe_still_terminates_worker() -> None:
    class Process:
        def __init__(self):
            self.alive = True
            self.terminate_calls = 0

        def is_alive(self):
            return self.alive

        def join(self, timeout=None):
            return None

        def terminate(self):
            self.terminate_calls += 1
            self.alive = False

        def close(self):
            return None

    class Connection:
        def send(self, _message):
            raise BrokenPipeError

        def close(self):
            return None

    process = Process()
    worker_pool.EarthEngineWorkerManager._stop_slot(
        worker_pool._WorkerSlot(0, 1, process, Connection()),
        graceful=True,
    )

    assert process.terminate_calls == 1
    assert process.is_alive() is False


def test_replacement_enqueue_during_controller_exit_is_not_stranded() -> None:
    """The singular controller must hand off an event queued while its thread is still exiting."""

    entered_empty = threading.Event()
    allow_empty_return = threading.Event()

    class RacingQueue:
        def __init__(self):
            self.items = []
            self.first_get = True
            self.lock = threading.Lock()

        def get_nowait(self):
            if self.first_get:
                self.first_get = False
                entered_empty.set()
                allow_empty_return.wait(timeout=2)
                raise worker_pool.queue.Empty
            with self.lock:
                if not self.items:
                    raise worker_pool.queue.Empty
                return self.items.pop(0)

        def put_nowait(self, item):
            with self.lock:
                self.items.append(item)

        def empty(self):
            with self.lock:
                return not self.items

    class Process:
        def is_alive(self):
            return True

    class Connection:
        pass

    manager = worker_pool.EarthEngineWorkerManager()
    manager._state = "available"
    manager._replacement_events = RacingQueue()
    spawned = []

    def spawn_slot(*, index, generation):
        spawned.append((index, generation))
        return worker_pool._WorkerSlot(index, generation, Process(), Connection())

    manager._spawn_slot = spawn_slot
    manager._await_ready = lambda _slot, _deadline: "ready"
    controller = threading.Thread(target=manager._replacement_controller, daemon=True)
    manager._replacement_thread = controller
    controller.start()
    assert entered_empty.wait(timeout=1)

    manager._schedule_replacement(0, 1)
    allow_empty_return.set()

    _wait_until(lambda: spawned == [(0, 2)])
    assert manager._replacement_events.empty()


def test_shutdown_and_restart_clear_replacement_generation_guards() -> None:
    """A new manager lifecycle must not inherit one-shot guards from the prior lifecycle."""

    manager = worker_pool.EarthEngineWorkerManager()
    manager._state = "unavailable"
    manager._replacement_attempts.add((0, 1))
    manager._replacement_events.put_nowait((1, 1))

    manager.shutdown()

    assert manager._replacement_attempts == set()
    assert manager._replacement_events.empty()


def test_replacement_generation_guards_remain_bounded_per_slot() -> None:
    class RunningController:
        def is_alive(self):
            return True

    manager = worker_pool.EarthEngineWorkerManager()
    manager._state = "available"
    manager._replacement_thread = RunningController()

    for generation in range(1, 11):
        manager._schedule_replacement(0, generation)
    for generation in range(1, 8):
        manager._schedule_replacement(1, generation)

    assert manager._replacement_attempts == {(0, 10), (1, 7)}


def test_failed_replacement_cleans_other_worker_and_all_pipes() -> None:
    manager, observations, starts = _lifecycle_manager("replacement_failure")
    for _ in range(2):
        observations.get(timeout=1)
    deadline = time.monotonic() + 1.5
    try:
        with pytest.raises(satellite.EarthEngineProviderError):
            asyncio.run(
                manager.fetch(
                    latitude=25.0375,
                    longitude=121.5645,
                    window_start="2026-06-22",
                    window_end="2026-09-20",
                    deadline=deadline,
                )
            )
        observations.get(timeout=1)
        observations.get(timeout=3)
        _wait_for_state(manager, "unavailable")
        _wait_until(lambda: manager.live_worker_count == 0)
        time.sleep(0.1)
        assert list(starts) == [2, 1]
        assert manager._slots == {}
    finally:
        manager.shutdown()


def test_shutdown_is_idempotent_and_leaves_no_workers() -> None:
    manager, observations, _starts = _lifecycle_manager("success")
    pids = {observations.get(timeout=1)[3], observations.get(timeout=1)[3]}

    manager.shutdown()
    manager.shutdown()

    assert manager.state == "stopped"
    assert manager.live_worker_count == 0
    assert pids.isdisjoint(child.pid for child in multiprocessing.active_children())


def test_shutdown_waits_for_pending_spawn_ownership_before_returning(monkeypatch) -> None:
    """Shutdown must not report stopped while a controller owns an unregistered live child."""

    monkeypatch.setattr(worker_pool, "_CLEANUP_RESERVE_SECONDS", 0.01)
    spawn_started = threading.Event()
    release_spawn = threading.Event()

    class Process:
        def __init__(self):
            self.alive = True

        def is_alive(self):
            return self.alive

        def join(self, timeout=None):
            del timeout

        def terminate(self):
            self.alive = False

        def kill(self):
            self.alive = False

        def close(self):
            return None

    class Connection:
        def close(self):
            return None

    process = Process()
    manager = worker_pool.EarthEngineWorkerManager()

    def delayed_spawn(*, index, generation):
        spawn_started.set()
        release_spawn.wait(timeout=2)
        return worker_pool._WorkerSlot(index, generation, process, Connection())

    manager._spawn_slot = delayed_spawn
    manager.start(enabled=True, project="fixed-project")
    assert spawn_started.wait(timeout=1)
    shutdown_thread = threading.Thread(target=manager.shutdown)
    shutdown_thread.start()
    time.sleep(0.05)

    assert shutdown_thread.is_alive()

    release_spawn.set()
    shutdown_thread.join(timeout=1)
    assert shutdown_thread.is_alive() is False
    assert process.is_alive() is False
    assert manager.state == "stopped"


@pytest.mark.parametrize(
    ("outcome", "reason"),
    [
        ("credential_unavailable", "credential_unavailable"),
        ("initialization_unavailable", "provider_error"),
    ],
)
def test_startup_failure_maps_to_truthful_allowlisted_reason(outcome, reason) -> None:
    manager = worker_pool.EarthEngineWorkerManager(
        worker_target=_readiness_worker,
        worker_target_args=(outcome,),
        startup_timeout_seconds=5.0,
    )
    try:
        manager.start(enabled=True, project="fixed-project")
        _wait_for_state(manager, "unavailable")
        assert manager.unavailable_reason == reason
        assert manager.live_worker_count == 0
    finally:
        manager.shutdown()


def test_credential_startup_failure_is_not_hidden_by_other_hung_worker() -> None:
    """Readiness polling must classify the first explicit failure across both slots."""

    class Process:
        def __init__(self):
            self.alive = True

        def is_alive(self):
            return self.alive

        def join(self, timeout=None):
            return None

        def terminate(self):
            self.alive = False

        def kill(self):
            self.alive = False

        def close(self):
            return None

    class Connection:
        def __init__(self, message=None):
            self.message = message

        def poll(self, timeout=0):
            if self.message is None:
                time.sleep(min(timeout, 0.01))
                return False
            return True

        def recv(self):
            message, self.message = self.message, None
            return message

        def close(self):
            return None

    manager = worker_pool.EarthEngineWorkerManager(startup_timeout_seconds=2.0)

    def spawn_slot(*, index, generation):
        ready = None
        if index == 1:
            ready = worker_pool.SatelliteWorkerReady(1, generation, "credential_unavailable")
        return worker_pool._WorkerSlot(index, generation, Process(), Connection(ready))

    manager._spawn_slot = spawn_slot
    started_at = time.monotonic()
    try:
        manager.start(enabled=True, project="fixed-project")
        _wait_for_state(manager, "unavailable")
        assert time.monotonic() - started_at < 1.0
        assert manager.unavailable_reason == "credential_unavailable"
        assert manager.live_worker_count == 0
    finally:
        manager.shutdown()


def test_readiness_arriving_during_shutdown_cannot_restore_availability() -> None:
    context = multiprocessing.get_context("spawn")
    release_event = context.Event()
    manager = worker_pool.EarthEngineWorkerManager(
        context=context,
        worker_target=_readiness_worker,
        worker_target_args=("ready", release_event),
        startup_timeout_seconds=5.0,
    )
    manager.start(enabled=True, project="fixed-project")
    _wait_for_state(manager, "starting")

    manager.shutdown()
    release_event.set()
    time.sleep(0.1)

    assert manager.state == "stopped"
    assert manager.live_worker_count == 0


def _blocking_manager():
    context = multiprocessing.get_context("spawn")
    release_event = context.Event()
    observations = context.Queue()
    manager = worker_pool.EarthEngineWorkerManager(
        context=context,
        worker_target=_blocking_worker,
        worker_target_args=(release_event, observations),
        startup_timeout_seconds=5.0,
    )
    manager.start(enabled=True, project="fixed-project")
    _wait_for_state(manager, "available")
    return manager, release_event, observations


def _fetch_task(manager, latitude: float, deadline: float):
    return manager.fetch(
        latitude=latitude,
        longitude=121.5645,
        window_start="2026-06-22",
        window_end="2026-09-20",
        deadline=deadline,
    )


def test_two_active_two_queued_and_fifth_fails_closed() -> None:
    manager, release_event, observations = _blocking_manager()

    async def scenario():
        deadline = time.monotonic() + 3.0
        accepted = [asyncio.create_task(_fetch_task(manager, 25.0 + index / 100, deadline)) for index in range(4)]
        await asyncio.to_thread(observations.get, True, 2)
        await asyncio.to_thread(observations.get, True, 2)
        started_at = time.monotonic()
        with pytest.raises(satellite.EarthEngineProviderError):
            await _fetch_task(manager, 25.5, deadline)
        assert time.monotonic() - started_at < 0.2
        release_event.set()
        assert await asyncio.gather(*accepted) == [b"bounded-jpeg"] * 4

    try:
        asyncio.run(scenario())
    finally:
        manager.shutdown()


def test_cancelled_queued_request_never_acquires_worker_or_sends_ipc() -> None:
    manager, release_event, observations = _blocking_manager()

    async def scenario():
        deadline = time.monotonic() + 3.0
        tasks = [asyncio.create_task(_fetch_task(manager, 25.0 + index / 100, deadline)) for index in range(4)]
        first = await asyncio.to_thread(observations.get, True, 2)
        second = await asyncio.to_thread(observations.get, True, 2)
        tasks[2].cancel()
        with pytest.raises(asyncio.CancelledError):
            await tasks[2]
        release_event.set()
        assert await tasks[0] == b"bounded-jpeg"
        assert await tasks[1] == b"bounded-jpeg"
        assert await tasks[3] == b"bounded-jpeg"
        third = await asyncio.to_thread(observations.get, True, 2)
        observed_latitudes = {first[0], second[0], third[0]}
        assert 25.02 not in observed_latitudes
        assert manager.available_admission_slots == 4

    try:
        asyncio.run(scenario())
    finally:
        manager.shutdown()


def test_repeated_queued_cancellation_does_not_accumulate_executor_work_items() -> None:
    """Canceled queue churn must remain physically bounded, not only logically admitted."""

    manager, release_event, observations = _blocking_manager()

    async def scenario():
        deadline = time.monotonic() + 5.0
        active = [asyncio.create_task(_fetch_task(manager, 25.0 + index / 100, deadline)) for index in range(2)]
        await asyncio.to_thread(observations.get, True, 2)
        await asyncio.to_thread(observations.get, True, 2)

        for index in range(10):
            queued = asyncio.create_task(_fetch_task(manager, 25.2 + index / 100, deadline))
            await asyncio.sleep(0.01)
            queued.cancel()
            with pytest.raises(asyncio.CancelledError):
                await queued

        assert manager._executor is not None
        retained_work_items = manager._executor._work_queue.qsize()
        release_event.set()
        assert await asyncio.gather(*active) == [b"bounded-jpeg"] * 2
        assert retained_work_items == 0

    try:
        asyncio.run(scenario())
    finally:
        release_event.set()
        manager.shutdown()


def test_cancellation_before_executor_entry_returns_assigned_worker_slots() -> None:
    """Canceling after slot assignment must not strand a live worker outside the idle queue."""

    manager, _release_event, _observations = _blocking_manager()
    executor_entries = worker_pool.queue.Queue()
    allow_executor_entry = threading.Event()
    original_execute = manager._execute_request

    def paused_execute(**kwargs):
        executor_entries.put(True)
        allow_executor_entry.wait(timeout=2)
        return original_execute(**kwargs)

    manager._execute_request = paused_execute

    async def scenario():
        deadline = time.monotonic() + 3.0
        tasks = [asyncio.create_task(_fetch_task(manager, 25.0 + index / 100, deadline)) for index in range(2)]
        await asyncio.to_thread(executor_entries.get, True, 1)
        await asyncio.to_thread(executor_entries.get, True, 1)
        for task in tasks:
            task.cancel()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert all(isinstance(result, asyncio.CancelledError) for result in results)

        allow_executor_entry.set()
        await asyncio.sleep(0.1)
        assert manager._idle_slots.qsize() == 2
        assert manager.live_worker_count == 2

    try:
        asyncio.run(scenario())
    finally:
        allow_executor_entry.set()
        manager.shutdown()


def test_expired_queued_request_never_acquires_worker_or_sends_ipc() -> None:
    manager, release_event, observations = _blocking_manager()

    async def scenario():
        active_deadline = time.monotonic() + 3.0
        active = [asyncio.create_task(_fetch_task(manager, 25.0 + index / 100, active_deadline)) for index in range(2)]
        first = await asyncio.to_thread(observations.get, True, 2)
        second = await asyncio.to_thread(observations.get, True, 2)
        expired = asyncio.create_task(_fetch_task(manager, 25.9, time.monotonic() + 0.1))
        with pytest.raises(satellite.EarthEngineProviderTimeout):
            await expired
        release_event.set()
        assert await asyncio.gather(*active) == [b"bounded-jpeg"] * 2
        await asyncio.sleep(0.1)
        assert {first[0], second[0]} == {25.0, 25.01}
        assert observations.empty()

    try:
        asyncio.run(scenario())
    finally:
        manager.shutdown()


def test_admission_slot_is_released_exactly_once_in_cancel_race() -> None:
    manager, release_event, observations = _blocking_manager()

    async def scenario():
        deadline = time.monotonic() + 3.0
        tasks = [asyncio.create_task(_fetch_task(manager, 25.0 + index / 100, deadline)) for index in range(4)]
        await asyncio.to_thread(observations.get, True, 2)
        await asyncio.to_thread(observations.get, True, 2)
        tasks[2].cancel()
        release_event.set()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        assert isinstance(results[2], asyncio.CancelledError)
        assert manager.available_admission_slots == 4

    try:
        asyncio.run(scenario())
    finally:
        manager.shutdown()


def test_active_cancellation_contains_worker_before_releasing_admission() -> None:
    manager, _release_event, observations = _blocking_manager()

    async def scenario():
        deadline = time.monotonic() + 3.0
        task = asyncio.create_task(_fetch_task(manager, 25.0, deadline))
        request = await asyncio.to_thread(observations.get, True, 2)
        old_pid = request[2]
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        assert old_pid not in {child.pid for child in multiprocessing.active_children()}
        assert manager.available_admission_slots == 4
        assert len(manager._replacement_attempts) == 1
        await asyncio.sleep(0.1)
        assert observations.empty()

    try:
        asyncio.run(scenario())
    finally:
        manager.shutdown()
