"use client";
import Link from "next/link";
import { useRef, useState, type FormEvent } from "react";
import { CommercialButton } from "@/components/design-system/button";
import { Message } from "@/components/design-system/message";
import { Section } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { METRICS, RISK_KEYS, emptyProfile, type PreferenceProfile, type PreferenceRule, type CommuteRule, type Priority } from "@/lib/preferences/profile";
import { preferenceCopy, type PreferenceCopyKey } from "@/lib/preferences/copy";
import { usePreferenceProfile } from "./use-profile";
import styles from "./preferences.module.css";
type DraftRule = Exclude<PreferenceRule, CommuteRule> | (Omit<CommuteRule, "max"> & { max: number | null });
type Draft = Omit<PreferenceProfile, "rules"> & { rules: DraftRule[] };
function newRule(metric: typeof METRICS[number], id: string): DraftRule {
  const base = { id, priority: "must" as const, rationale: "" };
  if (metric === "commute") return { ...base, metric, destination: "", mode: "driving", max: null };
  if (metric === "risk") return { ...base, metric, risk: "flood", requirement: "documented" };
  return { ...base, metric, min: null, max: null };
}
export function ProfileEditor() {
  const profile = usePreferenceProfile(); const { copyFrom } = useExperienceLocale();
  const c = (key: PreferenceCopyKey) => copyFrom(preferenceCopy, key);
  return <main id="main-content" className={styles.page}>
    <header><h1 className="text-page">{c("title")}</h1><p>{c("intro")}</p><p className="text-meta">{c("boundary")}</p><Link className="ds-button ds-button--secondary" href="/compare">{c("compare")}</Link></header>
    {profile.read ? <EditorForm profile={profile} /> : <p role="status">{c("loading")}</p>}
  </main>;
}
function EditorForm({ profile: { read, store, announce } }: { profile: ReturnType<typeof usePreferenceProfile> }) {
  const { copyFrom, formatDate } = useExperienceLocale();
  const c = (key: PreferenceCopyKey) => copyFrom(preferenceCopy, key);
  const [draft, setDraft] = useState<Draft>(() => read?.profile ?? emptyProfile());
  const [baseProfile, setBaseProfile] = useState(read?.profile ?? null);
  const [dirty, setDirty] = useState(false);
  const [feedback, setFeedback] = useState<PreferenceCopyKey | null>(null);
  const newField = useRef<HTMLFieldSetElement>(null);
  const addButton = useRef<HTMLButtonElement>(null);
  const blocked = !read || !["ready", "empty"].includes(read.status);
  const update = (next: Draft) => { setDraft(next); setDirty(true); setFeedback(null); };
  function ruleChanged(index: number, next: DraftRule) { update({ ...draft, rules: draft.rules.map((rule, i) => i === index ? next : rule) }); }
  function submit(event: FormEvent) {
    event.preventDefault(); const result = store.save(draft, baseProfile);
    setFeedback(result.status === "blocked" ? read?.status === "ready" || read?.status === "empty" ? "unavailable" : read?.status ?? "unavailable" : result.status);
    if (result.status === "saved" && result.profile) { setDraft(result.profile); setBaseProfile(result.profile); setDirty(false); announce(); }
  }
  function loadSaved() { const current = store.read(); if (["ready", "empty"].includes(current.status)) { setDraft(current.profile ?? emptyProfile()); setBaseProfile(current.profile); setDirty(false); setFeedback(null); } announce(); }
  function clear() { const result = store.clear(); setFeedback(result.status); if (result.status === "cleared") { setDraft(emptyProfile()); setBaseProfile(null); setDirty(false); announce(); } }
  return <form className={styles.form} noValidate onSubmit={submit}>
    {blocked && <Message variant="error">{c(read?.status === "corrupt" || read?.status === "unsupported" ? read.status : "unavailable")}</Message>}
    {read?.profile && <p className="text-meta">{copyFrom(preferenceCopy, "profileVersion", { revision: read.profile.revision, date: formatDate(read.profile.updatedAt) })}</p>}
    <div className={styles.fields}>
      <label className={styles.field}>{c("name")}<input maxLength={80} value={draft.name} onChange={e => update({ ...draft, name: e.target.value })} /></label>
      <label className={styles.field}>{c("rationale")}<textarea maxLength={2000} value={draft.rationale} onChange={e => update({ ...draft, rationale: e.target.value })} /></label>
    </div>
    <Section title={c("rules")} description={c("limits")}>
      <div className={styles.form}>{draft.rules.map((rule, index) => <fieldset ref={index === draft.rules.length - 1 ? newField : undefined} className={styles.rule} key={rule.id} data-testid="preference-rule">
        <legend>{index + 1}. {c(rule.metric)}</legend>
        <div className={styles.fields}>
          <label className={styles.field}>{c("metric")}<select value={rule.metric} onChange={e => ruleChanged(index, { ...newRule(e.target.value as typeof METRICS[number], rule.id), priority: rule.priority, rationale: rule.rationale })}>{METRICS.map(metric => <option key={metric} value={metric}>{c(metric)}</option>)}</select></label>
          <label className={styles.field}>{c("priority")}<select value={rule.priority} onChange={e => ruleChanged(index, { ...rule, priority: e.target.value as Priority })}>{(["must", "nice", "veto"] as const).map(priority => <option key={priority} value={priority}>{c(priority)}</option>)}</select></label>
          {rule.metric === "risk" ? <>
            <label className={styles.field}>{c("topic")}<select value={rule.risk} onChange={e => ruleChanged(index, { ...rule, risk: e.target.value as typeof RISK_KEYS[number] })}>{RISK_KEYS.map(key => <option key={key} value={key}>{c(key)}</option>)}</select></label>
            <label className={styles.field}>{c("requirement")}<select value={rule.requirement} onChange={e => ruleChanged(index, { ...rule, requirement: e.target.value as "documented" | "versioned" | "no_match" })}>{(["documented", "versioned", "no_match"] as const).map(key => <option key={key} value={key}>{c(key)}</option>)}</select></label>
          </> : <>
            {rule.metric === "commute" ? <>
              <label className={styles.field}>{c("destination")}<input maxLength={200} required value={rule.destination} onChange={e => ruleChanged(index, { ...rule, destination: e.target.value })} /></label>
              <label className={styles.field}>{c("mode")}<select value={rule.mode} onChange={e => ruleChanged(index, { ...rule, mode: e.target.value as CommuteRule["mode"] })}>{(["driving", "transit", "walking"] as const).map(mode => <option key={mode} value={mode}>{c(mode === "transit" ? "publicTransit" : mode)}</option>)}</select></label>
            </> : <label className={styles.field}>{c("min")}<input type="number" min={0} max={1e9} step="any" value={rule.min ?? ""} onChange={e => ruleChanged(index, { ...rule, min: e.target.value === "" ? null : e.target.valueAsNumber })} /></label>}
            <label className={styles.field}>{c("max")}<input type="number" min={0} max={1e9} step="any" required={rule.metric === "commute"} value={rule.max ?? ""} onChange={e => ruleChanged(index, { ...rule, max: e.target.value === "" ? null : e.target.valueAsNumber })} /></label>
          </>}
        </div>
        {rule.metric === "risk" && <p className="text-meta">{c("riskNote")}</p>}
        {rule.metric === "cash" && <p className="text-meta">{c("cashNote")}</p>}
        {rule.metric === "transit" && <p className="text-meta">{c("transitNote")}</p>}
        <label className={styles.field}>{c("note")}<textarea maxLength={500} value={rule.rationale} onChange={e => ruleChanged(index, { ...rule, rationale: e.target.value })} /></label>
        <div><CommercialButton variant="secondary" onClick={() => { update({ ...draft, rules: draft.rules.filter((_, i) => i !== index) }); requestAnimationFrame(() => addButton.current?.focus()); }}>{c("remove")}</CommercialButton></div>
      </fieldset>)}</div>
      <div className={styles.actions}><button type="button" ref={addButton} className="ds-button ds-button--secondary" disabled={draft.rules.length >= 12 || blocked} onClick={() => { update({ ...draft, rules: [...draft.rules, newRule("size", crypto.randomUUID())] }); requestAnimationFrame(() => newField.current?.querySelector("select")?.focus()); }}>{c("add")}</button></div>
    </Section>
    <p role="status" aria-live="polite">{feedback ? c(feedback) : dirty ? c("unsaved") : read?.status === "empty" ? c("empty") : ""}</p>
    <div className={styles.actions}><CommercialButton type="submit" disabled={blocked}>{c("save")}</CommercialButton><CommercialButton variant="secondary" onClick={loadSaved} disabled={blocked}>{c("reload")}</CommercialButton><CommercialButton variant="secondary" onClick={clear}>{c("clear")}</CommercialButton></div>
  </form>;
}
