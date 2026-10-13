"use client";
import Link from "next/link";
import { useEffect, useMemo, useRef, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { api } from "@/lib/api";
import { createBrowserCaseRepository } from "@/lib/workspace/case-repository";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import { browserStorage, buildCommuteComparisonSummary, createPlacesStore, createRoutesStore, makeStoredRoute, propertyFingerprint, routeKey, validOrigin, type MyPlace, type PropertyOrigin, type StoredRoute } from "@/lib/my-places";
import { createExplicitRouteBatch, createExplicitRouteQuery } from "@/lib/my-places-query";
import type { placesCopy } from "@/lib/my-places-copy";
import styles from "./places.module.css";

const query = createExplicitRouteQuery(api.commuteRoute);
function originFrom(workspace: PropertyCaseWorkspace): PropertyOrigin {
  const coordinates = workspace.location.property.coordinates;
  return { caseId: workspace.caseId, identity: workspace.identity.anchor?.journey_anchor_id ?? "unconfirmed", address: workspace.location.property.normalizedAddress,
    latitude: coordinates?.latitude ?? null, longitude: coordinates?.longitude ?? null, confirmed: workspace.identity.state === "confirmed" };
}

export function CommutePlanner({ caseId, catalogue }: { caseId: string; catalogue: typeof placesCopy }) {
  const { locale, formatNumber } = useExperienceLocale(); const c = catalogue[locale];
  const repository = useMemo(() => createBrowserCaseRepository(), []);
  const placesStore = useMemo(() => createPlacesStore(browserStorage()), []);
  const routesStore = useMemo(() => createRoutesStore(browserStorage()), []);
  const [cases, setCases] = useState<PropertyCaseWorkspace[]>([]); const [ready, setReady] = useState(false);
  const [places, setPlaces] = useState<MyPlace[]>([]); const [routes, setRoutes] = useState<StoredRoute[]>([]);
  const [selected, setSelected] = useState<string[] | null>(null); const [error, setError] = useState(false);
  const [loadingKeys, setLoadingKeys] = useState<string[]>([]);
  const active = useRef(false); const mounted = useRef(false); const latestContext = useRef("");
  const workspace = cases.find((item) => item.caseId === caseId);
  const origin = workspace ? originFrom(workspace) : null;
  const included = places.filter((p) => selected === null || selected.includes(p.id));
  const context = JSON.stringify([caseId, origin && propertyFingerprint(origin), included.map((p) => origin && routeKey(origin, p)), included.map((p) => p.weeklyTrips)]);
  latestContext.current = context;
  useEffect(() => {
    mounted.current = true;
    const load = () => {
      const p = placesStore.read(); const r = routesStore.read(); const saved = repository.readDiagnostic();
      setPlaces(p.places); setRoutes(r.routes); setSelected(Object.hasOwn(r.selections, caseId) ? r.selections[caseId] : null);
      setError(p.error || r.error || ["parse_error", "invalid_storage", "storage_unavailable"].includes(saved.status));
      setCases(saved.cases); setReady(true);
    };
    load(); const unsubscribe = repository.subscribe(load);
    window.addEventListener("storage", load);
    return () => { mounted.current = false; unsubscribe(); window.removeEventListener("storage", load); };
  }, [caseId, repository, placesStore, routesStore]);
  const currentRoutes = routes.filter((r) => !loadingKeys.includes(r.key));
  const summary = origin ? buildCommuteComparisonSummary(origin, included, currentRoutes) : null;
  const facts = origin ? buildCommuteComparisonSummary(origin, places, currentRoutes).destinations : [];
  function duration(minutes: number | null) {
    if (minutes === null) return c.unknown;
    const rounded = Math.round(minutes);
    return rounded < 60 ? c.minute.replace("{{n}}", formatNumber(rounded)) : c.hours.replace("{{h}}", formatNumber(Math.floor(rounded / 60))).replace("{{m}}", formatNumber(rounded % 60));
  }
  function select(id: string, checked: boolean) {
    const ids = places.filter((p) => p.id === id ? checked : selected === null || selected.includes(p.id)).map((p) => p.id);
    if (!routesStore.select(caseId, ids)) { setError(true); return; } setSelected(ids);
  }
  async function calculate(refresh: boolean, only?: string) {
    if (active.current || !origin || !validOrigin(origin) || error) return;
    const snapshot = context;
    // Re-read local storage to avoid spending on inputs edited in another tab before this click.
    const freshPlaces = placesStore.read(); const freshRoutes = routesStore.read(); const freshCase = repository.getCase(caseId);
    if (freshPlaces.error || freshRoutes.error || !freshCase) { setError(true); return; }
    const freshOrigin = originFrom(freshCase);
    if (propertyFingerprint(freshOrigin) !== propertyFingerprint(origin)) return;
    const freshSelected = Object.hasOwn(freshRoutes.selections, caseId) ? freshRoutes.selections[caseId] : null;
    const freshIncluded = freshPlaces.places.filter((p) => freshSelected === null || freshSelected.includes(p.id));
    const freshContext = JSON.stringify([caseId, propertyFingerprint(freshOrigin), freshIncluded.map((p) => routeKey(freshOrigin, p)), freshIncluded.map((p) => p.weeklyTrips)]);
    if (freshContext !== snapshot) {
      setPlaces(freshPlaces.places); setRoutes(freshRoutes.routes); setSelected(freshSelected); setCases(repository.readDiagnostic().cases);
      return;
    }
    const targets = included.filter((p) => (!only || p.id === only) && p.weeklyTrips > 0
      && freshPlaces.places.some((next) => routeKey(origin, next) === routeKey(origin, p))
      && (refresh || buildCommuteComparisonSummary(origin, [p], freshRoutes.routes).destinations[0].status !== "AVAILABLE"));
    if (!targets.length) return;
    const batchQuery = createExplicitRouteBatch(query);
    active.current = true; setLoadingKeys(targets.map((p) => routeKey(origin, p)));
    try {
      for (const place of targets) {
        if (!mounted.current || latestContext.current !== snapshot) break;
        let route: StoredRoute;
        try { route = makeStoredRoute(origin, place, await batchQuery(origin, place)); }
        catch { route = makeStoredRoute(origin, place, { status: "unavailable", source: "none", mode: place.transportMode, duration_min: null, duration_seconds: null, distance_m: null, partial: false, fallback: false, reason_code: "provider_error", checked_at: new Date().toISOString() }); }
        if (!mounted.current) break;
        if (!routesStore.put(route)) { setError(true); break; }
        setRoutes(routesStore.read().routes); setLoadingKeys((keys) => keys.filter((key) => key !== route.key));
      }
    } finally { active.current = false; if (mounted.current) setLoadingKeys([]); }
  }
  if (!ready) return <main id="main-content" className={styles.page}><p role="status">{c.loadingCase}</p></main>;
  if (!workspace) return <main id="main-content" className={styles.page}><h1>{c.planner}</h1><p role="alert">{error ? c.storageError : c.missingCase}</p><Link className={styles.button} href="/cases">{c.cases}</Link></main>;
  return <main id="main-content" className={styles.page}>
    <header className={styles.heading}><p className={styles.eyebrow}>{c.local}</p><h1>{c.planner}</h1><p className={styles.helper}>{c.property}</p><h2>{workspace.title}</h2><p>{workspace.displayAddress}</p>
      <div className={styles.actions}><Link className={styles.button} href="/places">{c.manage}</Link><Link className={styles.button} href={`/cases/${encodeURIComponent(caseId)}/overview`}>{c.overview}</Link><Link className={styles.button} href="/cases">{c.cases}</Link></div>
      {cases.length > 1 && <nav aria-label={c.switchProperty} className={styles.actions}>{cases.map((item) => <Link key={item.caseId} className={styles.button} href={`/cases/${encodeURIComponent(item.caseId)}/commute-planner`} aria-current={item.caseId === caseId ? "page" : undefined}>{item.title}</Link>)}</nav>}
    </header>
    {error && <p role="alert" className={`${styles.notice} ${styles.error}`}>{c.storageError}</p>}
    {!origin || !validOrigin(origin) ? <p className={`${styles.notice} ${styles.error}`}>{c.originBlocked}</p> : null}
    <p className={styles.helper}>{c.explicit}</p>
    <div className={styles.actions}><button className={`${styles.button} ${styles.primary}`} disabled={error || loadingKeys.length > 0 || !origin || !validOrigin(origin) || !included.some((p) => p.weeklyTrips > 0)} onClick={() => calculate(false)}>{c.calculate}</button>
      <button className={styles.button} disabled={error || loadingKeys.length > 0 || !origin || !validOrigin(origin) || !included.some((p) => p.weeklyTrips > 0)} onClick={() => calculate(true)}>{c.refresh}</button></div>
    {summary && <section className={styles.summary} aria-label={c.weekly} aria-live="polite" data-testid="weekly-summary"><h2>{c.weekly}</h2><p className={styles.time}>{duration(summary.knownWeeklyMinutes)}</p>
      <p>{c.knownCount}: {formatNumber(summary.knownDestinationsCount)} / {formatNumber(included.length)} · {c.unknownCount}: {formatNumber(summary.unknownPlaceIds.length)}</p>
      {summary.unknownPlaceIds.length > 0 && <><p>{c.unknownHelp}</p><ul>{included.filter((p) => summary.unknownPlaceIds.includes(p.id)).map((p) => <li key={p.id}>{p.label}</li>)}</ul></>}
      {included.length === 0 && <p>{c.noSelected}</p>}
    </section>}
    {places.length === 0 && <p className={styles.notice}>{c.empty}</p>}
    <div className={styles.grid}>{facts.map((fact) => {
      const p = fact.place; const r = fact.route;
      const loading = origin && loadingKeys.includes(routeKey(origin, p)); const status = loading ? "LOADING" : fact.status;
      const statusText = { NOT_CHECKED: c.notChecked, LOADING: c.loading, AVAILABLE: c.available, UNAVAILABLE: c.unavailable, STALE: c.stale }[status];
      return <article key={p.id} className={styles.card} aria-label={p.label} data-testid="commute-destination" data-status={status} aria-busy={Boolean(loading)}>
        <div className={styles.cardHeader}><div><h2>{p.label}</h2><p className={styles.helper}>{p.address}</p></div><span role="status" className={`${styles.badge} ${status === "STALE" || status === "UNAVAILABLE" ? styles.stale : ""}`}>{statusText}</span></div>
        <p className={styles.helper}>{c[p.category]} · {c[p.priority]} · {c[p.transportMode]} · {c.visits.replace("{{n}}", formatNumber(p.weeklyTrips))}</p>
        <label className={styles.selection}><input type="checkbox" checked={selected === null || selected.includes(p.id)} disabled={error || loadingKeys.length > 0} onChange={(event) => select(p.id, event.target.checked)} />{c.select}</label>
        {status === "STALE" && <div className={styles.previous}><p>{c.staleHelp}</p><p>{c.previous}: {r?.propertyAddress} → {r?.destinationAddress} · {r && c[r.requestedMode]}</p></div>}
        <dl className={styles.facts}>
          <div><dt>{c.duration}</dt><dd>{duration(status === "AVAILABLE" ? r?.durationMinutes ?? null : null)}</dd></div>
          <div><dt>{c.distance}</dt><dd>{status === "AVAILABLE" && r?.distanceM !== null && r?.distanceM !== undefined ? c.km.replace("{{n}}", formatNumber(Math.round(r.distanceM / 100) / 10)) : c.unknown}</dd></div>
          <div className={styles.wide}><dt>{c.individual}</dt><dd>{duration(loading ? null : fact.weeklyMinutes)}</dd></div>
          <div className={styles.wide}><dt>{c.source}</dt><dd>{r?.source === "google_routes" ? "Google Routes" : r?.source === "mock" ? c.mock : c.none}</dd></div>
          <div className={styles.wide}><dt>{c.checked}</dt><dd>{r?.checkedAt ? <time dateTime={r.checkedAt}>{new Intl.DateTimeFormat(locale, { dateStyle: "medium", timeStyle: "short" }).format(new Date(r.checkedAt))}</time> : c.unknown}</dd></div>
        </dl>
        <details><summary className={styles.selection}>{c.limitations}</summary><p className={styles.helper}>{c.reference}</p>
          {r && r.reasonCode !== "success" && <p>{c[r.reasonCode]}</p>}{r?.partial && <p>{c.partial}</p>}{(r?.fallback || r?.source === "mock") && <p>{c.fallback}</p>}{r && r.mode !== r.requestedMode && <p>{c.mismatch} {c.mode}: {c[r.mode]}</p>}
        </details>
        {p.weeklyTrips === 0 && <p className={styles.helper}>{c.zero}</p>}
        <button className={styles.button} disabled={error || loadingKeys.length > 0 || !origin || !validOrigin(origin) || p.weeklyTrips === 0 || selected !== null && !selected.includes(p.id)} onClick={() => calculate(true, p.id)}>{r ? c.refreshOne : c.calculateOne}</button>
      </article>;
    })}</div>
  </main>;
}
