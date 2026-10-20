"use client";

import Image from "next/image";
import { useState } from "react";
import styles from "./home-city-backdrop.module.css";

/** Decorative, locally optimized photography; independent of the Home start flow. */
export function HomeCityBackdrop() {
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");
  return <div className={styles.art} aria-hidden="true" data-testid="home-city-backdrop">
    <picture>
      <source media="(max-width: 1199px)" srcSet="/images/home/taipei-editorial-compact.webp" type="image/webp" />
      <Image
        unoptimized
        src="/images/home/taipei-editorial-desktop.webp"
        alt=""
        width={1800}
        height={1050}
        loading="lazy"
        decoding="async"
        fetchPriority="low"
        className={styles.image}
        data-testid="home-city-image"
        data-state={state}
        onLoad={() => setState("ready")}
        onError={() => setState("failed")}
      />
    </picture>
  </div>;
}
