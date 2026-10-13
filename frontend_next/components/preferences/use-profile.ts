"use client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { createProfileStore, PROFILE_EVENT, PROFILE_KEY, type ProfileRead } from "@/lib/preferences/profile";
export function usePreferenceProfile() {
  const store = useMemo(() => createProfileStore({ getItem: key => window.localStorage.getItem(key), setItem: (key, value) => window.localStorage.setItem(key, value), removeItem: key => window.localStorage.removeItem(key) }), []);
  const [read, setRead] = useState<ProfileRead | null>(null);
  const reload = useCallback(() => setRead(store.read()), [store]);
  useEffect(() => {
    reload();
    const changed = (event: StorageEvent) => { if (event.key === PROFILE_KEY || event.key === null) reload(); };
    window.addEventListener("storage", changed); window.addEventListener(PROFILE_EVENT, reload);
    return () => { window.removeEventListener("storage", changed); window.removeEventListener(PROFILE_EVENT, reload); };
  }, [reload]);
  const announce = () => window.dispatchEvent(new Event(PROFILE_EVENT));
  return { read, store, reload, announce };
}
