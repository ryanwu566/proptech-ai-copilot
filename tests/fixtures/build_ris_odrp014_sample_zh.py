"""Generator for the tiny sanitized RIS ODRP014 fixture in the 11504-style
Chinese source schema.

Mirrors ``build_ris_odrp014_sample.py`` but emits Chinese field names, so tests
can prove the provider's source-schema adapter turns a localized month into the
canonical English schema and paginates successfully. SYNTHETIC rows only.

The committed ``ris_odrp014_sample_zh.json`` is the authoritative deterministic
fixture; ``test_ris_population_provider`` asserts ``build()`` still matches it.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parent / "ris_odrp014_sample_zh.json"


def _age_fields(child_mf, work_mf, old_mf, top_mf):
    """Distribute totals into Chinese-named single-year buckets."""
    fields = {}
    for age in range(0, 100):
        fields[f"{age}歲-男"] = "0"
        fields[f"{age}歲-女"] = "0"
    fields["0歲-男"], fields["0歲-女"] = str(child_mf[0]), str(child_mf[1])
    fields["30歲-男"], fields["30歲-女"] = str(work_mf[0]), str(work_mf[1])
    fields["70歲-男"], fields["70歲-女"] = str(old_mf[0]), str(old_mf[1])
    fields["100歲以上-男"], fields["100歲以上-女"] = str(top_mf[0]), str(top_mf[1])
    return fields


def _row(district_code, site_id, village, household_no, child_mf, work_mf, old_mf, top_mf):
    male = child_mf[0] + work_mf[0] + old_mf[0] + top_mf[0]
    female = child_mf[1] + work_mf[1] + old_mf[1] + top_mf[1]
    total = male + female
    row = {
        "統計年月": "11504",
        "區域別代碼": district_code,
        "區域別": site_id,
        "村里": village,
        "戶數": str(household_no),
        "人口數": str(total),
        "人口數-男": str(male),
        "人口數-女": str(female),
    }
    row.update(_age_fields(child_mf, work_mf, old_mf, top_mf))
    return row


def build() -> dict:
    row_a = _row("65000010002", "新北市板橋區", "流芳里", 3, (1, 1), (2, 3), (1, 1), (1, 0))
    row_b = _row("68000030005", "臺中市西屯區", "何厝里", 2, (0, 1), (1, 2), (0, 1), (0, 0))
    row_c = _row("10017010012", "連江縣東引鄉", "樂華村", 1, (0, 0), (1, 0), (0, 1), (0, 0))

    total_data_size = 3
    return {
        "page_1": {
            "responseCode": "OD-0101-S",
            "responseMessage": "處理完成",
            "totalPage": "2",
            "totalDataSize": str(total_data_size),
            "page": "1",
            "pageDataSize": "2",
            "responseData": [row_a, row_b],
        },
        "page_2": {
            "responseCode": "OD-0101-S",
            "responseMessage": "處理完成",
            "totalPage": "2",
            "totalDataSize": str(total_data_size),
            "page": "2",
            "pageDataSize": "1",
            "responseData": [row_c],
        },
        "page_3": {
            "responseCode": "OD-0102-S",
            "responseMessage": "查無資料",
            "totalPage": None,
            "totalDataSize": None,
            "page": None,
            "pageDataSize": None,
        },
    }


def main() -> None:
    FIXTURE_PATH.write_text(json.dumps(build(), ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {FIXTURE_PATH}")


if __name__ == "__main__":
    main()
