"""Shared schemas for the PropTech MVP."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


DISCLAIMER = (
    "本系統僅供房仲與客戶進行初步稅務風險溝通與文件準備參考，不構成法律、"
    "稅務或申報保證。正式資格與稅額仍以主管稅捐機關、最新法令函釋及專業人士審查為準。"
)


@dataclass
class TaxCase:
    """Input fields used by the deterministic TaxOracle engine."""

    case_id: str
    client_name: str
    sold_self_occupied: bool
    residency_condition_met: bool
    purchase_within_reasonable_period: bool
    purchased_self_occupied: bool
    same_owner: bool
    land_value_available: bool
    required_docs_complete: bool
    enters_five_year_monitoring: bool
    exceptional_circumstances: bool


@dataclass
class RuleTrace:
    """One deterministic rule evaluation result."""

    code: str
    title: str
    outcome: str
    detail: str
    risk_points: int = 0


@dataclass
class TaxAnalysisResult:
    """Structured TaxOracle output contract."""

    eligibility_status: str
    risk_score: int
    signal_color: str
    hard_fail_rules: list[str] = field(default_factory=list)
    manual_review_rules: list[str] = field(default_factory=list)
    passed_rules: list[str] = field(default_factory=list)
    missing_docs: list[str] = field(default_factory=list)
    reminder_timeline: list[str] = field(default_factory=list)
    rule_traces: list[RuleTrace] = field(default_factory=list)
    ai_explanation: dict[str, Any] = field(default_factory=dict)
    disclaimer: str = DISCLAIMER

    def to_dict(self) -> dict[str, Any]:
        """Serialize nested dataclasses for Streamlit and SQLite."""

        return asdict(self)

