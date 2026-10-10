"""Bounded observation of valuation decisions; never selects or adjusts a row."""
from __future__ import annotations

import math
from collections import Counter
from typing import Any

EXCLUDED_EXAMPLE_BOUND = 5

def known_number(row: dict[str, Any], key: str) -> float | None:
    if key in row.get("_explanation_missing_fields", ()):
        return None
    value = row.get(key)
    return float(value) if isinstance(value, (int, float)) and math.isfinite(value) else None

def dimension(target=None, comparable=None, difference=None, *, role="context", threshold=None):
    return {"target": target, "comparable": comparable, "difference": difference, "role": role, "threshold": threshold}

class ComparableDecisionTrace:
    """Collect counters and five first-observed exclusions, not a raw audit log.

    Candidate ordinals are request-local and distinguish repeated observations.
    Provider SQL removals and LIMIT truncation are outside observed coverage.
    """
    def __init__(self, target, reference_period, recency_reference_period, window_start, official):
        self.target = target
        self.reference_period = reference_period
        self.recency_reference_period = recency_reference_period
        self.window_start = window_start
        self.official = official
        self.considered = 0
        self.excluded = 0
        self.counts: Counter[str] = Counter()
        self.examples: list[dict[str, Any]] = []
        self.scope = "none"
        self.iqr_bounds = None
        self.outlier_fallback = False
        self.community_distances: dict[int, int | None] = {}
        self.community_name = None

    def candidates(self, rows):
        self.considered = len(rows)
        return [{**row, "_decision_index": i} for i, row in enumerate(rows)]

    def public_row(self, row, reasons):
        target = self.target
        area, target_area = known_number(row, "area_ping"), known_number(target, "area_ping")
        age, target_age = known_number(row, "building_age_years"), known_number(target, "building_age_years")
        scored = "_same_building_type" in row
        period = row.get("transaction_period")
        try:
            year, month = map(int, str(period).split("-"))
            ref_year, ref_month = map(int, self.recency_reference_period.split("-"))
            age_months = (ref_year - year) * 12 + ref_month - month if 1 <= month <= 12 else None
        except (TypeError, ValueError):
            age_months = None
        return {
            "candidate_id": f"candidate-{row['_decision_index'] + 1}",
            "status": "included" if reasons == ["selected"] else "excluded",
            "reasons": reasons,
            "transaction_period": period if isinstance(period, str) else None,
            "dimensions": {
                "location": dimension(" / ".join(str(target.get(k) or "") for k in ("city", "district", "road")), " / ".join(str(row.get(k) or "") for k in ("city", "district", "road")), role="scope"),
                "building_type": dimension(target.get("building_type") or None, row.get("normalized_building_type") or row.get("building_type") or None, role="ranking" if scored else "context"),
                "area": dimension(target_area, area, abs(area - target_area) if area is not None and target_area is not None else None, role="ranking" if scored else "context"),
                "age": dimension(target_age, age, abs(age - target_age) if age is not None and target_age is not None else None, role="weight" if scored else "context"),
                "distance": dimension(None, row.get("distance_m"), role="weight" if scored else "context"),
                "recency": dimension(self.recency_reference_period, period, age_months, role="ranking" if scored else "context"),
                "unit_price": dimension(None, known_number(row, "unit_price_per_ping"), role="outlier" if scored and self.iqr_bounds is not None else "context", threshold=self.iqr_bounds if scored else None),
                "floor": dimension(known_number(target, "floor"), known_number(row, "floor")),
                # Neither adapter provides authoritative parking price semantics.
                "parking": dimension(),
                "community_distance": dimension(self.community_name, self.community_distances.get(row["_decision_index"]), role="scope" if self.scope == "community" else "context", threshold=[0, 600] if self.scope == "community" else None),
            },
        }

    def reject(self, row, reasons):
        self.excluded += 1
        self.counts.update(reasons)
        if len(self.examples) < EXCLUDED_EXAMPLE_BOUND:
            self.examples.append(self.public_row(row, reasons))

    def scope_decision(self, rows, selected, level):
        self.scope = level
        selected_ids = {row["_decision_index"] for row in selected}
        for row in rows:
            if row["_decision_index"] not in selected_ids:
                reason = "insufficient_samples" if level == "none" else "scope"
                if level == "community" and row["_decision_index"] in self.community_distances:
                    reason = "community_distance_unknown" if self.community_distances[row["_decision_index"]] is None else "community_distance"
                self.reject(row, [reason])

    def finish(self, selected):
        return {
            "version": "comparable-explanation-v1",
            "selection_version": "deterministic-valuation-v1",
            "coverage": "returned_candidates_only",
            "reference_period": self.reference_period,
            "recency_reference_period": self.recency_reference_period,
            "window_start": self.window_start if self.official else None,
            "scope": self.scope,
            "considered_count": self.considered,
            "selected_count": len(selected),
            "excluded_count": self.excluded,
            "provider_excluded_count": None,
            "reason_counts": dict(self.counts),
            "excluded_example_bound": EXCLUDED_EXAMPLE_BOUND,
            "outlier_bounds": self.iqr_bounds,
            "outlier_fallback": self.outlier_fallback,
            "selected": [self.public_row(row, ["selected"]) for row in selected],
            "excluded_examples": self.examples,
        }
