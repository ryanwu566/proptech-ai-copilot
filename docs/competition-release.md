# Competition-ready TaxOracle MVP

## Product boundary

TaxOracle and Holding Cost are the primary competition MVP: a Taiwan real-estate
transaction preparation surface for organizing property facts, preliminary
tax qualification, ownership-cost context, and official-source evidence before
a client conversation. They do not decide whether a property should be bought.

The homepage leads to the three-minute example, then exposes supporting
Location, Terrain, Valuation, Market, Financing, and Property Case tools.

## Three-minute demo

The `Competition Demo` surface uses the existing deterministic TaxOracle and
Holding Cost HTTP contracts. The example is explicitly illustrative, editable,
resettable, and not a customer case. Invalid input is shown as an error and is
never converted into a result. The screen shows the four steps, used inputs,
missing facts, rule version, source status, and limitations.

An explicitly labelled offline mode is available for rehearsal only. It is not
a silent fallback and does not claim current official data.

## Capability truth

Runtime capability metadata is defined in `frontend_next/lib/competition-release.ts`.
The evidence center distinguishes implemented, tested, source-dependent,
reference-only, professional-review-pending, market-validation-pending, and
planned capabilities. No customer, revenue, accuracy, or time-saving claim is
made without evidence.

## Public boundaries

Privacy and Terms pages describe current browser storage, native speech, case
data, source limitations, and professional review boundaries. Browser-native
print is used for the current summary; no server-side PDF service is introduced.
