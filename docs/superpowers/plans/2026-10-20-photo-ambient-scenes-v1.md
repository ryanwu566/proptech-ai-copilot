# Photo Ambient Scenes v1 Implementation Plan

**Goal:** Replace decorative diagrams with restrained real Taiwan photographs on all existing ambient routes.

**Architecture:** Keep the route host and shared phase/visibility/reduced-motion controller. Replace geometry with a responsive same-origin picture; disable all wake rhythms and use one finite photographic settle. Home retains its approved files and placement.

**Tech stack:** Existing Next/React, CSS masks/transforms, Pillow for read-only source cropping and metadata-free AVIF/WebP export, bundled Playwright Chromium.

**Spec:** User's PHOTO AMBIENT SCENE SYSTEM v1 implementation brief in this session.

## Constraints

No source archive mutations, originals in git, provider calls, backend changes, business logic changes, external image hosts, personal Chrome, push, or full browser matrix. Focused browser runs use workers=1 and retries=0.

## Review focus

Image failure must leave usable foreground; cached load must reveal; mobile must select a distinct crop; visibility pause must freeze finite motion; Risk/Compare photographs convey no data status or winner.

## Tasks

- [x] Inventory all stills and approved Home derivatives; inspect contact sheets; record selected/rejected sources, source dimensions and crop coordinates before implementation.
- [x] Update route/model and browser tests for real responsive pictures, no wake, static reduced motion, source locality, layout neutrality and pause/resume; observe a meaningful failure first.
- [x] Stage 1: export sanitized Market/Location/Risk desktop/mobile derivatives. Replace SVG layer rendering with pictures and restrained CSS; preserve Home. Inspect desktop/mobile screenshots.
- [x] Stage 2: export Overview/Finance/Decision/Report/Compare derivatives. Use shared neutral Compare photo. Inspect every page at 1440×900 and 390×844, spot-check 1920×1080, 1024×768, 430×932.
- [x] Verify metadata and source hashes; run focused unit/browser checks, typecheck/lint; document asset sizes, scores, screenshot locations, results and limitations.
- [x] Review diff, create local commit only, verify clean git status, report SHA (delivery step; command evidence retained in session).

## Execution ledger

- Initial branch is `feat/photo-ambient-scenes-v1`, clean, already a linked worktree. No worktree creation needed.
- User explicitly directs autonomous implementation without selection approval. Existing architecture is retained; no design approval gate added.
- 13 DJI folders found; 24 JPG stills and 121 MP4 videos. Still contact sheet/inventory in ignored `.local/photo-ambient/`; no video extraction planned.
- No-wake assertion observed RED, then GREEN after setting every rhythm to null. Asset metadata/budget test observed RED on Overview WebP weight; re-encoded to q70 desktop/q78 phone, then GREEN. No source image edits.
- First-stage five-size screenshots confirmed selection; initial phone mask too faint, extended its fade while preserving stronger foreground. Second-stage Report/Compare reuse Overview derivatives to avoid duplicate files and case-specific symbolism.
- Final: 7 unit/asset checks and 23 bundled Chromium checks passed; production E2E build/typecheck passed; lint 0 errors/23 existing warnings. 45 screenshots inspected at primary sizes plus spot sheets. All 30 derivative files metadata-free; source hashes unchanged.
- Independent read-only review found no blocking issues. Added monotonic animation-time checks across hidden/offscreen resume, verified in focused rerun and final combined run.
- Ruling: existing foreground OSM maps are mocked by browser routes rather than changed; ambient-only network assertions remain same-origin and zero provider traffic. Basemap/provider behavior is outside this visual feature.
- Ruling: final assets stay immutable during validation. A combined browser run overlapping re-encoding failed one load; stable assets passed focused and final 23/23 validation.
