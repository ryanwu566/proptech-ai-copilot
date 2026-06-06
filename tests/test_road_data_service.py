"""Road data service tests."""

from services.road_data_service import list_cities, list_districts, list_roads


def test_demo_road_data_is_available() -> None:
    assert "台北市" in list_cities()
    assert "大安區" in list_districts("台北市")
    assert "和平東路二段" in list_roads("台北市", "大安區")
    assert "文化路二段" in list_roads("新北市", "板橋區")
    assert "松仁路" in list_roads("台北市", "信義區")


def test_unknown_road_filters_return_empty_lists() -> None:
    assert list_districts("不存在城市") == []
    assert list_roads("台北市", "不存在區域") == []
