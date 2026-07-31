"""Coverage checks for the generated, offline road display dataset."""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "road-display-catalog-v2"
FORBIDDEN = ("Official road name (", "Unknown road ", "Road 123")


def _records() -> list[dict[str, object]]:
    manifest = json.loads((CATALOG / "manifest.json").read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    for file in manifest["files"]:
        records.extend(json.loads((CATALOG / file["path"]).read_text(encoding="utf-8"))["records"])
    return records


def test_catalog_has_all_scoped_road_keys_and_four_meaningful_labels() -> None:
    records = _records()
    assert len(records) == 35516
    assert len({(record["county"], record["district"], record["canonical"]) for record in records}) == len(records)
    for record in records:
        labels = record["labels"]
        assert labels["zh-TW"] == record["canonical"]
        assert labels["en"] and labels["ja"] and labels["ko"]
        assert any("\u30a0" <= char <= "\u30ff" for char in labels["ja"])
        assert any("\uac00" <= char <= "\ud7a3" for char in labels["ko"])
        assert not any(forbidden in labels["en"] or forbidden in labels["ja"] or forbidden in labels["ko"] for forbidden in FORBIDDEN)


def test_daxi_fixture_has_distinct_romanized_and_localized_road_names() -> None:
    records = [record for record in _records() if record["county"] == "桃園市" and record["district"] == "大溪區"]
    assert len(records) >= 20
    for locale in ("en", "ja", "ko"):
        labels = [record["labels"][locale] for record in records]
        assert len(set(labels)) == len(labels)
    assert all(any(char.isascii() and char.isalpha() for char in record["labels"]["en"]) for record in records)


def test_catalog_derivation_is_offline_and_no_runtime_translation_provider_is_declared() -> None:
    manifest = json.loads((CATALOG / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "road-display-v2"
    assert all(record["derivation"]["en"] == "offline_romanization" for record in _records())
    assert all(record["sourceVersion"] == "road-display-v2" for record in _records())
