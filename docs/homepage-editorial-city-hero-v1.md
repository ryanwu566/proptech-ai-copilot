# Home editorial Taipei city hero v1

Starting revision: `b97f0951a620a2b2ec91117f285ea64f8fc3e7bc` (`origin/main` after fetch).

## Ownership and selection

This is user-owned local DJI photography, used at the user's request. No external stock asset, generated image, government endorsement, developer sponsorship or Taipei 101 affiliation is claimed. No third-party stock license or attribution condition applies to the selected local source; this document preserves its ownership and provenance.

Selected source: `C:\拿來儲藏的\dji\1106敦化南路飛行\DJI_20251106131210_0071_D.JPG` (4032 × 2268).

Source SHA-256: `5560f33e15413d277332519ea29b7acde6358aac2b9c59f11114b8320438b515`.

Exactly three groups and six representative candidates were inspected. Source SHA-256 values were compared before and after reading/extraction. All six original hashes matched. No original was modified, moved, renamed, recompressed or given new metadata.

- Dunhua 0071: selected for daylight, an ordered tree-lined avenue, recognizable Taipei urban density and ordinary building materials, without a dominant landmark or advertised property.
- Dunhua 0079: rejected for foreground obstruction and ground-level clutter.
- Daan 0125: rejected for panorama distortion and an expansive scenic composition.
- Daan 0115 at 15 s: rejected because construction towers dominate despite Taipei 101 being visible.
- Zhishan 0100 at 15 s: rejected because direct sunset glare and river scenery read as travel imagery.
- Zhishan 0108 at 5 s: rejected because sky dominates and urban context is missing.

Candidate JPEGs, contact sheet and hash manifests are retained only in `C:\Projects\proptech-homepage-hero-assets-working`. The archive originals are never shipped.

## Published derivatives

| Asset | Dimensions | Size | Source crop (left, top, right, bottom) |
| --- | --- | --- | --- |
| `frontend_next/public/images/home/taipei-editorial-desktop.webp` | 1800 × 1050 | 315,354 bytes (308 KiB) | 280, 80, 3880, 2180 |
| `frontend_next/public/images/home/taipei-editorial-compact.webp` | 960 × 840 | 183,308 bytes (179 KiB) | 1400, 400, 3320, 2080 |

Both derivatives were resized with Lanczos, saturation reduced to 90% and contrast to 98%, then encoded as WebP. Metadata, including EXIF/GPS, was not copied. No objects, sky, buildings or text were synthesized or removed. A CSS mask fades the image left and around its edges into the existing canvas color.

## Integration and validation

Only modern Home receives the decorative layer. Navigation, typography, foreground spacing, the 780px form limit, input width, CTA and existing form handlers are retained. The photography is absolutely positioned behind the content and does not participate in layout. It cannot intercept input or keyboard focus.

Below 1200px the picture uses the independent compact crop. Below 640px the photography is hidden so the headline, address and CTA keep the small-screen space. The hidden lazy image is not required for the mobile experience. All assets are local public files; `next/image` is unoptimized here to avoid introducing a runtime image processing request.

The image alone fades in once for 720ms after loading, with no scaling or loop. Foreground content is immediately available. Reduced motion disables the reveal and makes the image static immediately; failed images remain transparent. The image has empty alternative text inside an `aria-hidden` layer.

Focused browser coverage: six requested viewport sizes; decorative semantics; preserved form width; finite reveal; reduced motion; delayed image with unchanged form geometry; failed image with keyboard start; no provider requests; same-origin assets without a runtime image service. Before/After screenshots and exact foreground geometry/style comparisons are kept under the working folder's `validation` directory.

Visual scoring and final validation results are recorded in the local validation report before commit. These are implementation judgments, not user-research measurements. No push or deployment is part of this wave.

## Final local results

- Production E2E build and its TypeScript check: passed.
- Focused ESLint on both changed product TypeScript files: passed without errors or warnings.
- `node e2e/run-e2e.cjs e2e/home-editorial-city-hero.spec.ts --project=chromium --workers=1 --retries=0`: 11 passed; bundled Chromium, headless.
- All six requested viewport sizes passed without horizontal overflow. Form width remains 780px on desktop and fills the available width on mobile.
- Exact Before/After comparisons of input, form, CTA, headline and navigation geometry plus input/CTA/headline typography and colors passed at every requested size.
- Delayed loading leaves typing available and causes no form shift. Reduced motion is static even while loading. Failed photography leaves keyboard case creation usable, with zero provider requests.
- No external image origin or runtime image processing endpoint was requested.
- Six source originals were hash-verified unchanged after candidate reads; the selected source was verified again after final validation. Published derivatives contain no EXIF/GPS or ICC payload.
- Final After screenshots were captured from the production build; desktop, laptop and mobile Before/After comparisons are available in the local working folder.

| Visual criterion | Score / 10 |
| --- | --- |
| Premium | 8.5 |
| Enterprise | 9 |
| PropTech relevance | 9 |
| Taiwan identity | 9 |
| UI integration | 9.5 |
| Risk of looking like a property ad (lower is better) | 2 |

These are visual implementation judgments, not user-research results. Both required gates pass: UI integration >= 9 and property-ad risk <= 4.

Local screenshot paths: `C:\Projects\proptech-homepage-hero-assets-working\validation\after\home-1920x1080.png`, `home-1366x768.png`, and `home-390x844.png`. Corresponding `comparison-1920x1080.png`, `comparison-1366x768.png`, and `comparison-390x844.png` are in the `validation` directory. All six Before and After captures are retained.

Limitations: photography is intentionally absent below 640px; no new physical-device or non-Chromium browser matrix was run. The exact full comparison metrics were captured with the same local development build mode before and after; final screenshots and focused behavioral checks use the production build. Existing Home copy and behavior are preserved.
