"""WRA flood hazard provider.

Phase 3B: this provider is wired to the Phase 3A runtime loader
(:mod:`services.wra_flood_runtime`).  The runtime is the *single owner* of the
R2 -> checksum -> decode -> cache -> STRtree pipeline; this provider never
downloads SHP, calls R2 directly, or duplicates checksum / STRtree / artifact
decoding logic.  It simply asks the shared process-local runtime to query one
clearly-defined default scenario and maps the result onto the existing terrain
risk hazard-layer contract.
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from services.wra_flood_runtime import (
    ChecksumMismatchError,
    InvalidScenarioError,
    SourceUnavailableError,
    WraFloodRuntimeError,
)
from services.wra_flood_runtime import query_point as _default_query_point

from .base import source_meta, unavailable_layer

#: The single, clearly-defined default scenario for the first production
#: wiring.  We deliberately do NOT blend all 10 scenarios into one score.
DEFAULT_SCENARIO = "24h-350mm"

#: Human-readable description of the default scenario for the caller/UI.
SCENARIO_LABEL = "24 小時 / 350mm 淹水潛勢情境"

_LAYER_KEY = "flood"
_LAYER_LABEL = "淹水潛勢"
_AGENCY = "經濟部水利署"

#: Class (1-5) -> canonical depth is owned by the dataset; here we only map the
#: official Class onto the existing terrain-risk qualitative level.  Shallower
#: potential depth (Class 1-2) -> medium; deeper (Class 3-5) -> high.  A matched
#: flood-potential polygon is always a real risk signal, never "low".
_CLASS_TO_LEVEL = {1: "medium", 2: "medium", 3: "high", 4: "high", 5: "high"}


class WraFloodProvider:
    """Flood-potential provider backed by the WRA flood R2 runtime loader."""

    source_url = "https://fhy.wra.gov.tw/"

    def __init__(
        self,
        query_point: Optional[Callable[..., dict[str, Any]]] = None,
        *,
        scenario: str = DEFAULT_SCENARIO,
    ) -> None:
        # ``query_point`` defaults to the module-level function which uses the
        # shared process-local runtime cache (single owner, warm calls reuse
        # the cache without re-downloading from R2).  Tests may inject a fake.
        self._query_point = query_point or _default_query_point
        self._scenario = scenario

    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict[str, Any]:
        # The WRA flood dataset is a point-in-polygon potential map; radius_m is
        # accepted for interface compatibility but not used for buffering here.
        try:
            result = self._query_point(self._scenario, longitude, latitude)
        except InvalidScenarioError as exc:
            return self._error_layer(
                "error",
                f"淹水潛勢情境設定無效（{self._scenario}），請聯繫維運人員確認資料版本。",
                detail=str(exc),
            )
        except ChecksumMismatchError as exc:
            # Never hide a checksum mismatch and never turn it into a miss.
            return self._error_layer(
                "error",
                "淹水潛勢資料完整性驗證失敗（checksum 不符），已停止使用該資料，請改至水利署防災圖台確認。",
                detail=str(exc),
            )
        except SourceUnavailableError as exc:
            # Includes missing R2 credentials / missing object / network error.
            return self._unavailable_layer(
                "目前無法取得官方淹水潛勢處理後資料，請至水利署防災圖台依降雨情境確認。",
                detail=str(exc),
            )
        except WraFloodRuntimeError as exc:
            # ArtifactInvalidError and any other runtime error: source-side
            # problem, surfaced as error -- never a no_match / low-risk verdict.
            return self._error_layer(
                "error",
                "官方淹水潛勢資料暫時無法解析，請改至水利署防災圖台確認。",
                detail=str(exc),
            )

        scenario = result.get("scenario", self._scenario)
        if result.get("matched"):
            return self._matched_layer(result, scenario)
        return self._no_match_layer(scenario)

    # -- response builders -------------------------------------------------

    def _scenario_source(self, status: str, **extra: Any) -> dict[str, Any]:
        return source_meta(
            "淹水潛勢與防災資訊",
            _AGENCY,
            self.source_url,
            status,
            scenario=self._scenario,
            scenario_label=SCENARIO_LABEL,
            dataset="wra_flood_potential",
            **{k: v for k, v in extra.items() if v is not None},
        )

    def _matched_layer(self, result: dict[str, Any], scenario: str) -> dict[str, Any]:
        class_value = result.get("class")
        # Defensive: only the official Class values 1-5 are legal. A matched
        # result carrying any other Class is a source/contract anomaly; fail
        # closed to an error rather than guessing a level or downgrading to a
        # miss. Never assume medium/high, never become no_match.
        if class_value not in _CLASS_TO_LEVEL:
            return self._error_layer(
                "error",
                "官方淹水潛勢資料回傳非法級距（Class 不在 1-5），已停止使用該結果，"
                "請改至水利署防災圖台確認。",
                detail=f"unexpected flood Class: {class_value!r}",
            )
        level = _CLASS_TO_LEVEL[class_value]
        canonical_depth = result.get("canonical_depth")
        city_name = result.get("city_name")
        town_name = result.get("town_name")
        where = "".join(part for part in (city_name, town_name) if part)
        explanation = (
            f"此位置落在水利署「{SCENARIO_LABEL}」的淹水潛勢範圍內，"
            f"官方淹水潛勢級距為 {canonical_depth}。"
            + (f"（{where}）" if where else "")
            + " 此為情境模擬潛勢，非實際淹水保證，仍需以現地與主管機關為準。"
        )
        return {
            "key": _LAYER_KEY,
            "label": _LAYER_LABEL,
            "status": "available",
            # matched=True must remain visible even alongside limited/partial
            # metadata (do not regress PR #141 behavior).
            "matched": True,
            "level": level,
            "distance_m": 0,
            "value": {
                "scenario": scenario,
                "scenario_label": SCENARIO_LABEL,
                "class": class_value,
                "canonical_depth": canonical_depth,
                "flood_dept_raw": result.get("flood_dept_raw"),
                "flood_dept_malformed": bool(result.get("flood_dept_malformed")),
                "city_name": city_name,
                "town_name": town_name,
                "matched_count": result.get("matched_count"),
            },
            "explanation": explanation,
            "source": self._scenario_source(
                "available",
                data_vintage="官方 SHP 處理後圖資（processed v1）",
            ),
        }

    def _no_match_layer(self, scenario: str) -> dict[str, Any]:
        # Source loaded successfully but the point is not inside any polygon for
        # THIS scenario.  This is NOT safe / low-risk / flood-impossible.
        explanation = (
            f"在水利署「{SCENARIO_LABEL}」情境下，此位置未落在該情境的淹水潛勢範圍內；"
            "此結果僅代表未命中此情境圖資，並不代表無淹水風險或低風險，"
            "其他降雨情境或實際狀況仍需另行確認。"
        )
        return {
            "key": _LAYER_KEY,
            "label": _LAYER_LABEL,
            "status": "available",
            "matched": False,
            "level": "unknown",
            "distance_m": None,
            "value": {
                "scenario": scenario,
                "scenario_label": SCENARIO_LABEL,
                "matched": False,
            },
            "explanation": explanation,
            "source": self._scenario_source(
                "available",
                data_vintage="官方 SHP 處理後圖資（processed v1）",
            ),
        }

    def _unavailable_layer(self, explanation: str, *, detail: str | None = None) -> dict[str, Any]:
        payload = unavailable_layer(
            _LAYER_KEY,
            _LAYER_LABEL,
            self._scenario_source("unavailable"),
            explanation,
        )
        return payload

    def _error_layer(self, status: str, explanation: str, *, detail: str | None = None) -> dict[str, Any]:
        return {
            "key": _LAYER_KEY,
            "label": _LAYER_LABEL,
            "status": status,
            "matched": False,
            "level": "unknown",
            "distance_m": None,
            "value": None,
            "explanation": explanation,
            "source": self._scenario_source(status),
        }
