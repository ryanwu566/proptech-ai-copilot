"""Server-side resolve deadline, bounded outcome events and concurrency: controlled HTTP only."""
from copy import deepcopy
import json
import threading

import httpx
import pytest

from services import anti_abuse
from services import location_resolver as resolver
from services.anti_abuse import AbuseControls, AbuseRejected, Policy


ADDRESS = "新北市新莊區中正路191號"


def google_payload(district="新莊區", precision="ROOFTOP"):
    return {"status": "OK", "results": [{
        "formatted_address": f"新北市{district}中正路191號",
        "partial_match": False,
        "geometry": {"location_type": precision, "location": {"lat": 25.0375, "lng": 121.5637}},
        "address_components": [
            {"long_name": "新北市", "types": ["administrative_area_level_1"]},
            {"long_name": district, "types": ["administrative_area_level_3"]},
            {"long_name": "中正路", "types": ["route"]},
            {"long_name": "191", "types": ["street_number"]},
        ],
    }]}


def tgos_payload():
    return {"Info": [{"OutMatchType": "完全比對"}], "AddressList": [{"FULL_ADDR": ADDRESS, "X": 121.5637, "Y": 25.0375}]}


@pytest.fixture
def state(monkeypatch):
    state = {"google": google_payload(), "tgos": tgos_payload(), "calls": [], "timeouts": [], "events": []}

    def get(url, *, params, timeout, **kwargs):
        name = "google" if url == resolver.GOOGLE_GEOCODING_URL else "tgos"
        state["calls"].append(name)
        state["timeouts"].append((name, timeout))
        payload = state[name]
        if isinstance(payload, Exception):
            raise payload
        return httpx.Response(200, json=deepcopy(payload), request=httpx.Request("GET", url))

    monkeypatch.setattr(resolver.httpx, "get", get)
    monkeypatch.setattr(resolver, "_emit_resolve_event", state["events"].append)
    state["google_provider"] = resolver.GoogleAddressProvider(api_key="test-google-key")
    state["tgos_provider"] = resolver.TgosAddressProvider(app_id="test-app", api_key="test-tgos-key")
    return state


def resolve(state, address=ADDRESS):
    return resolver.resolve_address(address, google_provider=state["google_provider"], tgos_provider=state["tgos_provider"])


def allowance(timeout: httpx.Timeout) -> float:
    return timeout.connect + timeout.read


def test_budget_stays_below_the_browser_bound():
    assert resolver.RESOLVE_BUDGET_SECONDS <= 8.0
    assert resolver.TGOS_MIN_REMAINING_SECONDS < resolver.RESOLVE_BUDGET_SECONDS


class Clock:
    def __init__(self):
        self.now = 1000.0

    def monotonic(self):
        return self.now


def test_provider_calls_fit_their_cap_and_the_remaining_budget(state, monkeypatch):
    clock = Clock()
    monkeypatch.setattr(resolver, "time", clock)
    original_get = resolver.httpx.get

    def slow_google(url, **kwargs):
        response = original_get(url, **kwargs)
        if url == resolver.GOOGLE_GEOCODING_URL:
            clock.now += 4.0
        return response

    monkeypatch.setattr(resolver.httpx, "get", slow_google)
    state["google"] = google_payload(precision="APPROXIMATE")
    assert resolve(state)["source"] == "tgos"
    (google_name, google_timeout), (tgos_name, tgos_timeout) = state["timeouts"]
    assert (google_name, tgos_name) == ("google", "tgos")
    assert allowance(google_timeout) == pytest.approx(5.0)
    assert google_timeout.connect <= resolver.CONNECT_TIMEOUT_CAP_SECONDS
    assert allowance(tgos_timeout) == pytest.approx(resolver.RESOLVE_BUDGET_SECONDS - 4.0)
    assert state["events"][-1]["google_ms"] == 4000


def test_fallback_is_skipped_without_enough_budget_and_fails_closed_retryable(state, monkeypatch):
    monkeypatch.setattr(resolver, "TGOS_MIN_REMAINING_SECONDS", resolver.RESOLVE_BUDGET_SECONDS + 1)
    state["google"] = google_payload(precision="APPROXIMATE")
    result = resolve(state)
    assert (result["status"], result["source"], result["latitude"]) == ("unavailable", "none", None)
    assert state["calls"] == ["google"]
    event = state["events"][-1]
    assert (event["outcome"], event["google"], event["tgos"], event["fallback"]) == ("unavailable", "precision_rejected", "skipped_budget", False)


def test_exhausted_deadline_starts_no_physical_call(state, monkeypatch):
    monkeypatch.setattr(resolver, "RESOLVE_BUDGET_SECONDS", resolver.PROVIDER_MIN_REMAINING_SECONDS / 2)
    result = resolve(state)
    assert result["status"] == "unavailable"
    assert state["calls"] == []
    assert state["events"][-1]["google"] == "deadline_exhausted"


def test_no_automatic_retry_on_google_timeout(state):
    state["google"] = httpx.ReadTimeout("slow")
    state["tgos"] = httpx.ConnectTimeout("slow")
    result = resolve(state)
    assert result["status"] == "unavailable"
    assert state["calls"] == ["google", "tgos"]
    event = state["events"][-1]
    assert (event["outcome"], event["google"], event["tgos"], event["fallback"]) == ("unavailable", "timeout", "timeout", True)


@pytest.mark.parametrize("google,tgos,outcome,google_reason,tgos_reason", [
    (google_payload(), tgos_payload(), "google_resolved", "accepted", "not_attempted"),
    (google_payload(precision="RANGE_INTERPOLATED"), tgos_payload(), "tgos_resolved", "precision_rejected", "accepted"),
    (google_payload(district="樹林區"), {"Info": [], "AddressList": []}, "unresolved", "structural_mismatch", "zero_results"),
    ({"status": "REQUEST_DENIED"}, {"Info": [{"OutMatchType": "模糊比對"}], "AddressList": [{"FULL_ADDR": ADDRESS, "X": 121.5, "Y": 25.0}]}, "unresolved", "provider_status", "fuzzy_rejected"),
])
def test_outcome_event_classifies_each_path(state, google, tgos, outcome, google_reason, tgos_reason):
    state["google"], state["tgos"] = google, tgos
    result = resolve(state)
    assert result["source"] != "google" or result["district"] == "新莊區"
    event = state["events"][-1]
    assert (event["outcome"], event["google"], event["tgos"]) == (outcome, google_reason, tgos_reason)
    assert isinstance(event["total_ms"], int) and event["budget_ms"] == 8000
    assert event["process_age"] in {"lt_30s", "lt_5m", "warm"}
    assert isinstance(event["first_in_process"], bool)


def test_outcome_event_never_carries_address_coordinates_or_credentials(state):
    state["google"] = google_payload(precision="APPROXIMATE")
    resolve(state)
    serialized = json.dumps(state["events"], ensure_ascii=False)
    for secret in ("新莊", "中正路", "191", "25.0375", "121.5637", "test-google-key", "test-tgos-key", "test-app"):
        assert secret not in serialized


def test_emitted_line_is_structured_json_with_severity(monkeypatch):
    lines = []
    monkeypatch.setattr(resolver._EVENT_LOGGER, "log", lambda level, message: lines.append((level, message)))
    resolver._emit_resolve_event({"outcome": "unavailable", "google": "timeout"})
    resolver._emit_resolve_event({"outcome": "google_resolved", "google": "accepted"})
    assert [json.loads(message)["severity"] for _, message in lines] == ["WARNING", "INFO"]
    assert all(json.loads(message)["message"] == "location_resolve" for _, message in lines)


def test_admission_rejection_is_classified_and_still_raised(state, monkeypatch):
    guard = AbuseControls({"geocoding": Policy(30, 60, 1, 300), "tgos": Policy(30, 60, 1, 300)})
    monkeypatch.setattr(anti_abuse, "CONTROLS", guard)
    assert guard.semaphores["geocoding"].acquire(blocking=False)
    try:
        with pytest.raises(AbuseRejected) as error:
            resolve(state)
    finally:
        guard.semaphores["geocoding"].release()
    assert error.value.status_code == 503
    assert state["calls"] == []
    event = state["events"][-1]
    assert (event["outcome"], event["admission"], event["google"]) == ("admission_rejected", "capacity_exhausted", "started")


def run_simultaneously(state, monkeypatch, workers: int, concurrency: int):
    """Hold every provider call open until all workers are inside or rejected."""
    guard = AbuseControls({"geocoding": Policy(30, 60, concurrency, 300), "tgos": Policy(30, 60, concurrency, 300)})
    monkeypatch.setattr(anti_abuse, "CONTROLS", guard)
    inside = threading.Semaphore(0)
    release = threading.Event()

    def get(url, *, params, timeout, **kwargs):
        inside.release()
        assert release.wait(5)
        number = params["address"].split("中正路")[1]
        payload = google_payload()
        payload["results"][0]["formatted_address"] = f"新北市新莊區中正路{number}"
        payload["results"][0]["address_components"][3]["long_name"] = number.rstrip("號")
        return httpx.Response(200, json=payload, request=httpx.Request("GET", url))

    monkeypatch.setattr(resolver.httpx, "get", get)
    outcomes = [None] * workers
    rejected = threading.Semaphore(0)

    def worker(index):
        try:
            outcomes[index] = resolve(state, f"新北市新莊區中正路{191 + index}號")["status"]
        except AbuseRejected as error:
            outcomes[index] = error.status_code
            rejected.release()

    threads = [threading.Thread(target=worker, args=(index,)) for index in range(workers)]
    for thread in threads:
        thread.start()
    for _ in range(min(workers, concurrency)):
        assert inside.acquire(timeout=5)
    for _ in range(max(0, workers - concurrency)):
        assert rejected.acquire(timeout=5)
    release.set()
    for thread in threads:
        thread.join(5)
    return outcomes


@pytest.mark.parametrize("workers", [2, 3])
def test_simultaneous_resolves_share_one_process_under_default_geocoding_concurrency(state, monkeypatch, workers):
    assert anti_abuse.POLICIES["geocoding"].concurrency >= 3
    assert run_simultaneously(state, monkeypatch, workers, anti_abuse.POLICIES["geocoding"].concurrency) == ["resolved"] * workers


def test_simultaneous_resolves_beyond_process_permits_fail_fast_not_queue(state, monkeypatch):
    outcomes = run_simultaneously(state, monkeypatch, 3, 2)
    assert sorted(outcomes, key=str) == sorted(["resolved", "resolved", 503], key=str)
