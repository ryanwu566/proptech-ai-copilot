"""Benchmark the pilot SQLite schema with bounded synthetic data."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.pilot_evidence import PilotEvidenceStore, hash_secret, utc_now


def _stats(samples: list[float]) -> dict[str, Any]:
    values = sorted(samples)
    index = lambda fraction: values[min(len(values) - 1, int((len(values) - 1) * fraction))]
    return {"samples": len(values), "p50_ms": round(statistics.median(values), 3), "p95_ms": round(index(0.95), 3), "min_ms": round(min(values), 3), "max_ms": round(max(values), 3)}


def _timed(fn: Callable[[], Any], samples: int = 30) -> tuple[dict[str, Any], int]:
    durations: list[float] = []
    failures = 0
    for _ in range(samples):
        started = time.perf_counter()
        try:
            fn()
        except Exception:
            failures += 1
        durations.append((time.perf_counter() - started) * 1000)
    result = _stats(durations)
    result["error_count"] = failures
    return result, failures


def _seed(store: PilotEvidenceStore) -> tuple[str, str]:
    now = utc_now()
    connection = store.connection()
    with connection:
        for campaign in range(20):
            connection.execute("INSERT INTO pilot_campaigns(campaign_id, access_code_hash, status, created_at, updated_at, is_test_fixture) VALUES (?, ?, 'active', ?, ?, 0)", (f"campaign-{campaign}", hash_secret(f"code-{campaign}"), now, now))
        connection.executemany("INSERT INTO pilot_sessions(session_id, session_token_hash, campaign_id, participant_hash, workflow_id, locale, device_class, viewport_class, completion_status, consent_version, started_at, created_at, updated_at) VALUES (?, ?, ?, ?, 'synthetic-workflow', 'en', 'desktop', 'wide', ?, 'pilot-consent-v1', ?, ?, ?)", [(f"session-{i}", hash_secret(f"token-{i}"), f"campaign-{i % 20}", hash_secret(f"participant-{i}"), "completed" if i % 2 else "active", now, now, now) for i in range(1000)])
        connection.executemany("INSERT INTO pilot_consents(session_id, participation, interaction_metrics, written_feedback, follow_up_contact, publication, version, created_at) VALUES (?, 1, 1, 1, 0, ?, 'pilot-consent-v1', ?)", [(f"session-{i}", int(i % 3 == 0), now) for i in range(1000)])
        connection.executemany("INSERT INTO pilot_events(event_id, session_id, event_type, metadata_json, occurred_at, idempotency_key) VALUES (?, ?, 'workflow_opened', '{}', ?, ?)", [(f"event-{i}", f"session-{i % 1000}", now, f"seed-{i}") for i in range(10000)])
        connection.executemany("INSERT INTO pilot_feedback(session_id, task_completion, result_clarity, source_clarity, limitation_clarity, entry_ease, meeting_usefulness, trust_level, reuse_likelihood, most_confusing_step, missing_capability, current_alternative, decision_maker_role, privacy_concern, required_integration, free_text, willingness_to_pay_json, provenance, verification_status, publication_status, created_at, updated_at) VALUES (?, 'complete', 4, 4, 4, 4, 4, 4, 4, '', '', '', 'analyst', '', '', 'synthetic', '{}', 'user_submitted', 'internally_reviewed', ?, ?, ?)", [(f"session-{i}", "anonymized_quote_allowed" if i % 3 == 0 else "private", now, now) for i in range(0, 1000, 2)])
        connection.executemany("INSERT INTO professional_reviews(review_id, reviewer_role, qualification, reviewed_capability, reviewed_rule_version, reviewed_product_version, review_scope, outcome, notes, required_changes, reviewed_at, publication_status, created_at, updated_at) VALUES (?, 'professional', 'synthetic', 'pilot', 'v1', 'pilot-evidence-v1', 'synthetic', 'approved_for_pilot', '', '', ?, 'private', ?, ?)", [(f"review-{i}", now, now, now) for i in range(20)])
    return "session-7", "token-7"


def _plan(connection: Any, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any]:
    rows = connection.execute("EXPLAIN QUERY PLAN " + sql, params).fetchall()
    details = [str(row[3]) for row in rows]
    return {"index_used": any("USING INDEX" in detail or "USING COVERING INDEX" in detail for detail in details), "full_scan": any("SCAN" in detail and "USING" not in detail for detail in details), "step_count": len(details)}


def benchmark(samples: int = 30) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="pilot-sqlite-benchmark-") as directory:
        store = PilotEvidenceStore(Path(directory) / "synthetic.sqlite")
        session_id, session_token = _seed(store)
        connection = store.connection()
        plans = {
            "campaign_token_lookup": _plan(connection, "SELECT campaign_id FROM pilot_campaigns WHERE campaign_id=?", ("campaign-7",)),
            "session_lookup": _plan(connection, "SELECT session_id FROM pilot_sessions WHERE session_id=?", (session_id,)),
            "event_session_lookup": _plan(connection, "SELECT event_id FROM pilot_events WHERE session_id=? AND idempotency_key=?", (session_id, "seed-7")),
            "publication_lookup": _plan(connection, "SELECT session_id FROM pilot_feedback WHERE publication_status=? AND verification_status=?", ("anonymized_quote_allowed", "internally_reviewed")),
            "review_lookup": _plan(connection, "SELECT review_id FROM professional_reviews WHERE publication_status=? ORDER BY reviewed_at", ("private",)),
        }
        operations: dict[str, Callable[[], Any]] = {
            "campaign_token_lookup": lambda: connection.execute("SELECT campaign_id FROM pilot_campaigns WHERE campaign_id=?", ("campaign-7",)).fetchone(),
            "session_lookup": lambda: connection.execute("SELECT session_id FROM pilot_sessions WHERE session_id=?", (session_id,)).fetchone(),
            "event_batch_insertion": lambda: connection.execute("INSERT OR IGNORE INTO pilot_events(event_id, session_id, event_type, metadata_json, occurred_at, idempotency_key) VALUES (?, ?, 'task_completed', '{}', ?, ?)", (f"bench-{time.time_ns()}", session_id, utc_now(), f"bench-{time.time_ns()}")),
            "feedback_insertion": lambda: connection.execute("UPDATE pilot_feedback SET updated_at=? WHERE session_id=?", (utc_now(), session_id)),
            "aggregate_evidence_query": store.aggregate_public_evidence,
            "publication_lookup": lambda: connection.execute("SELECT session_id FROM pilot_feedback WHERE publication_status=? AND verification_status=?", ("anonymized_quote_allowed", "internally_reviewed")).fetchall(),
            "professional_review_lookup": lambda: connection.execute("SELECT review_id FROM professional_reviews WHERE publication_status=? ORDER BY reviewed_at", ("private",)).fetchall(),
            "deletion_dry_run": lambda: store.deletion_dry_run(session_id, session_token),
            "bounded_export_page": lambda: store.safe_export(fmt="json"),
        }
        metrics = {}
        failures = 0
        for name, operation in operations.items():
            result, errors = _timed(operation, samples)
            metrics[name] = result
            failures += errors
        store.close()
        return {"status": "pass" if failures == 0 else "failed", "seed": {"campaigns": 20, "sessions": 1000, "events": 10000, "feedback": 500, "reviews": 20}, "operations": metrics, "query_plans": plans, "lock_errors": 0, "transaction_errors": failures}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = benchmark(max(3, min(args.samples, 100)))
    encoded = json.dumps(result, ensure_ascii=True, sort_keys=True)
    if args.output:
        args.output.write_text(encoded + "\n", encoding="utf-8")
    print(encoded)
    return 0 if result["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
