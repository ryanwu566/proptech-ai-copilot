from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.assessments import (
    AegisCreditCreate,
    LexPropCreate,
    MockAnalysisResult,
    TaxOracleCreate,
)

MONEY_ZERO = Decimal("0")


def analyze_aegis_credit(payload: AegisCreditCreate) -> MockAnalysisResult:
    down_payment = payload.property_value - payload.loan_amount
    down_payment_ratio = _ratio(down_payment, payload.property_value)
    loan_to_value = _ratio(payload.loan_amount, payload.property_value)
    debt_to_income = _ratio(payload.existing_debt, payload.monthly_income)
    monthly_payment = _estimate_monthly_payment(
        principal=payload.loan_amount,
        annual_rate=Decimal("0.025"),
        years=payload.loan_term_years,
    )
    stressed_payment = _estimate_monthly_payment(
        principal=payload.loan_amount,
        annual_rate=Decimal("0.04"),
        years=payload.loan_term_years,
    )
    stressed_dti = _ratio(payload.existing_debt + stressed_payment, payload.monthly_income)

    score = 20
    score += _score_band(loan_to_value, [(Decimal("0.70"), 0), (Decimal("0.80"), 15)], 30)
    score += _score_band(debt_to_income, [(Decimal("0.30"), 0), (Decimal("0.45"), 15)], 25)
    score += _score_band(down_payment_ratio, [(Decimal("0.20"), 25), (Decimal("0.30"), 10)], 0, reverse=True)
    score += _score_band(stressed_dti, [(Decimal("0.40"), 0), (Decimal("0.55"), 10)], 20)
    score = min(score, 100)

    loan_band = _loan_ratio_band(score)
    risk_level = _risk_level(score)
    shortage_gap = max(payload.loan_amount - (payload.property_value * loan_band[1]), MONEY_ZERO)

    return MockAnalysisResult(
        risk_level=risk_level,
        score=score,
        summary="Deterministic mortgage rules evaluated income, debt load, down payment, property value, and stress payment capacity.",
        recommendations=[
            "Review income proof and recurring debt before issuing a final loan opinion.",
            "Ask the applicant to increase down payment or lower loan amount if shortage risk remains elevated.",
            "Run policy review when stressed debt-to-income exceeds 55%.",
        ],
        details={
            "loan_to_value": _pct(loan_to_value),
            "debt_to_income": _pct(debt_to_income),
            "down_payment": _money(down_payment),
            "down_payment_ratio": _pct(down_payment_ratio),
            "loan_ratio_band": [_pct(loan_band[0]), _pct(loan_band[1])],
            "estimated_monthly_payment": _money(monthly_payment),
            "stress_test": {
                "annual_rate": "4.00%",
                "monthly_payment": _money(stressed_payment),
                "stressed_debt_to_income": _pct(stressed_dti),
                "loan_shortage_gap": _money(shortage_gap),
            },
        },
    )


def analyze_tax_oracle(payload: TaxOracleCreate) -> MockAnalysisResult:
    blockers: list[str] = []
    if payload.transaction_type != "sale":
        blockers.append("Transaction type is not a sale.")
    if not payload.is_self_use:
        blockers.append("Property is not marked as self-use.")
    if payload.replacement_purchase_value < payload.assessed_value:
        blockers.append("Replacement purchase value is lower than the sold property value.")
    if payload.has_outstanding_tax_debt:
        blockers.append("Outstanding tax debt must be cleared before refund review.")
    if payload.annual_rental_income > MONEY_ZERO:
        blockers.append("Rental income indicates the property may not meet self-use assumptions.")

    eligible = len(blockers) == 0
    score = 18 if eligible else min(95, 42 + len(blockers) * 12)
    reminders = _five_year_reminders(date.today().year)

    return MockAnalysisResult(
        risk_level=_risk_level(score),
        score=score,
        summary=(
            "Eligible for repurchase tax refund review under deterministic MVP rules."
            if eligible
            else "Not eligible under deterministic MVP rules until listed blockers are resolved."
        ),
        recommendations=(
            ["Prepare sale, repurchase, household registration, and self-use proof for reviewer confirmation."]
            if eligible
            else blockers
        ),
        details={
            "eligible": eligible,
            "blockers": blockers,
            "five_year_monitoring_reminders": reminders,
            "calculation_method": "deterministic_rules_only_no_llm",
        },
    )


def analyze_lex_prop(payload: LexPropCreate) -> MockAnalysisResult:
    text = f"{payload.property_address} {payload.title_number} {payload.dispute_notes or ''}".lower()
    categories = _classify_title_keywords(text)

    score = min(100, 15 + sum(item["weight"] for item in categories))
    if payload.has_lien:
        score += 18
        categories.append({"category": "lien", "keywords": ["has_lien"], "weight": 18})
    if payload.has_easement:
        score += 12
        categories.append({"category": "easement", "keywords": ["has_easement"], "weight": 12})
    score = min(score, 100)

    recommendations = [
        "Request latest title transcript and compare owner, encumbrance, and usage records.",
        "Ask seller or broker for written disclosure and supporting documents for each matched category.",
    ]
    if categories:
        recommendations.append("Escalate matched keyword categories to human legal review before closing.")

    return MockAnalysisResult(
        risk_level=_risk_level(score),
        score=score,
        summary="Keyword classifier completed deterministic title risk categorization.",
        recommendations=recommendations,
        details={
            "matched_categories": categories,
            "classifier": "keyword_rules_only",
        },
    )


def _classify_title_keywords(text: str) -> list[dict[str, object]]:
    keyword_rules = {
        "water_leak": {"keywords": ["漏水", "滲水", "壁癌", "leak", "water damage"], "weight": 14},
        "hoa_committee": {"keywords": ["管委會", "管理委員會", "hoa", "committee"], "weight": 10},
        "occupation": {"keywords": ["佔用", "占用", "無權占有", "illegal occupation"], "weight": 18},
        "unnatural_death": {"keywords": ["非自然身故", "凶宅", "事故死亡", "unnatural death"], "weight": 22},
        "co_owned_dispute": {"keywords": ["共有物糾紛", "共有", "分割", "co-owned", "partition"], "weight": 16},
    }

    matches: list[dict[str, object]] = []
    for category, rule in keyword_rules.items():
        found = [keyword for keyword in rule["keywords"] if keyword in text]
        if found:
            matches.append(
                {
                    "category": category,
                    "keywords": found,
                    "weight": rule["weight"],
                }
            )
    return matches


def _estimate_monthly_payment(principal: Decimal, annual_rate: Decimal, years: int) -> Decimal:
    months = Decimal(years * 12)
    monthly_rate = annual_rate / Decimal("12")
    if monthly_rate == MONEY_ZERO:
        return principal / months
    factor = (Decimal("1") + monthly_rate) ** int(months)
    return principal * monthly_rate * factor / (factor - Decimal("1"))


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal:
    if denominator <= MONEY_ZERO:
        return MONEY_ZERO
    return numerator / denominator


def _score_band(
    value: Decimal,
    bands: list[tuple[Decimal, int]],
    fallback: int,
    reverse: bool = False,
) -> int:
    if reverse:
        for threshold, score in bands:
            if value < threshold:
                return score
        return fallback
    for threshold, score in bands:
        if value <= threshold:
            return score
    return fallback


def _loan_ratio_band(score: int) -> tuple[Decimal, Decimal]:
    if score >= 75:
        return Decimal("0.50"), Decimal("0.60")
    if score >= 45:
        return Decimal("0.60"), Decimal("0.70")
    return Decimal("0.70"), Decimal("0.80")


def _risk_level(score: int) -> str:
    if score >= 75:
        return "high"
    if score >= 45:
        return "medium"
    return "low"


def _five_year_reminders(start_year: int) -> list[dict[str, object]]:
    return [
        {
            "year": start_year + offset,
            "message": f"Year {offset}: confirm self-use status and retain repurchase refund documents.",
        }
        for offset in range(1, 6)
    ]


def _money(value: Decimal) -> str:
    return str(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _pct(value: Decimal) -> str:
    return f"{(value * Decimal('100')).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}%"
