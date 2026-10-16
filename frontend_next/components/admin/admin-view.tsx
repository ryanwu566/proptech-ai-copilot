"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getVNextAuthClient, V_NEXT_SESSION_EXPIRED_EVENT } from "@/lib/vnext-auth-session";
import { loadAdminSection } from "@/lib/admin/client";
import { AdminReadError, type AdminErrorCode } from "@/lib/admin/transport";
import { sections, label, metricValue, scalarValue, costValue, adminTimestamp, sessionTransition, type AdminSection, type AdminSnapshot, type Cost } from "@/lib/admin/model";
import { adminCopy, type AdminCopyKey } from "@/lib/admin/copy";
import styles from "./admin-view.module.css";
import { AccountControls, QuotaControls } from './admin-controls';

type LoadState = { status: "loading" } | { status: "loaded"; data: AdminSnapshot } | { status: "failed"; code: AdminErrorCode };
type Cell = string | number | boolean | null | Cost;
type Column = { key: string; label?: AdminCopyKey; date?: boolean };
const columns: Record<Exclude<AdminSection, "overview">, Column[]> = {
  users: [{ key: "user_id" }, { key: "status" }, { key: "platform_role" }, { key: "created_at", date: true }, { key: "last_activity", date: true }, { key: "usage_requests" }],
  usage: ["capability", "provider", "requests", "provider_attempts", "admitted", "rejected", "http_429", "http_5xx", "latency_ms", "quota_consumed", "cache_hit", "cost"].map((key) => ({ key })),
  providers: [{ key: "capability" }, { key: "configuration", label: "configuration_status" }, { key: "status" }, { key: "freshness" }, { key: "checked_at", date: true }, { key: "last_success", date: true }, { key: "last_failure", date: true }, { key: "disabled" }, { key: "quota_evidence" }],
  limits: ["capability", "audience", "requests", "window_seconds", "operations", "operation_window_seconds", "concurrency", "enabled"].map((key) => ({ key })),
  operations: [{ key: "key", label: "operations" }, { key: "state", label: "status" }, { key: "value", label: "outcome" }, { key: "commit_sha", label: "release" }, { key: "source" }],
  audit: [{ key: "timestamp", date: true }, { key: "actor" }, { key: "event_type" }, { key: "target" }, { key: "reason" }, { key: "before_state" }, { key: "after_state" }, { key: "command_id" }],
};

function AdminContent({ data }: { data: AdminSnapshot }) {
  const { locale, copyFrom } = useExperienceLocale();
  const t = (key: AdminCopyKey) => copyFrom(adminCopy, key);
  const rows = data.section === "overview" ? [] : data[data.section] as Record<string, Cell>[];
  function cell(row: Record<string, Cell>, column: Column): string {
    const value = row[column.key] ?? null;
    if (column.key === "cost" && typeof value === "object" && value !== null) return costValue(value, locale);
    if (typeof value === "object") return t("unknown");
    if (['before_state','after_state'].includes(column.key) && typeof value === 'string') return value.split(' · ').map((pair) => pair.split(': ').map((part) => label(part, locale)).join(': ')).join(' · ');
    if (column.key === "disabled") return label(value ? "disabled" : "enabled", locale);
    if (column.date && typeof value === "string") return adminTimestamp(value, locale);
    return scalarValue(value, locale);
  }
  return <>
    <div className={styles.evidence}>
      <p><strong>{t("source")}:</strong> <code>{data.source}</code></p>
      <p><strong>{t("window")}:</strong> {label(data.window, locale)}</p>
      <p><strong>{t("as_of")}:</strong> <time dateTime={data.as_of}>{adminTimestamp(data.as_of, locale)}</time></p>
    </div>
    <div data-testid="admin-state" role="status" className={styles.notice}>
      <strong>{data.state === "empty" ? t("empty") : label(data.state, locale)}</strong>
      {data.reason && <p>{label(data.reason, locale)}</p>}
      {["provider_observations", "provider_cost_metrics", "anti_abuse"].includes(data.source) && <p>{t("process_local")}</p>}
    </div>
    {data.section === "overview" ? <div data-testid="admin-metrics" className={styles.metrics}>
      {data.metrics.map((metric) => <article className={styles.metric} key={metric.key}>
        <h3>{label(metric.key, locale)}</h3><p className={styles.value}>{metricValue(metric, locale)}</p>
        <p>{t("window")}: {label(metric.window, locale)}</p><p>{t("source")}: <code>{metric.source}</code> · {label(metric.state, locale)}</p>
      </article>)}
    </div> : <table data-testid="admin-table" className={`${styles.table} ${data.section === "usage" ? styles.wide : ""}`}>
      <caption className={styles.caption}>{label(data.section, locale)} · {label(data.window, locale)}</caption>
      <thead><tr>{columns[data.section].map((column) => <th key={column.key} scope="col">{label(column.label ?? column.key, locale)}</th>)}</tr></thead>
      <tbody>{rows.map((row, index) => <tr key={String(row.user_id ?? row.capability ?? row.key ?? row.timestamp ?? index)}>
        {columns[data.section as Exclude<AdminSection, "overview">].map((column) => <td key={column.key} data-label={label(column.label ?? column.key, locale)}>{cell(row, column)}</td>)}
      </tr>)}</tbody>
    </table>}
  </>;
}

export function AdminView({ section }: { section: AdminSection }) {
  const { locale, copyFrom } = useExperienceLocale();
  const t = (key: AdminCopyKey) => copyFrom(adminCopy, key);
  const [state, setState] = useState<LoadState>({ status: "loading" });
  const [revision, setRevision] = useState(0);
  const [saved, setSaved] = useState(false);
  const [cursor, setCursor] = useState<string | null>(null);
  const controllerRef = useRef<AbortController | null>(null);
  const identityRef = useRef<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    controllerRef.current = controller;
    void loadAdminSection(section, cursor, controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ status: "loaded", data });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: "failed", code: error instanceof AdminReadError ? error.code : "error" });
    });
    return () => controller.abort();
  }, [section, cursor, revision]);

  useEffect(() => {
    const revoke = () => { controllerRef.current?.abort(); setState({ status: "failed", code: "authentication" }); };
    window.addEventListener(V_NEXT_SESSION_EXPIRED_EVENT, revoke);
    const subscription = getVNextAuthClient()?.auth.onAuthStateChange((event, session) => {
      const next = sessionTransition(identityRef.current, event, session?.user.id ?? null);
      identityRef.current = next.identity;
      if (next.revoke) revoke();
    });
    return () => { window.removeEventListener(V_NEXT_SESSION_EXPIRED_EVENT, revoke); subscription?.data.subscription.unsubscribe(); };
  }, []);

  function refresh(nextCursor: string | null = null) {
    if (state.status === "loading") return;
    controllerRef.current?.abort();
    setState({ status: "loading" }); setCursor(nextCursor); setRevision((value) => value + 1);
  }
  const gated = state.status === "failed" && ["denied", "authentication", "configuration"].includes(state.code);
  return <main id="main-content" data-testid="admin-shell" className={styles.shell}>
    <header className={styles.header}>
      <div><p className={styles.eyebrow}>PROPTECH · {t("intro")}</p><h1>{t("title")}</h1><p>{t("manual")}</p></div>
      <button data-testid="admin-refresh" type="button" onClick={() => refresh()} disabled={state.status === "loading"}>{t("refresh")}</button>
    </header>
    <div className={styles.layout}>
      <nav className={styles.nav} aria-label={t("title")}>
        {sections.map((item) => <Link prefetch={false} key={item} data-testid={`admin-nav-${item}`} href={item === "overview" ? "/admin" : `/admin/${item}`} aria-current={section === item ? "page" : undefined}>{label(item, locale)}</Link>)}
      </nav>
      <section className={styles.panel} aria-labelledby="admin-section-title" aria-busy={state.status === "loading"}>
        <h2 id="admin-section-title">{label(section, locale)}</h2>
        {state.status === "loading" && <p data-testid="admin-loading" role="status">{t("loading")}</p>}
        {state.status === "failed" && <div data-testid={gated ? "admin-gate" : "admin-error"} role="alert" className={styles.notice}>
          <p>{label(state.code, locale)}</p>
          {state.code === "authentication" && <Link prefetch={false} href="/vnext/property-identity">{t("login")}</Link>}
        </div>}
        {state.status === "loaded" && <>
          {saved && <p role="status" className={styles.notice}>{t('command_saved')}</p>}
          {section === 'users' && <AccountControls onChanged={() => { setSaved(true); refresh(); }} />}
          {section === 'usage' && <QuotaControls onChanged={() => { setSaved(true); refresh(); }} />}
          <AdminContent data={state.data} />
          {(section === "users" || section === "audit") && <div className={styles.pagination}>
            {cursor && <button type="button" onClick={() => refresh()}>{t("first")}</button>}
            {state.data.next_cursor && state.data.next_cursor !== cursor && <button type="button" onClick={() => refresh(state.data.next_cursor)}>{t("next")}</button>}
          </div>}
        </>}
      </section>
    </div>
  </main>;
}
