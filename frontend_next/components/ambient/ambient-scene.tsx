"use client";

import { useEffect, useRef, type CSSProperties, type ReactNode } from "react";
import { PHASE_START, WAKE, nextWake, wakeDelay, type AmbientVariant } from "@/lib/ambient/scene-model";
import { SCENES } from "./scenes";
import styles from "./ambient-scene.module.css";

/**
 * The one ambient background framework. It owns timing, opacity, reduced motion, pausing (hidden tab or scrolled away),
 * stacking and pointer behaviour; each variant only supplies geometry (./scenes.tsx).
 * State is written to data-* attributes on the root, so the motion never re-renders React or reads layout.
 */
export function AmbientScene({ variant, ready = true, className, children }: { variant: AmbientVariant; ready?: boolean; className?: string; children?: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const element = root.current;
    if (!element || !ready) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    const rhythm = WAKE[variant];
    const timers = new Set<number>();
    let wake = -1;
    let hidden = document.hidden;
    let offscreen = false;
    let started = false;
    let frame = 0;
    const later = (run: () => void, delay: number) => { const id = window.setTimeout(() => { timers.delete(id); run(); }, delay); timers.add(id); };
    const clear = () => { cancelAnimationFrame(frame); timers.forEach((id) => window.clearTimeout(id)); timers.clear(); };
    const enter = (phase: keyof typeof PHASE_START) => {
      element.dataset.phase = phase;
      if (phase !== "reveal") element.setAttribute(`data-${phase}`, "");
    };
    const settle = () => { for (const phase of ["reveal", "focus", "lock", "resolve"] as const) enter(phase); };
    const scheduleWake = () => {
      if (!rhythm || reduced.matches) return;
      later(() => {
        wake = nextWake(wake, rhythm.count);
        element.dataset.wake = String(wake);
        later(() => { delete element.dataset.wake; scheduleWake(); }, rhythm.hold);
      }, wakeDelay(rhythm));
    };
    const run = () => {
      clear();
      const paused = hidden || offscreen;
      element.toggleAttribute("data-paused", paused);
      if (paused) { delete element.dataset.wake; return; }
      if (started || reduced.matches) { settle(); started = true; scheduleWake(); return; }
      started = true;
      // Two frames so the initial (pre-reveal) styles are committed before the first transition.
      frame = requestAnimationFrame(() => { frame = requestAnimationFrame(() => {
        enter("reveal");
        later(() => enter("focus"), PHASE_START.focus);
        later(() => enter("lock"), PHASE_START.lock);
        later(() => { enter("resolve"); scheduleWake(); }, PHASE_START.resolve);
      }); });
    };
    const onVisibility = () => { hidden = document.hidden; run(); };
    const observer = typeof IntersectionObserver === "undefined" ? null : new IntersectionObserver(([entry]) => {
      if (offscreen === !entry.isIntersecting) return;
      offscreen = !entry.isIntersecting;
      run();
    });
    document.addEventListener("visibilitychange", onVisibility);
    reduced.addEventListener("change", run);
    observer?.observe(element);
    run();
    return () => { clear(); document.removeEventListener("visibilitychange", onVisibility); reduced.removeEventListener("change", run); observer?.disconnect(); };
  }, [variant, ready]);
  const scene = SCENES[variant];
  const hold = WAKE[variant]?.hold;
  return <div ref={root} className={[styles.scene, styles[variant], className].filter(Boolean).join(" ")} style={hold ? { "--ambient-hold": `${hold}ms` } as CSSProperties : undefined} data-ambient-scene={variant} aria-hidden="true">
    {children}
    {scene && <>
      <svg className={styles.desktop} viewBox={scene.desktop.viewBox} preserveAspectRatio={scene.desktop.align ?? "xMaxYMin slice"} focusable="false">{scene.desktop.layers}</svg>
      <svg className={styles.mobile} viewBox={scene.mobile.viewBox} preserveAspectRatio={scene.mobile.align ?? "xMidYMin meet"} focusable="false">{scene.mobile.layers}</svg>
    </>}
  </div>;
}
