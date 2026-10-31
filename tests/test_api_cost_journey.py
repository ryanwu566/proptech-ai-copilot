"""Bounded representative provider journey with mocked physical transports.

Market/Valuation and snapshot consumer behavior is covered by the browser journey;
this measures the external-provider segment using one fixture tile per MVT layer.
"""
import asyncio
from datetime import datetime, timezone
from types import SimpleNamespace

import httpx

from services import location_resolver, commute_routing_service, satellite_reference
from services.adapters.google_places_adapter import GooglePlacesAdapter, CATEGORY_TYPES
from services.adapters.routes_adapter import GoogleRoutesAdapter
from services.adapters.nlsc_gateway_adapter import NlscGatewayAdapter
from services.terrain_risk_providers import geologycloud_provider, nlsc_terrain_provider, ardswc_slope_hazard_provider
from services.map_service import get_nearby_places


REPRESENTATIVE_GOOGLE_RESULT = {
    "formatted_address": "臺北市中正區北平西路3號",
    "partial_match": False,
    "geometry": {
        "location_type": "ROOFTOP",
        "location": {"lat": 25.0478, "lng": 121.517},
    },
    "address_components": [
        {"long_name": "臺北市", "types": ["administrative_area_level_1", "political"]},
        {"long_name": "中正區", "types": ["administrative_area_level_3", "political"]},
        {"long_name": "北平西路", "types": ["route"]},
        {"long_name": "3", "types": ["street_number"]},
    ],
}


def measure_journey(monkeypatch, modules=None):
    """Also used once locally against original modules to record the baseline."""
    modules = modules or SimpleNamespace(
        resolver=location_resolver, routes=commute_routing_service,
        satellite=satellite_reference, ardswc=ardswc_slope_hazard_provider,
        geology=geologycloud_provider, nlsc=nlsc_terrain_provider,
        places=GooglePlacesAdapter, route_adapter=GoogleRoutesAdapter,
    )
    counts = {"geocoding": 0, "places": 0, "routes": 0, "ardswc": 0,
              "tile_decodes": 0, "liquefaction": 0, "nlsc": 0, "satellite": 0}
    monkeypatch.setenv("GOOGLE_MAPS_API_KEY", "journey-fixture-only")
    monkeypatch.delenv("TGOS_APP_ID", raising=False)
    monkeypatch.delenv("TGOS_API_KEY", raising=False)
    def geocode(*args, **kwargs):
        counts["geocoding"] += 1
        return httpx.Response(200, request=httpx.Request("GET", "https://fixture.invalid"),
                              json={"status": "OK", "results": [REPRESENTATIVE_GOOGLE_RESULT]})
    monkeypatch.setattr(modules.resolver.httpx, "get", geocode)
    if hasattr(modules.resolver, "_RESOLVED_ADDRESS_CACHE"):
        modules.resolver._RESOLVED_ADDRESS_CACHE.clear()
    modules.routes.clear_route_cache()
    def transport(request):
        kind = "places" if "places" in request.url.host else "routes" if "routes" in request.url.host else "nlsc"
        counts[kind] += 1
        payload = {"places": []} if kind == "places" else {"routes": [{"duration": "900s", "distanceMeters": 4000}]} if kind == "routes" else {"status": "available", "source": "NLSC", "slope_value": 0, "slope_class": "gentle", "elevation_m": 0}
        return httpx.Response(200, json=payload)
    def tile_fetch(url, timeout):
        counts["ardswc"] += 1
        return b"fixture-tile"
    def tile_decode(payload, tile):
        counts["tile_decodes"] += 1
        return []
    def geology_fetch(url, timeout):
        counts["liquefaction"] += 1
        return b'{"type":"FeatureCollection","features":[]}'
    class SatelliteAdapter:
        def fetch(self, query):
            counts["satellite"] += 1
            return modules.satellite.SatelliteAdapterResult(b"\xff\xd8fixture-jpeg\xff\xd9")
    # This journey measures the accepted EE completed-result cache, not PHOTO2's
    # on-demand, unknown-vintage result (limited, with no completed-image cache).
    monkeypatch.setenv("SATELLITE_REFERENCE_PROVIDER", "earth_engine")
    satellite_adapter = SatelliteAdapter()
    tiles = modules.ardswc.ArdswcSlopeHazardProvider(http_get=tile_fetch, decoder=tile_decode)
    geology = modules.geology.GeologyCloudProvider(http_get=geology_fetch)
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        places = modules.places(api_key="fixture-only", client=client)
        routes = modules.route_adapter(api_key="fixture-only", client=client)
        nlsc = modules.nlsc.NlscTerrainProvider(gateway=NlscGatewayAdapter(client=client, environ={
            "NLSC_GATEWAY_BASE_URL": "https://gateway.example.tw", "NLSC_GATEWAY_CLIENT_TOKEN": "fixture-only-token-123"}))
        snapshots = []
        for _ in range(2):
            destination = modules.resolver.resolve_address("臺北市中正區北平西路3號")
            assert destination["status"] == "resolved"
            assert (destination["source"], destination["confidence"]) == ("google", "high")
            location = get_nearby_places(25.033, 121.5654, 800, list(CATEGORY_TYPES), adapter=places)
            assert len(location["categories"]) == 6
            route = modules.routes.estimate_commute_route((25.033, 121.5654), (destination["latitude"], destination["longitude"]), "transit", google_adapter=routes, allow_mock=False)
            assert route["duration_seconds"] == 900
            assert nlsc.analyze(25.033, 121.5654, 500)["slope_value"] == 0
            assert geology.analyze(25.033, 121.5654, 500, "臺北市")["liquefaction"]["level"] == "unknown"
            for layer in modules.ardswc.MVT_LAYERS:
                result = tiles._query_mvt_layer(layer, [modules.ardswc.TileCoord(14, 9876, 5678)], 25.033, 121.5654, 500)
                assert result["status"] == "available"
            satellite = asyncio.run(modules.satellite.fetch_satellite_reference(latitude=25.033, longitude=121.5654,
                now=datetime(2026, 10, 8, 4, tzinfo=timezone.utc), adapter=satellite_adapter))
            assert satellite.status == "available"
            assert satellite.provider == "earth_engine"
            snapshots.append(dict(counts))
    modules.routes.clear_route_cache()
    return snapshots


def test_representative_external_provider_journey_reuses_same_valid_context(monkeypatch):
    # The cost journey must exercise a legitimate direct Google acceptance.
    assert REPRESENTATIVE_GOOGLE_RESULT["geometry"]["location_type"] == "ROOFTOP"
    assert REPRESENTATIVE_GOOGLE_RESULT["partial_match"] is False
    assert {component["types"][0]: component["long_name"] for component in REPRESENTATIVE_GOOGLE_RESULT["address_components"]} == {
        "administrative_area_level_1": "臺北市", "administrative_area_level_3": "中正區",
        "route": "北平西路", "street_number": "3",
    }

    def reject_tgos(*args, **kwargs):
        raise AssertionError("A valid Google fixture must not call TGOS")

    monkeypatch.setattr(location_resolver.TgosAddressProvider, "resolve", reject_tgos)
    first, repeated = measure_journey(monkeypatch)
    expected = {"geocoding": 1, "places": 6, "routes": 1, "ardswc": 4,
                "tile_decodes": 4, "liquefaction": 3, "nlsc": 1, "satellite": 1}
    assert first == expected
    assert repeated == expected
    assert sum(value for key, value in repeated.items() if key != "tile_decodes") == 17
