# Homepage Editorial City Hero v1

Art direction: **Taiwan Urban Editorial**. One real DJI photograph sits behind the existing Home start
(headline, address field, CTA). The photo is decorative. It is not evidence, it implies no endorsement
or partnership (Taipei 101, Taipei City or any building shown), and it is not a listing. No product decision depends on it.

## Source selection

| Role | Source (immutable original) | Decision |
| --- | --- | --- |
| Desktop / tablet | `1106敦化南路飛行/DJI_20251106131528_0078_D.JPG` (8192×3126 panorama) | **Shipped.** Real Taipei blocks, tree-lined avenue depth, Taipei 101 as a small distant marker. |
| Mobile (<768px) | `1106敦化南路飛行/DJI_20251106131453_0076_D.JPG` (7200×5184) | **Shipped.** A crop of the avenue and the tower beats a 0078 crop on mobile: at phone width the 0078 crop puts Taipei 101 in the middle as the subject, which reads as tourism. |
| Fallback | `1008景美溪考試院飛行素材/DJI_20251008112930_0058_D.JPG` | Not used. Its hillside residential tone is more lifestyle than PropTech. |
| Launch Film only | `1008景美溪考試院飛行素材/DJI_20251008113332_0065_D.MP4` | Not shipped in Home. Use roughly 2–10s for the future Launch Film. Do not loop roughly 11–16.5s because the visible reframing shows the camera being operated. |

The originals under `C:\拿來儲藏的\dji` were opened read-only. Their SHA-256 hashes were checked before and after encoding and had not changed:

- 0078 `ec1f558178f4bd890d1a2cbb64f7843f39f356aabeec11f2c383de1cf81a85d5`
- 0076 `888c104e2f0f7e4e961f466d5105104dfbea1e16dc321678c7f647899d468bdf`
- 0058 `f68fc0799ef1ce379aa08b2b2c4ced6c1f0da990a890f24336c012e78ff1d0a3` (inspected only)

## Derivatives (`frontend_next/public/brand/home/`)

Treatment, the same for every file: Pillow `Color` 0.82 (mild desaturation that also tones down blue/green), `Contrast` 0.95,
`Brightness` 1.02, Lanczos resize. No LUT, no grade, no object removal, no generative edit. EXIF/GPS is not copied.

| File | Source | Crop (x0,y0,x1,y1 px) | Size | Encode | Bytes | SHA-256 |
| --- | --- | --- | --- | --- | --- | --- |
| `home-hero-taipei-desktop-2400.avif` | 0078 | 2300,700,6850,2250 | 2400×818 | AVIF q70 speed 2 | 256,707 | `cad2e1e7…f2cd8` |
| `home-hero-taipei-desktop-2400.webp` | 0078 | 2300,700,6850,2250 | 2400×818 | WebP q84 m6 | 304,376 | `dff52624…72993` |
| `home-hero-taipei-desktop-1600.avif` | 0078 | 2300,700,6850,2250 | 1600×545 | AVIF q70 speed 2 | 130,652 | `555d09bd…37b12` |
| `home-hero-taipei-desktop-1600.webp` | 0078 | 2300,700,6850,2250 | 1600×545 | WebP q84 m6 | 156,306 | `6b02601b…e76b2` |
| `home-hero-taipei-mobile-860.avif` | 0076 | 1800,1250,5400,3050 | 860×430 | AVIF q72 speed 2 | 57,401 | `f350f37e…ab580` |
| `home-hero-taipei-mobile-860.webp` | 0076 | 1800,1250,5400,3050 | 860×430 | WebP q86 m6 | 69,766 | `aed74542…7b17d` |

What the 0078 crop removes:
- The bottom edge sits above the open ground and blue-covered material.
- The right edge stops before the hard pink building.
- The left edge drops most of the foreground glass tower. The sliver that remains sits in the fully masked zone.
- The top edge trims excess sky.

Taipei 101 ends up in the right quarter of the frame, small and off-centre.

## Composition and behaviour

- `components/home-city-backdrop.tsx` renders a `<picture>` (mobile AVIF/WebP, desktop AVIF/WebP with `srcset`). It is `aria-hidden` with an empty `alt`, uses `fetchpriority="low"` and is out of flow, so the start UI is usable before the image arrives and never shifts.
- Desktop: the photo is anchored to the viewport's right edge, starts flush under the global header and is 66vw wide (52vw at ≤1199px). A horizontal mask fades it to nothing behind the headline and address field. A bottom mask dissolves it into the canvas. There is no vertical divider.
- Mobile: a full-bleed 2:1 band below the start actions, faded at the top and bottom. Headline, address field and CTA keep the whole first screen.
- Motion: when the image loads it reveals once (opacity over 700ms, scale 1.01→1 over 900ms) and then stays still. Nothing loops. `prefers-reduced-motion` shows the final state with no transition. Print hides the photo.
