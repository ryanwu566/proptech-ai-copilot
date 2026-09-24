"""Coordinate-to-village resolver backed by NLSC polygons and RIS codes."""

from __future__ import annotations

from threading import Lock
from typing import Any

from services.nlsc_village_boundary_runtime import (
    NlscVillageBoundaryRuntime,
    get_default_village_boundary_runtime,
)
from services.ris_demographics_insight import build_demographics_insight
from services.ris_population_query import RisPopulationQueryService, RisPopulationQueryUnavailable


class RisVillageResolver:
    """Resolve polygon identity first, then attach optional RIS demographics."""

    def __init__(
        self,
        *,
        boundary_runtime: NlscVillageBoundaryRuntime,
        demographics_query: RisPopulationQueryService,
        history_limit: int = 13,
    ) -> None:
        self._boundary_runtime = boundary_runtime
        self._demographics_query = demographics_query
        self._history_limit = max(1, min(history_limit, 13))

    def resolve(self, *, latitude: float, longitude: float) -> dict[str, Any]:
        boundary = self._boundary_runtime.resolve(latitude=latitude, longitude=longitude)
        if boundary["status"] != "resolved":
            return {
                "location": boundary,
                "demographics": {
                    "status": "no_data",
                    "reason": "village_identity_not_resolved",
                },
            }

        district_code = str(boundary["district_code"])
        try:
            latest = self._demographics_query.latest(district_code)
            if latest is None:
                return {
                    "location": boundary,
                    "demographics": build_demographics_insight(
                        None,
                        [],
                        reason="demographics_not_available_for_village_code",
                    ),
                }
            history = self._demographics_query.history(district_code, limit=self._history_limit)
            demographics = build_demographics_insight(latest, history)
        except RisPopulationQueryUnavailable:
            demographics = build_demographics_insight(
                None,
                [],
                reason="demographics_unavailable",
            )
        return {"location": boundary, "demographics": demographics}


_DEFAULT_RESOLVER: RisVillageResolver | None = None
_DEFAULT_RESOLVER_LOCK = Lock()


def get_default_ris_village_resolver() -> RisVillageResolver:
    global _DEFAULT_RESOLVER
    if _DEFAULT_RESOLVER is None:
        with _DEFAULT_RESOLVER_LOCK:
            if _DEFAULT_RESOLVER is None:
                _DEFAULT_RESOLVER = RisVillageResolver(
                    boundary_runtime=get_default_village_boundary_runtime(),
                    demographics_query=RisPopulationQueryService(),
                )
    return _DEFAULT_RESOLVER
