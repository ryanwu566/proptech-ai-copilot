from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_frontend(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_frontend_has_explicit_valuation_state_boundary() -> None:
    helper = read_frontend("frontend_next/lib/valuation-result-state.ts")
    boundary = read_frontend("frontend_next/components/valuation-result-boundary.tsx")
    assert "getValuationDisplayState" in helper
    assert "valuation_status" in helper
    assert "is_actionable" in helper
    assert "ValuationResultBoundary" in boundary
    assert "不能作為出價、貸款或案件決策依據" in boundary or "不能作為出價、貸款或案件決策依據" in helper


def test_frontend_share_rejects_non_actionable_valuation() -> None:
    share = read_frontend("frontend_next/lib/valuation-share.ts")
    assert "getValuationDisplayState" in share
    assert "displayState.kind !== \"available\"" in share
    assert "不可用或展示狀態的價格數字" in share


def test_frontend_page_uses_boundary_before_numeric_result_tiles() -> None:
    page = read_frontend("frontend_next/app/page.tsx")
    assert "ValuationResultBoundary" in page
    assert "getValuationDisplayState(result).kind !== \"available\"" in page


def test_no_public_contract_allows_provider_internals() -> None:
    routes = (ROOT / "backend/api/routes_valuation.py").read_text(encoding="utf-8")
    contract = (ROOT / "services/valuation_result_contract.py").read_text(encoding="utf-8")
    assert "safe_error" not in routes
    assert "PUBLIC_SOURCE_DETAIL_KEYS" in contract
    assert "raw provider payload" not in routes
