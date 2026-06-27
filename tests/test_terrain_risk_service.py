"""Terrain risk service tests."""

from services.terrain_risk_service import TerrainRiskLocationError, analyze_terrain_risk


def searcher(query: str) -> dict:
    return {"matched": True, "center": {"lat": 25.026, "lng": 121.543}, "formatted_address": query, "confidence": "mock"}


class TerrainProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return {
            "status": "available",
            "slope_value": 8,
            "slope_class": "gentle",
            "elevation_m": 22,
            "explanation": "Slope evidence is available.",
            "source": {"name": "NLSC", "agency": "NLSC", "source_url": "https://maps.nlsc.gov.tw/", "status": "available"},
        }


class SlopeHazardProvider:
    def __init__(self, landslide=None, debris_flow=None):
        self.calls = 0
        self.requested_layers = None
        self.landslide = landslide
        self.debris_flow = debris_flow

    def analyze(self, latitude: float, longitude: float, radius_m: int, include_layers=None) -> dict:
        self.calls += 1
        self.requested_layers = include_layers
        return {
            "landslide": self.landslide or layer("landslide", "landslide affect", "available", "low", False),
            "debris_flow": self.debris_flow or layer("debris_flow", "debris flow affect", "available", "low", False),
        }


class FloodProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return layer("flood", "flood", "available", "medium", True)


class GeologyProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return {
            "geological_sensitivity": layer("geological_sensitivity", "geological sensitivity", "available", "low", False),
            "liquefaction": layer("liquefaction", "liquefaction", "available", "low", False),
            "active_fault": layer("active_fault", "active fault", "available", "low", False),
        }


class FailingProvider:
    def analyze(self, *args, **kwargs):
        raise RuntimeError("provider down")


class UnavailableTerrainProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return {
            "status": "unavailable",
            "slope_value": None,
            "slope_class": None,
            "elevation_m": None,
            "explanation": "Terrain fixture unavailable.",
            "source": {"name": "fixture terrain", "agency": "fixture", "source_url": "", "status": "unavailable"},
        }


class UnavailableSlopeHazardProvider:
    def __init__(self):
        self.calls = 0
        self.http_calls = 0
        self.requested_layers = None

    def analyze(self, latitude: float, longitude: float, radius_m: int, include_layers=None) -> dict:
        self.calls += 1
        self.requested_layers = include_layers
        return {
            "landslide": layer("landslide", "fixture landslide", "unavailable", "unknown", False),
            "debris_flow": layer("debris_flow", "fixture debris flow", "unavailable", "unknown", False),
        }


class UnavailableFloodProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return layer("flood", "fixture flood", "unavailable", "unknown", False)


class UnavailableGeologyProvider:
    def analyze(self, latitude: float, longitude: float, radius_m: int) -> dict:
        return {
            "geological_sensitivity": layer("geological_sensitivity", "fixture geological sensitivity", "unavailable", "unknown", False),
            "liquefaction": layer("liquefaction", "fixture liquefaction", "unavailable", "unknown", False),
            "active_fault": layer("active_fault", "fixture active fault", "unavailable", "unknown", False),
        }


def providers(**overrides):
    rows = {
        "terrain": TerrainProvider(),
        "slope_hazard": SlopeHazardProvider(),
        "flood": FloodProvider(),
        "geology": GeologyProvider(),
    }
    rows.update(overrides)
    return rows


def unavailable_providers(**overrides):
    rows = {
        "terrain": UnavailableTerrainProvider(),
        "slope_hazard": UnavailableSlopeHazardProvider(),
        "flood": UnavailableFloodProvider(),
        "geology": UnavailableGeologyProvider(),
    }
    rows.update(overrides)
    return rows


def layer(key: str, label: str, status: str, level: str, matched: bool) -> dict:
    return {
        "key": key,
        "label": label,
        "status": status,
        "level": level,
        "matched": matched,
        "distance_m": 120 if matched else None,
        "value": None,
        "explanation": f"{label} test result",
        "source": {"name": label, "agency": "official", "source_url": "https://example.gov.tw", "status": status},
    }


def test_coordinates_take_priority() -> None:
    result = analyze_terrain_risk(latitude=25.0, longitude=121.5, providers=providers(), searcher=lambda query: (_ for _ in ()).throw(AssertionError("should not geocode")))
    assert result["resolved_location"]["geocoding_confidence"] == "provided_coordinates"
    assert result["hazards"]["flood"]["matched"] is True
    assert result["overall"]["level"] == "medium"


def test_address_uses_geocoding_fallback() -> None:
    result = analyze_terrain_risk(city="台北市", district="大安區", road="和平東路二段", searcher=searcher, providers=providers())
    assert result["resolved_location"]["address_label"] == "台北市大安區和平東路二段"
    assert result["data_quality"]["status"] == "good"


def test_geocoding_failure_is_friendly() -> None:
    try:
        analyze_terrain_risk(address="missing", searcher=lambda query: {"matched": False, "center": None})
    except TerrainRiskLocationError as exc:
        assert "無法定位" in str(exc)
    else:
        raise AssertionError("expected TerrainRiskLocationError")


def test_provider_failure_does_not_crash() -> None:
    result = analyze_terrain_risk(latitude=25, longitude=121, providers=providers(flood=FailingProvider()))
    assert result["hazards"]["flood"]["status"] == "error"
    assert any("淹水" in item or "flood" in item for item in result["missing_sources"])
    assert result["disclaimer"]


def test_unavailable_sources_do_not_create_low_risk_with_fake_providers() -> None:
    slope = UnavailableSlopeHazardProvider()
    result = analyze_terrain_risk(latitude=25, longitude=121, providers=unavailable_providers(slope_hazard=slope))
    assert result["overall"]["level"] == "unknown"
    assert result["data_quality"]["status"] in {"limited", "unavailable"}
    assert result["missing_sources"]
    assert result["hazards"]["debris_flow"]["status"] == "unavailable"
    assert slope.calls == 1
    assert slope.http_calls == 0


def test_unavailable_source_case_does_not_depend_on_mvt_decoder(monkeypatch) -> None:
    monkeypatch.setattr(
        "services.terrain_risk_providers.ardswc_slope_hazard_provider._optional_decoder_available",
        lambda: True,
    )
    slope = UnavailableSlopeHazardProvider()
    result = analyze_terrain_risk(latitude=25, longitude=121, providers=unavailable_providers(slope_hazard=slope))
    assert result["overall"]["level"] == "unknown"
    assert result["hazards"]["debris_flow"]["status"] == "unavailable"
    assert slope.http_calls == 0


def test_debris_affect_hit_is_high() -> None:
    slope = SlopeHazardProvider(debris_flow=layer("debris_flow", "debris affect", "available", "high", True))
    result = analyze_terrain_risk(latitude=25, longitude=121, providers=providers(slope_hazard=slope), include_layers=["debris_flow"])
    assert result["overall"]["level"] == "high"
    assert any(item["key"] == "debris_flow" for item in result["risk_factors"])


def test_potential_landslide_affect_hit_is_high() -> None:
    slope = SlopeHazardProvider(landslide=layer("landslide", "landslide affect", "available", "high", True))
    result = analyze_terrain_risk(latitude=25, longitude=121, providers=providers(slope_hazard=slope), include_layers=["landslide"])
    assert result["overall"]["level"] == "high"


def test_debris_flow_nearby_is_medium() -> None:
    slope = SlopeHazardProvider(debris_flow=layer("debris_flow", "debris flow nearby", "available", "medium", True))
    result = analyze_terrain_risk(latitude=25, longitude=121, providers=providers(slope_hazard=slope), include_layers=["debris_flow"])
    assert result["overall"]["level"] == "medium"


def test_no_hit_with_other_major_sources_unavailable_is_unknown() -> None:
    result = analyze_terrain_risk(latitude=25, longitude=121, providers=providers(), include_layers=["debris_flow"])
    assert result["hazards"]["debris_flow"]["status"] == "available"
    assert result["overall"]["level"] == "unknown"


def test_include_layers_exclusion_does_not_call_slope_provider() -> None:
    slope = SlopeHazardProvider()
    result = analyze_terrain_risk(latitude=25, longitude=121, providers=providers(slope_hazard=slope), include_layers=["flood"])
    assert slope.calls == 0
    assert result["hazards"]["debris_flow"]["status"] == "skipped"
    assert result["hazards"]["landslide"]["status"] == "skipped"


def test_include_layers_passes_only_requested_slope_layers() -> None:
    slope = SlopeHazardProvider()
    analyze_terrain_risk(latitude=25, longitude=121, providers=providers(slope_hazard=slope), include_layers=["debris_flow"])
    assert slope.requested_layers == ("debris_flow",)


def test_service_rejects_radius_outside_contract() -> None:
    try:
        analyze_terrain_risk(latitude=25, longitude=121, radius_m=3000)
    except ValueError as exc:
        assert "radius_m" in str(exc)
    else:
        raise AssertionError("expected ValueError")
