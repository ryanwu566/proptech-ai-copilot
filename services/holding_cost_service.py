"""Simplified monthly holding-cost estimates for pre-purchase planning."""

from __future__ import annotations

from typing import Any


DISCLAIMER = "本試算僅供買房前成本壓力估算；稅費為簡化估算，不構成正式稅務申報或銀行核貸結果。"


def calculate_holding_cost(
    property_price: float,
    loan_monthly_payment: float = 0,
    monthly_income: float | None = None,
    area_ping: float | None = None,
    management_fee_per_ping: float = 80,
    repair_reserve_per_ping: float = 50,
    annual_home_tax_rate: float = 0.0012,
    annual_land_tax_rate: float = 0.001,
    annual_insurance: float = 3000,
    include_tax_estimate: bool = True,
) -> dict[str, Any]:
    """Calculate a stable monthly and annual holding-cost breakdown."""

    _validate_inputs(
        property_price,
        loan_monthly_payment,
        monthly_income,
        area_ping,
        management_fee_per_ping,
        repair_reserve_per_ping,
        annual_home_tax_rate,
        annual_land_tax_rate,
        annual_insurance,
    )
    property_price_yuan = property_price * 10_000
    monthly_management_fee = (area_ping or 0) * management_fee_per_ping
    monthly_repair_reserve = (area_ping or 0) * repair_reserve_per_ping
    annual_home_tax = property_price_yuan * annual_home_tax_rate if include_tax_estimate else 0
    annual_land_tax = property_price_yuan * annual_land_tax_rate if include_tax_estimate else 0
    monthly_tax = (annual_home_tax + annual_land_tax) / 12
    monthly_insurance = annual_insurance / 12
    monthly_total = loan_monthly_payment + monthly_management_fee + monthly_repair_reserve + monthly_tax + monthly_insurance
    annual_total = monthly_total * 12
    income_yuan = monthly_income * 10_000 if monthly_income is not None else None
    burden_ratio = monthly_total / income_yuan if income_yuan else None
    level = _affordability_level(burden_ratio)

    input_summary = {
        "property_price_wan": round(property_price, 2),
        "loan_monthly_payment": round(loan_monthly_payment),
        "monthly_income_wan": round(monthly_income, 2) if monthly_income is not None else None,
        "area_ping": round(area_ping, 2) if area_ping is not None else None,
        "management_fee_per_ping": round(management_fee_per_ping, 2),
        "repair_reserve_per_ping": round(repair_reserve_per_ping, 2),
        "annual_home_tax_rate": round(annual_home_tax_rate, 6),
        "annual_land_tax_rate": round(annual_land_tax_rate, 6),
        "annual_insurance": round(annual_insurance),
        "include_tax_estimate": include_tax_estimate,
    }
    breakdown = [
        {"key": "loan", "label": "房貸月付", "monthly_amount": round(loan_monthly_payment)},
        {"key": "management", "label": "管理費", "monthly_amount": round(monthly_management_fee)},
        {"key": "repair_reserve", "label": "修繕預備金", "monthly_amount": round(monthly_repair_reserve)},
        {"key": "tax_estimate", "label": "稅費簡化估算", "monthly_amount": round(monthly_tax)},
        {"key": "insurance", "label": "保險預估", "monthly_amount": round(monthly_insurance)},
    ]
    return {
        "input": input_summary,
        "property_price_wan": round(property_price, 2),
        "loan_monthly_payment": round(loan_monthly_payment),
        "monthly_management_fee": round(monthly_management_fee),
        "monthly_repair_reserve": round(monthly_repair_reserve),
        "monthly_tax_estimate": round(monthly_tax),
        "annual_home_tax_estimate": round(annual_home_tax),
        "annual_land_tax_estimate": round(annual_land_tax),
        "monthly_insurance": round(monthly_insurance),
        "monthly_total_holding_cost": round(monthly_total),
        "annual_total_holding_cost": round(annual_total),
        "income_burden_ratio": round(burden_ratio, 4) if burden_ratio is not None else None,
        "affordability_level": level,
        "affordability_message": _affordability_message(level),
        "cost_breakdown": breakdown,
        "disclaimer": DISCLAIMER,
    }


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
        "comfortable": "每月總持有成本約占收入三成內，仍應保留生活支出與緊急預備金。",
        "manageable": "每月總持有成本尚可管理，建議預留稅費與修繕波動空間。",
        "tight": "每月總持有成本偏緊，建議重新檢視貸款、管理費與修繕預算。",
        "risky": "每月總持有成本占收入比例偏高，建議降低總價或增加現金緩衝。",
        "unknown": "輸入月收入後，可查看總持有成本負擔率與負擔等級。",
    }[level]


def _validate_inputs(
    property_price: float,
    loan_monthly_payment: float,
    monthly_income: float | None,
    area_ping: float | None,
    management_fee_per_ping: float,
    repair_reserve_per_ping: float,
    annual_home_tax_rate: float,
    annual_land_tax_rate: float,
    annual_insurance: float,
) -> None:
    values = {
        "property_price": property_price,
        "loan_monthly_payment": loan_monthly_payment,
        "management_fee_per_ping": management_fee_per_ping,
        "repair_reserve_per_ping": repair_reserve_per_ping,
        "annual_home_tax_rate": annual_home_tax_rate,
        "annual_land_tax_rate": annual_land_tax_rate,
        "annual_insurance": annual_insurance,
    }
    if property_price <= 0:
        raise ValueError("property_price must be greater than 0")
    for name, value in values.items():
        if name != "property_price" and value < 0:
            raise ValueError(f"{name} must be greater than or equal to 0")
    if monthly_income is not None and monthly_income <= 0:
        raise ValueError("monthly_income must be greater than 0")
    if area_ping is not None and area_ping < 0:
        raise ValueError("area_ping must be greater than or equal to 0")
