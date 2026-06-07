from services.community_index_service import load_communities, match_community


def test_community_index_loads_sample() -> None:
    assert len(load_communities()) >= 3


def test_community_index_matches_address_text() -> None:
    result = match_community("台北市", "大安區", "和平東路二段", "和平綠境 8 樓")
    assert result is not None
    assert result["community_name"] == "和平綠境"
    assert result["confidence"] == "high"


def test_community_index_unknown_road_returns_none() -> None:
    assert match_community("台北市", "大安區", "不存在路段") is None


def test_explicit_unknown_community_does_not_claim_match() -> None:
    assert match_community("台北市", "大安區", "和平東路二段", "不存在社區") is None
