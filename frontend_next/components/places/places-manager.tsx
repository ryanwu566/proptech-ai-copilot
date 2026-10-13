"use client";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState, type FormEvent } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { browserStorage, CATEGORIES, createPlacesStore, deletePlace, MAX_PLACES, MODES, movePlace, updatePlace, type MyPlace } from "@/lib/my-places";
import type { placesCopy } from "@/lib/my-places-copy";
import styles from "./places.module.css";

export function PlacesManager({ catalogue }: { catalogue: typeof placesCopy }) {
  const { locale, formatNumber } = useExperienceLocale(); const c = catalogue[locale];
  const store = useMemo(() => createPlacesStore(browserStorage()), []);
  const [places, setPlaces] = useState<MyPlace[]>([]); const [ready, setReady] = useState(false);
  const [error, setError] = useState(false); const [message, setMessage] = useState("");
  const [editing, setEditing] = useState<MyPlace | "new" | null>(null);
  const [removing, setRemoving] = useState<string | null>(null);
  const labelInput = useRef<HTMLInputElement>(null);
  useEffect(() => {
    const load = () => { const data = store.read(); setPlaces(data.places); setError(data.error); setReady(true); };
    load(); window.addEventListener("storage", load); return () => window.removeEventListener("storage", load);
  }, [store]);
  useEffect(() => { if (editing) labelInput.current?.focus(); }, [editing]);
  function save(next: MyPlace[], feedback: string) {
    if (!store.save(next)) { setError(true); return false; }
    setPlaces(next); setMessage(feedback); return true;
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const data = new FormData(event.currentTarget); const now = new Date().toISOString();
    const values = { label: String(data.get("label") ?? ""), address: String(data.get("address") ?? ""), category: data.get("category") as MyPlace["category"], transportMode: data.get("mode") as MyPlace["transportMode"], weeklyTrips: Number(data.get("trips")), priority: data.get("priority") as MyPlace["priority"] };
    if (!values.label.trim() || !values.address.trim() || !Number.isInteger(values.weeklyTrips) || values.weeklyTrips < 0 || values.weeklyTrips > 21) { setMessage("invalid"); return; }
    const current = store.read(); if (current.error) { setError(true); return; }
    // Address edits must discard optional normalization/coordinates belonging to the old destination.
    const next = editing && editing !== "new" ? updatePlace(current.places, editing.id, { ...values, ...(editing.address !== values.address ? { normalizedAddress: undefined, latitude: undefined, longitude: undefined } : {}) }, now)
      : [...current.places, { ...values, id: crypto.randomUUID(), createdAt: now, updatedAt: now }];
    if (save(next, "saved")) setEditing(null);
  }
  return <main id="main-content" className={styles.page}>
    <header className={styles.heading}><p className={styles.eyebrow}>{c.local}</p><h1>{c.places}</h1><p>{c.intro}</p><p className={styles.helper}>{c.privacy}</p>
      <div className={styles.actions}><button className={`${styles.button} ${styles.primary}`} disabled={!ready || error || places.length >= MAX_PLACES} onClick={() => { setEditing("new"); setMessage(""); }}>{c.add}</button><Link className={styles.button} href="/cases">{c.cases}</Link></div>
    </header>
    {error && <p role="alert" className={`${styles.notice} ${styles.error}`}>{c.storageError}</p>}
    <p role="status" aria-live="polite">{message && c[message as "saved" | "deleted" | "reordered" | "invalid"]}</p>
    {editing && <form className={styles.form} onSubmit={submit} key={editing === "new" ? "new" : editing.id}>
      <h2>{editing === "new" ? c.add : c.edit}</h2><div className={styles.fields}>
        <label className={styles.field}>{c.label}<input ref={labelInput} name="label" maxLength={100} required defaultValue={editing === "new" ? "" : editing.label} /></label>
        <label className={styles.field}>{c.address}<input name="address" maxLength={300} required defaultValue={editing === "new" ? "" : editing.address} /></label>
        <label className={styles.field}>{c.category}<select name="category" defaultValue={editing === "new" ? "custom" : editing.category}>{CATEGORIES.map((key) => <option key={key} value={key}>{c[key]}</option>)}</select></label>
        <label className={styles.field}>{c.mode}<select name="mode" defaultValue={editing === "new" ? "transit" : editing.transportMode}>{MODES.map((key) => <option key={key} value={key}>{c[key]}</option>)}</select></label>
        <label className={styles.field}>{c.trips}<input name="trips" type="number" min={0} max={21} step={1} required aria-describedby="frequency-help" defaultValue={editing === "new" ? 5 : editing.weeklyTrips} /></label>
        <label className={styles.field}>{c.priority}<select name="priority" defaultValue={editing === "new" ? "important" : editing.priority}><option value="important">{c.important}</option><option value="secondary">{c.secondary}</option></select></label>
      </div><p id="frequency-help" className={styles.helper}>{c.frequencyHelp}</p>
      <div className={styles.actions}><button className={`${styles.button} ${styles.primary}`} type="submit" disabled={error}>{c.save}</button><button className={styles.button} type="button" onClick={() => setEditing(null)}>{c.cancel}</button></div>
    </form>}
    {!ready ? <p role="status">{c.loadingCase}</p> : places.length === 0 ? <p className={styles.notice}>{c.empty}</p> : <div className={styles.grid}>
      {places.map((place, index) => <article className={styles.card} key={place.id} aria-label={place.label} data-testid="place-card">
        <div className={styles.cardHeader}><h2>{place.label}</h2><span className={styles.badge}>{c[place.priority]}</span></div>
        <p>{place.address}</p><p className={styles.helper}>{c[place.category]} · {c[place.transportMode]} · {c.visits.replace("{{n}}", formatNumber(place.weeklyTrips))}</p>
        <div className={styles.actions}><button className={styles.button} disabled={error} onClick={() => { setEditing(place); setMessage(""); }}>{c.edit}</button>
          <button className={styles.button} disabled={error} onClick={() => setRemoving(place.id)}>{c.remove}</button>
          <button className={styles.button} disabled={error || index === 0} aria-label={`${c.up}: ${place.label}`} onClick={() => save(movePlace(store.read().places, place.id, -1), "reordered")}>{c.up}</button>
          <button className={styles.button} disabled={error || index === places.length - 1} aria-label={`${c.down}: ${place.label}`} onClick={() => save(movePlace(store.read().places, place.id, 1), "reordered")}>{c.down}</button>
        </div>
        {removing === place.id && <div className={styles.notice}><p>{c.confirmDelete}</p><div className={styles.actions}><button className={styles.button} onClick={() => { if (save(deletePlace(store.read().places, place.id), "deleted")) setRemoving(null); }}>{c.remove}</button><button className={styles.button} onClick={() => setRemoving(null)}>{c.cancel}</button></div></div>}
      </article>)}
    </div>}
    {places.length >= MAX_PLACES && <p className={styles.helper}>{c.limit}</p>}
  </main>;
}
