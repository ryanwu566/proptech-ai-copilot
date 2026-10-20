# Ambient Scene System v1

One decorative background framework behind the major product pages. It is presentation only. It reads no case data, makes no
requests and changes no layout, and nothing a decision needs exists only in a scene.

## Architecture

| Piece | Role |
| --- | --- |
| `frontend_next/lib/ambient/scene-model.ts` | Route → variant map, shared phase timing (`PHASE_START`), wake rhythms (`WAKE`). Pure; unit-tested in `scene-model.test.ts`. |
| `frontend_next/components/ambient/ambient-scene.tsx` | `AmbientScene`, the only controller. It owns phase timing, reduced motion, pausing (hidden tab via `visibilitychange`, scrolled away via `IntersectionObserver`), wakes and `aria-hidden`. It writes `data-phase`, `data-focus/lock/resolve`, `data-wake` and `data-paused` on its root, so the motion never re-renders React or reads layout. |
| `frontend_next/components/ambient/scenes.tsx` | Geometry only: one desktop (1600×880, anchored top-right) and one mobile (390×560) SVG artboard per variant. |
| `frontend_next/components/ambient/ambient-scene.module.css` | Placement, mask language, paint vocabulary and the motion grammar classes. |
| `frontend_next/components/ambient/ambient-scene-host.tsx` | Mounted once in `app/layout.tsx` under the global header. Picks the variant from the pathname. |
| `frontend_next/components/home-city-backdrop.tsx` | Home's scene: `AmbientScene variant="home"` with the approved Taipei photograph as its only layer. |

Stacking: hosted scenes are `position: absolute; z-index: -1; pointer-events: none` under the global header, and they scroll away with the page.
`<body>` and the workspace shell are transparent so the canvas colour comes from `<html>`. Print hides every scene.

## Motion grammar

All pages use the same grammar: **REVEAL** (0ms, layer fades in over 700ms) → **FOCUS** (700ms, primary geometry draws or fades in)
→ **LOCK** (2100ms, the anchor settles) → **RESOLVE** (3300ms, emphasis recedes to rest). After RESOLVE a scene may *wake* one relationship
at a time, as a single slow pass every 8–16s (`WAKE`). Home and Report never wake. Only opacity, transform and stroke-dashoffset animate.
Reduced motion jumps straight to RESOLVE with no transitions, animations or wakes. A hidden tab or an off-screen scene clears the timers and pauses the CSS animations.

## Variants

| Variant | Route | Idea | Wake |
| --- | --- | --- | --- |
| home | `/` | Approved 0078 (desktop) / 0076 (mobile) photograph, revealed once, one ~2% settle over 26s, then still. Mobile is an absolute background behind the heading, never in flow. | — |
| overview | `/cases/:id/overview` | Four evidence glyphs (market band, location route, risk contour, money cadence) converge on one property outline. | one connector at a time |
| market | `…/market` | Transaction dots settle into a P25–median–P75 band; one asking-price marker locks. No values. | median trace / marker halo |
| location | `…/location` | Abstract street grid, footprints, facility nodes, routes from the property. No map tiles. | one route every 8–12s |
| risk | `…/risk` | Faint hazard contours and a polygon; one amber dashed zone stays visibly unresolved, never safe-looking. No score. | contour trace / amber outline trace |
| finance | `…/finance` | Equal payment steps accumulate on a timeline with cadence ticks. Neutral palette, not a market chart. | staircase / timeline trace |
| decision | `…/decision-room` | Evidence → question → task → owner → status down the right margin, resolved stage by stage. | whole chain trace |
| compare | `/compare` | Two identical silhouettes, four shared dimensions, symmetric difference marks. No winner. | one dimension halo |
| report | `…/report` | Three page outlines in the report margin; evidence tokens settle onto citation marks. No text. | — |

Presence: Home photograph 1 (0.62 on mobile, behind the heading), core analytical scenes `--presence: 0.34`, Report 0.24.

## Validation

- `npm run test:ambient`: route map, phase order, wake bounds.
- `e2e/ambient-scene.spec.ts`: every route at 1920×1080, 1440×900, 1366×768, 1024×768, 430×932 and 390×844 checks no horizontal overflow, no
  click interception (grid hit-test), identical layout with the scene hidden, the correct artboard and no remote-capable elements. It also checks zero
  requests across reveal and wake, reduced motion, hidden-tab pause/resume (fake clock) and print.
- `e2e/home-editorial-hero.spec.ts`: updated for the shared phases and the single finite drift.
