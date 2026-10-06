from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from copy import deepcopy
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/npm_audit_gate.py"
CONFIG = ROOT / ".github/security/npm-audit-exceptions.json"


CURRENT_AUDIT = {
    "auditReportVersion": 2,
    "vulnerabilities": {
        "@next/eslint-plugin-next": {
            "name": "@next/eslint-plugin-next",
            "severity": "high",
            "isDirect": True,
            "via": ["fast-glob"],
            "effects": [],
            "range": ">=14.3.0-canary.0",
            "nodes": ["node_modules/@next/eslint-plugin-next"],
            "fixAvailable": {
                "name": "@next/eslint-plugin-next",
                "version": "14.2.35",
                "isSemVerMajor": True,
            },
        },
        "braces": {
            "name": "braces",
            "severity": "high",
            "isDirect": False,
            "via": [
                {
                    "source": 1240992,
                    "name": "braces",
                    "dependency": "braces",
                    "title": "braces vulnerable to stack-exhaustion denial of service through deeply nested patterns",
                    "url": "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm",
                    "severity": "high",
                    "cwe": ["CWE-674"],
                    "cvss": {
                        "score": 7.5,
                        "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:N/I:N/A:H",
                    },
                    "range": "<=3.0.3",
                }
            ],
            "effects": ["chokidar", "micromatch"],
            "range": "*",
            "nodes": ["node_modules/braces"],
            "fixAvailable": {
                "name": "tailwindcss",
                "version": "4.3.3",
                "isSemVerMajor": True,
            },
        },
        "chokidar": {
            "name": "chokidar",
            "severity": "high",
            "isDirect": False,
            "via": ["braces"],
            "effects": ["tailwindcss"],
            "range": "2.0.0 - 3.6.0",
            "nodes": ["node_modules/chokidar"],
            "fixAvailable": {
                "name": "tailwindcss",
                "version": "4.3.3",
                "isSemVerMajor": True,
            },
        },
        "fast-glob": {
            "name": "fast-glob",
            "severity": "high",
            "isDirect": False,
            "via": ["micromatch"],
            "effects": ["@next/eslint-plugin-next"],
            "range": "*",
            "nodes": [
                "node_modules/@next/eslint-plugin-next/node_modules/fast-glob",
                "node_modules/fast-glob",
            ],
            "fixAvailable": {
                "name": "@next/eslint-plugin-next",
                "version": "14.2.35",
                "isSemVerMajor": True,
            },
        },
        "micromatch": {
            "name": "micromatch",
            "severity": "high",
            "isDirect": False,
            "via": ["braces"],
            "effects": ["fast-glob", "tailwindcss"],
            "range": ">=0.2.0",
            "nodes": ["node_modules/micromatch"],
            "fixAvailable": {
                "name": "tailwindcss",
                "version": "4.3.3",
                "isSemVerMajor": True,
            },
        },
        "tailwindcss": {
            "name": "tailwindcss",
            "severity": "high",
            "isDirect": True,
            "via": ["chokidar", "fast-glob", "micromatch"],
            "effects": [],
            "range": "<=0.0.0-oxide-insiders.ff2c25f || 2.1.0-canary.1 - 3.4.19",
            "nodes": ["node_modules/tailwindcss"],
            "fixAvailable": {
                "name": "tailwindcss",
                "version": "4.3.3",
                "isSemVerMajor": True,
            },
        },
    },
    "metadata": {
        "vulnerabilities": {
            "info": 0,
            "low": 0,
            "moderate": 0,
            "high": 6,
            "critical": 0,
            "total": 6,
        },
        "dependencies": {
            "prod": 31,
            "dev": 189,
            "optional": 40,
            "peer": 0,
            "peerOptional": 0,
            "total": 258,
        },
    },
}

EMPTY_AUDIT = {
    "auditReportVersion": 2,
    "vulnerabilities": {},
    "metadata": {
        "vulnerabilities": {
            "info": 0,
            "low": 0,
            "moderate": 0,
            "high": 0,
            "critical": 0,
            "total": 0,
        },
        "dependencies": {
            "prod": 31,
            "dev": 0,
            "optional": 0,
            "peer": 0,
            "peerOptional": 0,
            "total": 31,
        },
    },
}

CURRENT_EXPLANATION = [
    {
        "name": "braces",
        "version": "3.0.3",
        "location": "node_modules/braces",
        "isWorkspace": False,
        "dependents": [
            {
                "type": "prod",
                "name": "braces",
                "spec": "~3.0.2",
                "from": {
                    "name": "chokidar",
                    "version": "3.6.0",
                    "location": "node_modules/chokidar",
                    "dependents": [
                        {
                            "type": "prod",
                            "name": "chokidar",
                            "spec": "^3.6.0",
                            "from": {
                                "name": "tailwindcss",
                                "version": "3.4.19",
                                "location": "node_modules/tailwindcss",
                                "dependents": [
                                    {
                                        "type": "dev",
                                        "name": "tailwindcss",
                                        "spec": "^3.4.17",
                                        "from": {"location": "."},
                                    }
                                ],
                            },
                        }
                    ],
                },
            },
            {
                "type": "prod",
                "name": "braces",
                "spec": "^3.0.3",
                "from": {
                    "name": "micromatch",
                    "version": "4.0.8",
                    "location": "node_modules/micromatch",
                    "dependents": [
                        {
                            "type": "prod",
                            "name": "micromatch",
                            "spec": "^4.0.4",
                            "from": {
                                "name": "fast-glob",
                                "version": "3.3.1",
                                "location": "node_modules/@next/eslint-plugin-next/node_modules/fast-glob",
                                "dependents": [
                                    {
                                        "type": "prod",
                                        "name": "fast-glob",
                                        "spec": "3.3.1",
                                        "from": {
                                            "name": "@next/eslint-plugin-next",
                                            "version": "16.3.1",
                                            "location": "node_modules/@next/eslint-plugin-next",
                                            "dependents": [
                                                {
                                                    "type": "dev",
                                                    "name": "@next/eslint-plugin-next",
                                                    "spec": "^16.3.1",
                                                    "from": {"location": "."},
                                                }
                                            ],
                                        },
                                    }
                                ],
                            },
                        },
                        {
                            "type": "prod",
                            "name": "micromatch",
                            "spec": "^4.0.8",
                            "from": {
                                "name": "fast-glob",
                                "version": "3.3.3",
                                "location": "node_modules/fast-glob",
                                "dependents": [
                                    {
                                        "type": "prod",
                                        "name": "fast-glob",
                                        "spec": "^3.3.2",
                                        "from": {
                                            "name": "tailwindcss",
                                            "version": "3.4.19",
                                            "location": "node_modules/tailwindcss",
                                            "dependents": [
                                                {
                                                    "type": "dev",
                                                    "name": "tailwindcss",
                                                    "spec": "^3.4.17",
                                                    "from": {"location": "."},
                                                }
                                            ],
                                        },
                                    }
                                ],
                            },
                        },
                        {
                            "type": "prod",
                            "name": "micromatch",
                            "spec": "^4.0.8",
                            "from": {
                                "name": "tailwindcss",
                                "version": "3.4.19",
                                "location": "node_modules/tailwindcss",
                                "dependents": [
                                    {
                                        "type": "dev",
                                        "name": "tailwindcss",
                                        "spec": "^3.4.17",
                                        "from": {"location": "."},
                                    }
                                ],
                            },
                        },
                    ],
                },
            },
        ],
        "dev": True,
        "optional": False,
        "devOptional": False,
        "peer": False,
        "bundled": False,
        "overridden": False,
    }
]

POLICY = {
    "schemaVersion": 1,
    "exceptions": [
        {
            "id": "GHSA-vfj7-8cjw-p6xm",
            "npmSource": 1240992,
            "package": "braces",
            "installedVersion": "3.0.3",
            "severity": "high",
            "affectedRange": "<=3.0.3",
            "title": "braces vulnerable to stack-exhaustion denial of service through deeply nested patterns",
            "url": "https://github.com/advisories/GHSA-vfj7-8cjw-p6xm",
            "devOnly": True,
            "expiresOn": "2026-11-04",
            "rationale": "Temporary exception for the exact reviewed development-tooling dependency graph.",
            "auditGraph": {
                "@next/eslint-plugin-next": {
                    "severity": "high",
                    "isDirect": True,
                    "via": ["fast-glob"],
                    "range": ">=14.3.0-canary.0",
                },
                "braces": {
                    "severity": "high",
                    "isDirect": False,
                    "via": [1240992],
                    "range": "*",
                },
                "chokidar": {
                    "severity": "high",
                    "isDirect": False,
                    "via": ["braces"],
                    "range": "2.0.0 - 3.6.0",
                },
                "fast-glob": {
                    "severity": "high",
                    "isDirect": False,
                    "via": ["micromatch"],
                    "range": "*",
                },
                "micromatch": {
                    "severity": "high",
                    "isDirect": False,
                    "via": ["braces"],
                    "range": ">=0.2.0",
                },
                "tailwindcss": {
                    "severity": "high",
                    "isDirect": True,
                    "via": ["chokidar", "fast-glob", "micromatch"],
                    "range": "<=0.0.0-oxide-insiders.ff2c25f || 2.1.0-canary.1 - 3.4.19",
                },
            },
            "dependencyChains": [
                [
                    "@next/eslint-plugin-next@16.3.1",
                    "fast-glob@3.3.1",
                    "micromatch@4.0.8",
                    "braces@3.0.3",
                ],
                ["tailwindcss@3.4.19", "chokidar@3.6.0", "braces@3.0.3"],
                [
                    "tailwindcss@3.4.19",
                    "fast-glob@3.3.3",
                    "micromatch@4.0.8",
                    "braces@3.0.3",
                ],
                ["tailwindcss@3.4.19", "micromatch@4.0.8", "braces@3.0.3"],
            ],
        }
    ],
}


def load_gate():
    assert SCRIPT.is_file(), "the npm audit gate script must exist"
    spec = importlib.util.spec_from_file_location("npm_audit_gate", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_current_exact_dev_only_advisory_is_accepted_before_expiry() -> None:
    gate = load_gate()
    assert CONFIG.is_file(), "the machine-readable exception config must exist"
    policy = json.loads(CONFIG.read_text(encoding="utf-8"))

    result = gate.evaluate(
        CURRENT_AUDIT,
        EMPTY_AUDIT,
        CURRENT_EXPLANATION,
        policy,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "pass"
    assert result["accepted"] == [
        {"id": "GHSA-vfj7-8cjw-p6xm", "expiresOn": "2026-11-04"}
    ]


def test_alternate_hoisted_nodes_layout_is_accepted() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["fast-glob"]["nodes"] = [
        "node_modules/fast-glob"
    ]

    result = gate.evaluate(
        full_audit,
        EMPTY_AUDIT,
        CURRENT_EXPLANATION,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "pass"
    assert result["accepted"] == [
        {"id": "GHSA-vfj7-8cjw-p6xm", "expiresOn": "2026-11-04"}
    ]


def test_captured_linux_effects_difference_is_accepted() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["fast-glob"]["effects"] = [
        "@next/eslint-plugin-next",
        "tailwindcss",
    ]

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "pass"
    assert result["accepted"] == [
        {"id": "GHSA-vfj7-8cjw-p6xm", "expiresOn": "2026-11-04"}
    ]


def mixed_severity_audit() -> dict:
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["postcss-selector-parser"] = {
        "name": "postcss-selector-parser",
        "severity": "moderate",
        "isDirect": False,
        "via": [
            {
                "source": 1241232,
                "name": "postcss-selector-parser",
                "dependency": "postcss-selector-parser",
                "title": "PostCSS selector parsing CPU exhaustion",
                "url": "https://github.com/advisories/GHSA-rj75-hqrm-r3gf",
                "severity": "moderate",
                "cwe": ["CWE-400"],
                "cvss": {"score": 5.9, "vectorString": "CVSS:3.1/AV:N"},
                "range": "<7.1.6",
            }
        ],
        "effects": ["postcss-nested", "tailwindcss"],
        "range": "<7.1.6",
        "nodes": ["node_modules/postcss-selector-parser"],
        "fixAvailable": True,
    }
    full_audit["vulnerabilities"]["postcss-nested"] = {
        "name": "postcss-nested",
        "severity": "moderate",
        "isDirect": False,
        "via": ["postcss-selector-parser"],
        "effects": [],
        "range": "2.0.3 - 6.2.0",
        "nodes": ["node_modules/postcss-nested"],
        "fixAvailable": True,
    }
    full_audit["vulnerabilities"]["tailwindcss"]["via"].extend(
        ["postcss-nested", "postcss-selector-parser"]
    )
    full_audit["vulnerabilities"]["tailwindcss"]["range"] = (
        "<=0.0.0-oxide-insiders.ff2c25f || 0.5.0 - 3.4.19"
    )
    full_audit["metadata"]["vulnerabilities"].update(
        {"moderate": 2, "total": 8}
    )
    return full_audit


def test_nonblocking_advisory_does_not_change_reviewed_blocking_graph() -> None:
    gate = load_gate()
    full_audit = mixed_severity_audit()

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "pass"
    assert result["accepted"] == [
        {"id": "GHSA-vfj7-8cjw-p6xm", "expiresOn": "2026-11-04"}
    ]


def test_nonblocking_advisory_cannot_hide_blocking_range_drift() -> None:
    gate = load_gate()
    full_audit = mixed_severity_audit()
    full_audit["vulnerabilities"]["tailwindcss"]["range"] = "*"

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert "Audit graph identity mismatch for tailwindcss: field=range" in result[
        "errors"
    ]


def test_blocking_graph_range_change_still_fails() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["tailwindcss"]["range"] = "<=3.4.19"

    result = gate.evaluate(
        full_audit,
        EMPTY_AUDIT,
        CURRENT_EXPLANATION,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert "Audit graph identity mismatch for tailwindcss: field=range" in result[
        "errors"
    ]


def test_same_advisory_in_production_dependencies_fails() -> None:
    gate = load_gate()
    production_audit = deepcopy(EMPTY_AUDIT)
    production_audit["vulnerabilities"] = {
        "braces": deepcopy(CURRENT_AUDIT["vulnerabilities"]["braces"])
    }
    production_audit["metadata"]["vulnerabilities"].update(
        {"high": 1, "total": 1}
    )

    result = gate.evaluate(
        CURRENT_AUDIT,
        production_audit,
        CURRENT_EXPLANATION,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("production" in error.lower() for error in result["errors"])


def test_unknown_high_advisory_fails() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["unknown-package"] = {
        "name": "unknown-package",
        "severity": "high",
        "isDirect": False,
        "via": [
            {
                "source": 9999999,
                "name": "unknown-package",
                "dependency": "unknown-package",
                "title": "Unknown high-severity advisory",
                "url": "https://github.com/advisories/GHSA-xxxx-yyyy-zzzz",
                "severity": "high",
                "cwe": ["CWE-400"],
                "cvss": {"score": 7.5, "vectorString": "CVSS:3.1/AV:N"},
                "range": "<=1.0.0",
            }
        ],
        "effects": [],
        "range": "<=1.0.0",
        "nodes": ["node_modules/unknown-package"],
        "fixAvailable": False,
    }
    full_audit["metadata"]["vulnerabilities"].update({"high": 7, "total": 7})

    result = gate.evaluate(
        full_audit,
        EMPTY_AUDIT,
        CURRENT_EXPLANATION,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("unknown-package" in error for error in result["errors"])


def test_critical_advisory_fails() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["critical-package"] = {
        "name": "critical-package",
        "severity": "critical",
        "isDirect": False,
        "via": [
            {
                "source": 9999998,
                "name": "critical-package",
                "dependency": "critical-package",
                "title": "Unknown critical advisory",
                "url": "https://github.com/advisories/GHSA-wwww-xxxx-yyyy",
                "severity": "critical",
                "cwe": ["CWE-400"],
                "cvss": {"score": 9.8, "vectorString": "CVSS:3.1/AV:N"},
                "range": "<=1.0.0",
            }
        ],
        "effects": [],
        "range": "<=1.0.0",
        "nodes": ["node_modules/critical-package"],
        "fixAvailable": False,
    }
    full_audit["metadata"]["vulnerabilities"].update(
        {"critical": 1, "total": 7}
    )

    result = gate.evaluate(
        full_audit,
        EMPTY_AUDIT,
        CURRENT_EXPLANATION,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("critical-package" in error for error in result["errors"])


def test_changed_advisory_identity_fails() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["braces"]["via"][0]["source"] = 1240993

    result = gate.evaluate(
        full_audit,
        EMPTY_AUDIT,
        CURRENT_EXPLANATION,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("identity" in error.lower() for error in result["errors"])


def test_changed_canonical_field_names_the_field() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["fast-glob"]["via"] = ["braces"]

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert "Audit graph identity mismatch for fast-glob: field=via" in result[
        "errors"
    ]


def test_exception_fails_closed_on_expiry_date() -> None:
    gate = load_gate()

    result = gate.evaluate(
        CURRENT_AUDIT,
        EMPTY_AUDIT,
        CURRENT_EXPLANATION,
        POLICY,
        today=date(2026, 11, 4),
    )

    assert result["status"] == "failed"
    assert any("expired" in error.lower() for error in result["errors"])


def test_zero_vulnerabilities_passes_without_using_exception() -> None:
    gate = load_gate()

    result = gate.evaluate(
        EMPTY_AUDIT,
        EMPTY_AUDIT,
        [],
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result == {"status": "pass", "accepted": [], "errors": []}


def test_changed_dependency_chain_identity_fails() -> None:
    gate = load_gate()
    explanation = deepcopy(CURRENT_EXPLANATION)
    next_plugin = explanation[0]["dependents"][1]["from"]["dependents"][0][
        "from"
    ]["dependents"][0]["from"]
    next_plugin["version"] = "16.3.2"

    result = gate.evaluate(
        CURRENT_AUDIT,
        EMPTY_AUDIT,
        explanation,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("chain" in error.lower() for error in result["errors"])


def test_changed_fast_glob_version_fails() -> None:
    gate = load_gate()
    explanation = deepcopy(CURRENT_EXPLANATION)
    fast_glob = explanation[0]["dependents"][1]["from"]["dependents"][0][
        "from"
    ]
    fast_glob["version"] = "3.3.2"

    result = gate.evaluate(
        CURRENT_AUDIT,
        EMPTY_AUDIT,
        explanation,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("chain" in error.lower() for error in result["errors"])


def test_missing_reviewed_dependency_chain_fails() -> None:
    gate = load_gate()
    explanation = deepcopy(CURRENT_EXPLANATION)
    micromatch_dependents = explanation[0]["dependents"][1]["from"]["dependents"]
    del micromatch_dependents[2]

    result = gate.evaluate(
        CURRENT_AUDIT,
        EMPTY_AUDIT,
        explanation,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("chain" in error.lower() for error in result["errors"])


def test_additional_dependency_chain_fails() -> None:
    gate = load_gate()
    explanation = deepcopy(CURRENT_EXPLANATION)
    micromatch_dependents = explanation[0]["dependents"][1]["from"]["dependents"]
    additional = deepcopy(micromatch_dependents[2])
    additional["from"].update(
        {
            "name": "unreviewed-tool",
            "version": "1.0.0",
            "location": "node_modules/unreviewed-tool",
            "dependents": [
                {
                    "type": "dev",
                    "name": "unreviewed-tool",
                    "spec": "1.0.0",
                    "from": {"location": "."},
                }
            ],
        }
    )
    micromatch_dependents.append(additional)

    result = gate.evaluate(
        CURRENT_AUDIT,
        EMPTY_AUDIT,
        explanation,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("chain" in error.lower() for error in result["errors"])


def test_dependency_explanation_with_production_root_fails() -> None:
    gate = load_gate()
    explanation = deepcopy(CURRENT_EXPLANATION)
    tailwind_root = explanation[0]["dependents"][0]["from"]["dependents"][0][
        "from"
    ]["dependents"][0]
    tailwind_root["type"] = "prod"

    result = gate.evaluate(
        CURRENT_AUDIT,
        EMPTY_AUDIT,
        explanation,
        POLICY,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("dev-only" in error.lower() for error in result["errors"])


def test_malformed_audit_json_fails_closed() -> None:
    gate = load_gate()
    assert hasattr(gate, "evaluate_json"), "gate must parse its JSON inputs"

    result = gate.evaluate_json(
        "{not-json",
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("malformed" in error.lower() for error in result["errors"])


def test_inconsistent_audit_metadata_fails_closed() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["metadata"]["vulnerabilities"].update({"high": 0, "total": 0})

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("interpret" in error.lower() for error in result["errors"])


def test_empty_node_path_fails_closed() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["fast-glob"]["nodes"] = [""]

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("interpret" in error.lower() for error in result["errors"])


def test_empty_effect_name_fails_closed() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["fast-glob"]["effects"] = [""]

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("interpret" in error.lower() for error in result["errors"])


def test_cli_prints_accepted_advisory_and_expiry(tmp_path: Path) -> None:
    full_path = tmp_path / "full.json"
    production_path = tmp_path / "production.json"
    explanation_path = tmp_path / "explanation.json"
    full_path.write_text(json.dumps(CURRENT_AUDIT), encoding="utf-8")
    production_path.write_text(json.dumps(EMPTY_AUDIT), encoding="utf-8")
    explanation_path.write_text(json.dumps(CURRENT_EXPLANATION), encoding="utf-8")

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--full-audit-json",
            str(full_path),
            "--production-audit-json",
            str(production_path),
            "--dependency-explanation-json",
            str(explanation_path),
            "--policy",
            str(CONFIG),
            "--as-of",
            "2026-10-05",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0
    assert "GHSA-vfj7-8cjw-p6xm" in completed.stdout
    assert "2026-11-04" in completed.stdout
    assert "TEMPORARY" in completed.stdout


def test_policy_must_require_dev_only_scope() -> None:
    gate = load_gate()
    policy = deepcopy(POLICY)
    policy["exceptions"][0]["devOnly"] = False

    result = gate.evaluate(
        CURRENT_AUDIT,
        EMPTY_AUDIT,
        CURRENT_EXPLANATION,
        policy,
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("policy" in error.lower() for error in result["errors"])


def test_nested_critical_advisory_cannot_hide_under_low_severity() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["masked-package"] = {
        "name": "masked-package",
        "severity": "low",
        "isDirect": False,
        "via": [
            {
                "source": 9999997,
                "name": "masked-package",
                "dependency": "masked-package",
                "title": "Masked critical advisory",
                "url": "https://github.com/advisories/GHSA-vvvv-wwww-xxxx",
                "severity": "critical",
                "cwe": ["CWE-400"],
                "cvss": {"score": 9.8, "vectorString": "CVSS:3.1/AV:N"},
                "range": "<=1.0.0",
            }
        ],
        "effects": [],
        "range": "<=1.0.0",
        "nodes": ["node_modules/masked-package"],
        "fixAvailable": False,
    }
    full_audit["metadata"]["vulnerabilities"].update({"low": 1, "total": 7})

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("interpret" in error.lower() for error in result["errors"])


def test_invalid_nested_advisory_value_fails_closed() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["braces"]["via"] = [None]

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("interpret" in error.lower() for error in result["errors"])


def test_boolean_vulnerability_counts_fail_closed() -> None:
    gate = load_gate()
    audit = deepcopy(EMPTY_AUDIT)
    audit["metadata"]["vulnerabilities"]["high"] = False

    result = gate.evaluate_json(
        json.dumps(audit),
        json.dumps(EMPTY_AUDIT),
        "[]",
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("interpret" in error.lower() for error in result["errors"])


def test_duplicate_json_keys_fail_closed() -> None:
    gate = load_gate()
    full_audit_json = (
        '{"auditReportVersion":2,"vulnerabilities":'
        + json.dumps(CURRENT_AUDIT["vulnerabilities"])
        + ',"metadata":'
        + json.dumps(CURRENT_AUDIT["metadata"])
        + ',"vulnerabilities":{},"metadata":'
        + json.dumps(EMPTY_AUDIT["metadata"])
        + "}"
    )

    result = gate.evaluate_json(
        full_audit_json,
        json.dumps(EMPTY_AUDIT),
        "[]",
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("malformed" in error.lower() for error in result["errors"])


def test_string_reference_cannot_hide_higher_severity_finding() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["masked-package"] = {
        "name": "masked-package",
        "severity": "low",
        "isDirect": False,
        "via": ["braces"],
        "effects": [],
        "range": "<=1.0.0",
        "nodes": ["node_modules/masked-package"],
        "fixAvailable": False,
    }
    full_audit["metadata"]["vulnerabilities"].update({"low": 1, "total": 7})

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("interpret" in error.lower() for error in result["errors"])


def test_missing_string_advisory_reference_fails_closed() -> None:
    gate = load_gate()
    full_audit = deepcopy(CURRENT_AUDIT)
    full_audit["vulnerabilities"]["masked-package"] = {
        "name": "masked-package",
        "severity": "low",
        "isDirect": False,
        "via": ["omitted-critical-package"],
        "effects": [],
        "range": "<=1.0.0",
        "nodes": ["node_modules/masked-package"],
        "fixAvailable": False,
    }
    full_audit["metadata"]["vulnerabilities"].update({"low": 1, "total": 7})

    result = gate.evaluate_json(
        json.dumps(full_audit),
        json.dumps(EMPTY_AUDIT),
        json.dumps(CURRENT_EXPLANATION),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("interpret" in error.lower() for error in result["errors"])


def test_malformed_dependency_root_fails_closed() -> None:
    gate = load_gate()
    explanation = deepcopy(CURRENT_EXPLANATION)
    tailwind_root = explanation[0]["dependents"][0]["from"]["dependents"][0][
        "from"
    ]["dependents"][0]
    tailwind_root["from"] = []

    result = gate.evaluate_json(
        json.dumps(CURRENT_AUDIT),
        json.dumps(EMPTY_AUDIT),
        json.dumps(explanation),
        json.dumps(POLICY),
        today=date(2026, 10, 5),
    )

    assert result["status"] == "failed"
    assert any("malformed" in error.lower() for error in result["errors"])
