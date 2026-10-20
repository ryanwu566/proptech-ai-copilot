# Ambient Scene System v1

One presentation-only background framework behind major product pages. Real editorial Taiwan photography replaces the original geometry. No case data or provider integration is used. The photograph conveys no risk status, valuation or comparison outcome.

| Piece | Role |
| --- | --- |
| `frontend_next/lib/ambient/scene-model.ts` | Existing route map, ordered reveal/focus/lock/resolve phase timing. Every wake rhythm is null. |
| `frontend_next/components/ambient/ambient-scene.tsx` | Shared controller. Cached/load-ready reveal, reduced motion, hidden-tab and offscreen pause, aria-hidden. State updates use data attributes, without motion-driven React rerenders or layout reads. |
| `frontend_next/components/ambient/scenes.tsx` | Same-origin desktop/mobile photograph descriptors. Home supplies its existing approved picture. Compare and Report reuse Overview's neutral photo. |
| `frontend_next/components/ambient/ambient-scene.module.css` | Absolute placement, masks, CSS photographic treatment, one finite settle, pause and print rules. |
| `frontend_next/components/ambient/ambient-scene-host.tsx` | Existing route-based host below the global header, keyed by variant. |
| `frontend_next/components/home-city-backdrop.tsx` | Unchanged approved 0078 desktop / 0076 mobile picture, behind Home Hero. |

Hosted scenes remain absolute at z-index -1 with pointer-events none. Home remains absolute at z-index 0 with foreground at 1. `<html>` paints the canvas, body/workspace stay transparent. No layout space is reserved for decoration; delayed or failed images leave the foreground usable.

After the photograph loads, the existing controller reveals once and progresses through focus/lock/resolve. CSS animates only opacity and the image transform. Each photograph settles over 24–32 seconds, once, then stays still. All wake rhythms are disabled. Reduced motion renders the final static photograph immediately after load with no transitions or animations. Visibility and IntersectionObserver pause the finite CSS animation; resuming does not restart it. Print hides every ambient scene.

Mobile uses a dedicated crop selected by `<picture>` at 767px, with a quieter mask than desktop. AVIF is preferred with WebP alternatives; all files are local. There are no SVG accents, canvas, video, remote decorative images or animation libraries.

Full source inventory, crop coordinates, sizes, metadata verification, screenshot locations and visual scores: [Photo Ambient Scenes v1](photo-ambient-scenes-v1.md).

Validation: `npm run test:ambient`; `npm run test:e2e:ambient` runs only bundled Chromium with one worker and zero retries. Tests cover all routes and five requested viewports, responsive asset selection, layout neutrality, control clicks, same-origin sources, failed/delayed load, finite motion, reduced motion, hidden-tab/offscreen pause and print. Existing foreground OSM maps are intercepted within the browser tests and do not reach the network.
