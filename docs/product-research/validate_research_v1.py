"""Validate research artifacts only; no app, provider, database or network calls."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATE = "2026-10-10"
VALIDATION_DATE = "2026-10-11"
SHA = "c2ddf1890897f44659b91079a563691fe337295e"
VALUES = {"YES", "PARTIAL", "NO", "UNKNOWN"}
STATUSES = {"VERIFIED_CURRENT", "ANNOUNCED", "INFERRED", "UNVERIFIED", "REPOSITORY_OBSERVED"}
CLASSES = {"STRONG", "PARTIAL", "FOUNDATION_ONLY", "BLOCKED", "NOT_IMPLEMENTED"}
TAGS = {"COMMODITY_EXPECTATION", "HIGH_USER_VALUE", "TRUST_DIFFERENTIATOR", "PROFESSIONAL_FEATURE", "GROWTH_FEATURE", "MONETIZATION_FEATURE", "LOW_VALUE_DEMO", "LEGAL_OR_DATA_RISK", "NOT_RECOMMENDED"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def validate() -> dict:
    names = [
        "current-capability-inventory-v1.json",
        "market-source-register-v1.json",
        "emerging-source-register-v1.json",
        "github-research-v1.json",
        "competitive-feature-matrix-v1.json",
        "competitive-gap-backlog-v1.json",
    ]
    data = {name: read(name) for name in names}
    for name, obj in data.items():
        require(not any("\ufffd" in s for s in strings(obj)), f"Replacement character in {name}")

    inv = data[names[0]]
    market = data[names[1]]
    emerging = data[names[2]]
    github = data[names[3]]
    matrix = data[names[4]]
    backlog = data[names[5]]
    for obj in (inv, matrix, backlog):
        require(obj["scope_sha"] == SHA, "Wrong research baseline")
        require(obj["research_date"] == DATE, "Wrong research date")
    require(inv["production_verdict"] == matrix["production_verdict"] == "NO-GO", "Production verdict changed")
    require(inv["ml_boundary"] == {"target_a": "BLOCKED", "target_b": "BLOCKED", "pit_valid": 0, "approved_cohort": 0, "ml_b_may_begin": False}, "ML boundary changed")

    source_ids = [s["id"] for s in matrix["sources"]]
    require(len(source_ids) == len(set(source_ids)), "Duplicate source IDs")
    valid_sources = set(source_ids)
    require(backlog["sources"] == matrix["sources"], "Source corpora diverge")
    corpus = inv["sources"] + market["sources"] + emerging["sources"] + github["sources"]
    require(matrix["sources"] == corpus, "Matrix source corpus differs from registers")
    for source in corpus:
        if "path" in source:
            require((ROOT / source["path"]).is_file(), f"Missing local source {source['id']}")
        else:
            require(source["url"].startswith("https://"), f"Invalid source URL {source['id']}")
        date = next((source[k] for k in ("checked_at", "date_checked", "checked_date") if k in source), None)
        require(date is not None and DATE <= date[:10] <= VALIDATION_DATE, f"Missing/wrong checked date {source['id']}")
        pub = source.get("publication_date")
        if pub and re.match(r"\d{4}-\d{2}-\d{2}", str(pub)):
            require(str(pub)[:10] <= date[:10], f"Future source {source['id']}")

    def refs(ids, location):
        require(set(ids) <= valid_sources, f"Unresolved source reference in {location}: {set(ids) - valid_sources}")

    for product in market["products"]:
        refs(product["source_ids"], product["id"])
        for cid, claim in product["capabilities"].items():
            refs(claim["source_ids"], f"{product['id']}/{cid}")
            if claim["status"] == "VERIFIED_CURRENT":
                require(bool(claim["source_ids"]), "Unsourced market claim")
    for product in emerging["products"]:
        for claim in product["capabilities"]:
            refs(claim["source_ids"], claim["capability_id"])
    for project in github["projects"]:
        refs(project["source_ids"], project["id"])
        require(project["reuse_assessment"]["copied_source_code"] is False, "Code reuse boundary changed")
        require(project["reuse_assessment"]["blanket_clearance"] is False, "Blanket reuse clearance")
        require(project["activity"]["latest_meaningful_source_commit"]["committed_at_utc"][:10] <= VALIDATION_DATE, "Future repo source change")

    product_ids = [p["id"] for p in matrix["products"]]
    cap_ids = [r["id"] for r in matrix["capabilities"]]
    require(len(product_ids) == len(set(product_ids)) == 21, "Expected 21 unique product columns")
    require(len(cap_ids) == len(set(cap_ids)) == 64, "Expected 64 unique capability rows")
    require(len(market["products"]) == 13 and len(emerging["products"]) == 7 and len(github["projects"]) == 10, "Research counts differ")
    by_cap = {r["id"]: r for r in matrix["capabilities"]}
    item_ids = {g["id"] for g in backlog["items"]}
    cell_counts = Counter()
    for row in matrix["capabilities"]:
        require(row["copilot_classification"] in CLASSES, "Invalid classification")
        require(set(row["cells"]) == set(product_ids), f"Missing column in {row['id']}")
        require(set(row["gap_ids"]) <= item_ids, "Unresolved gap reference")
        if row["cells"]["copilot"]["value"] != "YES":
            require(bool(row["gap_ids"]) and bool(row["gap_classifications"]), f"Unclassified gap {row['id']}")
        for pid, cell in row["cells"].items():
            require(cell["value"] in VALUES and cell["evidence_status"] in STATUSES, f"Invalid cell {row['id']}/{pid}")
            refs(cell["source_ids"], f"{row['id']}/{pid}")
            if cell["value"] != "UNKNOWN":
                require(bool(cell["source_ids"]), f"Unsourced cell {row['id']}/{pid}")
            if pid != "copilot" and cell["value"] == "UNKNOWN":
                require(bool(cell.get("acquisition_target")), "Unknown cell without acquisition target")
            if pid != "copilot":
                require(cell["hands_on_tested"] is False, "Unsupported hands-on claim")
            cell_counts[cell["value"]] += 1

    with (HERE / "competitive-feature-matrix-v1.csv").open(encoding="utf-8-sig", newline="") as f:
        csv_rows = list(csv.reader(f))
    require(len(csv_rows) == 65 and len(csv_rows[0]) == 24, "CSV shape differs")
    for row, csv_row in zip(matrix["capabilities"], csv_rows[1:]):
        require(csv_row[0] == row["id"], "CSV row mismatch")
        require(csv_row[3:] == [row["cells"][pid]["value"] for pid in product_ids], "CSV value mismatch")

    weights = backlog["scoring_model"]["weights"]
    costs = set(backlog["scoring_model"]["cost_dimensions"])
    require(sum(weights.values()) == 100 and len(weights) == 10, "Scoring weights invalid")
    for gap in backlog["items"]:
        require(set(gap["capability_ids"]) <= set(cap_ids), "Invalid backlog capability")
        require(set(gap["dependencies"]) <= item_ids and gap["id"] not in gap["dependencies"], "Invalid dependency")
        require(set(gap["classifications"]) <= TAGS, "Invalid gap classification")
        refs(gap["source_ids"] + gap["benchmark_source_ids"], gap["id"])
        ratings = gap["dimension_scores"]
        require(set(ratings) == set(weights) and all(1 <= v <= 5 for v in ratings.values()), "Invalid ratings")
        expected = round(sum(weights[k] * ((6 - v) if k in costs else v) / 5 for k, v in ratings.items()), 1)
        require(gap["weighted_score"] == expected, f"Wrong score {gap['id']}")
        if gap["priority"] in ("P1", "P2"):
            require(bool(gap["benchmark_source_ids"]), f"Unsupported proposal {gap['id']}")
    visiting, visited = set(), set()
    by_gap = {g["id"]: g for g in backlog["items"]}

    def visit(gid):
        require(gid not in visiting, "Cyclic backlog dependency")
        if gid in visited:
            return
        visiting.add(gid)
        for dep in by_gap[gid]["dependencies"]:
            visit(dep)
        visiting.remove(gid)
        visited.add(gid)

    for gid in by_gap:
        visit(gid)
    priorities = Counter(g["priority"] for g in backlog["items"])
    require(set(priorities) == {"P0", "P1", "P2", "P3", "DO_NOT_BUILD"}, "Missing priority band")
    for priority in priorities:
        group = [g for g in backlog["items"] if g["priority"] == priority]
        require([g["rank_in_priority"] for g in group] == list(range(1, len(group) + 1)), "Invalid ranking")
        require([g["weighted_score"] for g in group] == sorted((g["weighted_score"] for g in group), reverse=True), "Score ranking differs")

    credits = {"YES": 1, "PARTIAL": 0.5, "NO": 0, "UNKNOWN": 0}
    parity = matrix["scores"]["parity"]
    eligible = parity["eligible_rows"]
    for row in eligible:
        require(len(row["documented_peer_ids"]) >= 2, "Insufficient parity support")
        require(row["credit"] == credits[by_cap[row["capability_id"]]["cells"]["copilot"]["value"]], "Parity credit differs")
        for pid in row["documented_peer_ids"]:
            cell = by_cap[row["capability_id"]]["cells"][pid]
            require(cell["evidence_status"] == "VERIFIED_CURRENT" and cell["value"] in {"YES", "PARTIAL"}, "Unsupported parity peer")
    exclusions = {(p["product_id"], p["capability_id"]) for p in parity["peer_scope_exclusions"]}
    require(not any((pid, r["capability_id"]) in exclusions for r in eligible for pid in r["documented_peer_ids"]), "Excluded scope in parity score")
    require(parity["denominator"] == len(eligible), "Wrong parity denominator")
    require(parity["value"] == round(100 * sum(r["credit"] for r in eligible) / len(eligible), 1), "Wrong parity index")
    diff = matrix["scores"]["differentiation"]
    require(sum(r["weight"] for r in diff["dimensions"]) == 100, "Differentiation weights invalid")
    require(diff["value"] == round(sum(r["weight"] * r["credit"] for r in diff["dimensions"]), 1), "Wrong differentiation index")

    rubric = (HERE / "work-commercial-rubric-v2.md").read_text(encoding="utf-8")
    points = [int(n) for n in re.findall(r"^\| [^|]+ \| (\d+) \|", rubric, flags=re.M)]
    require(len(points) == 20 and sum(points) == 100, "Work rubric does not total 100")
    for path in HERE.glob("*.md"):
        content = path.read_text(encoding="utf-8")
        require("\ufffd" not in content, f"Replacement character in {path.name}")
        for target in re.findall(r"\]\(([^)]+)\)", content):
            if target.startswith("https://"):
                continue
            resolved = (HERE / target.split("#")[0]).resolve()
            require(resolved.is_relative_to(ROOT.resolve()) and resolved.is_file(), f"Broken local link in {path.name}: {target}")

    return {
        "validation": "PASS",
        "schema_version": "1.0",
        "research_date": DATE,
        "validation_date": VALIDATION_DATE,
        "scope_sha": SHA,
        "checks": ["JSON parsing / Unicode", "source uniqueness / checked dates / local references", "claim source references", "64x21 matrix / evidence status / acquisition targets", "CSV matrix equality", "gap coverage / scores / ranks / acyclic dependencies", "parity and differentiation arithmetic", "100-point Work rubric", "Markdown local links", "ML and production boundaries"],
        "counts": {"capabilities": 64, "product_columns": 21, "matrix_cells": 1344, "established_products": 13, "emerging_products": 7, "github_repositories": 10, "source_records": len(source_ids), "cell_values": dict(cell_counts), "backlog_priorities": dict(priorities)},
        "scores": {"research_parity": parity["value"], "internal_differentiation_strength": diff["value"], "deployed_work_score": None},
        "limitations": ["Artifact integrity validation, not competitor/app execution or legal/model/data acceptance.", "No application tests/build/live provider requests performed in research lane.", "Final commit SHA belongs in delivery response to avoid self-reference."],
        "external_requests_from_validator": 0,
        "production_application_changes": False,
        "independent_review": {
            "date": VALIDATION_DATE,
            "review_scopes": ["Precise competitor/emerging capability mapping, parity eligibility and readiness claims", "Scoring arithmetic, dependencies, 100-point rubric, GitHub reuse/activity and scope"],
            "critical_remaining": 0,
            "important_remaining": 0,
            "corrections": ["Excluded restricted AI beta and professional/report-subscription scope from commodity parity", "Separated after-repair property value from renovation cash costs", "Qualified personalized-fit and memory patterns as inferred", "Scoped comparative leadership claims to repository strengths", "Corrected and scoped substantive GitHub update evidence"],
        },
    }


if __name__ == "__main__":
    result = validate()
    (HERE / "research-validation-v1.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True, indent=2))
