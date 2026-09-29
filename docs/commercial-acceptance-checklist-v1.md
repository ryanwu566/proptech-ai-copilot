# Commercial Acceptance Checklist v1

Use this checklist against the exact hosted production candidate before broker sessions and after any material release. It validates invariants, not exact live market values.

Allowed status values: `PASS`, `PARTIAL`, `FAIL`, `NOT TESTED`.

- `PASS`: expected invariant is directly observed with evidence.
- `PARTIAL`: some of the invariant is observed, with a named limitation.
- `FAIL`: observed behavior violates the invariant or creates unsafe ambiguity.
- `NOT TESTED`: no valid evidence was collected. This is not a pass.

For every item, record the status and concise evidence such as screenshot ID, timestamp, visible message, route, or operator note. Do not paste credentials, tokens, raw provider payloads, private addresses, or production response bodies.

## Run record

| Field | Value |
| --- | --- |
| Run ID | |
| Date/time and timezone | |
| Operator | Participant ID or initials only |
| Hosted frontend URL | |
| Hosted backend boundary | Hostname only; no secrets |
| Frontend/build SHA | |
| Backend/build SHA | |
| Browser/version | |
| Device/OS | |
| Viewports tested | Desktop / 390px |
| Data/provider notes | |
| Final decision | NO-GO / LIMITED PILOT / COMMERCIAL MVP PILOT READY |

## Standard fixture

Public building location:

- Dongming Social Housing (東明社會住宅)
- `臺北市南港區南港路二段60巷16號`

Fictional test inputs:

- Asking price: `2,480 萬`
- Area: `26 坪`
- Building age: `7 年`
- Floor: `8 樓`
- Cash: `650 萬`
- Down payment: `20%`
- Loan: `30 年`, `2.40%`
- Monthly household income: `180,000 元`
- Other monthly obligations: `20,000 元`
- Monthly ownership reserve: `6,000 元`
- Commute destination: Taipei City Hall, `臺北市信義區市府路1號`

These inputs do not describe a real listing, resident, unit, loan offer, or client.

## Entry

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| E-01 | Open hosted root | Page loads without fatal error or localhost request. | NOT TESTED | |
| E-02 | Find primary entry | Property Finder / guided property entry is discoverable without coaching. | NOT TESTED | |
| E-03 | Enter standard fixture | Address, area, building details, and asking price accept explicit units. | NOT TESTED | |
| E-04 | Submit property | Loading and completion state are visible; duplicate submission is controlled. | NOT TESTED | |
| E-05 | Input privacy | No prompt requests client name, phone, email, ID, bank statement, or ownership document. | NOT TESTED | |

## Property integrity

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| PI-01 | Confirm active property | Current address/property context is visible before analysis. | NOT TESTED | |
| PI-02 | Trace outputs | Operator can state which property each visible result belongs to. | NOT TESTED | |
| PI-03 | Change address to `臺北市南港區向陽路248號` | Old location, market, valuation, commute, and risk evidence clears or is explicitly stale. | NOT TESTED | |
| PI-04 | Continue after address change | New results attach only to the second property; no old evidence is presented as current. | NOT TESTED | |
| PI-05 | Revalidation state | UI explains what must be refreshed when identity/context changes. | NOT TESTED | |

Any unresolved wrong-property evidence is a release-blocking `FAIL`.

## Market & price

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| MP-01 | Run Market | Available, no-data, partial, stale, or unavailable state is explicit. | NOT TESTED | |
| MP-02 | Inspect market evidence | Geography, unit, source, period/date, coverage, and limitation are understandable. | NOT TESTED | |
| MP-03 | Run Valuation | Official/actionable evidence is distinguished from demo, sample, unavailable, or non-actionable evidence. | NOT TESTED | |
| MP-04 | Inspect valuation | Range, unit, confidence, comparables, freshness, and “not formal appraisal” boundary are visible. | NOT TESTED | |
| MP-05 | Valuation unavailable | No estimate is invented; other modules remain usable. | NOT TESTED | |
| MP-06 | Change asking price to `2,680 萬` | Asking-price basis and affected downstream outputs update or invalidate without changing property identity. | NOT TESTED | |

## Location & commute

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| LC-01 | Run Location | Resolved location and data-quality state are visible. | NOT TESTED | |
| LC-02 | Open map | Map corresponds to the active property and does not imply legal parcel identity. | NOT TESTED | |
| LC-03 | Inspect nearby evidence | Source/coverage limits are understandable; mock/demo output is not presented as verified live data. | NOT TESTED | |
| LC-04 | Run commute to City Hall | Origin, destination, mode/assumption, units, and status are explicit. | NOT TESTED | |
| LC-05 | Commute unavailable | Location remains usable; commute is explicitly unavailable and recoverable locally. | NOT TESTED | |

## Risk

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| R-01 | Run risk/environment analysis | Result is tied to the active property with checked-at/source context. | NOT TESTED | |
| R-02 | Inspect each layer/provider | Available, partial, unknown, and unavailable states remain distinct. | NOT TESTED | |
| R-03 | Partial provider failure | Available layers remain visible; unavailable layers do not become low risk. | NOT TESTED | |
| R-04 | Read limitations | UI states that reference data is not site inspection, structural, engineering, or legal advice. | NOT TESTED | |
| R-05 | Next action | Missing/unknown evidence produces a verification action, not an all-clear. | NOT TESTED | |

## Finance

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| F-01 | Run loan calculation | Price, down payment, rate, term, payment, and currency units are explicit. | NOT TESTED | |
| F-02 | Inspect loan boundary | Result is a scenario, not approval, underwriting, or an actual offer. | NOT TESTED | |
| F-03 | Run holding cost | Included assumptions and omitted inputs are visible. | NOT TESTED | |
| F-04 | Remove area | Area-dependent costs show missing/unestimated, not zero. | NOT TESTED | |
| F-05 | Run TaxOracle | Rule/reference status, assumptions, trace, and advice boundary are visible. | NOT TESTED | |
| F-06 | Change asking price | Loan, holding-cost, tax, and affected decision outputs update or invalidate. | NOT TESTED | |

## Decision

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| D-01 | Open decision stage | Active property and selected price basis are clear. | NOT TESTED | |
| D-02 | Review synthesis | Known, estimated, partial, unavailable, and unknown evidence remain distinguishable. | NOT TESTED | |
| D-03 | Review readiness | Missing evidence prevents a false complete/safe/recommended state. | NOT TESTED | |
| D-04 | Review next actions | Verification questions are specific and tied to gaps. | NOT TESTED | |
| D-05 | Professional boundary | No purchase, investment, legal, tax, engineering, or lending conclusion is implied. | NOT TESTED | |

## Save / reopen

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| SR-01 | Save current case | Save succeeds only with required case name and property identifier. | NOT TESTED | |
| SR-02 | Leave and reopen | Same-browser case can be found and loaded without re-entering core inputs. | NOT TESTED | |
| SR-03 | Inspect reopened case | Active property, selected price basis, and intended compact evidence are coherent. | NOT TESTED | |
| SR-04 | Persistence disclosure | Browser-local, maximum-case, and non-team limitations are understandable. | NOT TESTED | |
| SR-05 | Clear current case | Current context clears without silently deleting all saved cases. | NOT TESTED | |

## Compare

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| C-01 | Select two eligible cases | Only cases with required title, identity, and positive price can be compared. | NOT TESTED | |
| C-02 | Compare cases | Each column/row remains tied to the correct property. | NOT TESTED | |
| C-03 | Inspect missing data | Missing evidence is explicit and does not create a favorable rank. | NOT TESTED | |
| C-04 | Interpret ranking | Ranking/summary is bounded and not a purchase recommendation. | NOT TESTED | |
| C-05 | Add a third case | Maximum supported count is enforced without losing selected cases. | NOT TESTED | |

## Report

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| RP-01 | Open/download current report | Available report or print action works using the advertised format. | NOT TESTED | |
| RP-02 | Inspect property identity | Report names the correct active property and does not mix cases. | NOT TESTED | |
| RP-03 | Inspect evidence semantics | Known, estimated, unavailable, and unknown information are distinguishable. | NOT TESTED | |
| RP-04 | Inspect sources and dates | Material sources, freshness/date, assumptions, and limitations are understandable. | NOT TESTED | |
| RP-05 | Print comparison | Browser print produces a readable comparison and conservative notice. | NOT TESTED | |
| RP-06 | Client suitability | Operator can identify what is safe to share and what requires verification. | NOT TESTED | |

## Navigation

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| N-01 | Move across journey steps | Inputs and active-property context remain coherent. | NOT TESTED | |
| N-02 | Browser back | No unexpected property switch or silent loss of committed context. | NOT TESTED | |
| N-03 | Browser forward | Restored screen corresponds to the visible active context. | NOT TESTED | |
| N-04 | Refresh | Any lost transient state is explicit and recoverable through saved cases. | NOT TESTED | |
| N-05 | Leave and reopen | Return path is discoverable without a deep link supplied by the operator. | NOT TESTED | |

## Mobile — 390px viewport

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| M-01 | Open property entry | Primary fields and submit action are reachable with ordinary touch/click behavior. | NOT TESTED | |
| M-02 | Use journey navigation | All primary steps are reachable; current step is understandable. | NOT TESTED | |
| M-03 | Review results | Primary content does not require horizontal page scrolling; dense tables disclose their own horizontal scroll. | NOT TESTED | |
| M-04 | Save/reopen/compare | Primary actions are visible and operable without overlap or clipped controls. | NOT TESTED | |
| M-05 | Open report | Report content is readable or clearly directs the user to an appropriate print/export flow. | NOT TESTED | |
| M-06 | Keyboard/focus spot check | Focus is visible; labels and status messages remain usable. | NOT TESTED | |

## Failure recovery

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| FR-01 | One provider times out/errors | Failure is local; unrelated completed modules remain usable. | NOT TESTED | |
| FR-02 | Retry an eligible failure | Retry does not duplicate or attach results to the wrong property. | NOT TESTED | |
| FR-03 | No data response | No fabricated number, zero, “safe,” or “low risk” state appears. | NOT TESTED | |
| FR-04 | Partial evidence | Available evidence remains visible with missing sources named. | NOT TESTED | |
| FR-05 | Recover through reopen | Saved context can restore the case without concealing unavailable evidence. | NOT TESTED | |

Do not induce a real production outage. Use an approved staging/control seam or mark the item `NOT TESTED`.

## Professional language

| ID | Check | Expected invariant | Status | Evidence notes |
| --- | --- | --- | --- | --- |
| PL-01 | Review labels | Terms are understandable to a broker without internal product vocabulary. | NOT TESTED | |
| PL-02 | Review claims | No unsupported “official,” “verified,” “complete,” “safe,” or “recommended” claim. | NOT TESTED | |
| PL-03 | Review units | TWD/萬元, 坪, percentages, periods, distance, and time are explicit. | NOT TESTED | |
| PL-04 | Review unknowns | Unknown, unavailable, partial, stale, and not assessed are not conflated. | NOT TESTED | |
| PL-05 | Review advice boundaries | Formal valuation/legal/tax/engineering/lending disclaimers are proportionate and visible. | NOT TESTED | |
| PL-06 | Review client output | Output supports explanation and next verification, not visual appeal alone. | NOT TESTED | |

## Final gate summary

| Gate | Result | Evidence / unresolved issue |
| --- | --- | --- |
| Entry | PASS / PARTIAL / FAIL / NOT TESTED | |
| Property integrity | PASS / PARTIAL / FAIL / NOT TESTED | |
| Market & price | PASS / PARTIAL / FAIL / NOT TESTED | |
| Location & commute | PASS / PARTIAL / FAIL / NOT TESTED | |
| Risk | PASS / PARTIAL / FAIL / NOT TESTED | |
| Finance | PASS / PARTIAL / FAIL / NOT TESTED | |
| Decision | PASS / PARTIAL / FAIL / NOT TESTED | |
| Save/reopen | PASS / PARTIAL / FAIL / NOT TESTED | |
| Compare | PASS / PARTIAL / FAIL / NOT TESTED | |
| Report | PASS / PARTIAL / FAIL / NOT TESTED | |
| Navigation | PASS / PARTIAL / FAIL / NOT TESTED | |
| Mobile | PASS / PARTIAL / FAIL / NOT TESTED | |
| Failure recovery | PASS / PARTIAL / FAIL / NOT TESTED | |
| Professional language | PASS / PARTIAL / FAIL / NOT TESTED | |

### Release rule

- Any unresolved wrong-property carryover, unknown/unavailable shown as safe or zero, confidential-data exposure, or fabricated successful evidence makes the result `NO-GO`.
- Any core section with `FAIL` makes the result `NO-GO` until fixed and rerun.
- A core section with `PARTIAL` or `NOT TESTED` permits at most `LIMITED PILOT`, with the exact supported cases and facilitator contingency documented.
- `COMMERCIAL MVP PILOT READY` requires all core sections to pass and the behavioral pilot gates in the broker pilot spec to pass.
- `COMMERCIAL BETA CANDIDATE` cannot be awarded from this checklist or a single-session pilot; it requires repeated-use evidence.

## Operator sign-off

| Field | Value |
| --- | --- |
| Decision | |
| Supported cohort/cases | |
| Known limitations disclosed | |
| Critical failures | |
| Follow-up owner | |
| Rerun required after | |
| Operator signature/initials | |
| Reviewer signature/initials | |
