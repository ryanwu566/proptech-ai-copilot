# Navigation & Discoverability v1

## Intent and boundaries
Make existing product capabilities discoverable and connect analysis, scenarios,
decisions, comparison and reporting. Preserve anonymous exploration, four locales,
Auth, local case diagnostics and all evidence semantics. No migration, Admin,
billing, provider changes, automatic analysis or fictional Copilot entry.

Authoritative base: fetched origin/main and remote refs/heads/main both resolve
to 59631992e03c05ff01e67fb691710c738fcc6d1b. The supplied linked worktree is clean
on feat/navigation-discoverability-v1 at that revision.

## Current IA audit
| Area | Existing entry | Gap / disposition |
| --- | --- | --- |
| Home | / | Keep address workflow and local recent cases; add capability orientation |
| Property workflow | Home finder button | Give it a stable workflow deep link |
| Market / Valuation / Location / Risk | Home Methods buttons, ?tool= | Group as analysis; retain existing tool IDs and labels |
| Finance / ownership costs | Case rail | Also expose globally with the explicit case chooser |
| Scenario Lab | Case rail, /cases/:id/scenarios | Discover globally with explicit case chooser |
| Decision Room | Case rail, /cases/:id/decision-room | Same chooser; connect from scenarios |
| Compare | Cases page and case rail | Persistent global entry; preserve cases query |
| Report | Case rail and saved row | Chooser globally; handoff from comparison |
| Preferences | Global link | Keep in personal group |
| My Places | Global link | Keep in personal group |
| Commute | Case rail | Discover globally with chooser and case context |
| Saved Cases | /cases | Persistent global entry; local storage limitations explicit |
| Account | /account | Preserve visible global entry and existing Auth behavior |
| Future Copilot | Not implemented | Omit actionable entry; reserve navigation model extension seam |
| Tax / Credit / Identity / Demo / Accessibility | Methods | Retain under supporting tools, including demo context |
| Advanced planning | Case rail | Retain existing availability semantics |

## Design
Use a compact static route model, a native disclosure containing grouped product
links and a labeled search field. The disclosure works with keyboard, touch and
Escape, closes when focus leaves, restores focus on Escape, and never traps focus.
Home, Saved Cases and Compare remain outside it. Use the same structure on desktop
and mobile; responsive wrapping prevents overflow. Existing Methods selectors and
method button labels remain compatible with the regression pack. Reuse canonical
lightweight entry catalogues for Preferences, My Places, Commute, Scenario Lab and
Account; never import the complete profile editor or operational room catalogue
just to display a navigation label.

Case capabilities resolve against the current case route when available; otherwise
they link to /cases?next=<allowlisted section>. The chooser shows actual local cases
and carries the requested section into each case link. It never selects an arbitrary
case or substitutes another ID. Empty/corrupt/blocked stores retain diagnostics and
offer a concrete property-workflow entry. Home continues to use actual updatedAt
ordering for recent saved cases, without adding navigation history storage.

A small case workflow component connects analysis → scenarios → Decision Room →
Compare → Report, including on standalone case output routes. Links retain case ID;
comparison preserves the existing selection contract. Handoff copy describes review
and saved snapshots, never analytical completion or approval. Shared navigation
imports entry copy only, never scenario/decision/provider implementation catalogues.

## Acceptance
Unit tests cover route inventory, search, case encoding, safe chooser destinations
and next steps. Browser tests cover 390/430/1024/1440 widths, four locales, keyboard
disclosure/skip links/focus, Saved Cases, direct links and history, local empty states,
workflow handoffs and absence of expensive provider requests. Run Chromium and Chrome
with retries=0, the commercial regression pack, typecheck, lint, ordinary production
build and unchanged route/global budgets. Review UX and accessibility before the
single requested local commit; do not push, merge or deploy.
