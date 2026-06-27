"use client";
import { useEffect, useState } from "react";

export type ViewMode = "beginner" | "pro";
export const VIEW_MODE_STORAGE_KEY = "proptech.viewMode.v1";
export const VIEW_MODE_EVENT = "proptech:view-mode-change";
export const DEFAULT_VIEW_MODE: ViewMode = "beginner";

export function readViewMode(): ViewMode {
  if (typeof window === "undefined") return DEFAULT_VIEW_MODE;
  return window.localStorage.getItem(VIEW_MODE_STORAGE_KEY) === "pro" ? "pro" : DEFAULT_VIEW_MODE;
}
export function setViewMode(mode: ViewMode) {
  window.localStorage.setItem(VIEW_MODE_STORAGE_KEY, mode);
  window.dispatchEvent(new CustomEvent<ViewMode>(VIEW_MODE_EVENT, { detail: mode }));
}
export function useViewMode(): [ViewMode, (mode: ViewMode) => void] {
  const [mode, setModeState] = useState<ViewMode>(DEFAULT_VIEW_MODE);
  useEffect(() => {
    setModeState(readViewMode());
    const update = (event: Event) => setModeState((event as CustomEvent<ViewMode>).detail);
    window.addEventListener(VIEW_MODE_EVENT, update);
    return () => window.removeEventListener(VIEW_MODE_EVENT, update);
  }, []);
  return [mode, setViewMode];
}
