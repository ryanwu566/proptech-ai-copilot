"use client";

import { useMemo, useState, type CSSProperties, type ReactNode } from "react";
import { terrainReferenceStateLabel } from "@/lib/terrain-reference-evidence";
import {
  COMPARE_FIELD_GROUPS,
  COMPARE_MAX_CASES,
  COMPARE_MIN_CASES,
  compareMetricDelta,
  formatMetric,
  normalizeComparisonDataset,
  stateLabel,
  visibleCompareFields,
  type CompareFieldKey,
} from "@/lib/vnext-compare/presentation";
import type { CompareDataState, CompareMetric, PropertyCompareCase } from "@/lib/vnext-compare/types";
import styles from "./property-compare-workspace.module.css";

export type PropertyCompareWorkspaceProps = {
  cases: readonly PropertyCompareCase[];
  datasetLabel?: string;
};

const FIELD_LABELS: Record<CompareFieldKey, string> = {
  identity: "物件身分",
  askingPrice: "開價",
  area: "面積",
  buildingType: "建物型態",
  valuation: "估價區間／狀態",
  downPayment: "頭期款金額",
  monthlyMortgage: "房貸月付",
  monthlyHoldingCost: "每月持有成本",
  location: "位置觀察",
  terrain: "地勢／風險參考",
  tax: "稅務參考狀態",
  warnings: "缺漏、衝突與警示",
  freshness: "資料時間",
  sources: "來源與限制",
  nextChecks: "下一步查核",
};

export function PropertyCompareWorkspace({ cases: suppliedCases, datasetLabel }: PropertyCompareWorkspaceProps) {
  const dataset = useMemo(() => normalizeComparisonDataset(suppliedCases), [suppliedCases]);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [filter, setFilter] = useState("");
  const [differencesOnly, setDifferencesOnly] = useState(false);
  const [referenceId, setReferenceId] = useState("");
  const [limitMessage, setLimitMessage] = useState("");
  const selectedCases = selectedIds.map((id) => dataset.cases.find((item) => item.caseId === id)).filter((item): item is PropertyCompareCase => Boolean(item));
  const referenceCase = selectedCases.find((item) => item.caseId === referenceId) ?? null;
  const visibleFields = visibleCompareFields(selectedCases, differencesOnly);
  const normalizedFilter = filter.trim().toLocaleLowerCase("zh-Hant");
  const filteredCases = dataset.cases.filter((item) => !normalizedFilter || `${item.title} ${item.locationSummary} ${item.caseId}`.toLocaleLowerCase("zh-Hant").includes(normalizedFilter));
  const ready = selectedCases.length >= COMPARE_MIN_CASES;
  const columnStyle = { "--compare-columns": selectedCases.length } as CSSProperties;

  function toggleCase(caseId: string) {
    if (selectedIds.includes(caseId)) {
      removeCase(caseId);
      return;
    }
    if (selectedIds.length >= COMPARE_MAX_CASES) {
      setLimitMessage(`最多只能選擇 ${COMPARE_MAX_CASES} 個案件。請先移除一個比較欄，再加入其他案件。`);
      return;
    }
    setSelectedIds((current) => [...current, caseId]);
    setLimitMessage("");
  }

  function removeCase(caseId: string) {
    setSelectedIds((current) => current.filter((id) => id !== caseId));
    if (referenceId === caseId) setReferenceId("");
    setLimitMessage("");
  }

  function moveCase(caseId: string, direction: -1 | 1) {
    setSelectedIds((current) => {
      const index = current.indexOf(caseId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= current.length) return current;
      const reordered = [...current];
      [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
      return reordered;
    });
  }

  return (
    <section className={styles.workspace} data-testid="property-compare-workspace" aria-labelledby="compare-workspace-title">
      <div className={styles.workspaceHeading}>
        <div>
          <p className={styles.eyebrow}>PROPERTY COMPARISON · NON-RANKED</p>
          <h2 id="compare-workspace-title">多物件比較工作區</h2>
          <p>把已知欄位放在同一尺度檢視；不評分、不排序，也不自動選出建議物件。</p>
        </div>
        {datasetLabel && <span className={styles.datasetTag}>{datasetLabel}</span>}
      </div>

      <div className={styles.boundaryNote}>
        <span aria-hidden="true">◇</span>
        <p><strong>比較界線</strong>　最多選擇 {COMPARE_MAX_CASES} 案。較低價格不等於較佳物件；參考基準只用於相容數值的算術差額。</p>
      </div>

      {dataset.issues.length > 0 && (
        <div className={styles.datasetIssues} role="alert" data-testid="dataset-issues">
          <strong>輸入資料需要處理</strong>
          <ul>{dataset.issues.map((issue) => <li key={`${issue.code}-${issue.itemIndex}`}>{issue.message}</li>)}</ul>
        </div>
      )}

      <section className={styles.selectionPanel} aria-labelledby="compare-selection-title">
        <div className={styles.selectionHeading}>
          <div>
            <p className={styles.stepLabel}>01 · 選擇案件</p>
            <h3 id="compare-selection-title">明確選擇要並排的案件</h3>
          </div>
          <p className={styles.selectionCount} role="status" data-testid="selection-count"><strong>{selectedCases.length}</strong> / {COMPARE_MAX_CASES} 已選擇</p>
        </div>
        <label className={styles.filterLabel}>
          <span>篩選供選案件</span>
          <input value={filter} onChange={(event) => setFilter(event.target.value)} placeholder="輸入案件名稱、位置或案件 ID" data-testid="case-filter" />
        </label>
        <div className={styles.casePicker}>
          {filteredCases.map((item) => {
            const selected = selectedIds.includes(item.caseId);
            return (
              <button
                type="button"
                key={item.caseId}
                className={`${styles.caseOption} ${selected ? styles.caseOptionSelected : ""}`}
                aria-pressed={selected}
                onClick={() => toggleCase(item.caseId)}
                data-testid={`case-option-${item.caseId}`}
              >
                <span className={styles.checkMark} aria-hidden="true">{selected ? "✓" : "+"}</span>
                <span className={styles.caseOptionText}>
                  <strong>{item.title}</strong>
                  <small>{item.locationSummary}</small>
                  <code>Case · {item.caseId}</code>
                </span>
              </button>
            );
          })}
          {filteredCases.length === 0 && <p className={styles.noMatches}>沒有符合篩選條件的案件；已選比較欄不會因此移除。</p>}
        </div>
        {limitMessage && <p className={styles.limitMessage} role="alert" data-testid="selection-limit-message">{limitMessage}</p>}
        <SelectionGuidance count={selectedCases.length} />
      </section>

      {ready ? (
        <>
          <section className={styles.controlBar} aria-labelledby="comparison-controls-title">
            <div>
              <p className={styles.stepLabel}>02 · 檢視方式</p>
              <h3 id="comparison-controls-title">欄位與差額</h3>
            </div>
            <label className={styles.toggleLabel}>
              <input type="checkbox" checked={differencesOnly} onChange={(event) => setDifferencesOnly(event.target.checked)} data-testid="differences-only" />
              <span>只顯示差異</span>
            </label>
            <label className={styles.referenceControl}>
              <span>差額參考案</span>
              <select value={referenceCase?.caseId ?? ""} onChange={(event) => setReferenceId(event.target.value)} data-testid="reference-case-select">
                <option value="">不顯示差額</option>
                {selectedCases.map((item) => <option key={item.caseId} value={item.caseId}>{item.title}</option>)}
              </select>
              <small>僅是視覺／算術基準，不代表推薦或已確認的標準物件。</small>
            </label>
          </section>

          <section className={styles.comparisonSection} aria-labelledby="comparison-matrix-title">
            <div className={styles.comparisonHeading}>
              <div>
                <p className={styles.stepLabel}>03 · 並排查核</p>
                <h3 id="comparison-matrix-title">比較內容</h3>
              </div>
              <p>{differencesOnly ? "相同且完整的欄位已收合；缺漏、過期、衝突、風險與來源限制仍會保留。" : "顯示全部欄位與每案證據限制。"}</p>
            </div>

            <div className={styles.desktopMatrix} style={columnStyle} data-testid="comparison-desktop">
              <div className={`${styles.matrixRow} ${styles.caseHeaderRow}`}>
                <div className={styles.fieldHeader}>比較欄位</div>
                {selectedCases.map((item, index) => (
                  <CaseColumnHeader key={item.caseId} item={item} index={index} count={selectedCases.length} onMove={moveCase} onRemove={removeCase} />
                ))}
              </div>
              {COMPARE_FIELD_GROUPS.map((group) => {
                const fields = group.fields.filter((field) => visibleFields.has(field));
                if (!fields.length) return null;
                return (
                  <div key={group.label} className={styles.matrixGroup}>
                    <div className={styles.groupLabel}>{group.label}</div>
                    {fields.map((field) => (
                      <div key={field} className={styles.matrixRow} data-testid={`row-${field}`}>
                        <div className={styles.fieldLabel}>{FIELD_LABELS[field]}{field === "downPayment" && <small>不等於完整初始現金需求</small>}</div>
                        {selectedCases.map((item) => (
                          <div key={item.caseId} className={styles.valueCell} data-testid={`cell-${field}-${item.caseId}`}>
                            <FieldValue field={field} item={item} reference={referenceCase} />
                          </div>
                        ))}
                      </div>
                    ))}
                  </div>
                );
              })}
            </div>

            <div className={styles.mobileCards} data-testid="comparison-mobile">
              {selectedCases.map((item, index) => (
                <article className={styles.mobileCard} key={item.caseId} data-testid={`mobile-case-${item.caseId}`}>
                  <CaseColumnHeader item={item} index={index} count={selectedCases.length} onMove={moveCase} onRemove={removeCase} />
                  {COMPARE_FIELD_GROUPS.map((group) => {
                    const fields = group.fields.filter((field) => visibleFields.has(field));
                    if (!fields.length) return null;
                    return <section key={group.label} className={styles.mobileGroup}><h4>{group.label}</h4>{fields.map((field) => <div className={styles.mobileField} key={field}><p>{FIELD_LABELS[field]}{field === "downPayment" && <small>不等於完整初始現金需求</small>}</p><div data-testid={`mobile-cell-${field}-${item.caseId}`}><FieldValue field={field} item={item} reference={referenceCase} /></div></div>)}</section>;
                  })}
                </article>
              ))}
            </div>
          </section>
        </>
      ) : (
        <section className={styles.emptyComparison} aria-live="polite">
          <span aria-hidden="true">↔</span>
          <div><strong>尚未建立比較欄</strong><p>上方明確選擇 2–3 個案件後，才會顯示比較內容；系統不會自動代選。</p></div>
        </section>
      )}
    </section>
  );
}

function SelectionGuidance({ count }: { count: number }) {
  const message = count === 0
    ? "尚未選擇。請先選兩個案件開始比較。"
    : count === 1
      ? "已選 1 個案件；再選 1 個即可開始。"
      : count === 2
        ? "已可比較；如需三案並排，可再選 1 個。"
        : "已達 3 案上限；可移除或調整欄位順序。";
  return <p className={styles.guidance} data-testid="selection-guidance">{message}</p>;
}

function CaseColumnHeader({ item, index, count, onMove, onRemove }: { item: PropertyCompareCase; index: number; count: number; onMove: (id: string, direction: -1 | 1) => void; onRemove: (id: string) => void }) {
  return (
    <div className={styles.caseHeader} data-testid={`compare-column-${item.caseId}`} data-case-id={item.caseId}>
      <div className={styles.caseOrdinal}>CASE {String(index + 1).padStart(2, "0")}</div>
      <h4>{item.title}</h4>
      <p>{item.locationSummary}</p>
      <code>{item.caseId}</code>
      <div className={styles.columnActions}>
        <button type="button" onClick={() => onMove(item.caseId, -1)} disabled={index === 0} aria-label={`將 ${item.title} 向左移`}>←</button>
        <button type="button" onClick={() => onMove(item.caseId, 1)} disabled={index === count - 1} aria-label={`將 ${item.title} 向右移`}>→</button>
        <button type="button" className={styles.removeButton} onClick={() => onRemove(item.caseId)} aria-label={`從比較中移除 ${item.title}`}>移除</button>
      </div>
    </div>
  );
}

function FieldValue({ field, item, reference }: { field: CompareFieldKey; item: PropertyCompareCase; reference: PropertyCompareCase | null }) {
  if (field === "identity") return <IdentityValue item={item} />;
  if (field === "askingPrice") return <MetricValue metric={item.askingPrice} reference={reference?.askingPrice} isReference={reference?.caseId === item.caseId} />;
  if (field === "area") return <MetricValue metric={item.area} reference={reference?.area} isReference={reference?.caseId === item.caseId} />;
  if (field === "buildingType") return <TextState value={item.buildingType.value} state={item.buildingType.state} limitation={item.buildingType.limitation} />;
  if (field === "valuation") return <ValuationValue item={item} reference={reference} />;
  if (field === "downPayment") return <MetricValue metric={item.downPayment} reference={reference?.downPayment} isReference={reference?.caseId === item.caseId} />;
  if (field === "monthlyMortgage") return <MetricValue metric={item.monthlyMortgage} reference={reference?.monthlyMortgage} isReference={reference?.caseId === item.caseId} />;
  if (field === "monthlyHoldingCost") return <MetricValue metric={item.monthlyHoldingCost} reference={reference?.monthlyHoldingCost} isReference={reference?.caseId === item.caseId} />;
  if (field === "location") return <ObservationValue state={item.location.state} items={item.location.items} limitation={item.location.limitation} />;
  if (field === "terrain") return <TerrainValue item={item} />;
  if (field === "tax") return <TextState value={item.tax.summary} state={item.tax.state} limitation={item.tax.limitation} />;
  if (field === "warnings") return <WarningsValue item={item} />;
  if (field === "freshness") return <FreshnessValue item={item} />;
  if (field === "sources") return <SourcesValue item={item} />;
  return <ListValue items={item.nextChecks} empty="尚未列出查核項目" />;
}

function IdentityValue({ item }: { item: PropertyCompareCase }) {
  const labels = { confirmed: "已確認", resolving: "解析中", unverified: "尚未驗證", legacy_unverified: "舊版案件／未驗證" };
  return <div className={styles.valueStack}><StatePill state={item.identity.status === "confirmed" ? "known" : "unverified"}>{labels[item.identity.status]}</StatePill>{item.identity.displayLabel && <strong>{item.identity.displayLabel}</strong>}{item.identity.propertyEntityId && <code>PropertyEntity · {item.identity.propertyEntityId}</code>}<small>{item.identity.note}</small></div>;
}

function MetricValue({ metric, reference, isReference }: { metric: CompareMetric; reference?: CompareMetric; isReference: boolean }) {
  const delta = reference ? compareMetricDelta(metric, reference, isReference) : null;
  return <div className={styles.valueStack}><strong>{formatMetric(metric)}</strong><span className={styles.basisLabel}>基礎：{basisLabel(metric.basis)}</span>{metric.state !== "known" && <StatePill state={metric.state}>{stateLabel(metric.state)}</StatePill>}{metric.limitation && <small>{metric.limitation}</small>}{delta && <span className={`${styles.delta} ${delta.kind === "unavailable" ? styles.deltaUnavailable : ""}`} data-testid="metric-delta">{delta.label}</span>}</div>;
}

function TextState({ value, state, limitation }: { value: string | null; state: CompareDataState; limitation?: string }) {
  return <div className={styles.valueStack}><strong>{value || stateLabel(state)}</strong>{state !== "known" && <StatePill state={state}>{stateLabel(state)}</StatePill>}{limitation && <small>{limitation}</small>}</div>;
}

function ValuationValue({ item, reference }: { item: PropertyCompareCase; reference: PropertyCompareCase | null }) {
  if (!item.valuation.transferable) return <div className={styles.valueStack}><strong>不可供比較</strong><StatePill state={item.valuation.state}>{stateLabel(item.valuation.state)}</StatePill><small>{item.valuation.limitation}</small></div>;
  const delta = reference ? compareMetricDelta(item.valuation.midpoint, reference.valuation.midpoint, reference.caseId === item.caseId) : null;
  return <div className={styles.valueStack}><strong>{formatMetric(item.valuation.low)} – {formatMetric(item.valuation.high)}</strong><span>中位 {formatMetric(item.valuation.midpoint)}</span><StatePill state="known">{item.valuation.statusLabel}</StatePill><small>{item.valuation.limitation}</small>{delta && <span className={`${styles.delta} ${delta.kind === "unavailable" ? styles.deltaUnavailable : ""}`} data-testid="valuation-delta">{delta.label}</span>}</div>;
}

function ObservationValue({ state, items, limitation }: { state: CompareDataState; items: string[]; limitation: string }) {
  return <div className={styles.valueStack}><StatePill state={state}>{stateLabel(state)}</StatePill><ListValue items={items} empty="沒有可顯示的位置觀察" /><small>{limitation}</small></div>;
}

function TerrainValue({ item }: { item: PropertyCompareCase }) {
  const terrainState = item.terrain.state;
  const pillState: CompareDataState = terrainState === "available" ? "known" : terrainState === "error" ? "unavailable" : terrainState;
  return <div className={styles.valueStack}><div className={styles.pillLine}><StatePill state={pillState}>{terrainReferenceStateLabel(terrainState)}</StatePill>{item.terrain.riskLevel === "high" && <span className={styles.highRiskPill}>已知高風險</span>}</div><strong>{item.terrain.summary}</strong><ListValue items={item.terrain.observations} empty="沒有可顯示的圖層觀察" /><small>{item.terrain.limitation}</small></div>;
}

function WarningsValue({ item }: { item: PropertyCompareCase }) {
  const gaps = collectGaps(item);
  if (!item.warnings.length && !gaps.length) return <span className={styles.quietValue}>目前沒有列出的警示；不代表已完成查核。</span>;
  return <ul className={styles.warningList}>{item.warnings.map((warning, index) => <li key={`warning-${index}`} className={warning.severity === "high" ? styles.highWarning : styles.cautionWarning}><span aria-hidden="true">{warning.severity === "high" ? "!" : "△"}</span>{warning.label}</li>)}{gaps.map((gap) => <li key={gap} className={styles.gapWarning}><span aria-hidden="true">·</span>{gap}</li>)}</ul>;
}

function collectGaps(item: PropertyCompareCase): string[] {
  const rows: Array<[string, CompareDataState]> = [
    ["開價", item.askingPrice.state], ["面積", item.area.state], ["建物型態", item.buildingType.state],
    ["估價", item.valuation.state], ["頭期款", item.downPayment.state], ["房貸月付", item.monthlyMortgage.state],
    ["持有成本", item.monthlyHoldingCost.state], ["位置", item.location.state], ["稅務", item.tax.state],
  ];
  return rows.filter(([, state]) => state !== "known").map(([label, state]) => `${label}：${stateLabel(state)}`);
}

function FreshnessValue({ item }: { item: PropertyCompareCase }) {
  const datedSources = item.sources.filter((source) => source.retrievedAt || source.effectiveAt);
  return <div className={styles.valueStack}><span><b>案件更新</b>　{formatDate(item.caseUpdatedAt)}</span>{datedSources.length ? datedSources.map((source) => <span key={source.sourceId}><b>{source.label}</b><br />取得：{formatDate(source.retrievedAt)}<br />資料時點：{formatDate(source.effectiveAt)}</span>) : <small>來源取得時間與資料時點未提供；不能以案件更新時間代替。</small>}</div>;
}

function SourcesValue({ item }: { item: PropertyCompareCase }) {
  if (!item.sources.length) return <span className={styles.quietValue}>未提供來源；無法判斷涵蓋或新鮮度。</span>;
  return <div className={styles.sourceList}>{item.sources.map((source) => <details key={source.sourceId} data-testid="source-disclosure"><summary><span>{source.label}</span><StatePill state={source.state}>{stateLabel(source.state)}</StatePill></summary><p>涵蓋：{coverageLabel(source.coverage)}</p><p>取得：{formatDate(source.retrievedAt)} · 資料時點：{formatDate(source.effectiveAt)}</p><small>{source.limitation}</small></details>)}</div>;
}

function ListValue({ items, empty }: { items: string[]; empty: string }) {
  return items.length ? <ul className={styles.plainList}>{items.map((item, index) => <li key={`${item}-${index}`}>{item}</li>)}</ul> : <span className={styles.quietValue}>{empty}</span>;
}

function StatePill({ state, children }: { state: CompareDataState; children: ReactNode }) {
  const tone = state === "known" ? styles.stateKnown : ["conflicting", "malformed"].includes(state) ? styles.stateDanger : ["unknown", "unavailable", "not_assessed", "no_match"].includes(state) ? styles.stateUnknown : styles.stateCaution;
  return <span className={`${styles.statePill} ${tone}`}>{children}</span>;
}

function coverageLabel(value: PropertyCompareCase["sources"][number]["coverage"]): string {
  return { known: "已知", partial: "部分", unknown: "未知", unavailable: "不可用" }[value];
}

function basisLabel(value: CompareMetric["basis"]): string {
  return {
    asking_price: "開價",
    transaction_price: "成交價",
    official_valuation: "通過門檻的估價",
    down_payment: "頭期款",
    mortgage_payment: "房貸付款",
    holding_cost: "持有成本",
    floor_area: "面積",
  }[value];
}

function formatDate(value: string | null): string {
  if (!value) return "未提供";
  return new Intl.DateTimeFormat("zh-TW", { dateStyle: "medium", timeZone: "Asia/Taipei" }).format(new Date(value));
}
