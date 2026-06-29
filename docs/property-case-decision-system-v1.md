# Property Case Decision System v1

## Purpose

Property Case Decision System v1 gives the existing buyer workflow a clear
case-level model and readiness view. It does not replace Property Finder,
Viewing Decision, Case Manager, Case Comparison, Decision Report, or print
export. It organizes the same in-memory and saved-case results so users can
understand whether a property case is ready to save, compare, or print.

## Case Model

The frontend case draft is built from existing module outputs:

- `property_input`
- `location_input`
- `financial_input`
- `analysis_status`
- `analysis_summary`
- `readiness`

The model is intentionally minimal. It does not store provider raw payloads,
database rows, tokens, credentials, raw errors, coordinates from providers, or
debug logs.

## Property Input

`property_input` contains user-facing property facts:

- `address`
- `listing_price`
- `building_area`
- `property_type`
- `building_age`
- `floor`
- `total_floors`
- `parking_type`
- `parking_price`
- `notes`

Missing values remain missing. The system does not invent prices, addresses,
parking details, or building facts.

## Location Input

`location_input` summarizes status only:

- `address_status`
- `location_analysis_status`
- `terrain_analysis_status`
- `commute_analysis_status`
- `map_available`

Unavailable or incomplete location, terrain, or commute data is shown as a
data limitation. It is not treated as low risk.

## Financial Input

`financial_input` summarizes existing calculator outputs:

- `down_payment`
- `loan_amount`
- `loan_years`
- `interest_rate`
- `grace_period_months`
- `monthly_income`
- `other_monthly_debt`
- `estimated_holding_cost`

The case model does not change loan formulas, valuation logic, tax logic, or
market data behavior.

## Readiness Rules

Draft readiness:

- A draft can be shown when there is a case name or address.
- A case is comparison-ready only when it has a case name, address, and
  reference price.
- A print/report-ready case requires valuation and a risk summary.
- Missing, unavailable, or incomplete data is listed as a limitation and never
  converted into zero, safe, or complete.

## UI Flow

The new readiness card appears in the existing Immersive Viewing Workspace,
before the existing Case Manager. Users still use the same Case Manager to
save, load, compare, and export cases.

## Boundaries

This feature does not:

- call new APIs
- create database writes
- change PLVR read model or market refresh workflow
- change Render, Vercel, GitHub Actions, or GitHub Secrets
- change Viewing Decision behavior
- persist new state to localStorage, sessionStorage, cookies, or URL query
- use commute or market data to alter valuation, loan, tax, legal, terrain, or
  purchase decisions

All decision language remains conservative. The system does not say a property
is safe, guaranteed, best, legally approved, loan-approved, or suitable to buy.
