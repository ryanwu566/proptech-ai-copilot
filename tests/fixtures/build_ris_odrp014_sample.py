"""Generator for the tiny sanitized RIS ODRP014 test fixture.

Kept beside the fixture to document its provenance and keep it rebuildable. It
writes small SYNTHETIC rows (not real village figures) that nonetheless follow
the exact ODRP014 schema, so tests can exercise pagination + normalization
offline without committing the full ~7781-row dataset.

This is a test-support artifact, not a production ingestion script. The
committed ``ris_odrp014_sample.json`` is the authoritative deterministic
fixture; ``test_ris_population_dataset`` asserts that ``build()`` still matches
it so the two never drift.
"""

from __future__ import annotations

import json
from pathlib import Path

FIXTURE_PATH = Path(__file__).resolve().parent / "ris_odrp014_sample.json"


def _age_fields(child_mf, work_mf, old_mf, top_mf):
    """Distribute totals into single-year buckets.

    child_mf -> put entirely at age 000; work_mf -> age 030; old_mf (65..99)
    -> age 070; top_mf -> 100up. Every other single-year bucket is "0".
    Each arg is a (male, female) tuple.
    """
    fields = {}
    for age in range(0, 100):
        fields[f"people_age_{age:03d}_m"] = "0"
        fields[f"people_age_{age:03d}_f"] = "0"
    fields["people_age_000_m"], fields["people_age_000_f"] = str(child_mf[0]), str(child_mf[1])
    fields["people_age_030_m"], fields["people_age_030_f"] = str(work_mf[0]), str(work_mf[1])
    fields["people_age_070_m"], fields["people_age_070_f"] = str(old_mf[0]), str(old_mf[1])
    fields["people_age_100up_m"], fields["people_age_100up_f"] = str(top_mf[0]), str(top_mf[1])
    return fields


def _row(district_code, site_id, village, household_no, child_mf, work_mf, old_mf, top_mf):
    male = child_mf[0] + work_mf[0] + old_mf[0] + top_mf[0]
    female = child_mf[1] + work_mf[1] + old_mf[1] + top_mf[1]
    total = male + female
    row = {
        "statistic_yyymm": "11507",
        "district_code": district_code,
        "site_id": site_id,
        "village": village,
        "household_no": str(household_no),
        "people_total": str(total),
        "people_total_m": str(male),
        "people_total_f": str(female),
    }
    row.update(_age_fields(child_mf, work_mf, old_mf, top_mf))
    return row


def build() -> dict:
    # Page 1: 2 rows (representative full page in miniature).
    row_a = _row("65000010001", "新北市板橋區", "留侯里", 3, (1, 1), (2, 3), (1, 1), (1, 0))
    # child=2, work=5, old=2, top=1 -> total 10, m=5, f=5
    row_b = _row("68000030005", "臺中市西屯區", "何厝里", 2, (0, 1), (1, 2), (0, 1), (0, 0))
    # child=1, work=3, old=1, top=0 -> total 5, m=1, f=4
    # Page 2: 1 row -> partial final page.
    row_c = _row("10017010012", "連江縣東引鄉", "樂華村", 1, (0, 0), (1, 0), (0, 1), (0, 0))
    # child=0, work=1, old=1, top=0 -> total 2, m=1, f=1

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
