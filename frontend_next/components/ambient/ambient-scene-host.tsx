"use client";

import { useEffect } from "react";
import { usePathname } from "next/navigation";
import { ambientVariantForPath } from "@/lib/ambient/scene-model";
import { AmbientScene } from "./ambient-scene";
import styles from "./ambient-scene.module.css";

// The variant whose scene has already revealed in this document; null until the first one mounts.
let shownVariant: string | null = null;

/**
 * Picks the page's ambient scene from the route; keyed by variant so each page gets its own scene.
 * The first scene in a document gets the full REVEAL; in-app section changes only cross-fade briefly,
 * so moving through one case never replays the slow settle.
 */
export function AmbientSceneHost() {
  const variant = ambientVariantForPath(usePathname());
  useEffect(() => { if (variant) shownVariant = variant; }, [variant]);
  return variant ? <AmbientScene key={variant} variant={variant} continuity={shownVariant !== null && shownVariant !== variant} className={styles.hosted} /> : null;
}
