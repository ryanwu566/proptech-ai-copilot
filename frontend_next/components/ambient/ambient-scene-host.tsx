"use client";

import { usePathname } from "next/navigation";
import { ambientVariantForPath } from "@/lib/ambient/scene-model";
import { AmbientScene } from "./ambient-scene";
import styles from "./ambient-scene.module.css";

/** Picks the page's ambient scene from the route; keyed by variant so each page gets a fresh REVEAL. */
export function AmbientSceneHost() {
  const variant = ambientVariantForPath(usePathname());
  return variant ? <AmbientScene key={variant} variant={variant} className={styles.hosted} /> : null;
}
