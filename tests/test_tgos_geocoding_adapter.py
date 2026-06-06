from services.adapters.tgos_geocoding_adapter import TgosGeocodingAdapter


def test_tgos_without_credentials_skips_request() -> None:
    adapter = TgosGeocodingAdapter(app_id="", api_key="")
    assert adapter.available is False
    assert adapter.search("台北101", []) is None
