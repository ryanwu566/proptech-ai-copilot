"""
Tests for risk-summary factor localization correctness.
Verifies:
- Confidence factors use confidence semantics, NOT burden semantics.
- Price factors do not render "price" as standalone internal key.
- Confidence factors do not render "confidence" as standalone internal key.
- Location-price factors do not render "location-price" as standalone internal key.
- All 4 locales have correct copy for new keys.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RISK_SUMMARY = (ROOT / "frontend_next" / "lib" / "risk-summary.ts").read_text(encoding="utf-8")
LOCALIZERS = (ROOT / "frontend_next" / "lib" / "dynamic-copy-localizers.ts").read_text(encoding="utf-8")
RUNTIME_COPY = (ROOT / "frontend_next" / "lib" / "runtime-copy.ts").read_text(encoding="utf-8")


def test_confidence_factor_uses_confidence_semantics_not_burden():
    """High valuation confidence must use confidence message, NOT burden message."""
    # The addConfidenceFactors function must reference confidence-specific keys
    assert "riskSummary.confidenceHighMessage" in RISK_SUMMARY
    assert "riskSummary.confidenceMediumMessage" in RISK_SUMMARY
    assert "riskSummary.confidenceLowMessage" in RISK_SUMMARY
    # It must NOT use burden keys for confidence
    # Find the addConfidenceFactors function content
    start = RISK_SUMMARY.index("function addConfidenceFactors")
    end = RISK_SUMMARY.index("\n}", start) + 2
    confidence_fn = RISK_SUMMARY[start:end]
    assert "burdenHealthy" not in confidence_fn
    assert "burdenCaution" not in confidence_fn
    assert "burdenHigh" not in confidence_fn
    # Must use confidence param, not ratio param
    assert "confidence" in confidence_fn
    assert "ratio" not in confidence_fn


def test_confidence_copy_keys_exist_in_all_4_locales():
    """All confidence message keys must exist in zh-TW, en, ja, ko dictionaries."""
    keys = [
        "riskSummary.confidenceHighMessage",
        "riskSummary.confidenceMediumMessage",
        "riskSummary.confidenceLowMessage",
    ]
    for key in keys:
        occurrences = RUNTIME_COPY.count(f'"{key}"')
        # Key appears in KEYS array + 4 locale dicts = at least 5
        assert occurrences >= 5, f"{key} found only {occurrences} times, expected >= 5 (key def + 4 locales)"


def test_location_price_title_keys_exist_in_all_4_locales():
    """Location-price support/not-support title keys must exist in all 4 locales."""
    keys = [
        "riskSummary.titleLocationSupportsPrice",
        "riskSummary.titleLocationNotSupportsPrice",
    ]
    for key in keys:
        occurrences = RUNTIME_COPY.count(f'"{key}"')
        assert occurrences >= 5, f"{key} found only {occurrences} times, expected >= 5"


def test_localizer_handles_price_factor_without_raw_key():
    """localizeFactorMessage for key=price must not return 'price' as raw text."""
    # The localizer must have explicit handling for key === "price"
    assert 'key === "price"' in LOCALIZERS
    # Must reference price explanation keys
    assert "riskSummary.priceOverpricedExplanation" in LOCALIZERS
    assert "riskSummary.priceReasonableExplanation" in LOCALIZERS


def test_localizer_handles_confidence_factor_without_raw_key():
    """localizeFactorMessage for key=confidence must not return 'confidence' as raw text."""
    assert 'key === "confidence"' in LOCALIZERS
    assert "riskSummary.confidenceHighMessage" in LOCALIZERS
    assert "riskSummary.confidenceMediumMessage" in LOCALIZERS
    assert "riskSummary.confidenceLowMessage" in LOCALIZERS


def test_localizer_handles_location_price_factor_without_raw_key():
    """localizeFactorMessage for key=location-price must not return 'location-price' as raw text."""
    assert 'key === "location-price"' in LOCALIZERS


def test_localizer_generic_fallback_does_not_return_raw_key():
    """The generic fallback in localizeFactorMessage must not return the raw key string."""
    # The fallback must use a safe translated label
    assert "common.noData" in LOCALIZERS
    # Must NOT have a bare `return key` as the final fallback
    lines = LOCALIZERS.split("\n")
    factor_msg_start = next(i for i, line in enumerate(lines) if "export function localizeFactorMessage" in line)
    # Find the end of the function
    brace_count = 0
    factor_msg_end = factor_msg_start
    for i in range(factor_msg_start, len(lines)):
        brace_count += lines[i].count("{") - lines[i].count("}")
        if brace_count == 0 and i > factor_msg_start:
            factor_msg_end = i
            break
    factor_fn = "\n".join(lines[factor_msg_start:factor_msg_end + 1])
    # Must not have a bare "return key" or "return params?.message ?? key"
    assert "?? key" not in factor_fn, "localizeFactorMessage must not fallback to raw key"


def test_factor_title_keys_cover_all_known_factor_types():
    """FACTOR_TITLE_KEYS must include all 7 known factor types."""
    for factor_key in ["loan", "holding", "location", "risk-facilities", "price", "confidence", "location-price"]:
        assert f'"{factor_key}"' in LOCALIZERS, f"FACTOR_TITLE_KEYS missing: {factor_key}"


def test_confidence_en_copy_contains_confidence_semantics():
    """EN copy for confidence high must contain 'confidence' wording, not 'burden'."""
    # Find the EN confidenceHighMessage value
    idx = RUNTIME_COPY.index('"riskSummary.confidenceHighMessage": "')
    # Read until the next quote
    start = idx + len('"riskSummary.confidenceHighMessage": "')
    end = RUNTIME_COPY.index('"', start)
    en_msg = RUNTIME_COPY[start:end]
    # Must contain confidence-related wording
    assert "confidence" in en_msg.lower() or "Confidence" in en_msg
    # Must NOT contain burden-related wording
    assert "burden" not in en_msg.lower()
    assert "ratio" not in en_msg.lower()


def test_localizer_title_does_not_return_raw_key_for_unknown():
    """localizeFactorTitle must not return raw key for unknown factor types."""
    assert "common.noData" in LOCALIZERS
    # The function must not have a bare return of `key`
    lines = LOCALIZERS.split("\n")
    title_start = next(i for i, line in enumerate(lines) if "export function localizeFactorTitle" in line)
    brace_count = 0
    title_end = title_start
    for i in range(title_start, len(lines)):
        brace_count += lines[i].count("{") - lines[i].count("}")
        if brace_count == 0 and i > title_start:
            title_end = i
            break
    title_fn = "\n".join(lines[title_start:title_end + 1])
    # Should not have `: key;` or `return key;` as bare fallback
    assert "return key" not in title_fn.replace("return key ?", "").replace("(key", ""), \
        "localizeFactorTitle should not return raw key"
