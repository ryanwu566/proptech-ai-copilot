"""Semantic regression guards for the checked-in four-locale label artifact."""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STRUCTURED = ROOT / "frontend_next/lib/structured-options.ts"
ADMIN = ROOT / "frontend_next/lib/taiwan-admin-areas.json"
LABELS = ROOT / "frontend_next/lib/taiwan-admin-labels.json"

LOCALES = ("zh-TW", "en", "ja", "ko")
FAKE_LABEL_PATTERNS = (
    re.compile(r"^Taiwan administrative area \d+$", re.I),
    re.compile(r"^Taiwan county \d+$", re.I),
    re.compile(r"^Road \d+", re.I),
    re.compile(r"^Building type \d+", re.I),
    re.compile(r"^Option \d+", re.I),
    re.compile(r"^Source \d+", re.I),
    re.compile(r"^Status \d+", re.I),
)


def _label_is_semantic(value: str, label: str, locale: str) -> bool:
    if not label.strip() or any(pattern.search(label) for pattern in FAKE_LABEL_PATTERNS):
        return False
    return not (locale in {"en", "ko"} and label.strip() == value.strip())


def test_versioned_artifact_covers_all_390_canonical_admin_values():
    registry = json.loads(ADMIN.read_text(encoding="utf-8"))
    artifact = json.loads(LABELS.read_text(encoding="utf-8"))
    values = [area["county"] for area in registry["areas"]]
    values.extend(district for area in registry["areas"] for district in area["districts"])
    entries = artifact["entries"]

    assert artifact["schema_version"] == "taiwan-admin-labels-v2"
    assert len(values) == 390
    assert len(entries) == len(values)
    assert {entry["value"] for entry in entries} == set(values)
    assert all(entry["code"] or entry["kind"] == "county" for entry in entries)
    assert all(entry["source"] and entry["englishSource"] for entry in entries)

    for entry in entries:
        for locale in LOCALES:
            assert _label_is_semantic(entry["value"], entry["labels"][locale], locale), entry["value"]


def test_semantic_coverage_rejects_fake_numeric_templates():
    for label in (
        "Taiwan administrative area 9176",
        "Taiwan county 2479",
        "Road 1234",
        "Building type 5678",
        "Option 9012",
        "Source 3456",
        "Status 6789",
    ):
        assert not _label_is_semantic("unknown", label, "en")


def test_deployed_screenshot_numeric_placeholders_are_absent_from_admin_artifact():
    artifact = LABELS.read_text(encoding="utf-8")
    placeholders = (
        "Taiwan administrative area 9176", "Taiwan administrative area 2479",
        "Taiwan administrative area 1729", "Taiwan administrative area 9348",
        "Taiwan administrative area 1987", "Taiwan administrative area 3937",
        "Taiwan administrative area 1974", "Taiwan administrative area 3873",
        "Taiwan administrative area 4662", "Taiwan administrative area 9608",
        "Taiwan administrative area 7022", "Taiwan administrative area 6163",
        "Taiwan administrative area 2449",
    )
    assert all(placeholder not in artifact for placeholder in placeholders)


def test_representative_counties_have_complete_expected_english_names():
    artifact = json.loads(LABELS.read_text(encoding="utf-8"))
    by_value = {entry["value"]: entry for entry in artifact["entries"]}
    expected = {
        "基隆市": {
            "仁愛區": "Renai District", "信義區": "Xinyi District", "中正區": "Zhongzheng District",
            "中山區": "Zhongshan District", "安樂區": "Anle District", "暖暖區": "Nuannuan District", "七堵區": "Qidu District",
        },
        "臺北市": {
            "中正區": "Zhongzheng District", "大同區": "Datong District", "中山區": "Zhongshan District",
            "松山區": "Songshan District", "大安區": "Daan District", "萬華區": "Wanhua District",
            "信義區": "Xinyi District", "士林區": "Shilin District", "北投區": "Beitou District",
            "內湖區": "Neihu District", "南港區": "Nangang District", "文山區": "Wenshan District",
        },
        "澎湖縣": {"馬公市": "Magong City"},
    }
    for districts in expected.values():
        for value, label in districts.items():
            assert by_value[value]["labels"]["en"] == label

    registry = json.loads(ADMIN.read_text(encoding="utf-8"))
    pingtung = next(area for area in registry["areas"] if area["county"] == "屏東縣")
    assert len(pingtung["districts"]) == 33
    assert all(_label_is_semantic(value, by_value[value]["labels"]["en"], "en") for value in pingtung["districts"])


def test_four_locale_labels_are_stable_and_korean_is_hangul_primary():
    artifact = json.loads(LABELS.read_text(encoding="utf-8"))
    entries = artifact["entries"]
    assert len({entry["labels"]["en"] for entry in entries}) > 300
    assert len({entry["labels"]["ko"] for entry in entries}) > 300
    assert all(any("\uac00" <= char <= "\ud7a3" for char in entry["labels"]["ko"]) for entry in entries)
    assert all(not any(char.isdigit() for char in entry["labels"][locale]) for entry in entries for locale in LOCALES)


def test_runtime_resolver_uses_artifact_and_truthful_unknown_fallback():
    source = STRUCTURED.read_text(encoding="utf-8")
    assert 'taiwan-admin-labels.json' in source
    assert "ADMIN_LABEL_BY_VALUE" in source
    assert "isSemanticallyUsableLabel" in source
    assert "hashLabel" not in source
    assert "genericLabel" not in source
    assert "Taiwan administrative area ${" not in source
    assert "Taiwan county ${" not in source
    assert "Road ${token}" not in source
    assert "option.labels[locale]" in source
    assert "truthfulLabels(value)" in source


def test_static_guard_rejects_customer_facing_hash_and_numeric_fallbacks():
    roots = (ROOT / "frontend_next/app", ROOT / "frontend_next/components", ROOT / "frontend_next/lib")
    forbidden = (
        "hashLabel(", "genericLabel(", "Taiwan administrative area ${", "Taiwan county ${",
        "Road ${token}", "Building type ${", "Option ${", "Source ${", "Status ${",
    )
    for root in roots:
        for path in root.rglob("*"):
            if path.suffix not in {".ts", ".tsx"}:
                continue
            source = path.read_text(encoding="utf-8")
            for expression in forbidden:
                assert expression not in source, f"{path}:{expression}: replace with an artifact label or truthful original value"


def test_actual_map_selector_and_search_remain_on_shared_locale_layer():
    page = (ROOT / "frontend_next/app/page.tsx").read_text(encoding="utf-8")
    map_search = (ROOT / "frontend_next/lib/map-search.ts").read_text(encoding="utf-8")
    assert "getLocalizedCountyLabel(item, locale)" in page
    assert "getLocalizedDistrictLabel(item, locale)" in page
    assert "getLocalizedRoadLabel(item, locale)" in page
    assert "localizeStructuredSelects(document, locale)" in page
    assert "localeAliases" in map_search
    assert "replacement: option.value" in map_search


def test_no_new_browser_storage_or_external_translation_provider():
    source = STRUCTURED.read_text(encoding="utf-8")
    assert "localStorage" not in source
    assert "sessionStorage" not in source
    assert "fetch(" not in source
    assert "translation" not in source.lower()
