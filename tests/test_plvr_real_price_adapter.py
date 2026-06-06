from services.adapters.plvr_real_price_adapter import PlvrRealPriceAdapter


def test_plvr_adapter_is_inactive_and_falls_back_to_sample() -> None:
    adapter = PlvrRealPriceAdapter()
    rows = adapter.load_transactions("台北市", "大安區", "和平東路二段")
    assert adapter.enabled is False
    assert rows
    assert all(row["road"] == "和平東路二段" for row in rows)
