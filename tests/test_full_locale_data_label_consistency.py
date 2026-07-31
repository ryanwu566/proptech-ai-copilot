"""Regression guards for complete locale-aware structured data labels."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRUCTURED = (ROOT / "frontend_next/lib/structured-options.ts").read_text(encoding="utf-8")
MAP_SEARCH = (ROOT / "frontend_next/lib/map-search.ts").read_text(encoding="utf-8")
HELP = (ROOT / "frontend_next/components/help-callout.tsx").read_text(encoding="utf-8")
PAGE = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
ADMIN = (ROOT / "frontend_next/lib/taiwan-admin-areas.json").read_text(encoding="utf-8")


def test_canonical_option_model_separates_value_id_and_localized_labels():
    assert "export type StructuredOption" in STRUCTURED
    for field in ("id:", "value:", "labels:", "aliases?", "originalLabel?", "source?"):
        assert field in STRUCTURED
    assert "getLocalizedOptionLabel" in STRUCTURED
    assert "createLocalizedOption" in STRUCTURED


def test_known_admin_and_road_labels_are_complete_in_each_locale():
    expected = (
        '"七堵區": { "zh-TW": "七堵區", en: "Qidu District", ja: "七堵区", ko: "치두구" }',
        '"屏東縣": { "zh-TW": "屏東縣", en: "Pingtung County", ja: "屏東県", ko: "핑둥현" }',
        '"林邊鄉": { "zh-TW": "林邊鄉", en: "Linbian Township", ja: "林辺郷", ko: "린볜향" }',
        '"忠信路": { "zh-TW": "忠信路", en: "Zhongxin Road", ja: "忠信通り（ジョンシン）", ko: "중신로" }',
    )
    for marker in expected:
        assert marker in STRUCTURED
    assert "\${value} District" not in STRUCTURED
    assert "\${value}구" not in STRUCTURED


def test_all_bundled_admin_values_are_covered_by_registry_driven_resolvers():
    assert "TAIWAN_ADMIN_AREAS.flatMap" in STRUCTURED
    assert "getAdministrativeOptions" in STRUCTURED
    assert "getAdministrativeDistrictOptions" in STRUCTURED
    assert "getStructuredOptionCoverage" in STRUCTURED
    assert "missingLabels" in STRUCTURED
    assert "duplicateIds" in STRUCTURED
    assert "duplicateCanonicalValues" in STRUCTURED
    assert '"areas"' in ADMIN


def test_map_search_accepts_localized_aliases_and_returns_canonical_values():
    assert "localeAliases" in MAP_SEARCH
    assert "getAdministrativeDistrictOptions" in MAP_SEARCH
    assert "new RegExp" in MAP_SEARCH
    assert "replacement: option.value" in MAP_SEARCH
    assert "normalizeTaiwanPlaceQuery(query: string, locale" in MAP_SEARCH


def test_locale_switch_and_structured_selects_never_mutate_logical_values():
    assert "option.value = stableValue" in STRUCTURED
    assert 'select[data-localize-structured-select]' in STRUCTURED
    provider = (ROOT / "frontend_next/components/experience-locale-provider.tsx").read_text(encoding="utf-8")
    assert "localStorage" not in provider
    assert "sessionStorage" not in provider
    assert "document.cookie" not in provider
    assert "setLocale" in provider


def test_shared_help_prefix_uses_active_locale_and_accessible_text():
    assert "useExperienceLocale" in HELP
    assert '"How to use:"' in HELP
    assert "aria-label={prefix}" in HELP
    assert "這頁怎麼用：" in HELP


def test_map_and_market_selectors_use_complete_label_resolvers():
    assert "getLocalizedCountyLabel(item, locale)" in PAGE
    assert "getLocalizedDistrictLabel(item, locale)" in PAGE
    assert "getLocalizedRoadLabel(item, locale)" in PAGE
    assert "getLocalizedSourceLabel(source, locale)" in PAGE
    assert "getLocalizedStateLabel" in PAGE
    assert "localizeStructuredSelects(document, locale)" in PAGE
