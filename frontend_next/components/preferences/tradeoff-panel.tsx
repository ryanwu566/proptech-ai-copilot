"use client";
import Link from "next/link";
import { Section } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { preferenceCopy, type PreferenceCopyKey } from "@/lib/preferences/copy";
import { buildTradeoffs } from "@/lib/preferences/tradeoff";
import type { PreferenceRule } from "@/lib/preferences/profile";
import type { PropertyCaseWorkspace } from "@/lib/workspace/workspace-model";
import { usePreferenceProfile } from "./use-profile";
import styles from "./preferences.module.css";
export function TradeoffPanel({ cases }: { cases: PropertyCaseWorkspace[] }) {
  const { read } = usePreferenceProfile();
  const { copyFrom, formatNumber, formatDate } = useExperienceLocale();
  const c = (key: PreferenceCopyKey, values?: Record<string, string | number>) => copyFrom(preferenceCopy, key, values);
  const profile = read?.profile;
  const model = profile ? buildTradeoffs(profile.rules, cases) : null;
  const title = (id: string) => { const i = cases.findIndex(w => w.caseId === id); return `${"ABCD"[i]} · ${cases[i]?.title ?? id}`; };
  const label = (rule: PreferenceRule) => rule.metric === "risk" ? c(rule.risk) : rule.metric === "commute" ? `${c("commute")} · ${rule.destination} · ${c(rule.mode === "transit" ? "publicTransit" : rule.mode)}` : c(rule.metric);
  const condition = (rule: PreferenceRule) => rule.metric === "risk" ? c(rule.requirement) : ["min" in rule && rule.min !== null ? `${c("min")}: ${formatNumber(rule.min)}` : "", rule.max !== null ? `${c("max")}: ${formatNumber(rule.max)}` : ""].filter(Boolean).join(" · ");
  return <div data-testid="preference-tradeoffs"><Section title={c("explanation")} description={c("description")}>
    <div className={styles.explanations}>
      <div><Link className="ds-button ds-button--secondary" href="/preferences">{c("edit")}</Link></div>
      {!read ? <p role="status">{c("loading")}</p> : !profile || !profile.rules.length ? <p>{c(read.status === "ready" ? "empty" : read.status)}</p> : model && <>
        <div><p><strong>{profile.name}</strong></p><p className="text-meta">{c("profileVersion", { revision: profile.revision, date: formatDate(profile.updatedAt) })}</p>{profile.rationale && <p>{c("rationale")}: {profile.rationale}</p>}</div>
        {model.pairs.map(pair => {
          const a = model.evaluations.find(e => e.caseId === pair.left)!.outcomes, b = model.evaluations.find(e => e.caseId === pair.right)!.outcomes;
          const differences = profile.rules.map((rule, index) => a[index].status !== b[index].status ? c("difference", { preference: label(rule), left: title(pair.left), right: title(pair.right), leftStatus: c(a[index].status), rightStatus: c(b[index].status) }) : null).filter(Boolean);
          return <article className={styles.pair} key={`${pair.left}-${pair.right}`}><h3 className="text-subsection">{title(pair.left)} / {title(pair.right)}</h3>
            {pair.statements.map((s, index) => <p key={index} data-testid="pair-statement">{s.kind === "commute_cash" ? c("pairTradeoff", { commute: title(s.commuteCase), cash: title(s.cashCase) }) : c("cashIncomparable")}</p>)}
            {differences.length ? <ul>{differences.map((text, index) => <li key={index}>{text}</li>)}</ul> : <p>{c("noDifference")}</p>}
          </article>;
        })}
        {profile.rules.map((rule, index) => <article className={styles.preference} key={rule.id}><header><h3 className="text-subsection">{index + 1}. {label(rule)}</h3><p>{c(rule.priority)} · {condition(rule)}</p>{rule.rationale && <p>{c("note")}: {rule.rationale}</p>}</header><div className={styles.outcomes}>{model.evaluations.map(evaluation => {
          const outcome = evaluation.outcomes[index];
          return <div className={styles.outcome} key={evaluation.caseId}><strong>{title(evaluation.caseId)}</strong>
            {outcome.status === "unknown" ? <p data-testid="unknown-preference">{c("unknownStatement", { case: title(evaluation.caseId), preference: label(rule) })}</p> : <p>{c(outcome.status)}{outcome.value !== null && ` · ${formatNumber(outcome.value)}`}</p>}
            {outcome.vetoBreached && <p><strong>{c("vetoBreached")}</strong></p>}<p className="text-meta">{c(outcome.reason)}</p>
          </div>;
        })}</div>{rule.metric === "risk" && <p className="text-meta">{c("riskNote")}</p>}{rule.metric === "cash" && <p className="text-meta">{c("cashNote")}</p>}</article>)}
      </>}
    </div>
  </Section></div>;
}
