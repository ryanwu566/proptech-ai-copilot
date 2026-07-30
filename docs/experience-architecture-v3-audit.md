# Experience Architecture v3 Phase 1 Audit

## 1. Executive Summary

This is a static repository audit for the Experience Architecture v3 Phase 1
scope. It does not claim browser, assistive-technology, production, or voice
provider validation.

The current product already has a useful decision spine: Property Finder,
location and market context, valuation and affordability, then a viewing
decision and case workspace. The same capability is exposed through several
surfaces at once: the homepage, the left navigation, the guided journey, the
expert-tools disclosure, the immersive workspace, and the case route. That
gives experienced users flexibility, but creates competing primary actions and
high first-screen density for a new user.

The repository has a five-step guided journey and native disclosure primitives
that can support v3 without a new wizard framework. The current layout is
Traditional Chinese (`zh-Hant`) with English product names mixed into copy;
no locale switcher, translation resource layer, or locale-aware route was
found in the inspected frontend paths. Read-aloud and voice input are not
implemented as product capabilities.

**Release decision: NO_GO for the v3 experience release.** The architecture
and contracts are ready for phased implementation, but the experience changes,
locale coverage, voice safety review, and browser/production acceptance work
remain pending. This audit intentionally makes no UI or business-logic change.

## 2. Current Route and Page Map

| Route | Entry | Current role | Static evidence |
| --- | --- | --- | --- |
| `/` | `frontend_next/app/page.tsx`, `Home` | Stateful homepage shell, guided journey, dashboard and tool views | `AppShell`, `GuidedPropertyJourney`, `renderPage` |
| `/cases/[caseId]` | `frontend_next/app/cases/[caseId]/page.tsx` | Direct saved-case command center route | `PropertyCaseCommandCenterPage` |

Shared shell and navigation:

- `frontend_next/components/app-shell.tsx`: desktop rail, mobile menu,
  topbar, onboarding tour, and content width.
- `frontend_next/components/sidebar.tsx`: direct navigation for map, terrain,
  valuation, tax, credit, market and history surfaces.
- `frontend_next/components/topbar.tsx`: page context and tour entry.
- `frontend_next/components/onboarding-tour.tsx` and
  `friendly-intro-walkthrough.tsx`: additional orientation surfaces.

Homepage and decision surfaces:

- `frontend_next/components/hero-intro.tsx`: headline, start, workspace and
  report actions plus outcome cards.
- `frontend_next/components/guided-journey/guided-property-journey.tsx`:
  five-step shell with a desktop rail and mobile disclosure.
- `frontend_next/lib/guided-journey.ts`: stable step and tool mapping.
- `frontend_next/components/guided-journey/location-market-stage.tsx`:
  location, market, terrain and commute grouping.
- `frontend_next/components/guided-journey/price-decision-stage.tsx`:
  valuation and property-search grouping.
- `frontend_next/components/guided-journey/affordability-decision-stage.tsx`:
  loan, holding-cost and tax grouping.
- `frontend_next/components/guided-journey/decision-case-stage.tsx`:
  case, comparison and decision grouping.
- `frontend_next/components/viewing-decision-panel.tsx` and
  `decision-report.tsx`: existing decision summary and report; these are
  protected boundaries for this phase.

## 3. Current Journey Map

The source-defined order is:

1. **Property**: `Property Finder` and `Property Search` establish the object
   context.
2. **Location**: `Location Insight`, `Terrain Risk`, `Commute Livability` and
   `Market Insight` establish location context.
3. **Price**: `Valuation`, official trend, comparable evidence and search
   context establish price evidence.
4. **Affordability**: `Loan`, `Holding Cost` and `TaxOracle` establish funding
   and ownership context.
5. **Decision**: `Viewing Decision`, `Property Case`, comparison and print or
   export provide the next action.

`GuidedPropertyJourney` starts at `property`, tracks visited steps in runtime
state, and renders only visited steps while hiding inactive stages. Users can
select steps directly; the source does not enforce completion of earlier
steps. `JourneyExpertTools` is closed by default and is therefore a reusable
progressive-disclosure boundary.

The dashboard still supplies a second route through the same capabilities via
`DecisionFlowEntry`, `DecisionWorkspaceSteps`, `decision-next-actions`, and
`advanced-tools`. This is the main information-architecture duplication to
resolve in v3. The case route remains a valid deep link and should not be
removed.

## 4. Interface Density Findings

- The homepage combines a high-contrast hero, a guided journey, dashboard
  entry cards, a viewing decision section, case actions, help content and an
  advanced-tools disclosure. Multiple surfaces can look primary even when the
  user has not entered a property.
- The left rail, journey stepper and in-page workflow navigation repeat the
  same destinations. They are useful for different expertise levels but need
  a single hierarchy and clearer ownership.
- `JourneyStage` gives each active stage a heading, question, description and
  tool labels before the actual tool content. This is semantically helpful but
  can become verbose on small screens.
- The existing mobile journey stepper uses native `details` and keeps inactive
  stages hidden. This is a good foundation; it should be retained while the
  amount of supporting copy is reduced.

**Finding UX-01:** make the current question and one primary action visually
dominant; move secondary tools and evidence behind a disclosed section.

## 5. Primary Action Findings

`HeroIntro` exposes start, workspace and report actions. `DecisionFlowEntry`,
`DecisionWorkspaceSteps`, stage navigation, `ViewingDecisionPanel` and the
sidebar add additional action paths. The behavior is intentionally flexible,
but a first-time user can reasonably ask which action is the correct start.

**Finding UX-02:** every view should declare one primary action target in its
contract. Secondary actions may remain visible, but must be visually and
semantically subordinate. No automatic API call should be introduced to
support this change.

## 6. Copy Density Findings

The inspected components use a mixture of Traditional Chinese and English
product labels. Repeated explanatory paragraphs, help callouts, result
disclaimers and step descriptions increase reading cost. Some source text is
also visibly affected by an existing encoding/rendering problem, so copy
quality needs a separate content pass rather than ad-hoc inline rewrites.

Recommended copy rules:

- one short question per stage;
- one next-step sentence for empty, loading and unavailable states;
- stable product and API names remain identifiable;
- legal, loan, tax, terrain and data-source caveats remain explicit;
- do not turn missing data into zero, low risk, a winner, or a purchase claim.

## 7. Visual and Chart Findings

The visual evidence layer is already componentized under
`frontend_next/components/data-visualization/` and uses:
`DataMetricCard`, `EvidenceSummary`, `EvidenceDetails`, `FreshnessIndicator`,
`TrendLineChart`, `VolumeBarChart`, `ChartEmptyState`, and
`ChartUnavailableState`.

The trend and volume charts expose SVG roles, titles and descriptions, and
use a text summary. Both use a minimum-height container that can be tall on
mobile. Empty and unavailable states exist, but v3 should hide a chart whose
dataset is not meaningful instead of presenting an empty visual block as a
result.

Valuation, market and terrain evidence must remain source-labelled and
separate. Terrain is a risk-reference surface, not a security score. Market
and valuation evidence must not be silently reused as a decision winner.

## 8. Responsive Risks

- The shell has a bounded content width, a mobile menu and `min-w-0` usage,
  which are positive foundations.
- The guided journey uses a 240px desktop rail and a collapsed mobile stepper;
  long translated labels may still wrap or push the stage below the fold.
- The immersive workspace has multi-column desktop layouts and a sticky side
  panel. It needs a mobile review for order, sticky behavior and keyboard
  reachability.
- SVG charts use fixed view boxes and minimum-height containers. Small labels,
  dense evidence tables and long source names need content-aware wrapping.

Browser viewport testing at narrow, medium and wide widths is still required.

## 9. Accessibility Risks

Existing contracts cover native buttons, `aria-current="step"`, labelled
sections, hidden inactive stages, native details/summary, chart roles and
text descriptions. These should be preserved.

Open risks for v3:

- repeated navigation landmarks and headings may create a noisy screen-reader
  outline;
- disclosure summaries and primary actions need a consistent focus order;
- status, loading and unavailable messages need live-region policy before
  translated copy is added;
- chart summaries and table alternatives need review in every target locale;
- long labels and mixed scripts need zoom and keyboard testing.

No accessibility claim in this audit substitutes for keyboard, screen-reader,
zoom, reduced-motion and contrast acceptance testing.

## 10. Multilingual Capability

`frontend_next/app/layout.tsx` declares `lang="zh-Hant"`. The inspected
frontend has mixed Traditional Chinese and English product names, but no
evidenced locale switcher, locale route segment, translation catalog, message
loader, or i18n dependency. This is a capability gap, not a reason to rewrite
business logic.

Target locale matrix:

| Locale | Navigation | Journey copy | Data/status labels | Legal and trust copy | Phase 1 status |
| --- | --- | --- | --- | --- | --- |
| `zh-TW` | source language baseline | source language baseline | source language baseline | source language baseline | audit baseline |
| `en` | not implemented | not implemented | not implemented | not implemented | planned |
| `ja` | not implemented | not implemented | not implemented | not implemented | planned |
| `ko` | not implemented | not implemented | not implemented | not implemented | planned |

API and domain enum values must remain stable (`available`, `unavailable`,
`not_started`, and equivalent backend statuses). Translate display labels,
never the values used in logic, persistence, or contracts.

## 11. Voice Read-Aloud Capability

The repository has no audited read-aloud control or speech provider. The v3
contract should start with a browser capability adapter, not a provider
commitment. It must be an explicit user action and remain unavailable when the
browser capability is absent.

Allowed output is a short, visible summary of already-rendered decision
information. It must exclude raw JSON, coordinates, addresses, provider
payloads, hidden state, tokens and URLs. There is no autoplay, background
audio, or speech triggered by route changes, API completion, or page load.

Required states are: `supported`, `unavailable`, `permission_not_required`,
`voice_missing`, `stopped`, `speaking`, `paused`, and `error`.

## 12. Voice Input Safety

Voice input is not implemented. If introduced, it must be opt-in at the point
of use, show microphone and recording state, provide an immediate stop action,
and show the transcript before any reversible action is proposed. Transcript
text must not be persisted by default and background listening is prohibited.

Safe first actions are navigation, opening a help section, selecting a
visible step, and filling a reversible in-memory field after confirmation.
Voice must not directly save or delete a case, export a report, attach
evidence, place a bid, submit a loan/tax action, or bypass a trust warning.
Those operations require an explicit visible confirmation or remain blocked.

## 13. Privacy Findings

The current app has existing runtime persistence patterns, including
`sessionStorage` for workflow and workspace context and existing case-storage
behavior. This audit adds no storage key and does not change those behaviors.

The future voice layer must not add raw audio persistence, transcript
persistence, cookies, URL query/hash state, or a third-party voice dependency
without a separate privacy and security review. Address, coordinates, station
data, provider payloads and hidden decision state must not be included in
spoken output or voice telemetry.

## 14. Proposed Experience Architecture v3

The proposed architecture keeps existing domain boundaries and changes only
presentation ownership:

1. **Property context view:** one property question and one primary entry to
   Property Finder; no analysis is auto-started.
2. **Location and evidence view:** location, market, terrain and commute in a
   single surface, with source/freshness and limitations close to each result.
3. **Price and funding view:** valuation first, followed by loan, holding cost
   and tax as clearly separate financial tools.
4. **Decision view:** existing Viewing Decision and Decision Report remain the
   integration boundary; comparison and case actions are secondary until case
   readiness is explicit.
5. **Evidence disclosure:** summaries first, details in native disclosures,
   and no chart rendered when data is empty or unavailable.
6. **Voice boundary:** read only visible safe summaries; input only safe,
   reversible, confirmed actions.
7. **Locale boundary:** translate display copy through a future resource
   layer while preserving API/domain enums and evidence values.

## 15. Recommended Implementation Phases

| Phase | Scope | Reuse | Main risks | Exit signal |
| --- | --- | --- | --- | --- |
| 2 | Homepage hierarchy and one-primary-action contracts | `GuidedPropertyJourney`, `JourneyStage`, `JourneyExpertTools` | breaking deep links or hiding needed tools | route and journey tests pass; browser flow reviewed |
| 3 | Copy and empty-state normalization | existing `*-state` components and help content | accidentally weakening caveats | copy review confirms conservative unavailable semantics |
| 4 | Evidence disclosure and responsive chart layout | data-visualization components | chart/data meaning changes | keyboard, zoom and viewport acceptance passes |
| 5 | Locale resource boundary for `zh-TW`, `en`, `ja`, `ko` | stable journey IDs and API enums | translated labels leaking into logic | locale matrix and fallback tests pass |
| 6 | Browser read-aloud for safe visible summaries | browser capability adapter | speaking sensitive/hidden data | explicit-play, stop, no-autoplay tests pass |
| 7 | Voice input for safe reversible actions | existing navigation and form handlers | destructive side effects or persistence | action allowlist and confirmation tests pass |
| 8 | Release hardening | existing release gate and frontend tests | untested real-device behavior | browser and production acceptance complete |

## 16. Acceptance Criteria

- Every primary view declares exactly one primary action target.
- Advanced tools are collapsed by default; deep links and direct navigation
  remain usable.
- Empty and unavailable datasets show conservative copy and do not render
  invented zeros, low-risk states or winner rankings.
- Terrain remains a risk-reference signal and never becomes a security score.
- Existing valuation, loan, tax, case, comparison, decision and report logic
  is not duplicated or rewritten by the experience layer.
- `zh-TW`, `en`, `ja`, and `ko` have an explicit fallback and translation
  coverage report before release.
- API/domain enum values remain stable and are not translated.
- Read aloud requires explicit play, has stop/pause/error states, and never
  autoplays or includes raw/hidden/provider data.
- Voice input is explicit, visible, reversible where allowed, non-persistent,
  and blocks or confirms dangerous actions.
- Keyboard, screen reader, zoom, reduced-motion, responsive and production
  smoke acceptance are completed. These are not completed in this audit.

## 17. Confirmed Non-Goals

- No new i18n library or voice provider in Phase 1.
- No direct UI rewrite in this audit.
- No API, database schema, PLVR, valuation, loan, tax, terrain, commute or
  decision-logic change.
- No autoplay, background microphone, raw audio storage or transcript storage.
- No address/coordinate/provider payload disclosure.
- No automatic API calls, browser persistence changes, deployment change or
  production workflow execution.

## 18. Release Decision

**NO_GO**

Reason: this commit is an audit and contract artifact only. The proposed
experience hierarchy, multilingual resources, voice safety boundary and
browser/production acceptance evidence are not yet implemented or verified.
Proceed to Phase 2 only after product ownership approves the primary-action
hierarchy and preserves the existing financial, terrain, legal, tax, commute
and decision trust boundaries.

## Audit Metadata

- Base SHA: `24f24733ea21cfc2f3992a8ef5768c91beb32dcf`
- Scope: static repository inspection only
- Browser validation: not completed
- Production validation: not completed
- External provider calls: none
- Files modified by this audit: documentation and static tests only
