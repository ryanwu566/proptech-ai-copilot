"""Road data service tests."""

from services import road_data_service
from services.road_data_service import DEMO_ROADS, list_cities, list_districts, list_roads


def test_demo_road_data_is_available() -> None:
    assert "台北市" in list_cities()
    assert "大安區" in list_districts("台北市")
    assert "和平東路二段" in list_roads("台北市", "大安區")
    assert "文化路二段" in list_roads("新北市", "板橋區")
    assert "松仁路" in list_roads("台北市", "信義區")


def test_unknown_road_filters_return_empty_lists() -> None:
    assert list_districts("不存在城市") == []
    assert list_roads("台北市", "不存在區域") == []


def test_missing_road_csv_falls_back_to_demo_rows(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(road_data_service, "DATA_PATH", tmp_path / "missing.csv")
    road_data_service.load_road_rows.cache_clear()
    try:
        assert road_data_service.load_road_rows() == DEMO_ROADS
    finally:
        road_data_service.load_road_rows.cache_clear()


def test_routes_import_does_not_load_road_csv() -> None:
    import importlib
    from backend.api import routes_road

    road_data_service.load_road_rows.cache_clear()
    importlib.reload(routes_road)
    assert road_data_service.load_road_rows.cache_info().currsize == 0
