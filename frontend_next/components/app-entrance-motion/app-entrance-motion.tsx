"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./app-entrance-motion.module.css";

/** Upper bound for removing the layer when the Web Animations API is unavailable. The CSS sequence itself is 1000ms. */
export const ENTRANCE_FALLBACK_MS = 1600;

/**
 * A once-per-document entrance layer. It is server-rendered so it is present at first paint, runs as a pure CSS
 * sequence that ends hidden even without JavaScript, and never blocks input. It lives in the root layout, which
 * client navigation never remounts, so in-app route changes cannot replay it. After hydration it unmounts as soon
 * as its own animations finish. It reads no data and waits for nothing: the application renders underneath.
 */
export function AppEntranceMotion() {
  const ref = useRef<HTMLDivElement>(null);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const layer = ref.current;
    if (!layer) return;
    let active = true;
    const finish = () => { if (active) setDone(true); };
    // The CSS already ends the layer hidden; unmounting is cleanup. Finished animations with a forwards fill are still
    // listed, so this also covers hydration after the sequence ended, and a cancelled animation removes the layer too.
    if (typeof layer.getAnimations !== "function") {
      const fallback = window.setTimeout(finish, ENTRANCE_FALLBACK_MS);
      return () => { active = false; window.clearTimeout(fallback); };
    }
    Promise.all(layer.getAnimations({ subtree: true }).map((animation) => animation.finished)).then(finish, finish);
    return () => { active = false; };
  }, []);

  if (done) return null;
  return (
    <div ref={ref} className={styles.layer} data-app-entrance="" aria-hidden="true">
      <div className={styles.stage}>
        <span className={styles.mark}>P</span>
        <span className={styles.wordmark}>PropTech Copilot</span>
        <span className={styles.trace}>
          <span className={styles.rule} />
          <span className={styles.point} />
          <span className={styles.point} />
          <span className={styles.point} />
        </span>
      </div>
    </div>
  );
}
