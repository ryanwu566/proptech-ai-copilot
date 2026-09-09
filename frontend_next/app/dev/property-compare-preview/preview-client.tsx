"use client";

import { useState } from "react";
import { PropertyCompareWorkspace } from "@/components/vnext-compare/property-compare-workspace";
import { COMPARE_PREVIEW_SCENARIOS } from "@/lib/vnext-compare-preview/fixtures";
import styles from "./preview.module.css";

export function PropertyComparePreview() {
  const [scenarioId, setScenarioId] = useState(COMPARE_PREVIEW_SCENARIOS[0].id);
  const scenario = COMPARE_PREVIEW_SCENARIOS.find((item) => item.id === scenarioId) ?? COMPARE_PREVIEW_SCENARIOS[0];
  return (
    <main className={styles.page} data-preview-marker="property-compare-synthetic-preview">
      <div className={styles.shell}>
        <header className={styles.previewHeader}>
          <div>
            <p>LOCAL DEVELOPMENT PREVIEW · TRACK D</p>
            <h1>比較呈現實驗室</h1>
          </div>
          <div className={styles.syntheticNotice} role="note">
            <strong>全頁皆為合成資料</strong>
            <span>不連接客戶、瀏覽器儲存空間或即時資料來源</span>
          </div>
        </header>
        <section className={styles.scenarioBar} aria-labelledby="scenario-title">
          <div><span>PREVIEW SCENARIO</span><h2 id="scenario-title">切換決定性情境</h2></div>
          <label>
            <span>情境</span>
            <select value={scenario.id} onChange={(event) => setScenarioId(event.target.value as typeof scenario.id)} data-testid="scenario-select">
              {COMPARE_PREVIEW_SCENARIOS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
            </select>
          </label>
          <p>{scenario.description}</p>
        </section>
        <PropertyCompareWorkspace key={scenario.id} cases={scenario.cases} datasetLabel={`合成情境 · ${scenario.label}`} />
      </div>
    </main>
  );
}
