"""Fail-closed policy gate for the reviewed npm development advisory."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any


BLOCKING_SEVERITIES = {"high", "critical"}
SEVERITIES = ("info", "low", "moderate", "high", "critical")
SEVERITY_RANK = {severity: rank for rank, severity in enumerate(SEVERITIES)}
ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend_next"
DEFAULT_POLICY = ROOT / ".github/security/npm-audit-exceptions.json"


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _strict_json_loads(text: str) -> object:
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_keys,
        parse_constant=_reject_json_constant,
    )


def _audit_schema_error(audit: object) -> str | None:
    if not isinstance(audit, dict) or audit.get("auditReportVersion") != 2:
        return "unsupported audit report version"
    vulnerabilities = audit.get("vulnerabilities")
    metadata = audit.get("metadata")
    if not isinstance(vulnerabilities, dict) or not isinstance(metadata, dict):
        return "missing vulnerabilities or metadata object"
    counts = metadata.get("vulnerabilities")
    if not isinstance(counts, dict):
        return "missing vulnerability counts"
    if any(type(counts.get(severity)) is not int or counts[severity] < 0 for severity in SEVERITIES):
        return "invalid vulnerability counts"
    if type(counts.get("total")) is not int or counts["total"] != sum(
        counts[severity] for severity in SEVERITIES
    ):
        return "inconsistent vulnerability total"

    observed = {severity: 0 for severity in SEVERITIES}
    for name, finding in vulnerabilities.items():
        if not isinstance(name, str) or not isinstance(finding, dict):
            return "invalid vulnerability entry"
        severity = finding.get("severity")
        if finding.get("name") != name or severity not in observed:
            return "invalid vulnerability identity or severity"
        if not isinstance(finding.get("isDirect"), bool):
            return "invalid direct dependency flag"
        via = finding.get("via")
        if not isinstance(via, list) or not via:
            return "invalid advisory path"
        for item in via:
            if isinstance(item, str):
                if not item:
                    return "invalid advisory reference"
                referenced = vulnerabilities.get(item)
                if not isinstance(referenced, dict):
                    return "advisory reference is missing from vulnerabilities"
                referenced_severity = referenced.get("severity")
                if referenced_severity not in SEVERITY_RANK:
                    return "advisory reference has invalid severity"
                if SEVERITY_RANK[referenced_severity] > SEVERITY_RANK[severity]:
                    return "advisory reference severity exceeds containing finding"
                continue
            if not isinstance(item, dict):
                return "invalid nested advisory value"
            string_fields = (
                "name",
                "dependency",
                "title",
                "url",
                "severity",
                "range",
            )
            if type(item.get("source")) is not int or any(
                not isinstance(item.get(field), str) or not item[field]
                for field in string_fields
            ):
                return "invalid nested advisory identity"
            if item["severity"] not in SEVERITY_RANK:
                return "invalid nested advisory severity"
            if SEVERITY_RANK[item["severity"]] > SEVERITY_RANK[severity]:
                return "nested advisory severity exceeds containing finding"
            cwe = item.get("cwe")
            cvss = item.get("cvss")
            if not isinstance(cwe, list) or not all(
                isinstance(value, str) and value for value in cwe
            ):
                return "invalid nested advisory CWE list"
            if (
                not isinstance(cvss, dict)
                or isinstance(cvss.get("score"), bool)
                or not isinstance(cvss.get("score"), (int, float))
                or not isinstance(cvss.get("vectorString"), str)
            ):
                return "invalid nested advisory CVSS data"
        if not isinstance(finding.get("effects"), list) or not all(
            isinstance(effect, str) for effect in finding["effects"]
        ):
            return "invalid effect list"
        if not isinstance(finding.get("range"), str):
            return "invalid affected range"
        if not isinstance(finding.get("nodes"), list) or not finding["nodes"] or not all(
            isinstance(node, str) for node in finding["nodes"]
        ):
            return "invalid node list"
        if not isinstance(finding.get("fixAvailable"), (bool, dict)):
            return "invalid remediation field"
        observed[severity] += 1

    if any(observed[severity] != counts[severity] for severity in SEVERITIES):
        return "vulnerability entries do not match metadata counts"
    return None


def _policy_schema_error(policy: object) -> str | None:
    if not isinstance(policy, dict) or policy.get("schemaVersion") != 1:
        return "unsupported schema"
    exceptions = policy.get("exceptions")
    if not isinstance(exceptions, list) or len(exceptions) != 1:
        return "exactly one reviewed exception is required"
    exception = exceptions[0]
    if not isinstance(exception, dict) or exception.get("devOnly") is not True:
        return "exception must be explicitly dev-only"
    required_strings = (
        "id",
        "package",
        "installedVersion",
        "severity",
        "affectedRange",
        "title",
        "url",
        "expiresOn",
        "rationale",
    )
    if any(
        not isinstance(exception.get(key), str) or not exception[key]
        for key in required_strings
    ):
        return "required identity fields are missing"
    if not isinstance(exception.get("npmSource"), int):
        return "npm advisory source must be numeric"
    if exception["severity"] not in BLOCKING_SEVERITIES:
        return "exception severity must be high or critical"
    if not exception["url"].endswith("/" + exception["id"]):
        return "advisory URL and identifier differ"
    try:
        date.fromisoformat(exception["expiresOn"])
    except ValueError:
        return "expiry must be an ISO date"
    graph = exception.get("auditGraph")
    if not isinstance(graph, dict) or exception["package"] not in graph:
        return "audit graph is missing the advisory package"
    chains = exception.get("dependencyChains")
    if (
        not isinstance(chains, list)
        or not chains
        or any(
            not isinstance(chain, list)
            or not chain
            or not all(isinstance(item, str) and item for item in chain)
            for chain in chains
        )
    ):
        return "dependency chains are missing or invalid"
    return None


def _blocked_findings(audit: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        name: finding
        for name, finding in audit.get("vulnerabilities", {}).items()
        if finding.get("severity") in BLOCKING_SEVERITIES
    }


def _finding_fingerprint(finding: dict[str, Any]) -> dict[str, Any]:
    via = [
        item.get("source") if isinstance(item, dict) else item
        for item in finding.get("via", [])
    ]
    return {
        "severity": finding.get("severity"),
        "isDirect": finding.get("isDirect"),
        "via": via,
        "effects": finding.get("effects"),
        "range": finding.get("range"),
        "nodes": finding.get("nodes"),
    }


def _advisory_identity_matches(
    finding: dict[str, Any], exception: dict[str, Any]
) -> bool:
    advisory_items = [item for item in finding.get("via", []) if isinstance(item, dict)]
    if len(advisory_items) != 1:
        return False
    advisory = advisory_items[0]
    expected = {
        "source": exception.get("npmSource"),
        "name": exception.get("package"),
        "dependency": exception.get("package"),
        "title": exception.get("title"),
        "url": exception.get("url"),
        "severity": exception.get("severity"),
        "range": exception.get("affectedRange"),
    }
    return all(advisory.get(key) == value for key, value in expected.items())


def _dependency_chains(
    dependency_explanation: list[dict[str, Any]],
) -> tuple[list[list[str]], list[str]]:
    entry = dependency_explanation[0]
    target = f"{entry['name']}@{entry['version']}"
    chains: list[list[str]] = []
    root_types: list[str] = []

    def visit(
        node: dict[str, Any], suffix: list[str], ancestors: set[tuple[str, str, str]]
    ) -> None:
        if not isinstance(node, dict):
            raise ValueError("dependency node must be an object")
        identity = (node.get("name"), node.get("version"), node.get("location"))
        if not all(isinstance(value, str) and value for value in identity):
            raise ValueError("dependency node identity is invalid")
        if identity in ancestors:
            raise ValueError("dependency explanation contains a cycle")
        dependents = node.get("dependents")
        if not isinstance(dependents, list) or not dependents:
            raise ValueError("dependency node has no dependents")

        next_ancestors = {*ancestors, identity}
        for dependent in dependents:
            if (
                not isinstance(dependent, dict)
                or dependent.get("name") != node["name"]
                or not isinstance(dependent.get("spec"), str)
                or not dependent["spec"]
                or not isinstance(dependent.get("type"), str)
            ):
                raise ValueError("dependency edge is invalid")
            parent = dependent.get("from")
            if not isinstance(parent, dict):
                raise ValueError("dependency ancestor must be an object")
            if "name" not in parent:
                if set(parent) != {"location"} or not isinstance(
                    parent["location"], str
                ) or not parent["location"]:
                    raise ValueError("dependency root evidence is invalid")
                normalized_root = parent["location"].replace("\\", "/").rstrip("/")
                if normalized_root != "." and normalized_root.split("/")[-1] != FRONTEND.name:
                    raise ValueError("dependency root location is invalid")
                chains.append(suffix)
                root_types.append(dependent.get("type"))
                continue
            if dependent["type"] != "prod":
                raise ValueError("transitive dependency edge is not production-scoped")
            visit(
                parent,
                [f"{parent['name']}@{parent['version']}", *suffix],
                next_ancestors,
            )

    visit(entry, [target], set())
    return chains, root_types


def evaluate(
    full_audit: object,
    production_audit: object,
    dependency_explanation: object,
    policy: object,
    *,
    today: date,
) -> dict[str, Any]:
    """Evaluate npm audit evidence against the temporary exception policy."""

    policy_error = _policy_schema_error(policy)
    if policy_error:
        return {
            "status": "failed",
            "accepted": [],
            "errors": [f"Invalid exception policy: {policy_error}"],
        }

    production_blockers = sorted(_blocked_findings(production_audit))
    if production_blockers:
        return {
            "status": "failed",
            "accepted": [],
            "errors": [
                "High or critical production dependency vulnerabilities: "
                + ", ".join(sorted(production_blockers))
            ],
        }

    exception = policy["exceptions"][0]
    actual_findings = _blocked_findings(full_audit)
    if not actual_findings:
        return {"status": "pass", "accepted": [], "errors": []}

    expected_graph = exception["auditGraph"]
    errors: list[str] = []

    expiry = date.fromisoformat(exception["expiresOn"])
    if actual_findings and today >= expiry:
        errors.append(
            f"Temporary exception {exception['id']} expired on {exception['expiresOn']}"
        )

    unexpected = sorted(set(actual_findings) - set(expected_graph))
    if unexpected:
        errors.append(
            "Unreviewed high or critical audit findings: " + ", ".join(unexpected)
        )

    missing = sorted(set(expected_graph) - set(actual_findings))
    if missing:
        errors.append(
            "Reviewed audit graph identity no longer matches; missing: "
            + ", ".join(missing)
        )

    for name in sorted(set(actual_findings) & set(expected_graph)):
        if _finding_fingerprint(actual_findings[name]) != expected_graph[name]:
            errors.append(f"Audit graph identity mismatch for {name}")

    advisory_package = exception["package"]
    if advisory_package in actual_findings and not _advisory_identity_matches(
        actual_findings[advisory_package], exception
    ):
        errors.append(
            f"Advisory identity mismatch for {exception['id']} ({advisory_package})"
        )

    if (
        len(dependency_explanation) != 1
        or dependency_explanation[0].get("name") != exception["package"]
        or dependency_explanation[0].get("version") != exception["installedVersion"]
        or dependency_explanation[0].get("dev") is not True
    ):
        errors.append(
            f"Dependency chain identity mismatch for {exception['package']}"
        )
    else:
        chains, root_types = _dependency_chains(dependency_explanation)
        if sorted(chains) != sorted(exception["dependencyChains"]):
            errors.append(
                f"Dependency chain identity mismatch for {exception['package']}"
            )
        if any(root_type != "dev" for root_type in root_types):
            errors.append(
                f"Dependency proof is not dev-only for {exception['package']}"
            )

    if errors:
        return {"status": "failed", "accepted": [], "errors": errors}

    return {
        "status": "pass",
        "accepted": [
            {"id": exception["id"], "expiresOn": exception["expiresOn"]}
        ],
        "errors": [],
    }


def evaluate_json(
    full_audit_json: str,
    production_audit_json: str,
    dependency_explanation_json: str,
    policy_json: str,
    *,
    today: date,
) -> dict[str, Any]:
    """Parse JSON evidence and fail closed when it cannot be interpreted."""

    try:
        full_audit = _strict_json_loads(full_audit_json)
        production_audit = _strict_json_loads(production_audit_json)
        dependency_explanation = _strict_json_loads(dependency_explanation_json)
        policy = _strict_json_loads(policy_json)
        for label, audit in (
            ("full audit", full_audit),
            ("production audit", production_audit),
        ):
            error = _audit_schema_error(audit)
            if error:
                return {
                    "status": "failed",
                    "accepted": [],
                    "errors": [f"Cannot safely interpret {label}: {error}"],
                }
        return evaluate(
            full_audit,
            production_audit,
            dependency_explanation,
            policy,
            today=today,
        )
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        return {
            "status": "failed",
            "accepted": [],
            "errors": ["Malformed or unsupported npm audit policy JSON"],
        }


def _run_npm_json(arguments: list[str]) -> str:
    npm = shutil.which("npm")
    if npm is None:
        raise RuntimeError("npm executable is unavailable")
    completed = subprocess.run(
        [npm, *arguments],
        cwd=FRONTEND,
        capture_output=True,
        text=True,
        check=False,
    )
    if not completed.stdout.strip():
        raise RuntimeError(
            f"npm {' '.join(arguments)} produced no machine-readable output"
        )
    return completed.stdout


def _read_json_input(path: str | None, npm_arguments: list[str]) -> str:
    if path:
        return Path(path).read_text(encoding="utf-8")
    return _run_npm_json(npm_arguments)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enforce the bounded npm development advisory exception."
    )
    parser.add_argument("--full-audit-json")
    parser.add_argument("--production-audit-json")
    parser.add_argument("--dependency-explanation-json")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--as-of", default=date.today().isoformat())
    args = parser.parse_args(argv)

    try:
        policy_json = Path(args.policy).read_text(encoding="utf-8")
        full_audit_json = _read_json_input(args.full_audit_json, ["audit", "--json"])
        production_audit_json = _read_json_input(
            args.production_audit_json,
            ["audit", "--omit=dev", "--audit-level=high", "--json"],
        )
        if args.dependency_explanation_json:
            dependency_explanation_json = Path(
                args.dependency_explanation_json
            ).read_text(encoding="utf-8")
        else:
            parsed_full = _strict_json_loads(full_audit_json)
            parsed_policy = _strict_json_loads(policy_json)
            package = parsed_policy["exceptions"][0]["package"]
            dependency_explanation_json = (
                _run_npm_json(["explain", package, "--json"])
                if _audit_schema_error(parsed_full) is None
                and _blocked_findings(parsed_full)
                else "[]"
            )
        result = evaluate_json(
            full_audit_json,
            production_audit_json,
            dependency_explanation_json,
            policy_json,
            today=date.fromisoformat(args.as_of),
        )
    except (OSError, RuntimeError, TypeError, ValueError, KeyError, IndexError):
        result = {
            "status": "failed",
            "accepted": [],
            "errors": ["Unable to obtain or safely interpret npm audit evidence"],
        }

    if result["status"] != "pass":
        for error in result["errors"]:
            print(f"npm audit gate failed: {error}", file=sys.stderr)
        return 1

    if result["accepted"]:
        accepted = result["accepted"][0]
        print(
            "TEMPORARY npm audit exception accepted: "
            f"{accepted['id']} (dev-only); expires {accepted['expiresOn']} "
            "and fails closed on that date."
        )
    else:
        print("npm audit gate passed: no high or critical vulnerabilities.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
