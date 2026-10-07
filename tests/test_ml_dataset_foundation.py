"""Offline contract tests; every transaction below is synthetic, never training data."""
from copy import deepcopy
from decimal import Decimal
import json
import math
import os
import subprocess
import sys
import zipfile

import pytest

from scripts.ml import semantics as s
from scripts.ml import lineage as l
from scripts.ml import contracts as c
from scripts.ml import audit_foundation as a


def proof():
    return {"sha256": "b" * 64, "locator": "reviewed-fixture-evidence", "version": "fixture-v1"}


def row(**changes):
    item = {
        "交易標的": "房地(土地+建物)", "主要用途": "住家用",
        "建物型態": "公寓(5樓含以下無電梯)", "交易年月日": "1130615",
        "建築完成年月": "10306", "交易筆棟數": "土地2建物1車位0",
        "車位類別": "", "車位總價元": "0", "車位移轉總面積平方公尺": "0",
        "建物移轉總面積平方公尺": "100", "總價元": "10000000",
        "單價元平方公尺": "100000", "移轉層次": "三層", "總樓層數": "五層",
        "鄉鎮市區": "中壢區", "縣市": "桃園市", "編號": "SYNTHETIC-1", "備註": "",
    }
    item.update(changes)
    return item


def context(**changes):
    item = {"member_name": "h_lvr_land_a.csv", "schema_evidence": proof(),
            "rights_evidence": proof(), "full_rights": True, "one_dwelling": True,
            "area_evidence": proof(), "area_basis": s.AREA_VERSION,
            "parking_evidence": proof(), "parking_detail_count": 0,
            "blank_parking_means_absent": False, "source_schema_version": "fixture-v1",
            "special_transaction": False}
    item.update(changes)
    return item


@pytest.mark.parametrize("city,district,member,valid,reason", [
    ("臺北市", "大安區", "a_lvr_land_a.csv", True, "canonical"),
    ("台北市", "大安區", "a_lvr_land_a.csv", True, "tai_variant"),
    ("台南市", "中壢區", "d_lvr_land_a.csv", False, "current_registry_mismatch"),
    ("台南市", "中壢區", "h_lvr_land_a.csv", False, "source_county_conflict"),
    ("臺北縣", "板橋市", "f_lvr_land_a.csv", False, "historical_admin_name"),
    ("新竹市", "新竹市", "o_lvr_land_a.csv", False, "city_level_only"),
    ("台 北市", "大安區", "a_lvr_land_a.csv", False, "malformed_source_value"),
    ("臺北市", "大安區�", "a_lvr_land_a.csv", False, "source_encoding_issue"),
    ("臺北市", "大安區", "a_lvr_land_b.csv", False, "unsupported_source_member"),
])
def test_geography_does_not_guess_county(city, district, member, valid, reason):
    result = s.normalize_geography(city, district, member)
    assert result["valid"] is valid
    assert result["reason"] == reason
    assert result["raw_city"] == city


@pytest.mark.parametrize("value,expected", [
    ("1130615", {"value": "2024-06-15", "precision": "day"}),
    ("10306", {"value": "2014-06", "precision": "month"}),
    ("1130230", None), ("1100231", None), ("11313", None), ("113", None),
    ("1130600", None), ("NaN", None), ("", None),
])
def test_date_validates_calendar_and_preserves_precision(value, expected):
    assert s.parse_roc_date(value) == expected


@pytest.mark.parametrize("value,expected", [("十一層",11),("3",3),("三層",3),
    ("3,4",None),("三層,四層",None),("全",None),("地下二層",None),("0",None)])
def test_floor_rejects_multifloor_and_basements(value, expected):
    assert s.parse_floor(value) == expected


@pytest.mark.parametrize("changes,ctx,want", [
    ({}, {}, "NO_PARKING_CONFIRMED"),
    ({"交易筆棟數":"土地1建物1車位2"}, {}, "PARKING_PRESENT"),
    ({"車位類別":"坡道平面"}, {}, "PARKING_PRESENT"),
    ({"車位總價元":"100000"}, {}, "PARKING_PRESENT"),
    ({"車位移轉總面積平方公尺":"10"}, {}, "PARKING_PRESENT"),
    ({"車位總價元":""}, {}, "PARKING_SEMANTICS_AMBIGUOUS"),
    ({"車位總價元":""}, {"blank_parking_means_absent":True}, "NO_PARKING_CONFIRMED"),
    ({"交易筆棟數":""}, {}, "UNKNOWN"),
    ({"車位總價元":"NaN"}, {}, "PARKING_SEMANTICS_AMBIGUOUS"),
    ({}, {"parking_detail_count":None}, "UNKNOWN"),
    ({}, {"parking_evidence":None}, "UNKNOWN"),
])
def test_parking_requires_independent_absence_evidence(changes, ctx, want):
    raw = row(**changes)
    result = s.classify_parking(raw, context(**ctx))
    assert result == want
    if want != "NO_PARKING_CONFIRMED":
        assert not s.evaluate_row(raw, context(**ctx))["eligible"]


def test_target_is_ntd_per_registered_ping_without_prerounding():
    result = s.construct_target(row(), context())
    assert result["area_ping"] == "30.2500"
    assert Decimal(result["unit_price_ntd_ping"]) == Decimal(10000000) / Decimal("30.2500")
    assert result["log_unit_price"] == pytest.approx(math.log(330578.5123966942))
    assert result["target_version"] == "residential-unit-ntd-ping-log-v1"


@pytest.mark.parametrize("changes,ctx", [
    ({"總價元":"0"},{}), ({"總價元":"-1"},{}), ({"總價元":"NaN"},{}),
    ({"總價元":"Infinity"},{}), ({"建物移轉總面積平方公尺":""},{}),
    ({"建物移轉總面積平方公尺":"0"},{}), ({"建物移轉總面積平方公尺":"-1"},{}),
    ({"建物移轉總面積平方公尺":"bad"},{}), ({"建物移轉總面積平方公尺":"NaN"},{}),
    ({"單價元平方公尺":"999"},{}), ({"單價元平方公尺":"Infinity"},{}),
    ({"交易筆棟數":"土地1建物1車位1"},{}), ({},{"area_evidence":None}),
])
def test_invalid_target_fails_closed(changes, ctx):
    assert not s.construct_target(row(**changes), context(**ctx))["valid"]


@pytest.mark.parametrize("changes,ctx,reason", [
    ({"主要用途":"住商用"},{},"non_residential_use"),
    ({"交易標的":"房地(土地+建物)+車位"},{},"unsupported_transaction_target"),
    ({},{"rights_evidence":None},"rights_unverified"),
    ({},{"full_rights":False},"rights_unverified"),
    ({"交易筆棟數":"土地1建物2車位0"},{},"not_single_building"),
    ({"備註":"親友交易"},{},"special_note_requires_review"),
    ({"移轉層次":"三層,四層"},{},"floor_ambiguous"),
    ({"交易年月日":"11306"},{},"transaction_day_required"),
])
def test_cohort_eligibility_does_not_substitute_type_for_proof(changes,ctx,reason):
    result=s.evaluate_row(row(**changes), context(**ctx))
    assert not result["eligible"]
    assert reason in result["reasons"]


def test_month_age_never_uses_wall_clock_or_invents_day():
    assert s.age_at_transaction("1130615", "10306") == {"age_months":120,"age_years":10.0,"precision":"month"}
    assert s.age_at_transaction("1130615", "11406") is None
    assert s.age_at_transaction("1130615", "1030231") is None


def occurrence(raw=None, release="r1", available="2024-07-01T00:00:00+00:00", number=1, **changes):
    item={"raw":raw or row(),"context":context(),"source_dataset_id":c.SOURCE_ID,
          "release_id":release,"archive_sha256":("a" if release=="r1" else "d")*64,"member_sha256":"c"*64,
          "member_name":"h_lvr_land_a.csv","physical_row_number":number,
          "source_release_available_at":available,"availability_evidence":proof(),
          "ingested_at":"2024-07-02T00:00:00+00:00","transformed_at":"2024-07-03T00:00:00+00:00",
          "import_batch_id":"fixture-batch", "parser_version":s.PARSER_VERSION,
          "transform_version":s.TRANSFORM_VERSION,"identity_evidence":proof(),
          "supersedes_version_id":None,"cancelled":False}
    item.update(changes)
    return item


def test_family_identity_is_price_independent_and_county_scoped():
    first=occurrence()
    changed=occurrence(row(**{"總價元":"11000000"}))
    assert l.identify(first)["transaction_family_id"] == l.identify(changed)["transaction_family_id"]
    assert l.identify(first)["version_id"] != l.identify(changed)["version_id"]
    assert l.identify(first)["occurrence_id"] != l.identify(occurrence(number=2))["occurrence_id"]
    wrong=occurrence(member_name="d_lvr_land_a.csv")
    assert l.identify(first)["transaction_family_id"] != l.identify(wrong)["transaction_family_id"]


def test_duplicate_and_republication_retain_all_occurrence_accounting():
    result=l.select_as_of([occurrence(),occurrence(number=2),occurrence(release="r2",number=3)],"2024-09-01T00:00:00+00:00")
    assert len(result["selected"]) == 1
    assert result["excluded_reasons"] == {"exact_duplicate":1,"republication":1}
    assert result["input_occurrences"] == 3


def test_later_correction_cannot_leak_back_or_resurrect_older_eligible_row():
    old=occurrence()
    new=occurrence(row(**{"主要用途":"店舖"}),release="r2",available="2024-08-01T00:00:00+00:00",
        supersedes_version_id=l.identify(old)["version_id"])
    early=l.select_as_of([new,old],"2024-07-15T00:00:00+00:00")
    assert early["selected"][0]["raw"]["主要用途"] == "住家用"
    late=a.audit_staging([old,new],"2024-09-01T00:00:00+00:00")
    assert late["final_candidate_count"] == 0
    assert late["funnel"][0]["excluded_reasons"] == {"superseded_version":1}


def test_unknown_or_unordered_version_quarantines_whole_family():
    old=occurrence()
    unknown=occurrence(row(**{"總價元":"11000000"}),release="r2",available=None)
    assert not l.select_as_of([old,unknown],"2024-09-01T00:00:00+00:00")["selected"]
    unordered=occurrence(row(**{"總價元":"11000000"}),release="r2",available="2024-08-01T00:00:00+00:00")
    result=l.select_as_of([old,unordered],"2024-09-01T00:00:00+00:00")
    assert result["excluded_reasons"] == {"revision_ambiguous":2}


def test_cancellation_is_selected_before_cohort_filtering():
    old=occurrence()
    canceled=occurrence(release="r2",available="2024-08-01T00:00:00+00:00",cancelled=True,
        supersedes_version_id=l.identify(old)["version_id"])
    result=a.audit_staging([old,canceled],"2024-09-01T00:00:00+00:00")
    assert result["final_candidate_count"] == 0
    assert result["funnel"][0]["excluded_reasons"] == {"cancelled_as_of_cutoff":1,"superseded_version":1}


def test_funnel_is_deterministic_reconciled_and_never_mutates_inputs():
    items=[occurrence(),occurrence(row(**{"編號":"SYNTHETIC-2","車位類別":"坡道平面"}),number=2)]
    before=deepcopy(items)
    report=a.audit_staging(items,"2024-09-01T00:00:00+00:00")
    assert report == a.audit_staging(list(reversed(items)),"2024-09-01T00:00:00+00:00")
    assert items == before
    assert report["final_candidate_count"] == 1
    assert report["parking_classification"] == {"NO_PARKING_CONFIRMED":1,"PARKING_PRESENT":1}
    for stage in report["funnel"]:
        assert stage["input_count"] == stage["remaining_count"] + stage["excluded_count"]
        assert stage["excluded_count"] == sum(stage["excluded_reasons"].values())
    assert "SYNTHETIC" not in json.dumps(report)


def test_bounded_jsonl_refuses_to_report_truncated_input(tmp_path):
    path=tmp_path/'private.jsonl'
    path.write_text('\n'.join(json.dumps(occurrence(number=n)) for n in range(1,4)),encoding='utf-8')
    with pytest.raises(ValueError,match='row_limit'):
        a.read_staging(path,max_rows=2)


def test_manifest_rejects_unknown_availability_and_count_mismatch():
    manifest=manifest_fixture()
    c.validate_manifest(manifest)
    manifest["row_count"]=2
    with pytest.raises(ValueError,match='count'):
        c.validate_manifest(manifest)
    manifest=manifest_fixture()
    manifest["source_releases"][0]["source_release_available_at"]=None
    with pytest.raises(ValueError,match='availab'):
        c.validate_manifest(manifest)


def manifest_fixture():
    return {
        "schema_version":c.MANIFEST_VERSION,"dataset_version":"residential-valuation-v1.synthetic-fixture",
        "target_version":s.TARGET_VERSION,"area_version":s.AREA_VERSION,
        "price_version":"whole-rights-land-and-residential-building-sale-no-parking-v1",
        "feature_columns":["county_district","building_type","area_ping","floor","prediction_year","prediction_month"],
        "feature_schema_version":"residential-model-a-v1","source_ledger_version":c.LEDGER_VERSION,
        "geography_version":s.GEOGRAPHY_VERSION,"identity_version":l.IDENTITY_VERSION,
        "selection_version":l.SELECTION_VERSION,"cohort_version":s.COHORT_VERSION,
        "transform_version":s.TRANSFORM_VERSION,"parser_version":s.PARSER_VERSION,
        "built_at":"2024-09-02T00:00:00+00:00","training_data_cutoff":"2024-09-01T00:00:00+00:00",
        "label_observation_cutoff":"2024-09-01T00:00:00+00:00","timezone":"Asia/Taipei",
        "prediction_framing":"public_information_research",
        "feature_cutoff_policy":"prediction_clock_and_independently_available_subject_attributes",
        "availability_cutoff":"2024-09-01T00:00:00+00:00","row_count":1,"raw_row_count":2,"excluded_row_count":1,
        "dataset_checksum":"a"*64,"exclusion_ledger_checksum":"b"*64,"cohort_definition_hash":"c"*64,
        "source_ledger_checksum":"d"*64,"transform_code_checksum":"e"*64,"dependency_lock_checksum":"f"*64,
        "builder_git_commit":"e"*40,"registry_checksum":"a"*64,"split_manifest_checksum":"b"*64,
        "preprocessing_manifest_checksum":None,"artifact_format":"canonical-jsonl-utf8-v1",
        "output_sort_key":["transaction_family_id","version_id"],"complete_coverage_evidence":proof(),
        "subject_attribute_availability_evidence":proof(),
        "subgroup_counts":{
            "county_district":[{"label":"桃園市/中壢區","rows":1}],
            "building_type":[{"label":"公寓","rows":1}],
            "transaction_month":[{"label":"2024-06","rows":1}],
        },
        "source_releases":[{"source_release_id":"fixture-r1","archive_sha256":"a"*64,"schema_sha256":"b"*64,
            "source_release_available_at":"2024-07-01T00:00:00+00:00","availability_evidence":proof(),
            "members":[{"member_name":"h_lvr_land_a.csv","member_sha256":"c"*64,"schema_sha256":"b"*64,
                        "raw_row_count":2,"accepted_row_count":1,"rejected_row_count":1}]}],
    }


def test_recovery_does_not_treat_metadata_as_bytes(tmp_path):
    evidence=json.loads(a.CANONICAL_EVIDENCE.read_text(encoding='utf-8'))
    ledger=a.inventory_releases(evidence,tmp_path)
    assert len(ledger["releases"]) == 17
    assert {x["recovery_status"] for x in ledger["releases"]} == {"MISSING"}
    assert all(x["source_release_available_at"] is None for x in ledger["releases"])
    c.validate_ledger(ledger)


def test_missing_parking_type_is_unknown_even_with_zero_numeric_fields():
    raw=row()
    del raw["車位類別"]
    assert s.classify_parking(raw,context()) == "UNKNOWN"
    assert not s.evaluate_row(raw,context())["eligible"]


def test_conflicting_context_for_identical_payload_is_not_hash_tiebroken():
    old=occurrence()
    contradictory=occurrence(number=2,context=context(full_rights=False))
    report=a.audit_staging([old,contradictory],"2024-09-01T00:00:00+00:00")
    assert report["final_candidate_count"] == 0
    assert report["funnel"][0]["excluded_reasons"] == {"semantic_evidence_conflict":2}


def test_exact_same_facts_with_distinct_official_ids_are_not_merged():
    first=occurrence()
    second=occurrence(row(**{"編號":"SYNTHETIC-2"}),number=2)
    assert a.audit_staging([first,second],"2024-09-01T00:00:00+00:00")["final_candidate_count"] == 2


def test_timestamp_rejects_date_only_and_release_sequence_is_not_availability():
    assert l.timestamp("2024-07-01") is None
    item=occurrence(available=None,artifact_sequence=999)
    assert l.select_as_of([item],"2024-09-01T00:00:00+00:00")["excluded_reasons"] == {"availability_unknown":1}


def test_manifest_rejects_effective_cutoff_after_availability_cutoff():
    manifest=manifest_fixture()
    manifest["training_data_cutoff"]="2024-09-02T00:00:00+00:00"
    with pytest.raises(ValueError,match="cutoff"):
        c.validate_manifest(manifest)


def test_demo_and_arbitrary_source_cannot_enter_official_cohort():
    for source in ("real_price_sample","unknown","moi-plvr-rental"):
        report=a.audit_staging([occurrence(source_dataset_id=source)],"2024-09-01T00:00:00+00:00")
        assert report["final_candidate_count"] == 0
        assert report["funnel"][0]["excluded_reasons"] == {"unsupported_source":1}


def test_physical_row_conflict_across_official_ids_quarantines_both_families():
    first=occurrence()
    second=occurrence(row(**{"編號":"SYNTHETIC-2"}))
    result=a.audit_staging([first,second],"2024-09-01T00:00:00+00:00")
    assert result["final_candidate_count"] == 0
    assert result["funnel"][0]["excluded_reasons"] == {"occurrence_conflict":2}


@pytest.mark.parametrize("change", [
    {"source_release_available_at":"2024-07-01T00:00:00+00:00"},
    {"member_sha256":"d"*64},
])
def test_immutable_release_member_conflicts_are_checked_before_cutoff(change):
    first=occurrence(available="2024-08-01T00:00:00+00:00")
    second=deepcopy(first)
    second.update(change)
    report=a.audit_staging([first,second],"2024-07-15T00:00:00+00:00")
    assert report["final_candidate_count"] == 0
    assert report["funnel"][0]["excluded_reasons"] == {"immutable_lineage_conflict":2}


def test_manifest_pins_feature_schema_and_ledger_pins_each_source(tmp_path):
    manifest=manifest_fixture()
    manifest["feature_schema_version"]="private-road-age-v999"
    with pytest.raises(ValueError):
        c.validate_manifest(manifest)
    ledger=a.inventory_releases(a.read_json(a.CANONICAL_EVIDENCE),tmp_path)
    ledger["releases"][0]["source_dataset_id"]="real_price_sample"
    with pytest.raises(ValueError):
        c.validate_ledger(ledger)


def test_local_contracts_also_pass_formal_json_schema_validation(tmp_path):
    jsonschema=pytest.importorskip("jsonschema")
    for name,value in (
        ("dataset-manifest-v1.schema.json",manifest_fixture()),
        ("release-ledger-v1.schema.json",a.inventory_releases(a.read_json(a.CANONICAL_EVIDENCE),tmp_path)),
        ("staging-occurrence-v1.schema.json",occurrence()),
    ):
        schema=json.loads((s.ROOT/'docs/ml/contracts'/name).read_text(encoding='utf-8'))
        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema,format_checker=jsonschema.FormatChecker()).validate(value)


def test_archive_inventory_verifies_bytes_and_requires_embedded_schemas(tmp_path):
    path=tmp_path/'synthetic.zip'
    with zipfile.ZipFile(path,'w') as archive:
        for name in ('MANIFEST.CSV','schema-main.csv','schema-build.csv','schema-land.csv','schema-park.csv','h_lvr_land_a.csv'):
            archive.writestr(name,'synthetic fixture,not real source')
    checksum=a.file_sha256(path)
    assert a._archive_status(path,checksum)[0] == "AVAILABLE"
    assert a._archive_status(path,"0"*64) == ("PARTIALLY AVAILABLE","historical_checksum_mismatch")
    incomplete=tmp_path/'incomplete.zip'
    with zipfile.ZipFile(incomplete,'w') as archive:
        archive.writestr('h_lvr_land_a.csv','synthetic fixture')
    assert a._archive_status(incomplete,a.file_sha256(incomplete))[0] == "PARTIALLY AVAILABLE"


def test_cli_reports_only_aggregates_and_does_not_modify_private_input(tmp_path):
    path=tmp_path/'private.jsonl'
    path.write_text(json.dumps(occurrence(),ensure_ascii=False)+'\n',encoding='utf-8')
    original=path.read_bytes()
    args=[sys.executable,'-m','scripts.ml.audit_foundation','--staging',str(path),
          '--cutoff','2024-09-01T00:00:00+00:00']
    result=subprocess.run(args,cwd=s.ROOT,capture_output=True,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    assert result.returncode == 0
    report=json.loads(result.stdout)
    assert report['final_candidate_count'] == 1
    assert b'SYNTHETIC-1' not in result.stdout
    assert path.read_bytes() == original
    path.write_text('{"raw":"private-secret"}',encoding='utf-8')
    invalid=subprocess.run(args,cwd=s.ROOT,capture_output=True,env={**os.environ,'PYTHONIOENCODING':'utf-8'})
    assert invalid.returncode == 2
    assert b'private-secret' not in invalid.stderr + invalid.stdout


@pytest.mark.parametrize('value', ['1130000', '1130230', '0000615'])
def test_bad_effective_dates_cannot_enter_cohort(value):
    result=a.audit_staging([occurrence(row(**{'交易年月日':value}))], '2024-09-01T00:00:00+00:00')
    assert result['final_candidate_count'] == 0


def test_present_unit_price_tolerance_and_missing_unit_price_are_explicit():
    assert s.construct_target(row(**{'單價元平方公尺':'100100'}),context())['valid']
    assert not s.construct_target(row(**{'單價元平方公尺':'100101'}),context())['valid']
    assert s.construct_target(row(**{'單價元平方公尺':''}),context())['valid']


def test_missing_id_cannot_hide_conflicting_payload_for_known_physical_row():
    known=occurrence()
    missing=occurrence(row(**{'編號':''}))
    report=a.audit_staging([known,missing],'2024-09-01T00:00:00+00:00')
    assert report['final_candidate_count'] == 0
    assert report['funnel'][0]['excluded_reasons'] == {'identity_missing':1,'occurrence_conflict':1}


def test_registry_report_hash_ignores_git_line_ending_conversion(tmp_path,monkeypatch):
    canonical=a.read_json(a.CANONICAL_EVIDENCE)
    ledger=a.inventory_releases(canonical,tmp_path)
    registry_text=s.REGISTRY.read_text(encoding='utf-8')
    path=tmp_path/'registry.json'
    monkeypatch.setattr(s,'REGISTRY',path)
    path.write_bytes(registry_text.encode('utf-8'))
    lf=a.audit_inventory(canonical,ledger)['registry_sha256']
    path.write_bytes(registry_text.replace('\n','\r\n').encode('utf-8'))
    crlf=a.audit_inventory(canonical,ledger)['registry_sha256']
    assert lf == crlf


def test_code_text_hash_ignores_git_line_ending_conversion(tmp_path):
    path=tmp_path/'source.py'
    path.write_bytes(b'x = 1\n')
    lf=a.repository_text_sha256(path)
    path.write_bytes(b'x = 1\r\n')
    assert a.repository_text_sha256(path) == lf
