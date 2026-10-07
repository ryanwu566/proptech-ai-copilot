"""Non-destructive occurrence identity and conservative as-of revision selection."""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
import re

from . import semantics as s

IDENTITY_VERSION = "plvr-county-official-family-v1"
SELECTION_VERSION = "plvr-explicit-revision-asof-v1"


def canonical_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def timestamp(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return result if result.tzinfo is not None and result.utcoffset() is not None else None


def identify(item: dict) -> dict:
    county = s.source_county(item.get("member_name", ""))
    official_id = s.text(item.get("raw", {}).get("編號"))
    dataset = s.text(item.get("source_dataset_id"))
    family = digest([IDENTITY_VERSION, dataset, county, official_id]) if county and official_id and dataset else None
    payload = digest({"raw":item.get("raw"),"cancelled":item.get("cancelled")})
    return {"transaction_family_id":family,"raw_payload_sha256":payload,
            "version_id":digest([family,payload]) if family else None,
            "occurrence_id":digest([dataset,item.get("archive_sha256"),item.get("member_name"),
                                     item.get("physical_row_number")])}


def lineage_valid(item: dict) -> bool:
    hashes = (item.get("archive_sha256"), item.get("member_sha256"))
    ingest, transform = timestamp(item.get("ingested_at")), timestamp(item.get("transformed_at"))
    return (all(isinstance(h,str) and re.fullmatch("[0-9a-f]{64}",h) for h in hashes)
            and type(item.get("physical_row_number")) is int and item["physical_row_number"] >= 1
            and bool(s.text(item.get("release_id"))) and bool(s.text(item.get("import_batch_id")))
            and item.get("parser_version") == s.PARSER_VERSION
            and item.get("transform_version") == s.TRANSFORM_VERSION
            and ingest is not None and transform is not None and ingest <= transform
            and s.evidence_valid(item.get("identity_evidence"))
            and isinstance(item.get("raw"),dict) and isinstance(item.get("context"),dict)
            and item["context"].get("member_name") == item.get("member_name")
            and type(item.get("cancelled")) is bool)


def select_as_of(items: list[dict], cutoff: str) -> dict:
    boundary = timestamp(cutoff)
    if boundary is None:
        raise ValueError("cutoff_requires_timezone")
    families = defaultdict(list)
    reasons = Counter()
    classifications = Counter()
    selected = []
    global_locators = defaultdict(set)
    release_metadata = defaultdict(set)
    member_metadata = defaultdict(set)
    for item in items:
        if item.get("source_dataset_id") != s.SOURCE_DATASET_ID:
            reasons["unsupported_source"] += 1
            continue
        identity = identify(item)
        # Index every canonical-source physical occurrence, including missing IDs.
        # A malformed identity must not conceal a conflicting payload for a known family.
        global_locators[identity["occurrence_id"]].add(identity["raw_payload_sha256"])
        release_metadata[item.get("release_id")].add(digest([
            item.get("archive_sha256"),item.get("source_release_available_at")]))
        member_metadata[(item.get("archive_sha256"),item.get("member_name"))].add(
            digest(item.get("member_sha256")))
        if identity["transaction_family_id"] is None:
            reasons["identity_missing"] += 1
        else:
            families[identity["transaction_family_id"]].append((item,identity))
    conflicting_locators={key for key,values in global_locators.items() if len(values)>1}
    conflicting_releases={key for key,values in release_metadata.items() if len(values)>1}
    conflicting_members={key for key,values in member_metadata.items() if len(values)>1}
    for family in sorted(families):
        entries = families[family]
        if any(x.get("release_id") in conflicting_releases
               or (x.get("archive_sha256"),x.get("member_name")) in conflicting_members for x,_ in entries):
            reasons["immutable_lineage_conflict"] += len(entries)
            continue
        if any(ids["occurrence_id"] in conflicting_locators for _,ids in entries):
            reasons["occurrence_conflict"] += len(entries)
            classifications["ambiguous_collision_families"] += 1
            continue
        if any(not lineage_valid(x) for x,_ in entries):
            reasons["lineage_unverified"] += len(entries)
            continue
        if any(timestamp(x.get("source_release_available_at")) is None
               or not s.evidence_valid(x.get("availability_evidence")) for x,_ in entries):
            reasons["availability_unknown"] += len(entries)
            continue
        eligible = [(x,ids) for x,ids in entries if timestamp(x["source_release_available_at"]) <= boundary]
        reasons["after_availability_cutoff"] += len(entries) - len(eligible)
        if not eligible:
            continue
        # An occurrence locator cannot describe two payloads. No hash tie-break resolves that conflict.
        locators = defaultdict(set)
        for x,ids in eligible:
            locators[ids["occurrence_id"]].add(ids["version_id"])
        if any(len(v)>1 for v in locators.values()):
            reasons["occurrence_conflict"] += len(eligible)
            classifications["ambiguous_collision_families"] += 1
            continue
        versions = defaultdict(list)
        for x,ids in eligible:
            versions[ids["version_id"]].append((x,ids))
        if any(len({digest(x["context"]) for x,_ in group}) != 1 for group in versions.values()):
            reasons["semantic_evidence_conflict"] += len(eligible)
            continue
        # Same payload's supersession evidence must agree across republications.
        if any(len({x.get("supersedes_version_id") for x,_ in group}) != 1 for group in versions.values()):
            reasons["revision_ambiguous"] += len(eligible)
            classifications["ambiguous_collision_families"] += 1
            continue
        order = sorted(versions, key=lambda v:(min(timestamp(x["source_release_available_at"]) for x,_ in versions[v]),v))
        ambiguous = False
        for index,version in enumerate(order):
            group = versions[version]
            parent = group[0][0].get("supersedes_version_id")
            if parent != (order[index-1] if index else None):
                ambiguous = True
            if index:
                current_time = min(timestamp(x["source_release_available_at"]) for x,_ in group)
                prior_time = min(timestamp(x["source_release_available_at"]) for x,_ in versions[order[index-1]])
                if current_time <= prior_time:
                    ambiguous = True
        if ambiguous:
            reasons["revision_ambiguous"] += len(eligible)
            classifications["ambiguous_collision_families"] += 1
            continue
        if len(order)>1:
            classifications["explicit_correction_families"] += 1
        latest = order[-1]
        for version in order[:-1]:
            reasons["superseded_version"] += len(versions[version])
        representatives = sorted(versions[latest], key=lambda pair:(timestamp(pair[0]["source_release_available_at"]),pair[1]["occurrence_id"],pair[0]["release_id"]))
        choice, ids = representatives[0]
        seen_releases = {choice["release_id"]}
        for duplicate,_ in representatives[1:]:
            reason = "exact_duplicate" if duplicate["release_id"] in seen_releases else "republication"
            seen_releases.add(duplicate["release_id"])
            reasons[reason] += 1
            classifications[reason + "_occurrences"] += 1
        if choice["cancelled"]:
            reasons["cancelled_as_of_cutoff"] += 1
        else:
            selected.append({**choice, **ids})
    reasons += Counter()  # remove zero counts for stable sparse output
    assert len(items) == len(selected) + sum(reasons.values())
    return {"selected":selected,"input_occurrences":len(items),
            "excluded_reasons":dict(sorted(reasons.items())),
            "classifications":dict(sorted(classifications.items())),"selection_version":SELECTION_VERSION}
