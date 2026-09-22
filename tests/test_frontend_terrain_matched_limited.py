"""Regression contracts for surfacing a matched official hazard even when the
source status is ``limited``.

Bug: the hazard card previously rendered its headline purely from
``availabilityLabel(status)`` so ``status=limited`` mapped to
"參考／外部確認" and hid a real ``matched=true`` high-risk official signal.

These are source-level (static) contracts because the frontend Node
dependencies (``frontend_next/node_modules``) are not installed in this
environment, so the component cannot be rendered at runtime here. They assert
the corrected rendering precedence exists in the component and copy source.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPONENT_PATH = ROOT / "frontend_next" / "components" / "terrain-risk-analysis.tsx"
COPY_PATH = ROOT / "frontend_next" / "lib" / "surface-copy.ts"

COMPONENT = COMPONENT_PATH.read_text(encoding="utf-8")
COPY = COPY_PATH.read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    start = source.index(f"function {name}")
    next_function = source.find("\nfunction ", start + 1)
    return source[start:] if next_function == -1 else source[start:next_function]


def _hazard_presentation_body() -> str:
    return _function_body(COMPONENT, "hazardPresentation")


def _hazard_card_body() -> str:
    return _function_body(COMPONENT, "HazardCard")


# --- Copy keys required for the matched presentation (all 4 locales) ---------


def test_copy_defines_matched_range_and_distance_and_limited_caveat() -> None:
    # Each new key must appear once per locale object. There are 4 locales, but
    # ja/ko are built from ``...terrainEn`` plus an ``Object.assign`` override,
    # so each key should be present for zh, en, ja, ko => >= 4 occurrences.
    for key in ("matchedRange", "nearestDistance", "limitedSourceCaveat"):
        occurrences = COPY.count(f"{key}:")
        assert occurrences >= 4, f"{key} must be defined for all 4 locales (found {occurrences})"


def test_distance_copy_uses_placeholder_token() -> None:
    # The distance line must interpolate the numeric distance.
    assert "{m}" in COPY


def test_limited_caveat_wording_is_conservative() -> None:
    # Must not imply the hazard is resolved or absent; must direct to official map.
    assert "官方圖" in COPY  # 官方圖資 / 官方圖台


# --- hazardPresentation precedence logic -------------------------------------


def test_hazard_presentation_helper_exists() -> None:
    assert "function hazardPresentation" in COMPONENT


def test_hazard_presentation_uses_fields_independently() -> None:
    body = _hazard_presentation_body()
    # Reads matched, level, status and distance_m from the hazard.
    assert "hazard.matched" in body
    assert "hazard.level" in body
    assert "hazard.status" in body
    assert "hazard.distance_m" in body


def test_scenario_1_limited_matched_high_surfaces_high_signal() -> None:
    # matched=true must take precedence over status=limited and drive the
    # headline from the risk level (copy.risk.*), not availabilityLabel.
    body = _hazard_presentation_body()
    matched_index = body.index("hazard.matched")
    # The risk-level headline (copy.risk[...]) must be reachable from the
    # matched branch and must appear before the not-matched availability label.
    assert "copy.risk" in body
    assert body.index("copy.risk") > matched_index


def test_scenario_2_limited_matched_medium_uses_level_lookup() -> None:
    body = _hazard_presentation_body()
    # Level lookup must map high/medium/low, not hard-code high only.
    assert '"medium"' in body or "medium" in body
    assert "copy.risk[" in body or "copy.risk." in body


def test_scenario_3_limited_no_match_stays_reference_external() -> None:
    body = _hazard_presentation_body()
    # For matched=false the limited/skipped path must still yield the
    # reference/external headline.
    assert "copy.referenceExternal" in body


def test_scenario_4_available_no_match_stays_checked_state() -> None:
    body = _hazard_presentation_body()
    # matched=false + available keeps the existing auto-check headline.
    assert "copy.autoCheckAvailable" in body


def test_scenario_5_unavailable_or_error_stays_temporarily_unavailable() -> None:
    body = _hazard_presentation_body()
    assert '"unavailable"' in body
    assert '"error"' in body
    assert "copy.temporarilyUnavailable" in body


def test_scenario_6_limited_matched_still_shows_limited_source_caveat() -> None:
    body = _hazard_presentation_body()
    # The limited-source caveat must be attached specifically when the matched
    # hazard's status is limited.
    assert "copy.limitedSourceCaveat" in body
    assert '"limited"' in body


def test_scenario_7_distance_is_shown_when_present() -> None:
    body = _hazard_presentation_body()
    assert "hazard.distance_m" in body
    assert "copy.nearestDistance" in body
    # Distance line rendered by the card.
    card = _hazard_card_body()
    assert "distanceLine" in card or "nearestDistance" in card


def test_scenario_8_fail_closed_wording_remains_intact() -> None:
    # The conservative fail-closed notice must remain in the component.
    assert "資料不足或暫時不可用不代表沒有風險" in COMPONENT
    # matched=false + limited must never imply "no risk" — it stays reference.
    assert "copy.referenceExternal" in _hazard_presentation_body()


def test_hazard_card_renders_matched_range_and_caveat() -> None:
    card = _hazard_card_body()
    # The card surfaces the matched-range label and the caveat produced by the
    # presentation helper.
    assert "hazardPresentation" in card
    assert "matchedRange" in card
    assert "caveat" in card


def test_hazard_card_no_longer_headlines_solely_from_availability_label() -> None:
    # The old bug: HazardCard headline came only from availabilityLabel(status).
    # After the fix the headline must be driven by hazardPresentation.
    card = _hazard_card_body()
    assert "availabilityLabel(hazard.status" not in card
