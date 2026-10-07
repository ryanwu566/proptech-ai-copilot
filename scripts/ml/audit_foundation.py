"""Bounded read-only foundation audit; stdout contains aggregate JSON only.

Run from the repository root with python -m scripts.ml.audit_foundation.
Inventory mode consumes the canonical ML-A evidence, not the serving database.
Staging mode checks a private, evidence-linked JSONL contract; no dataset is built.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
import hashlib
import json
from pathlib import Path
import zipfile
from zoneinfo import ZoneInfo

from . import contracts as c
from . import lineage as l
from . import semantics as s

CANONICAL_EVIDENCE = s.ROOT / "docs/ml/valuation-dataset-audit-evidence-v1.json"
MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_ROWS = 10000
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
STAGES = ("parse_valid","geography_valid","residential_use","rights_valid",
          "property_type_supported","parking_safe","target_valid","physical_valid")
BLOCKERS = {
    "B1":"Recover raw sale-main, matching schemas/details, and residential/rights/area/parking proof.",
    "B2":"Establish evidenced availability and complete ordered revision/cancellation history.",
    "B3":"Verify source county and official ID namespace; quarantine unresolved conflicts.",
    "B4":"Restore exact bytes and demonstrate two complete offline dataset builds with matching hashes.",
    "B5":"Measure actual eligible chronological volume, coverage and label maturity after B1–B4.",
    "B6":"Strict parser fixtures pass; real-release schema/detail integration remains unverified.",
}


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda:handle.read(1024*1024),b""):
            digest.update(block)
    return digest.hexdigest()


def repository_text_sha256(path: Path) -> str:
    """Pin UTF-8 source content with universal LF endings, across Git checkouts."""
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def read_json(path: Path, limit: int = MAX_INPUT_BYTES):
    if path.stat().st_size > limit:
        raise ValueError("input_byte_limit")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))


def read_staging(path: Path, max_rows: int = MAX_ROWS) -> list[dict]:
    if not 1 <= max_rows <= 100000:
        raise ValueError("row_limit_out_of_bounds")
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("input_byte_limit")
    items = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                raise ValueError("blank_staging_line")
            if len(items) >= max_rows:
                raise ValueError("row_limit_exceeded_no_partial_report")
            item = json.loads(line, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite_json")))
            if not isinstance(item,dict) or not isinstance(item.get("raw"),dict) or not isinstance(item.get("context"),dict):
                raise ValueError("staging_shape")
            c.validate_staging(item)
            items.append(item)
    return items


def _archive_status(path: Path, expected: str) -> tuple[str,str]:
    if path.stat().st_size > MAX_ARCHIVE_BYTES:
        return "PARTIALLY AVAILABLE", "archive_byte_limit"
    if file_sha256(path) != expected:
        return "PARTIALLY AVAILABLE", "historical_checksum_mismatch"
    try:
        with zipfile.ZipFile(path) as archive:
            infos=archive.infolist()
            if len(infos)>2000 or sum(x.file_size for x in infos)>MAX_ARCHIVE_BYTES:
                return "PARTIALLY AVAILABLE", "archive_expansion_limit"
            names={Path(x.filename.replace("\\","/")).name.lower() for x in infos}
            required={"schema-main.csv","schema-build.csv","schema-land.csv","schema-park.csv","manifest.csv"}
            if not required <= names or not any(s.source_county(n) for n in names):
                return "PARTIALLY AVAILABLE", "schemas_or_sale_main_missing"
            if archive.testzip() is not None:
                return "PARTIALLY AVAILABLE", "archive_crc_failure"
    except (zipfile.BadZipFile,OSError,RuntimeError,NotImplementedError):
        return "PARTIALLY AVAILABLE", "archive_invalid"
    return "AVAILABLE", "exact_archive_bytes_verified_schema_semantics_not_yet_reviewed"


def inventory_releases(evidence: dict, root: Path = s.ROOT) -> dict:
    releases = []
    for artifact in evidence["historical_metadata_only"]["artifacts"]:
        filename=artifact["local_filename"]
        if Path(filename).name != filename or any(ch in filename for ch in ("/","\\",":")):
            raise ValueError("unsafe_archive_filename")
        candidates=[root / relative / filename for relative in ("data/raw/plvr/phase2c","artifacts",".local/plvr","")]
        present=[p for p in candidates if p.is_file()]
        status,reason=("MISSING","no_local_bytes_in_declared_inventory_locations")
        for path in present:
            local_status,local_reason=_archive_status(path,artifact["sha256"])
            status,reason=local_status,local_reason
            if status == "AVAILABLE":
                break
        kind, release=artifact["kind"],artifact["release"]
        if kind=="season":
            url=f"https://plvr.land.moi.gov.tw/DownloadSeason?season={release}&type=zip&fileName=lvr_landcsv.zip"
        elif kind=="history":
            url=f"https://plvr.land.moi.gov.tw/DownloadHistory?type=history&fileName={release}"
        elif kind=="current":
            url="https://plvr.land.moi.gov.tw/opendata/lvr_landAcsv.zip"
        else:
            raise ValueError("unsupported_release_kind")
        releases.append({
            "source_release_id":artifact["artifact_id"],"release_label":release,"release_kind":kind,
            "source_url":url,"catalog_url":"https://data.gov.tw/dataset/25119",
            "source_dataset_id":c.SOURCE_ID,"effective_data_period":{
                "description":artifact["source_window_description"],"basis":"registration window for existing sales; not transaction or publication time"},
            "original_archive_filename":({"season":"lvr_landcsv.zip","history":"opendata.zip",
                                          "current":"current-20260811.zip"}[kind]
                                         if release=="20260811" or kind!="current" else None),
            "local_archive_filename":filename,"archive_sha256":artifact["sha256"],
            "declared_archive_bytes":artifact["byte_size"],"retrieved_at":artifact["retrieved_at"],
            "retrieval_evidence_status":"inherited_metadata_not_reverified_bytes",
            "source_release_available_at":None,"availability_evidence":None,
            "publication_date":None,"publication_precision":"unknown",
            "parser_version":None,"transform_version":None,"import_batch_id":None,
            "raw_row_count":None,"accepted_row_count":None,"rejected_row_count":None,
            "supersedes_release_id":None,"supersession_evidence":None,
            "recovery_status":status,"recovery_reason":reason,"remote_recoverability":"UNKNOWN",
            "historical_source_status":artifact["source_status"],
            "status":"metadata_only" if status=="MISSING" else "bytes_pending_semantic_review",
            "members":[],
        })
    ledger={"schema_version":c.LEDGER_VERSION,"source_dataset_id":c.SOURCE_ID,
            "historical_evidence_sha256":l.digest(evidence["historical_metadata_only"]),
            "inventory_scope":["data/raw/plvr/phase2c","artifacts",".local/plvr","workspace root"],
            "availability_policy":"Never use release labels, schedule, retrieval claims or registration windows as publication timestamps.",
            "releases":sorted(releases,key=lambda x:x["source_release_id"])}
    c.validate_ledger(ledger)
    return ledger


def reconcile_evidence(evidence: dict) -> None:
    total=evidence["all_sources_summary"]["official_rows"]
    for key in ("cities","months","types"):
        if sum(x["rows"] for x in evidence["official_profile"][key])!=total:
            raise ValueError("canonical_profile_count_mismatch")
    pairs=evidence["by_district"]
    if sum(x["official_rows"] for x in pairs)!=total or len(pairs)!=539:
        raise ValueError("canonical_geography_count_mismatch")
    if sum(x["type_only_residential_proxy_rows"] for x in pairs)!=evidence["cohort_counts"]["type_only_residential_proxy"]:
        raise ValueError("canonical_proxy_count_mismatch")
    duplicate=evidence["duplicate_profile"]
    if duplicate["rounded_fact_collision_rows"] - duplicate["rounded_fact_collision_groups"] != duplicate["rounded_fact_collision_excess"]:
        raise ValueError("canonical_collision_count_mismatch")


def audit_inventory(evidence: dict, ledger: dict) -> dict:
    reconcile_evidence(evidence)
    c.validate_ledger(ledger)
    geography=Counter()
    cross_county=0
    variants=0
    for pair in evidence["by_district"]:
        geo=s.normalize_geography(pair["city"],pair["district"])
        category="current_registry_plausible" if geo["valid"] else geo["reason"]
        geography[category]+=pair["official_rows"]
        if "台" in pair["city"]+pair["district"]:
            variants+=pair["official_rows"]
        if geo["reason"]=="current_registry_mismatch" and any(geo["district"] in values for values in s.DISTRICTS.values()):
            cross_county+=pair["official_rows"]
    statuses=Counter(x["recovery_status"] for x in ledger["releases"])
    observed=evidence["all_sources_summary"]["official_rows"]
    funnel=[{"stage":"legacy_official_population","remaining_count":observed,
             "excluded_count":evidence["all_sources_summary"]["other_rows"],"reason":"demo_source_excluded"}]
    for stage in STAGES:
        funnel.append({"stage":stage,"remaining_count":None,"excluded_count":None,
                       "reason":"raw_fields_and_per_row_source_evidence_unavailable"})
    return {
        "schema_version":"ml-foundation-aggregate-evidence-v1","starting_sha":"9435233ca38843dbeabbe8327148acd199f405ee",
        "evidence_basis":"canonical ML-A aggregates inherited; current bounded local inventory; no database recount or raw row export",
        "canonical_evidence_sha256":l.digest(evidence),"source_ledger_sha256":l.digest(ledger),
        "registry_sha256":l.digest(read_json(s.REGISTRY)),"parser_version":s.PARSER_VERSION,
        "cohort_definition_hash":l.digest(read_json(s.ROOT / "docs/ml/contracts/source-contract-v1.json")),
        "transform_code_checksum":l.digest({p.name:repository_text_sha256(p) for p in sorted((s.ROOT / "scripts/ml").glob("*.py"))}),
        "repository_checksum_policy":"canonical JSON for registry/cohort; UTF-8 LF-normalized code; archives remain exact-byte SHA256",
        "transform_version":s.TRANSFORM_VERSION,"cohort_version":s.COHORT_VERSION,
        "source_counts":{"legacy_official_observed":observed,"demo_excluded":evidence["all_sources_summary"]["other_rows"],
            "type_only_residential_proxy":evidence["cohort_counts"]["type_only_residential_proxy"],"historical_releases":len(ledger["releases"]),
            "historical_declared_bytes":sum(x["declared_archive_bytes"] for x in ledger["releases"]),
            "local_recovery_status_counts":dict(sorted(statuses.items())),"official_staging_rows_audited":0},
        "cohort_funnel":funnel,"final_candidate_cohort":None,"target_valid_candidate_count":None,
        "geography":{"counts":dict(sorted(geography.items())),"tai_variant_label_rows":variants,
            "mismatch_with_district_found_in_other_county_rows":cross_county,
            "source_proven_repairs_applied":0,"failure_root_cause":"Prior forensic reports identify import county contamination; aggregate labels cannot establish each row's source county.",
            "classification_limits":"Cross-county presence is diagnostic, not a mapping. Historical/encoding/malformed categories describe observable labels; source causes remain unverified without bytes."},
        "parking_classification":{"UNKNOWN":observed,"NO_PARKING_CONFIRMED":0,"PARKING_PRESENT":0,"PARKING_SEMANTICS_AMBIGUOUS":0},
        "parking_basis":"legacy schema has no parking fields; zero confirmed is an evidence count, not actual no-parking population",
        "target_validity":{"verified":None,"legacy_gross_area_mismatch_gt_1pct":evidence["official_profile"]["official_summary"]["gross_price_area_mismatch_gt_1pct"]},
        "duplicate_revision_findings":evidence["duplicate_profile"],
        "identity_disposition":"457 fact collision groups / 1026 rows unresolved; no deletions or merges",
        "temporal_field_availability":{"legacy_transaction_precision":"month","release_availability":"absent",
            "ingestion":"present; not publication","completion_date":"absent","transformation_time":"not row-persisted",
            "age_feature":"DEFERRED; month-age computation tested only on fixtures"},
        "lineage_completeness":{"historical_archive_hash_claims":17,"exact_archives_verified":statuses.get("AVAILABLE",0),
            "known_historical_publication_timestamps":0,"legacy_rows_with_proven_release_join":0,
            "residential_rights_area_parking_proof":"unavailable"},
        "raw_source_reproducibility":"NOT_DEMONSTRATED",
        "final_blockers":BLOCKERS,"readiness":"BLOCKED","ml_b_may_begin":False,
    }


def audit_staging(items: list[dict], cutoff: str) -> dict:
    if len(items)>100000:
        raise ValueError("row_limit_exceeded")
    selection=l.select_as_of(items,cutoff)
    remaining=selection["selected"]
    funnel=[{"stage":"identity_availability_revision","input_count":len(items),
             "remaining_count":len(remaining),"excluded_count":len(items)-len(remaining),
             "excluded_reasons":selection["excluded_reasons"]}]
    evaluations=[(x,s.evaluate_row(x["raw"],x["context"])) for x in remaining]
    parking=Counter(y["parking"] for _,y in evaluations)
    target=Counter("valid" if y["target"]["valid"] else "invalid" for _,y in evaluations)
    geo=Counter(y["geography"]["reason"] for _,y in evaluations)
    all_reasons=Counter(reason for _,y in evaluations for reason in y["reasons"])
    active=evaluations
    for stage in STAGES:
        reasons=Counter()
        next_active=[]
        for item,result in active:
            stage_reasons=list(result["stage_reasons"].get(stage,[]))
            if stage=="parse_valid":
                trans=result["transaction_effective_period"]
                if trans and trans["precision"]=="day":
                    effective=date.fromisoformat(trans["value"])
                    public=l.timestamp(item["source_release_available_at"]).astimezone(ZoneInfo("Asia/Taipei")).date()
                    if effective>public or effective>l.timestamp(cutoff).astimezone(ZoneInfo("Asia/Taipei")).date():
                        stage_reasons.append("effective_date_after_availability_or_cutoff")
            if stage_reasons:
                reasons[stage_reasons[0]]+=1
            else:
                next_active.append((item,result))
        funnel.append({"stage":stage,"input_count":len(active),"remaining_count":len(next_active),
                       "excluded_count":sum(reasons.values()),"excluded_reasons":dict(sorted(reasons.items()))})
        active=next_active
    input_hash=l.digest(sorted((l.digest(item) for item in items)))
    return {"schema_version":"ml-foundation-staging-audit-v1","scope":"bounded private staging; evidence references are supplied, not independently authenticated by this tool",
            "availability_cutoff":cutoff,"input_checksum":input_hash,"funnel":funnel,
            "parking_classification":dict(sorted(parking.items())),"target_validity":dict(sorted(target.items())),
            "geography_classification":dict(sorted(geo.items())),"all_semantic_exclusion_reason_counts":dict(sorted(all_reasons.items())),
            "duplicate_revision_findings":selection["classifications"],"final_candidate_count":len(active),
            "cohort_version":s.COHORT_VERSION,"target_version":s.TARGET_VERSION,
            "transform_version":s.TRANSFORM_VERSION,"readiness":"NOT_A_READINESS_APPROVAL"}


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--staging",type=Path)
    parser.add_argument("--cutoff")
    parser.add_argument("--max-rows",type=int,default=MAX_ROWS)
    parser.add_argument("--ledger-only",action="store_true")
    args=parser.parse_args()
    try:
        if args.staging:
            if not args.cutoff or args.ledger_only:
                raise ValueError("staging_requires_cutoff_and_no_ledger_only")
            report=audit_staging(read_staging(args.staging,args.max_rows),args.cutoff)
        else:
            if args.cutoff:
                raise ValueError("cutoff_requires_staging")
            evidence=read_json(CANONICAL_EVIDENCE)
            ledger=inventory_releases(evidence)
            report=ledger if args.ledger_only else audit_inventory(evidence,ledger)
        print(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True,allow_nan=False))
    except (ValueError,KeyError,TypeError,OSError) as error:
        # Never echo private payloads, paths or credentials from exception messages.
        parser.exit(2,"foundation_audit_failed: invalid or unavailable bounded input\n")


if __name__ == "__main__":
    main()
