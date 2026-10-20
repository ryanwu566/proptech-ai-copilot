"use client";

import { useCallback, useState } from "react";
import { AmbientScene } from "@/components/ambient/ambient-scene";

const DESKTOP = "/brand/home/home-hero-taipei-desktop";
const MOBILE = "/brand/home/home-hero-taipei-mobile";

/**
 * Home's ambient scene: the decorative Taipei photograph behind the start (no evidence, endorsement or listing meaning).
 * It is absolutely positioned out of flow, so the start form is usable before it loads and never shifts. AmbientScene
 * reveals it once on load, then it drifts ~2% over 26s and stays still. Derivative provenance: docs/homepage-editorial-hero-v1.md.
 */
export function HomeCityBackdrop() {
  const [loaded, setLoaded] = useState(false);
  // A cached image can finish before hydration attaches onLoad; the ref catches that case.
  const watch = useCallback((image: HTMLImageElement | null) => { if (image?.complete && image.naturalWidth) setLoaded(true); }, []);
  return <AmbientScene variant="home" ready={loaded} className="commercial-home-hero">
    <picture>
      <source media="(max-width: 767px)" type="image/avif" srcSet={`${MOBILE}-860.avif 860w`} sizes="100vw" />
      <source media="(max-width: 767px)" type="image/webp" srcSet={`${MOBILE}-860.webp 860w`} sizes="100vw" />
      <source type="image/avif" srcSet={`${DESKTOP}-1600.avif 1600w, ${DESKTOP}-2400.avif 2400w`} sizes="(max-width: 1199px) 52vw, 66vw" />
      <img ref={watch} src={`${DESKTOP}-1600.webp`} srcSet={`${DESKTOP}-1600.webp 1600w, ${DESKTOP}-2400.webp 2400w`} sizes="(max-width: 1199px) 52vw, 66vw" width={2400} height={818} alt="" decoding="async" fetchPriority="low" draggable={false} onLoad={() => setLoaded(true)} />
    </picture>
  </AmbientScene>;
}
