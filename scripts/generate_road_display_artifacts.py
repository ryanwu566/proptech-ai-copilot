"""Generate reviewable offline road display artifacts from the official road CSV.

The generator is intentionally build-time only.  The web app consumes the compact
character phonetic map; the county-scoped JSON files remain available for review,
diffing, and coverage audits without shipping the nationwide catalog to browsers.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

from unidecode import unidecode


ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "data" / "taiwan_roads.csv"
PHONETICS_PATH = ROOT / "frontend_next" / "lib" / "road-phonetics.ts"
CATALOG_ROOT = ROOT / "data" / "road-display-catalog-v2"
VERSION = "road-display-v2"

CHINESE_NUMBERS = {
    "零": 0,
    "一": 1,
    "二": 2,
    "兩": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}
DIRECTIONS = {"東": "East", "西": "West", "南": "South", "北": "North"}
EN_SUFFIXES = (("高速公路", "Expressway"), ("公路", "Highway"), ("大道", "Boulevard"), ("路", "Road"), ("街", "Street"), ("巷", "Lane"), ("弄", "Alley"))
JA_SUFFIXES = (("高速公路", "高速道路 ハイウェイ"), ("公路", "幹線道路 ハイウェイ"), ("大道", "大通り メインストリート"), ("路", "道路 ロード"), ("街", "通り ストリート"), ("巷", "路地 レーン"), ("弄", "路地 アレイ"))
KO_SUFFIXES = (("高速公路", "고속도로"), ("公路", "간선도로"), ("大道", "대로"), ("路", "로"), ("街", "길"), ("巷", "골목"), ("弄", "골목"))

KATA_INITIALS = {"zh": "ジ", "ch": "チ", "sh": "シ", "j": "ジ", "q": "チ", "x": "シ", "b": "ブ", "p": "プ", "m": "ム", "f": "フ", "d": "ド", "t": "ト", "n": "ヌ", "l": "ル", "g": "グ", "k": "ク", "h": "ホ", "r": "ル", "z": "ズ", "c": "ツ", "s": "ス", "y": "イ", "w": "ウ"}
KATA_FINALS = {"ang": "アン", "eng": "ン", "ong": "オン", "iang": "ヤン", "uang": "ワン", "ian": "イェン", "uan": "ワン", "iao": "ヤオ", "ing": "イン", "iong": "ヨン", "ai": "アイ", "ei": "エイ", "ao": "アオ", "ou": "オウ", "an": "アン", "en": "エン", "in": "イン", "un": "ウン", "a": "ア", "e": "エ", "i": "イ", "o": "オ", "u": "ウ", "er": "アー"}

CHOSEONG = {"g": 0, "k": 15, "h": 18, "j": 12, "q": 14, "x": 9, "zh": 12, "ch": 14, "sh": 9, "r": 5, "z": 12, "c": 14, "s": 9, "b": 7, "p": 17, "m": 6, "f": 8, "d": 3, "t": 16, "n": 2, "l": 5, "y": 11, "w": 11}
JUNGSEONG = {"a": 0, "ai": 3, "an": 0, "ang": 0, "ao": 8, "e": 4, "ei": 6, "en": 4, "eng": 4, "er": 4, "i": 20, "ia": 2, "ian": 2, "iang": 2, "iao": 10, "ie": 2, "in": 20, "ing": 20, "io": 8, "iong": 8, "iu": 13, "o": 8, "ong": 8, "ou": 13, "u": 13, "ua": 9, "uai": 9, "uan": 14, "uang": 14, "ui": 13, "un": 13, "uo": 14, "v": 13, "ve": 13, "yu": 13}
JONGSEONG = {"n": 4, "ng": 21, "m": 16, "r": 8, "k": 15, "t": 7, "p": 17}


def chinese_number(value: str) -> int | None:
    if not value or any(char not in CHINESE_NUMBERS for char in value):
        return None
    if value == "十":
        return 10
    if "十" in value:
        left, _, right = value.partition("十")
        return (CHINESE_NUMBERS.get(left, 1) * 10) + CHINESE_NUMBERS.get(right, 0)
    result = 0
    for char in value:
        result = result * 10 + CHINESE_NUMBERS[char]
    return result


def pinyin_for_char(char: str) -> str:
    return unidecode(char).strip().lower() if "\u4e00" <= char <= "\u9fff" else char


def kata_for_token(token: str) -> str:
    token = token.lower()
    if not token:
        return ""
    for final in sorted(KATA_FINALS, key=len, reverse=True):
        if token.endswith(final) and len(token) > len(final):
            initial = token[: -len(final)]
            prefix = KATA_INITIALS.get(initial, KATA_INITIALS.get(initial[:1], ""))
            return prefix + KATA_FINALS[final]
    return KATA_FINALS.get(token, KATA_INITIALS.get(token[:1], "イ") + "ア")


def hangul_for_token(token: str) -> str:
    token = token.lower()
    if not token:
        return ""
    initial_key = next((key for key in ("zh", "ch", "sh") if token.startswith(key)), token[:1])
    rest = token[len(initial_key):]
    vowel = next((key for key in sorted(JUNGSEONG, key=len, reverse=True) if rest.startswith(key)), "a")
    ending = rest[len(vowel):]
    onset = CHOSEONG.get(initial_key, 11)
    medial = JUNGSEONG[vowel]
    final = JONGSEONG.get(ending, 0)
    return chr(0xAC00 + ((onset * 21) + medial) * 28 + final)


def phonetic_record(char: str) -> dict[str, str]:
    pinyin = pinyin_for_char(char)
    return {"en": pinyin.title(), "ja": kata_for_token(pinyin), "ko": hangul_for_token(pinyin)}


def romanized_base(value: str) -> str:
    result: list[str] = []
    current: list[str] = []
    for char in value:
        if char in DIRECTIONS:
            if current:
                result.append("".join(current).title())
                current = []
            result.append(DIRECTIONS[char])
        else:
            current.append(pinyin_for_char(char).lower())
    if current:
        result.append("".join(current).title())
    return " ".join(part for part in result if part)


def split_structure(canonical: str) -> tuple[str, str | None, str]:
    if canonical.endswith("段"):
        for length in (2, 1):
            number = canonical[-1 - length : -1]
            if chinese_number(number) is not None:
                return canonical[: -1 - length], str(chinese_number(number)), "section"
    for suffix, label in EN_SUFFIXES:
        if canonical.endswith(suffix):
            return canonical[: -len(suffix)], None, label
    return canonical, None, ""


def labels_for(canonical: str) -> dict[str, str]:
    base, section, suffix = split_structure(canonical)
    trailing_number = None
    if section is None:
        match = re.search(r"([零一二兩三四五六七八九十]+)$", base)
        if match and match.start() > 0:
            trailing_number = chinese_number(match.group(1))
            base = base[: match.start()]
    english = romanized_base(base)
    if trailing_number is not None:
        ordinal = {1: "1st", 2: "2nd", 3: "3rd"}.get(trailing_number, f"{trailing_number}th")
        english = f"{english} {ordinal}"
    if suffix:
        english = f"{english} {suffix}"
    if section is not None:
        english_base = base[:-1] if base.endswith("路") else base
        english = f"{romanized_base(english_base)} Road, Section {section}"

    ja_base = "".join(phonetic_record(char)["ja"] if "\u4e00" <= char <= "\u9fff" else char for char in base)
    ko_base = "".join(phonetic_record(char)["ko"] if "\u4e00" <= char <= "\u9fff" else char for char in base)
    if trailing_number is not None:
        ja_base += str(trailing_number)
        ko_base += str(trailing_number)
    ja_suffix = dict(JA_SUFFIXES).get(next((raw for raw, label in EN_SUFFIXES if label == suffix), ""), "")
    ko_suffix = dict(KO_SUFFIXES).get(next((raw for raw, label in EN_SUFFIXES if label == suffix), ""), "")
    ja = ja_base + ja_suffix
    ko = ko_base + ko_suffix
    if section is not None:
        ja_core = ja_base[:-2] if base.endswith("路") else ja_base
        ko_core = ko_base[:-1] if base.endswith("路") else ko_base
        ja = f"{ja_core}道路 第{section}区間"
        ko = f"{ko_core}로 제{section}구간"
    if not ja:
        ja = "".join(phonetic_record(char)["ja"] for char in canonical)
    if not ko:
        ko = "".join(phonetic_record(char)["ko"] for char in canonical)
    return {"zh-TW": canonical, "en": english or romanized_base(canonical), "ja": ja, "ko": ko}


def slug(index: int) -> str:
    return f"county-{index:02d}"


def main() -> None:
    rows = list(csv.DictReader(CSV_PATH.open("r", encoding="utf-8-sig", newline="")))
    scoped: dict[str, set[tuple[str, str]]] = defaultdict(set)
    all_chars = sorted({char for row in rows for char in row["road"] if "\u4e00" <= char <= "\u9fff"})
    for row in rows:
        city = row["city"].strip()
        district = row["site_id"].strip().removeprefix(city).strip()
        road = row["road"].strip()
        if city and district and road:
            scoped[city].add((district, road))

    PHONETICS_PATH.write_text(
        "// Generated by scripts/generate_road_display_artifacts.py; do not edit manually.\n"
        + "export type RoadPhonetics = { en: string; ja: string; ko: string };\n"
        + "export const ROAD_PHONETICS: Record<string, RoadPhonetics> = "
        + json.dumps({char: phonetic_record(char) for char in all_chars}, ensure_ascii=False, sort_keys=True, indent=2)
        + ";\n",
        encoding="utf-8",
    )
    CATALOG_ROOT.mkdir(parents=True, exist_ok=True)
    for old in CATALOG_ROOT.glob("county-*.json"):
        old.unlink()
    manifest = {"schema_version": VERSION, "source": "data/taiwan_roads.csv", "record_count": 0, "scoped_key_count": 0, "files": []}
    for index, city in enumerate(sorted(scoped), 1):
        entries = []
        for district, canonical in sorted(scoped[city]):
            entries.append({"county": city, "district": district, "canonical": canonical, "labels": labels_for(canonical), "romanization": labels_for(canonical)["en"], "source": "offline Unidecode build artifact", "sourceVersion": VERSION, "derivation": {"en": "offline_romanization", "ja": "offline_transliteration", "ko": "offline_transliteration"}})
        filename = slug(index) + ".json"
        (CATALOG_ROOT / filename).write_text(json.dumps({"schema_version": VERSION, "county": city, "records": entries}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        manifest["record_count"] += len(entries)
        manifest["scoped_key_count"] += len({(entry["district"], entry["canonical"]) for entry in entries})
        manifest["files"].append({"county": city, "path": filename, "record_count": len(entries)})
    (CATALOG_ROOT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"ROAD_RECORDS_TOTAL={len(rows)}")
    print(f"SCOPED_ROAD_KEYS_TOTAL={manifest['scoped_key_count']}")
    print(f"PHONETIC_CHARACTERS={len(all_chars)}")


if __name__ == "__main__":
    main()
