"""TaxOracle application service."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from backend.repositories.sqlite_repo import save_tax_analysis
from models.schemas import TaxCase
from rules.tax_rules import evaluate_tax_case
from services.llm_service import generate_ai_explanation


def analyze_tax_case(case: TaxCase, persist: bool = True) -> dict[str, Any]:
    """Run deterministic analysis, attach explanation, and optionally persist."""

    result = evaluate_tax_case(case)
    payload = result.to_dict()
    payload["ai_explanation"] = generate_ai_explanation(payload)
    payload["case_input"] = asdict(case)
    if persist:
        save_tax_analysis(case.case_id, case.client_name, payload)
    return payload
