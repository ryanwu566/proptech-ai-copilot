# Photo Ambient Scene System v1

Presentation-only replacement of the existing ambient illustrations. Real local still photography, no generative assets or video extraction. Existing host, route mapping, controller, accessibility and pause behavior are retained.

## Media inventory and selection (before implementation)

Read-only inventory: 13 DJI folders, 24 JPG stills, 121 MP4 files, 126 SRT files. All 24 stills and the three approved Home WebP sizes were inspected on a contact sheet; selected sources also inspected larger. The archive was not imported. Local inventory/contact sheet: `.local/photo-ambient/` (ignored).

| Page | Selected source | Source dimensions | Why it fits | Desktop concept | Mobile concept | New derivative |
| --- | --- | --- | --- | --- | --- | --- |
| Home | `DJI_20251106131528_0078_D.JPG` / `DJI_20251106131453_0076_D.JPG` | 8192×3126 / 7200×5184 | Approved editorial Taipei | Existing approved 0078 crop | Existing approved 0076 crop behind Hero | No; preserve all six files byte-for-byte |
| Market | `DJI_20251106131453_0076_D.JPG` | 7200×5184 | Dense mixed-height street blocks, no fake transaction marks | Right-hand blocks, remove sky and construction | Tight residential blocks, exclude landmark | Yes |
| Location | `DJI_20251106131210_0071_D.JPG` | 4032×2268 | Avenue, cross street and footbridge establish connectivity | Road corridor plus surrounding buildings | Avenue depth and crossing, away from left-hand text | Yes |
| Risk | `DJI_20251008112952_0062_D.JPG` | 8192×4096 | Jingmei river, urban bank and terrain edge | Crop sky and distorted panorama base, preserve river bend | River channel and urban bank | Yes |
| Overview | `DJI_20251008112930_0058_D.JPG` | 4032×2268 | Neutral mid-density urban fabric at a terrain edge | Built context, restrained hill backdrop | Neighbourhood and buildings | Yes |
| Finance / Money | `DJI_20251106131210_0071_D.JPG` | 4032×2268 | Ordered office architecture, neutral daylight | Office facades and avenue, no graphics | Quiet facade and street | Yes |
| Decision Room | `DJI_20251106131453_0076_D.JPG` | 7200×5184 | Mature city, understated authority | Quiet office-lined corridor | Restrained architectural crop | Yes |
| Report | Shared Overview derivative | 4032×2268 source | City as softened texture | Strong fade and CSS blur | Lower presence, softened texture | Reuse |
| Compare | Shared Overview derivative | 4032×2268 source | One neutral shared context for both cases | One continuous background | Same shared scene | Reuse; no competing property photographs |

## Rejected candidates

| Sources | Reason |
| --- | --- |
| 0010 (4032×2268) | Sun glare, backlit underexposure; weaker urban detail |
| 0028 / 0029 / 0030 (4032×2268) | Night lighting, blur or ground-level park; no credible Taipei analytical context |
| 0063 (3600×7090) | Narrow panorama provides no advantage over 0062 river still |
| 0070 / 0075 (8192×4096) | Panorama seams and stretched lower streets; 0071 avenue is cleaner |
| 0072 (4032×2268) | Foreground construction, oversized pink facade, prominent Taipei 101 |
| 0079 (4032×2268) | Finger obscures frame; personal capture unsuitable |
| 0080 (4032×2268) | Open riverfront skyline reads more like leisure/travel than chosen river/terrain crop |
| 0124 / 0125 (8192×4096), 0126 (3600×9024), 0127 (7200×5184) | Dramatic blue sky, panorama distortion or tilted composition; less restrained than 0071 |
| 0136 / 0137 (8192×4096), 0138 (7200×5184), 0139 (3600×8940), 0140 (8192×3136) | Glare and construction/development dominate; reads as development promotion |
| Videos / sunset folders without stills | Suitable still photographs already exist; no reason to extract video frames |

## Crop coordinates

Coordinates are `(left, top, right, bottom)` on original oriented pixels. All new desktop derivatives are 1800px wide, mobile 780px wide. No color effects are baked in; treatment belongs to CSS.

| Asset family | Desktop crop | Mobile crop |
| --- | --- | --- |
| market | 2800,1700,7000,3500 | 4700,1400,6500,3477 |
| location | 500,420,3500,2020 | 1100,500,2600,2230 |
| risk | 500,1750,5600,3700 | 2000,1500,3900,3692 |
| overview (also compare/report) | 650,700,4032,2200 | 2000,500,3500,2230 |
| finance | 0,180,2900,1600 | 250,200,1750,1930 |
| decision | 600,1100,4400,3200 | 1800,1000,3600,3077 |

Home crop provenance remains in `homepage-editorial-hero-v1.md`; its older in-flow mobile description is superseded by the absolute Hero background implementation and regression tests.

## Asset derivatives and privacy

All new files live in `frontend_next/public/brand/ambient/`. Each family contains `ambient-{family}-{desktop|mobile}.{avif|webp}`. Compare and Report reuse Overview files rather than duplicating downloads. Exact byte sizes, source/crop dimensions and full source/derivative SHA-256 values are in [the manifest](photo-ambient-asset-manifest.json).

| Family | Desktop dimensions | Desktop AVIF / WebP bytes | Mobile dimensions | Mobile AVIF / WebP bytes |
| --- | --- | --- | --- | --- |
| market | 1800×771 | 168,445 / 223,790 | 780×900 | 66,014 / 82,266 |
| location | 1800×960 | 190,455 / 235,430 | 780×900 | 100,661 / 126,504 |
| risk | 1800×688 | 208,854 / 288,370 | 780×900 | 106,082 / 142,920 |
| overview | 1800×798 | 265,839 / 300,882 | 780×900 | 117,146 / 153,530 |
| finance | 1800×881 | 143,744 / 177,692 | 780×900 | 71,670 / 89,218 |
| decision | 1800×995 | 163,404 / 210,090 | 780×900 | 57,047 / 69,514 |

24 new files total 3,759,567 bytes. Browsers select one format and one responsive crop, not all four. AVIF q62; WebP q80 except Overview desktop q70/mobile q78. Encoding used fresh RGB pixel buffers with no inherited metadata. Effects are CSS, not baked grades. Home retains its original six approved derivatives (desktop AVIF 130,652/256,707 bytes; desktop WebP 156,306/304,376; mobile AVIF/WebP 57,401/69,766). All assets meet the 300 KiB desktop / 150 KiB phone budget; the byte table avoids unit ambiguity.

Privacy verified using both Pillow on export and Sharp on final files: no EXIF (including GPS/camera serial), XMP, IPTC, ICC or orientation payload in all 30 new/existing derivatives. Selected originals were hashed before and after encoding; final source hashes still match the manifest. No originals were changed or copied into git. Approved Home files and Home CSS/component show no git diff. Original paths exist only in ignored local inventory tooling, never browser-visible copy, DOM, filenames or public metadata.

## SVG removal and motion

Removed every decorative SVG from all eight hosted variants: market dots/price bands, street grids/routes/facility nodes, hazard contours/polygons, finance staircase/ticks, overview evidence glyphs/connectors, decision spine/task shapes, compare silhouettes/difference marks, report page outlines/citations. Removed their paint/draw/trace/halo animation styles. Retained **zero ambient SVG elements**. Existing foreground data maps and icons are unchanged.

The route host and shared controller remain. Existing phase attributes still coordinate the reveal and resolved state; all `WAKE` rhythms are null. New pictures wait for successful load, including cached images, before revealing. Failed images remain invisible and do not block content.

| Page | One finite settle | Desktop / mobile opacity | Treatment |
| --- | --- | --- | --- |
| Home | Existing 26s, 1.022→1 | 1 / 0.62 | Existing approved masks and image treatment preserved |
| Market | 28s, 1.018→1, 0.3% pan | 0.32 / 0.24 | Neutral desaturation, fade behind heading/cards |
| Location | 32s, 1.02→1, 0.45% pan | 0.34 / 0.24 | Strongest photographic motion, no moving map |
| Risk | 30s, 1.018→1, 0.3% pan | 0.30 / 0.24 | Neutral environmental photograph, no safe/unsafe tint |
| Overview | 28s, 1.018→1, 0.3% pan | 0.25 / 0.24 | Neutral urban fabric |
| Finance | 24s, 1.006→1 | 0.19 / 0.13 | Low noise architecture, minimal motion |
| Decision Room | 30s, 1.008→1 | 0.16 / 0.11 | Quiet authority behind opaque action areas |
| Compare | 28s, 1.008→1 | 0.19 / 0.13 | One shared neutral scene; no case association or winner |
| Report | 24s, 1.004→1 | 0.12 / 0.08 | CSS blur 2px, extra desaturation; report sheet dominates |

Every animation runs once and ends at scale 1; no pulse, scan, particles or obvious loop. CSS masks reduce actual presence further. Reduced motion shows the final static image: no transform, transition, animation or wake. Hidden tabs and offscreen scenes freeze animation time, then resume without replay. Print hides the layer.

## Screenshot validation and scores

45 full viewport PNGs are retained at `.local/photo-ambient/screenshots/` in this worktree. Filename pattern: `{home|overview|market|location|risk|finance|decision|report|compare}-{width}x{height}.png`. Every page has 1440×900 and 390×844, plus 1920×1080, 1024×768 and 430×932. All screenshot pixel dimensions were checked. The three `spot-check-{width}x{height}.jpg` contact sheets support quick review; full PNGs remain the inspection originals.

All nine desktop/mobile primary variants were visually inspected, plus the three spot-check sheets. Initial phone masking was too faint; the final longer portrait mask retains identifiable architecture/river context behind the heading and fades before core content. Photography remains the sole ambient medium. Report intentionally has almost no visible photo on narrow screens because its opaque report sheet dominates.

Scores below are implementation self-assessment, not owner sign-off. Each row applies to both primary sizes and was checked against the spot sizes; photographs were judged as ambient layers with their intended presence, not as standalone marketing images.

| Page | Photography /10 | Enterprise credibility /10 | Relevance /10 | Foreground readability /10 | Restraint /10 |
| --- | --- | --- | --- | --- | --- |
| Home | 9 | 9 | 9 | 9 | 9 |
| Market | 9 | 9 | 9 | 10 | 9 |
| Location | 9 | 9 | 10 | 10 | 9 |
| Risk | 9 | 9 | 10 | 10 | 9 |
| Overview | 9 | 9 | 9 | 10 | 9 |
| Finance | 9 | 10 | 9 | 10 | 10 |
| Decision Room | 9 | 10 | 9 | 10 | 10 |
| Report | 9 | 10 | 9 | 10 | 10 |
| Compare | 9 | 9 | 9 | 10 | 10 |

Home regression: at 390×844 and 430×932 the photograph is absolute and overlaps the Hero heading, behind the address field/CTA. It does not become an in-flow image band below controls. All five Home size checks passed, including foreground button hit testing.

## Files changed

- `components/ambient/scenes.tsx`: photograph descriptors replacing geometry.
- `components/ambient/ambient-scene.tsx`: responsive picture and cached/load-ready reveal, existing shared controller retained.
- `components/ambient/ambient-scene.module.css`: photographic treatment, mobile masks, finite transforms, pause/reduced-motion/print styles.
- `lib/ambient/scene-model.ts` and `.test.ts`: all wakes disabled, route/phase contracts retained and tested.
- `e2e/ambient-scene.spec.ts`: route/responsive/locality/layout/click/motion/pause/failure/print coverage and screenshots.
- `e2e/home-editorial-hero.spec.ts`: explicit mobile behind-Hero regression and five screenshot sizes.
- `scripts/ambient-photo-assets.test.cjs`: metadata, byte budget, dimensions and manifest/hash verification.
- `package.json`: asset checks in `test:ambient`, focused Chromium one-worker/zero-retry command.
- `public/brand/ambient/`: 24 optimized assets listed above.
- `docs/ambient-scene-system-v1.md`, this report, asset manifest and implementation plan: architecture/provenance/validation record.

Frontend paths above are relative to `frontend_next/`. No backend, provider logic/contracts, data models, risk semantics, financial formulas, auth, billing or infrastructure files changed.

## Validation and network boundary

Build uses the existing E2E fixture environment. Browser validation uses bundled Chromium only, `--workers=1 --retries=0`, and only the two Ambient/Home specs; no production browser matrix or personal Chrome.

| Final check | Result |
| --- | --- |
| `npm run build:e2e` | PASS, production compilation/type validation/static generation |
| `npm run test:ambient` | PASS, 7/7 route, phase, no-wake, metadata, budget and manifest checks |
| `node e2e/run-e2e.cjs e2e/ambient-scene.spec.ts e2e/home-editorial-hero.spec.ts --project=chromium --workers=1 --retries=0` | PASS, 23/23 in 2.6 minutes, final immutable-asset run |
| `npm run typecheck` | PASS, exit 0 |
| `npm run lint` | PASS, exit 0; 0 errors and 23 existing unused-variable warnings, none in changed implementation files |
| `git diff --check` | PASS |
| Original source SHA-256 recheck | PASS; every selected source matches the before/after encode hash |
| Home preservation diff | PASS; six approved files, backdrop component and global CSS unchanged |
| Screenshot dimensions | PASS; 45 PNGs across all nine pages and all five requested viewports |
| Read-only independent code review | No blocking findings; suggested animation time continuity assertions were added and passed |

Browser assertions verify correct route, responsive crop, same-origin sources, no ambient SVG/video/canvas, empty alt/aria-hidden, pointer pass-through and actual navigation clicks, no horizontal overflow, identical layout with decoration removed, no movement on delayed image load, failed-image usability, single finite motion, all scenes static under reduced motion, all scenes hidden in print, hidden/offscreen freeze and continuous resume, and plain routes remaining undecorated. Home tests cover failed imagery, keyboard use and English/Japanese/Korean layouts as well as the explicit mobile background regression.

The scenes load same-origin local AVIF/WebP files only. Their controller and descriptors have no fetch, provider API, case/evidence dependency, storage writes or business logic. Existing Location/Risk foreground Leaflet basemaps are intercepted with local 204 responses, following the existing Risk test strategy; existing API calls use fixture responses. This is **zero external decorative/provider traffic**, not a claim that existing product maps have no provider integration. After initial page loading, a 40-second simulated settle/rest window generates zero requests.

During development, the first browser run caught a test serialization mistake (a Node variable was referenced inside browser evaluation); corrected by passing the expected path explicitly. A second run identified existing foreground OSM requests, which are now intercepted. The first combined run passed 22/23 while asset re-encoding overlapped a Decision image load; after assets stabilized, the Decision and strengthened pause tests passed 2/2. Final combined validation passed 23/23 with immutable assets.

Git delivery: local branch `feat/photo-ambient-scenes-v1`, one final feature commit, no push. The exact SHA and post-commit status are returned in the final handoff to avoid a self-referential commit hash inside this committed report.

## Remaining limitations

- Visual scores are a reasoned self-assessment; owner aesthetic acceptance cannot be automated.
- Photographs are shared Taiwan ambient context, not photographs of the active case or environmental evidence. No case data selects or changes them.
- Live providers were intentionally not exercised. Foreground maps/APIs were mocked in the browser checks.
- Existing lint unused-variable warnings remain outside this visual feature's scope.
- No push, deployment, merge or full production browser matrix is part of this task.
