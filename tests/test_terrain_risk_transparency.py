"""Terrain risk source transparency contracts."""

from services.terrain_risk_service import analyze_terrain_risk


def _source(name: str, status: str = "available", **extra: str) -> dict[str, str]:
    payload = {
        "name": name,
        "agency": "official fixture",
        "source_url": "https://fixture.example.invalid/raw",
        "status": status,
    }
    payload.update(extra)
    return payload


def _hazard(key: str, *, status: str = "available", matched: bool = False, level: str = "low", source: dict[str, str] | None = None) -> dict:
    return {
        "key": key,
        "label": key,
        "status": status,
        "level": level,
        "matched": matched,
        "distance_m": 80 if matched else None,
        "value": None,
        "explanation": f"{key} fixture",
        "source": source or _source(f"{key} source", status=status, data_updated_at="2026-01-01"),
        "raw_payload": {"should": "not leak"},
    }


class TerrainProvider:
    def __init__(self, *, status: str = "available", source: dict[str, str] | None = None):
        self.status = status
        self.source = source

    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return {
            "status": self.status,
            "slope_value": 8 if self.status == "available" else None,
            "slope_class": "gentle" if self.status == "available" else None,
            "elevation_m": 20 if self.status == "available" else None,
            "explanation": "terrain fixture",
            "source": self.source or _source("terrain source", status=self.status, data_updated_at="2026-01-01"),
            "latitude": latitude,
            "longitude": longitude,
        }


class SlopeProvider:
    def __init__(self, *, landslide: dict | None = None, debris_flow: dict | None = None):
        self.landslide = landslide
        self.debris_flow = debris_flow

    def analyze(self, latitude: float, longitude: float, radius_m: int, include_layers=None) -> dict:
        return {
            "landslide": self.landslide or _hazard("landslide"),
            "debris_flow": self.debris_flow or _hazard("debris_flow"),
        }


class FloodProvider:
    def __init__(self, hazard: dict | None = None):
        self.hazard = hazard

    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return self.hazard or _hazard("flood", matched=True, level="medium")


class GeologyProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int, include_layers=None) -> dict:
        return {
            "geological_sensitivity": _hazard("geological_sensitivity"),
            "liquefaction": _hazard("liquefaction"),
            "active_fault": _hazard("active_fault"),
        }


def _providers(**overrides):
    rows = {
        "terrain": TerrainProvider(),
        "slope_hazard": SlopeProvider(),
        "flood": FloodProvider(),
        "geology": GeologyProvider(),
    }
    rows.update(overrides)
    return rows


def _analyze(**kwargs):
    return analyze_terrain_risk(latitude=25, longitude=121, providers=_providers(**kwargs))


def test_source_transparency_preserves_existing_risk_result() -> None:
    result = _analyze()

    assert result["overall"]["level"] == "medium"
    assert [item["key"] for item in result["risk_factors"]] == ["flood"]
    assert result["source_transparency"]["notice"] == "地勢與災害資料僅供看房風險參考，資料不足或暫時不可用不代表沒有風險。"


def test_successful_layers_become_minimal_safe_source_rows() -> None:
    result = _analyze()
    layers = {row["layer_id"]: row for row in result["source_transparency"]["layers"]}

    assert layers["flood"]["assessment_status"] == "matched"
    assert layers["flood"]["coverage_status"] == "covered"
    assert layers["flood"]["source_name"] == "flood source"
    assert layers["flood"]["source_kind"] == "official fixture"
    assert layers["flood"]["data_updated_at"] == "2026-01-01"


def test_unavailable_provider_is_not_low_or_no_risk_transparency() -> None:
    result = _analyze(flood=FloodProvider(_hazard("flood", status="unavailable", level="unknown", matched=False)))
    flood = next(row for row in result["source_transparency"]["layers"] if row["layer_id"] == "flood")

    assert flood["assessment_status"] == "unavailable"
    assert flood["coverage_status"] == "unknown"
    assert "不能解讀為低風險" in flood["caveat"]
    assert result["overall"]["level"] != "low"


def test_missing_source_date_uses_unknown_without_guessing() -> None:
    terrain = TerrainProvider(source=_source("terrain source", status="available"))
    result = _analyze(terrain=terrain)
    terrain_row = next(row for row in result["source_transparency"]["layers"] if row["layer_id"] == "terrain")

    assert terrain_row["data_updated_at"] == "unknown"
    assert terrain_row["coverage_status"] == "covered"


def test_transparency_output_omits_sensitive_or_raw_fields() -> None:
    result = _analyze()
    text = str(result["source_transparency"])

    for forbidden in (
        "source_url",
        "raw_payload",
        "latitude",
        "longitude",
        "address",
        "token",
        "secret",
        "provider raw",
    ):
        assert forbidden not in text
