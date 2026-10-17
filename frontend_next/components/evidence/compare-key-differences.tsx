"use client";
import { Section } from "@/components/design-system/section";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { CaseEvidenceModel } from "@/lib/workspace/case-evidence";
import { compareCopy, type CompareCopyKey } from "@/lib/workspace/compare-copy";
import type { KeyDifferencesModel } from "@/lib/workspace/compare-diff";
import { cellResolution } from "@/lib/workspace/compare-diff";
import { EVIDENCE_STATUS_LABELS } from "@/lib/workspace/evidence-labels";
import { evidenceValueText } from "./evidence-view";
import styles from "./evidence.module.css";

/** Bounded list of saved fields that differ; cases keep selection order and are never ranked. */
export function CompareKeyDifferences({ model, cases }: { model: KeyDifferencesModel; cases: CaseEvidenceModel[] }) {
  const { copyFrom } = useExperienceLocale();
  const c = (key: CompareCopyKey, values?: Record<string, string | number>) => copyFrom(compareCopy, key, values);
  const caseLabel = (index: number) => `${"ABCD"[index]} · ${cases[index]?.title ?? ""}`;
  const empty = model.items.length === 0 && model.gapCounts === null;
  return <div data-testid="compare-key-differences"><Section title={c("keyTitle")} description={c("keyDescription")}>
    {empty ? <p>{c("keyNone")}</p> : <ul className={styles.keyList}>
      {model.items.map((item) => <li key={item.group} className={styles.keyItem} data-testid={`key-difference-${item.group}`}>
        <h3 className="text-subsection">{c(item.group)}</h3>
        {item.rows.map((row) => <div key={row.id} className={styles.keyRow} data-testid={`key-row-${row.id}`}>
          <span>{row.label}</span>
          <span className={styles.keyCells}>{row.cells.map((cell, index) => {
            const resolution = cellResolution(cell);
            return <span key={cases[index]?.caseId ?? index} className={styles.keyCell} data-evidence-status={cell.status}>
              <span className="text-meta">{caseLabel(index)}：</span><strong>{evidenceValueText(cell)}</strong>
              <span className="text-meta"> · {EVIDENCE_STATUS_LABELS[cell.status]}</span>
              {resolution !== "resolved" && <span className={styles.tag}>{c(resolution === "stale" ? "stale" : "unknown")}</span>}
            </span>;
          })}</span>
        </div>)}
      </li>)}
      {model.gapCounts && <li className={styles.keyItem} data-testid="key-difference-gaps">
        <h3 className="text-subsection">{c("gaps")}</h3>
        <span className={styles.keyCells}>{model.gapCounts.map((count, index) => <span key={cases[index]?.caseId ?? index} className={styles.keyCell}><span className="text-meta">{caseLabel(index)}：</span>{c("gapCount", { count })}</span>)}</span>
      </li>}
    </ul>}
    {!empty && <p className="text-meta">{c("keyRowHint")}</p>}
  </Section></div>;
}
