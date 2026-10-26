"use client";

import { useEffect, useRef, useState } from "react";
import styles from "./app-entrance-motion.module.css";

/** Upper bound for removing the layer when the Web Animations API is unavailable. The CSS sequence itself is 2600ms. */
export const ENTRANCE_FALLBACK_MS = 3400;

/** Input that means someone wants the app now; any of these fast-forwards the entrance to its end. */
const INTENT_EVENTS = ["pointerdown", "keydown", "wheel", "touchstart"] as const;

/**
 * A once-per-document entrance layer. It is server-rendered so it is present at first paint, runs as a pure CSS
 * sequence that ends hidden even without JavaScript, and never blocks input. It lives in the root layout, which
 * client navigation never remounts, so in-app route changes cannot replay it. After hydration it unmounts as soon
 * as its own animations finish, or at once on the first pointer, wheel or key press. It reads no data and waits for
 * nothing: the application renders underneath.
 *
 * The scene is a corridor of architectural frames in real CSS perspective, ending in a lit doorway. Planes are listed
 * far to near so they paint in depth order; the camera dollies forward through them and the doorway becomes the app.
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
    const skip = () => { for (const animation of layer.getAnimations({ subtree: true })) animation.finish(); };
    for (const type of INTENT_EVENTS) window.addEventListener(type, skip, { capture: true, passive: true, once: true });
    Promise.all(layer.getAnimations({ subtree: true }).map((animation) => animation.finished)).then(finish, finish);
    return () => {
      active = false;
      for (const type of INTENT_EVENTS) window.removeEventListener(type, skip, { capture: true });
    };
  }, []);

  if (done) return null;
  return (
    <div ref={ref} className={styles.layer} data-app-entrance="" aria-hidden="true">
      <div className={styles.space}>
        <span className={`${styles.plane} ${styles.doorPlane}`}><span className={styles.door} /><span className={styles.light} /></span>
        <span className={`${styles.plane} ${styles.frame4}`}><span className={styles.frame} /></span>
        <span className={`${styles.plane} ${styles.frame3}`}><span className={styles.frame} /></span>
        <span className={`${styles.plane} ${styles.frame2}`}>
          <span className={styles.frame} />
          <span className={styles.trace}>
            <span className={styles.rule} />
            <span className={styles.point} />
            <span className={styles.point} />
            <span className={styles.point} />
            <span className={styles.point} />
          </span>
        </span>
        <span className={`${styles.plane} ${styles.frame1}`}><span className={styles.frame} /></span>
        <span className={`${styles.plane} ${styles.brandPlane}`}>
          <span className={styles.brand}>
            <span className={styles.mark}>P</span>
            <span className={styles.wordmark}>PropTech Copilot</span>
          </span>
        </span>
      </div>
      <span className={styles.wash} />
    </div>
  );
}
