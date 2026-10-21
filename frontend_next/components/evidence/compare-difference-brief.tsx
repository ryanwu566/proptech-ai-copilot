"use client";
import Link from "next/link";
import { Section } from "@/components/design-system/section";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { evidenceFields, type CaseEvidenceModel } from "@/lib/workspace/case-evidence";
import { buildDifferenceBrief } from "@/lib/workspace/compare-difference-brief";
import { buildEvidenceChecklist } from "@/lib/workspace/evidence-checklist";
import { EvidenceValue, date } from "./evidence-view";
import styles from "./evidence.module.css";

/** A deterministic reading aid for saved evidence. A/B/C/D retain the buyer's selection order. */
export function CompareDifferenceBrief({ cases }: { cases: CaseEvidenceModel[] }) {
  const { locale } = useExperienceLocale();
  const t = (zh: string, en: string, ja: string, ko: string) => ({ "zh-TW": zh, en, ja, ko })[locale];
  const model = buildDifferenceBrief(cases, locale);
  if (!model.categories.length) return null;
  const sourcesLabel = t("保存證據與查證項目", "Saved evidence and verification items", "保存エビデンス・確認項目", "저장 근거·검증 항목");
  const label = (index: number) => `${"ABCD"[index]} · ${cases[index].title}`;
  return <div data-testid="compare-difference-brief"><Section title={t("差異摘要", "Difference Brief", "相違点の要約", "차이 요약")} description={t("僅依已儲存案件證據整理；案件代號依選取順序，不提供購買建議。", "Based only on saved case evidence. Case letters follow selection order; no purchase advice.", "保存された案件情報のみを使用。記号は選択順であり、購入の助言は行いません。", "저장된 사례 근거만 사용합니다. 문자는 선택 순서이며 구매 조언을 제공하지 않습니다.")}>
    <div className={styles.briefList}>
      {model.categories.map((category) => <article key={category.id} className={styles.briefCategory} data-testid={`brief-${category.id}`}>
        <h3 className="text-subsection">{category.title}</h3>
        <dl className={styles.briefStatements}>
          {category.statements.map((statement, index) => <div key={statement.caseId} data-brief-case={statement.caseId}>
            <dt>{label(index)}</dt><dd>{statement.text}</dd>
          </div>)}
        </dl>
        <p className={styles.briefContrast}><strong>{t("差異", "Difference", "相違点", "차이")}：</strong>{category.difference}</p>
        {category.caution && <p className="text-meta">{category.caution}</p>}
        <DetailsDisclosure variant="compact" summary={sourcesLabel}>
          <div className={styles.briefSources}>
            {category.statements.map((statement, index) => {
              const item = cases[index];
              const fields = evidenceFields(item).filter((field) => statement.fieldIds.includes(field.id));
              const gaps = item.gaps.filter((gap) => statement.gapIds.includes(gap.id));
              const actions = statement.actionIds.length ? buildEvidenceChecklist(item).filter((action) => statement.actionIds.includes(action.id)) : [];
              return <section key={item.caseId}>
                <h4 className="text-subsection">{label(index)}</h4>
                <p className="text-meta">{t("案件保存", "Case saved", "案件保存", "사례 저장")}：{date(item.savedAt)}</p>
                {category.id === "location" && <>
                  <p>{item.displayAddress} · {item.comparisonContext?.administration ?? t("行政資訊未完整保存", "Administrative information incomplete", "行政情報の保存が不完全", "행정 정보 일부 미저장")}</p>
                  <p>{item.identity.limitation}</p>
                  {item.comparisonContext?.nearby && <p>Google Places · {item.comparisonContext.nearby.radiusM} m · {date(item.comparisonContext.nearby.checkedAt)}</p>}
                </>}
                {fields.map((field) => <div key={field.id} className={styles.briefSourceField}>
                  <h5>{field.label}</h5><EvidenceValue field={field} density="compact" />
                </div>)}
                {gaps.length > 0 && <ul>{gaps.map((gap) => <li key={gap.id}>{gap.item} · {gap.impact}</li>)}</ul>}
                {actions.length > 0 && <ul>{actions.map((action) => <li key={action.id}><Link prefetch={false} href={action.href}>{action.name} · {action.nextAction}</Link></li>)}</ul>}
                {category.id === "verification" && (item.savedFinanceActions ?? []).length > 0 && <ul>{item.savedFinanceActions!.map((action) => <li key={action}>{action}</li>)}</ul>}
              </section>;
            })}
          </div>
        </DetailsDisclosure>
      </article>)}
    </div>
  </Section></div>;
}
