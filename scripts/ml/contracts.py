"""Offline release/manifest validation; no database schema or production state."""
from __future__ import annotations

import re
import json
from datetime import date
from urllib.parse import urlsplit

from . import lineage as l
from . import semantics as s

SOURCE_ID = s.SOURCE_DATASET_ID
LEDGER_VERSION = "plvr-ml-release-ledger-v1"
MANIFEST_VERSION = "residential-valuation-manifest-v1"


def validate_shape(value, schema: dict, path: str = "contract") -> None:
    """Check the assertion subset used by our local JSON Schemas; no remote refs.

    Formal Draft 2020-12 validation is additionally exercised in tests when the
    existing jsonschema package is available. This tool has no third-party imports.
    """
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            try:
                validate_shape(value,option,path)
                return
            except ValueError:
                pass
        raise ValueError(path + "_union_shape")
    if "const" in schema and value != schema["const"]:
        raise ValueError(path + "_constant")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(path + "_enum")
    kind=schema.get("type")
    valid_type={"object":isinstance(value,dict),"array":isinstance(value,list),
                "string":isinstance(value,str),"integer":type(value) is int,
                "boolean":type(value) is bool,"null":value is None}
    if kind and not valid_type.get(kind,False):
        raise ValueError(path + "_type")
    if kind=="object":
        properties=schema.get("properties",{})
        if not set(schema.get("required",[])) <= value.keys():
            raise ValueError(path + "_required")
        if schema.get("additionalProperties") is False and not value.keys() <= properties.keys():
            raise ValueError(path + "_unknown_fields")
        for key,item in value.items():
            if key in properties:
                validate_shape(item,properties[key],path+"."+key)
            elif isinstance(schema.get("additionalProperties"),dict):
                validate_shape(item,schema["additionalProperties"],path+".additional_field")
    elif kind=="array":
        if len(value)<schema.get("minItems",0):
            raise ValueError(path + "_minimum_items")
        if schema.get("uniqueItems") and len({l.digest(x) for x in value}) != len(value):
            raise ValueError(path + "_duplicate_items")
        for item in value:
            validate_shape(item,schema.get("items",{}),path+"[]")
    elif kind=="string":
        if len(value)<schema.get("minLength",0) or ("pattern" in schema and not re.search(schema["pattern"],value)):
            raise ValueError(path + "_string_shape")
        if schema.get("format")=="date-time" and l.timestamp(value) is None:
            raise ValueError(path + "_timestamp")
        if schema.get("format")=="date":
            try:
                date.fromisoformat(value)
            except ValueError as error:
                raise ValueError(path + "_date") from error
    elif kind=="integer" and value<schema.get("minimum",value):
        raise ValueError(path + "_minimum")


def _schema(name: str) -> dict:
    return json.loads((s.ROOT / "docs/ml/contracts" / name).read_text(encoding="utf-8"))


def validate_staging(item: dict) -> None:
    validate_shape(item,_schema("staging-occurrence-v1.schema.json"))


def _hash(value):
    return isinstance(value,str) and re.fullmatch("[0-9a-f]{64}",value) is not None


def _counts(item):
    values = [item.get(k) for k in ("raw_row_count","accepted_row_count","rejected_row_count")]
    if all(x is None for x in values):
        return
    if not all(type(x) is int and x >= 0 for x in values) or values[0] != values[1]+values[2]:
        raise ValueError("row_count_reconciliation")


def validate_ledger(ledger: dict) -> None:
    validate_shape(ledger,_schema("release-ledger-v1.schema.json"))
    if ledger.get("schema_version") != LEDGER_VERSION or ledger.get("source_dataset_id") != SOURCE_ID:
        raise ValueError("ledger_version_or_source")
    ids = set()
    for release in ledger["releases"]:
        key = release["source_release_id"]
        if not isinstance(key,str) or not key or key in ids:
            raise ValueError("release_identity")
        ids.add(key)
        parsed = urlsplit(release["source_url"])
        if parsed.scheme != "https" or parsed.hostname != "plvr.land.moi.gov.tw" or parsed.username or parsed.password:
            raise ValueError("source_url")
        if not _hash(release["archive_sha256"]):
            raise ValueError("archive_checksum")
        if release["recovery_status"] not in {"AVAILABLE","PARTIALLY AVAILABLE","MISSING","UNKNOWN"}:
            raise ValueError("recovery_status")
        if release["source_release_available_at"] is not None:
            if not l.timestamp(release["source_release_available_at"]) or not s.evidence_valid(release["availability_evidence"]):
                raise ValueError("availability_evidence")
        if release["retrieved_at"] is not None and not l.timestamp(release["retrieved_at"]):
            raise ValueError("retrieval_timestamp")
        _counts(release)
        for member in release["members"]:
            _counts(member)
        if release["members"] and release["raw_row_count"] is not None:
            for key in ("raw_row_count","accepted_row_count","rejected_row_count"):
                if sum(member[key] for member in release["members"]) != release[key]:
                    raise ValueError("release_member_count_reconciliation")
    for release in ledger["releases"]:
        parent=release.get("supersedes_release_id")
        if parent is not None and (parent not in ids or parent == release["source_release_id"]):
            raise ValueError("supersession_reference")


def validate_manifest(manifest: dict) -> None:
    validate_shape(manifest,_schema("dataset-manifest-v1.schema.json"))
    if manifest.get("schema_version") != MANIFEST_VERSION:
        raise ValueError("manifest_version")
    for key in ("dataset_version","feature_schema_version","source_ledger_version","transform_version","parser_version"):
        if not isinstance(manifest.get(key),str) or not manifest[key]:
            raise ValueError("manifest_required_version")
    if (manifest.get("target_version") != s.TARGET_VERSION or manifest.get("area_version") != s.AREA_VERSION
            or manifest["source_ledger_version"] != LEDGER_VERSION
            or manifest["transform_version"] != s.TRANSFORM_VERSION or manifest["parser_version"] != s.PARSER_VERSION):
        raise ValueError("unsupported_manifest_contract")
    for key in ("built_at","training_data_cutoff","availability_cutoff"):
        if l.timestamp(manifest.get(key)) is None:
            raise ValueError("manifest_cutoff_timezone")
    if l.timestamp(manifest["availability_cutoff"]) > l.timestamp(manifest["built_at"]):
        raise ValueError("future_availability_cutoff")
    if l.timestamp(manifest["training_data_cutoff"]) > l.timestamp(manifest["availability_cutoff"]):
        raise ValueError("effective_cutoff_after_availability_cutoff")
    for key in ("dataset_checksum","exclusion_ledger_checksum","cohort_definition_hash","source_ledger_checksum","transform_code_checksum","dependency_lock_checksum"):
        if not _hash(manifest.get(key)):
            raise ValueError("manifest_checksum")
    row_count, raw_count, excluded = (manifest.get(k) for k in ("row_count","raw_row_count","excluded_row_count"))
    if not all(type(x) is int and x >= 0 for x in (row_count,raw_count,excluded)) or row_count+excluded != raw_count:
        raise ValueError("manifest_count_reconciliation")
    releases = manifest.get("source_releases")
    if not isinstance(releases,list) or not releases:
        raise ValueError("manifest_source_releases")
    ids = set()
    for release in releases:
        available = l.timestamp(release.get("source_release_available_at"))
        if available is None or not s.evidence_valid(release.get("availability_evidence")):
            raise ValueError("manifest_availability_unknown")
        if available > l.timestamp(manifest["availability_cutoff"]):
            raise ValueError("manifest_availability_after_cutoff")
        if not _hash(release.get("archive_sha256")) or not _hash(release.get("schema_sha256")):
            raise ValueError("manifest_source_checksum")
        if release.get("source_release_id") in ids or not release.get("source_release_id"):
            raise ValueError("manifest_release_identity")
        ids.add(release["source_release_id"])
        members=release["members"]
        member_names=[member["member_name"] for member in members]
        if len(set(member_names))!=len(member_names) or member_names!=sorted(member_names):
            raise ValueError("manifest_member_order_or_identity")
        for member in members:
            _counts(member)
    if [x["source_release_id"] for x in releases] != sorted(ids):
        raise ValueError("manifest_source_order")
    for group in manifest["subgroup_counts"].values():
        labels=[x["label"] for x in group]
        if sum(x["rows"] for x in group)!=row_count or len(set(labels))!=len(labels) or labels!=sorted(labels):
            raise ValueError("manifest_subgroup_count_or_order")
    if sum(member["raw_row_count"] for release in releases for member in release["members"]) != raw_count:
        raise ValueError("manifest_source_raw_count")
    if l.timestamp(manifest["label_observation_cutoff"])>l.timestamp(manifest["built_at"]):
        raise ValueError("future_label_cutoff")
