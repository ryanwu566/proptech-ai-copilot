"""Transparent mortgage payment calculations for pre-purchase planning."""

from __future__ import annotations

from typing import Any


DISCLAIMER = "本試算僅供買房前估算，不代表銀行核貸結果。"


def calculate_loan(
    property_price: float,
    down_payment_ratio: float = 0.2,
    annual_interest_rate: float = 2.2,
    loan_years: int = 30,
    monthly_income: float | None = None,
    grace_period_years: int = 0,
    include_sensitivity: bool = True,
) -> dict[str, Any]:
    """Calculate principal-and-interest payments using amounts entered in wan."""

    _validate_inputs(
        property_price,
        down_payment_ratio,
        annual_interest_rate,
        loan_years,
        monthly_income,
        grace_period_years,
    )
    property_price_yuan = property_price * 10_000
    down_payment_yuan = property_price_yuan * down_payment_ratio
    principal = property_price_yuan - down_payment_yuan
    schedule = _payment_schedule(principal, annual_interest_rate, loan_years, grace_period_years)
    income_yuan = monthly_income * 10_000 if monthly_income is not None else None
    burden_ratio = schedule["monthly_payment"] / income_yuan if income_yuan else None
    level = _affordability_level(burden_ratio)

    return {
        "property_price_wan": round(property_price, 2),
        "down_payment_ratio": round(down_payment_ratio, 4),
        "down_payment_wan": round(down_payment_yuan / 10_000, 2),
        "loan_amount_wan": round(principal / 10_000, 2),
        "annual_interest_rate": round(annual_interest_rate, 4),
        "loan_years": loan_years,
        "grace_period_years": grace_period_years,
        "monthly_income_wan": round(monthly_income, 2) if monthly_income is not None else None,
        "monthly_payment": round(schedule["monthly_payment"]),
        "grace_period_monthly_payment": _rounded_or_none(schedule["grace_period_monthly_payment"]),
        "post_grace_monthly_payment": _rounded_or_none(schedule["post_grace_monthly_payment"]),
        "total_payment": round(schedule["total_payment"]),
        "total_interest": round(schedule["total_interest"]),
        "income_burden_ratio": round(burden_ratio, 4) if burden_ratio is not None else None,
        "affordability_level": level,
        "affordability_message": _affordability_message(level),
        "sensitivity": _sensitivity(principal, annual_interest_rate, loan_years, grace_period_years, schedule["monthly_payment"])
        if include_sensitivity
        else [],
        "disclaimer": DISCLAIMER,
    }


def _payment_schedule(principal: float, annual_rate: float, loan_years: int, grace_years: int) -> dict[str, float | None]:
    total_months = loan_years * 12
    grace_months = grace_years * 12
    monthly_rate = annual_rate / 100 / 12
    remaining_months = total_months - grace_months
    amortized_payment = _amortized_payment(principal, monthly_rate, remaining_months)
    grace_payment = principal * monthly_rate if grace_months else None
    total_payment = amortized_payment * remaining_months + (grace_payment or 0) * grace_months
    return {
        "monthly_payment": amortized_payment,
        "grace_period_monthly_payment": grace_payment,
        "post_grace_monthly_payment": amortized_payment if grace_months else None,
        "total_payment": total_payment,
        "total_interest": total_payment - principal,
    }


def _amortized_payment(principal: float, monthly_rate: float, months: int) -> float:
    if monthly_rate == 0:
        return principal / months
    return principal * monthly_rate / (1 - (1 + monthly_rate) ** -months)


def _sensitivity(principal: float, base_rate: float, loan_years: int, grace_years: int, base_payment: float) -> list[dict[str, float | int]]:
    rates = [max(0, base_rate - 0.5), base_rate, base_rate + 0.5, base_rate + 1.0]
    items = []
    for rate in (round(item, 4) for item in rates):
        schedule = _payment_schedule(principal, rate, loan_years, grace_years)
        payment = schedule["monthly_payment"]
        items.append(
            {
                "annual_interest_rate": rate,
                "monthly_payment": round(payment),
                "total_interest": round(schedule["total_interest"]),
                "difference_from_base": round(payment - base_payment),
            }
        )
    return items


def _affordability_level(ratio: float | None) -> str:
    if ratio is None:
        return "unknown"
    if ratio <= 0.30:
        return "comfortable"
    if ratio <= 0.40:
        return "manageable"
    if ratio <= 0.50:
        return "tight"
    return "risky"


def _affordability_message(level: str) -> str:
    return {
        "comfortable": "月付約占月收入三成內，仍應保留緊急預備金與其他持有成本。",
        "manageable": "月付負擔尚可管理，建議同步評估生活支出與利率上升情境。",
        "tight": "月付負擔偏緊，建議提高頭期款、降低總價或延長準備期。",
        "risky": "月付占收入比例偏高，建議重新評估總價、貸款條件與現金流。",
        "unknown": "輸入月收入後，可查看月付負擔率與負擔能力等級。",
    }[level]


def _validate_inputs(
    property_price: float,
    down_payment_ratio: float,
    annual_interest_rate: float,
    loan_years: int,
    monthly_income: float | None,
    grace_period_years: int,
) -> None:
    if property_price <= 0:
        raise ValueError("property_price must be greater than 0")
    if not 0 <= down_payment_ratio <= 1:
        raise ValueError("down_payment_ratio must be between 0 and 1")
    if annual_interest_rate < 0:
        raise ValueError("annual_interest_rate must be greater than or equal to 0")
    if loan_years <= 0:
        raise ValueError("loan_years must be greater than 0")
    if monthly_income is not None and monthly_income <= 0:
        raise ValueError("monthly_income must be greater than 0")
    if grace_period_years < 0:
        raise ValueError("grace_period_years must be greater than or equal to 0")
    if grace_period_years >= loan_years:
        raise ValueError("grace_period_years must be less than loan_years")


def _rounded_or_none(value: float | None) -> int | None:
    return round(value) if value is not None else None
