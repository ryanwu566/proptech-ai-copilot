"use client";

import { useState } from "react";
import type { ReportChecklistItem } from "@/lib/vnext-report";
import styles from "./decision-report-presentation.module.css";

export function BeforeViewingChecklist({ items }: { items: ReportChecklistItem[] }) {
  const [reviewed, setReviewed] = useState<Set<string>>(() => new Set());

  function update(id: string, checked: boolean) {
    setReviewed((current) => {
      const next = new Set(current);
      if (checked) next.add(id); else next.delete(id);
      return next;
    });
  }

  return <section className={styles.reportSection} aria-labelledby="before-viewing-title" data-testid="before-viewing-checklist">
    <div className={styles.sectionHeading}>
      <div>
        <p className={styles.eyebrow}>BEFORE VIEWING</p>
        <h2 id="before-viewing-title">看屋前檢查清單</h2>
      </div>
      <p aria-live="polite" data-testid="checklist-progress">本頁已檢視 {reviewed.size}／{items.length}</p>
    </div>
    <p className={styles.checklistBoundary}>這是個人檢視清單。勾選不會驗證證據、確認物件身分，也不會儲存或變更案件。</p>
    <ul className={styles.checklist}>
      {items.map((item) => <li key={item.id}>
        <label>
          <input type="checkbox" checked={reviewed.has(item.id)} onChange={(event) => update(item.id, event.currentTarget.checked)} />
          <span>
            <b>{item.label}</b>
            {item.detail && <small>{item.detail}</small>}
            <em>{item.reviewOnlyNotice}</em>
          </span>
        </label>
      </li>)}
    </ul>
  </section>;
}
