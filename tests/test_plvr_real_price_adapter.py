from services.adapters.plvr_real_price_adapter import PlvrRealPriceAdapter


def test_plvr_adapter_is_inactive_without_explicit_demo_provider() -> None:
    adapter = PlvrRealPriceAdapter()
    rows = adapter.load_transactions("Taipei City", "Central District", "Example Road")
    assert adapter.enabled is False
    assert rows == []
