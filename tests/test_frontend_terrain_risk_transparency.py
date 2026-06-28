"""Static frontend checks for terrain risk transparency UI."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_PATH = ROOT / "frontend_next" / "components" / "terrain-risk-analysis.tsx"
API_PATH = ROOT / "frontend_next" / "lib" / "api.ts"
VIEWING_DECISION_PATHS = [
    ROOT / "frontend_next" / "components" / "viewing-decision-panel.tsx",
    ROOT / "frontend_next" / "components" / "decision-report.tsx",
    ROOT / "frontend_next" / "lib" / "viewing-decision.ts",
]

COMPONENT = COMPONENT_PATH.read_text(encoding="utf-8")
API = API_PATH.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index(f"function {name}")
    next_function = source.find("\nfunction ", start + 1)
    return source[start:] if next_function == -1 else source[start:next_function]


def test_transparency_type_contract_is_whitelisted() -> None:
    assert "TerrainRiskSourceTransparencyLayer" in API
    for field in (
        "layer_id",
        "display_name",
        "source_name",
        "source_kind",
        "assessment_status",
        "coverage_status",
        "data_updated_at",
        "caveat",
    ):
        assert field in API
    assert "source_transparency?: { notice: string; layers: TerrainRiskSourceTransparencyLayer[] }" in API


def test_terrain_risk_transparency_ui_exists_with_conservative_notice() -> None:
    assert "風險資料來源與限制" in COMPONENT
    assert "地勢與災害資料僅供看房風險參考，資料不足或暫時不可用不代表沒有風險。" in COMPONENT
    assert "SourceLayerCard" in COMPONENT
    assert "不能解讀為低風險" in COMPONENT


def test_transparency_ui_does_not_render_raw_provider_fields() -> None:
    body = _function_body(COMPONENT, "RiskSourceTransparency")
    source_card = _function_body(COMPONENT, "SourceLayerCard")
    combined = body + source_card

    for forbidden in ("source_url", "external_view_url", "latitude", "longitude", "formatted_address", "token", "secret", "raw"):
        assert forbidden not in combined


def test_transparency_ui_adds_no_api_call_or_browser_storage() -> None:
    body = _function_body(COMPONENT, "RiskSourceTransparency")
    assert "api.terrainRiskAnalyze" not in body
    assert "useEffect" not in body
    for forbidden in ("localStorage", "sessionStorage", "document.cookie", "location.search", "location.hash"):
        assert forbidden not in body


def test_viewing_decision_files_are_not_wired_to_terrain_transparency() -> None:
    for path in VIEWING_DECISION_PATHS:
        text = path.read_text(encoding="utf-8")
        assert "source_transparency" not in text
        assert "風險資料來源與限制" not in text
