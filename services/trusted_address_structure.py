"""Bounded Taiwan address agreement, deliberately without fuzzy matching.

Only supplied components are required. Unparseable address input fails closed;
this is an acceptance gate, not a general purpose address repair service.
"""
from __future__ import annotations

import re


COUNTIES = (
    "臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市", "基隆市", "新竹市", "嘉義市",
    "新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣",
    "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣",
)
_DIGITS = str.maketrans("０１２３４５６７８９－", "0123456789-")
_NUMERAL = r"[0-9零〇一二三四五六七八九十百千]{1,8}"


def normalize_address(value: object) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 500:
        return ""
    text = re.sub(r"[\s,，、。．]", "", value.translate(_DIGITS).replace("台", "臺"))
    text = re.sub(r"^\d{3}(?:\d{2,3})?(?=[^0-9號段巷弄鄰之-])", "", text)
    text = re.sub(r"^(?:臺灣|中華民國)", "", text)
    text = re.sub(r"^\d{3}(?:\d{2,3})?(?=[^0-9號段巷弄鄰之-])", "", text)
    return text


def _number(text: str) -> str:
    if text.isascii() and text.isdigit():
        return str(int(text))
    digits = {c: i for i, c in enumerate("零一二三四五六七八九")}
    digits["〇"] = 0
    if all(c in digits for c in text):
        return str(int("".join(str(digits[c]) for c in text)))
    total = digit = 0
    for char in text:
        if char in digits:
            digit = digits[char]
        elif char in "十百千":
            total += (digit or 1) * {"十": 10, "百": 100, "千": 1000}[char]
            digit = 0
        else:
            return text
    return str(total + digit)


def address_parts(value: object) -> dict[str, str] | None:
    text = normalize_address(value)
    if not text:
        return None
    parts: dict[str, str] = {}
    for county in COUNTIES:
        if text.startswith(county):
            parts["county"] = county
            text = text[len(county):]
            break
    # Administrative prefixes only; 市府路 and 新市區 must not be truncated at 市.
    district = re.match(r"([\u4e00-\u9fff]{1,8}?[區鄉鎮]|[\u4e00-\u9fff]{1,8}?市)(?![區鄉鎮路街])", text)
    if district:
        parts["district"] = district[0]
        text = text[district.end():]
    # Only an explicit neighborhood delimiter disambiguates a village prefix.
    # Without it, 仁里五街 is a road name, not village 仁里 + road 五街.
    text = re.sub(rf"^(?:[\u4e00-\u9fff]{{1,8}}?[村里])?{_NUMERAL}鄰", "", text)
    road = re.match(r"([\u4e00-\u9fff0-9]{1,30}?(?:大道|路|街))", text)
    if road:
        parts["road"] = road[0]
        text = text[road.end():]
    for key, suffix in (("section", "段"), ("lane", "巷"), ("alley", "弄")):
        match = re.match(rf"({_NUMERAL})(?:[之-]({_NUMERAL}))?{suffix}", text)
        if match:
            parts[key] = _number(match[1]) + ("-" + _number(match[2]) if match[2] else "")
            text = text[match.end():]
    number = re.match(rf"({_NUMERAL})(?:[之-]({_NUMERAL}))?號(?:之({_NUMERAL}))?", text)
    if number:
        if number[2] and number[3]:
            return None
        parts["number"] = _number(number[1]) + ("-" + _number(number[2] or number[3]) if number[2] or number[3] else "")
        text = text[number.end():]
    # Floor/unit details are outside geocoding identity. Unknown structural residue is not.
    if text and not re.fullmatch(r"(?:地下)?[0-9一二三四五六七八九十BFbf之-]+[樓室Ff](?:之[0-9]+)?", text):
        return None
    return parts or None


def addresses_agree(supplied: object, returned: object, *, county: object = None, district: object = None) -> bool:
    expected = address_parts(supplied)
    actual = address_parts(returned)
    if not expected or not actual:
        return False
    if any(actual.get(key) != value for key, value in expected.items()):
        return False
    # Structured fields cannot contradict either the input or the formatted address.
    for key, value in (("county", county), ("district", district)):
        if isinstance(value, str) and value.strip():
            normalized = normalize_address(value)
            if (key in expected and expected[key] != normalized) or (key in actual and actual[key] != normalized):
                return False
    return True
