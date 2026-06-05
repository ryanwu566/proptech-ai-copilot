"""Deterministic TaxOracle qualification and risk scoring rules."""

from __future__ import annotations

from models.schemas import RuleTrace, TaxAnalysisResult, TaxCase


def _signal_color(score: int) -> str:
    if score <= 24:
        return "green"
    if score <= 54:
        return "yellow"
    return "red"


def evaluate_tax_case(case: TaxCase) -> TaxAnalysisResult:
    """Evaluate TX001-TX009 without using an LLM."""

    traces: list[RuleTrace] = []
    hard_fail: list[str] = []
    manual_review: list[str] = []
    passed: list[str] = []
    missing_docs: list[str] = []

    def record(
        code: str,
        title: str,
        passed_rule: bool,
        fail_type: str,
        fail_detail: str,
        risk_points: int,
    ) -> None:
        if passed_rule:
            passed.append(code)
            traces.append(RuleTrace(code, title, "passed", "條件已符合", 0))
            return
        if fail_type == "hard_fail":
            hard_fail.append(code)
        else:
            manual_review.append(code)
        traces.append(RuleTrace(code, title, fail_type, fail_detail, risk_points))

    record("TX001", "賣出物件是否自住", case.sold_self_occupied, "hard_fail", "賣出物件非自住", 35)
    record("TX002", "賣出時是否設籍或符合自住條件", case.residency_condition_met, "manual_review", "需確認設籍或自住佐證", 15)
    record("TX003", "換購時間是否合理", case.purchase_within_reasonable_period, "hard_fail", "換購時間不符初步條件", 30)
    record("TX004", "換購物件是否自住", case.purchased_self_occupied, "hard_fail", "換購物件非自住", 35)
    record("TX005", "所有權主體是否一致", case.same_owner, "manual_review", "所有權主體需人工核對", 20)
    record("TX006", "公告土地現值是否齊備", case.land_value_available, "manual_review", "缺少公告土地現值資料", 10)
    record("TX007", "文件是否足夠", case.required_docs_complete, "manual_review", "文件尚未齊備", 15)
    record("TX008", "是否進入五年列管", case.enters_five_year_monitoring, "passed", "需確認五年列管提醒", 8)
    record("TX009", "是否有例外事由需人工複核", not case.exceptional_circumstances, "manual_review", "存在例外事由", 20)

    if not case.land_value_available:
        missing_docs.append("公告土地現值資料")
    if not case.required_docs_complete:
        missing_docs.extend(["買賣契約影本", "戶籍或自住佐證文件", "完稅或申報相關文件"])
    if not case.residency_condition_met:
        missing_docs.append("設籍或自住條件佐證")

    score = min(100, sum(trace.risk_points for trace in traces))
    eligibility = "not_eligible" if hard_fail else "manual_review" if manual_review else "eligible"
    timeline = (
        [f"第 {year} 年：確認換購住宅仍符合自住與列管條件" for year in range(1, 6)]
        if case.enters_five_year_monitoring
        else []
    )
    return TaxAnalysisResult(
        eligibility_status=eligibility,
        risk_score=score,
        signal_color=_signal_color(score),
        hard_fail_rules=hard_fail,
        manual_review_rules=manual_review,
        passed_rules=passed,
        missing_docs=list(dict.fromkeys(missing_docs)),
        reminder_timeline=timeline,
        rule_traces=traces,
    )

