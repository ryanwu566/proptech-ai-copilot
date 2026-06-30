"use client";

import { useMemo, useState } from "react";
import { PARTIAL_CASE_PRINT_NOTICE, buildPropertyCaseDraft, type PropertyDecisionStatus } from "@/lib/property-case";
import {
  buildPropertyCaseFinancialAnalysis,
  buildPropertyCaseFinancialScenarios,
  type FundingMode,
  type FinancialMetric,
  type PropertyCaseFinancialScenarioInput,
} from "@/lib/property-case-financials";
import {
  DUE_DILIGENCE_STATUS_LABELS,
  DUE_DILIGENCE_STATUS_OPTIONS,
  buildDefaultDueDiligenceItems,
  buildDueDiligenceReadiness,
  groupDueDiligenceItems,
  type DueDiligenceItem,
  type DueDiligenceStatus,
} from "@/lib/property-case-due-diligence";
import { buildPropertyCaseReadiness } from "@/lib/property-case-readiness";
import type { ValuationInputs } from "@/lib/valuation-share";

const DECISION_STATUS_OPTIONS: Array<{ value: PropertyDecisionStatus; label: string }> = [
  { value: "draft", label: "草稿" },
  { value: "reviewing", label: "檢視中" },
  { value: "shortlisted", label: "候選" },
  { value: "rejected", label: "暫不考慮" },
  { value: "purchased", label: "已購買" },
];

type CommandCenterState = {
  caseName: string;
  address: string;
  propertyType: string;
  listingPrice: string;
  floorAreaPing: string;
  buildingAgeYears: string;
  notes: string;
  downPayment: string;
  loanAmount: string;
  loanYears: string;
  loanRate: string;
  fundingMode: FundingMode;
  fundingValue: string;
  estimatedBuyerCosts: string;
  renovationReserve: string;
  availableLiquidCash: string;
  monthlyHouseholdIncome: string;
  monthlyFixedObligations: string;
  monthlyOwnershipReserve: string;
  scenarios: FinancialScenarioState[];
  userEstimatedValue: string;
  userEstimatedTaxCost: string;
  valuationNote: string;
  taxNote: string;
  decisionStatus: PropertyDecisionStatus;
  decisionNote: string;
  locationMarketNote: string;
  dueDiligenceItems: DueDiligenceItem[];
  decisionReviewSummary: string;
  decisionOpenQuestions: string;
  decisionNextStep: string;
};

type FinancialScenarioState = {
  id: string;
  scenarioName: string;
  optionalListingPrice: string;
  optionalAnnualInterestRate: string;
  optionalEstimatedBuyerCosts: string;
  optionalRenovationReserve: string;
  optionalMonthlyHouseholdIncome: string;
  optionalMonthlyFixedObligations: string;
  optionalMonthlyOwnershipReserve: string;
};

const emptyInputs: ValuationInputs = {
  city: "",
  district: "",
  road: "",
  building_type: "",
  area_ping: 0,
  building_age_years: 0,
  floor: 0,
};

const initialState: CommandCenterState = {
  caseName: "",
  address: "",
  propertyType: "",
  listingPrice: "",
  floorAreaPing: "",
  buildingAgeYears: "",
  notes: "",
  downPayment: "",
  loanAmount: "",
  loanYears: "",
  loanRate: "",
  fundingMode: "loan_amount",
  fundingValue: "",
  estimatedBuyerCosts: "",
  renovationReserve: "",
  availableLiquidCash: "",
  monthlyHouseholdIncome: "",
  monthlyFixedObligations: "",
  monthlyOwnershipReserve: "",
  scenarios: [
    emptyScenario("scenario-a", "Scenario A"),
    emptyScenario("scenario-b", "Scenario B"),
  ],
  userEstimatedValue: "",
  userEstimatedTaxCost: "",
  valuationNote: "",
  taxNote: "",
  decisionStatus: "draft",
  decisionNote: "",
  locationMarketNote: "",
  dueDiligenceItems: buildDefaultDueDiligenceItems(),
  decisionReviewSummary: "",
  decisionOpenQuestions: "",
  decisionNextStep: "",
};

export function PropertyCaseCommandCenter({ caseId }: { caseId: string }) {
  const [state, setState] = useState<CommandCenterState>(initialState);
  const numeric = {
    listingPrice: parsePositiveNumber(state.listingPrice),
    floorAreaPing: parsePositiveNumber(state.floorAreaPing),
    buildingAgeYears: parsePositiveNumber(state.buildingAgeYears),
    downPayment: parsePositiveNumber(state.downPayment),
    loanAmount: parsePositiveNumber(state.loanAmount),
    loanYears: parsePositiveNumber(state.loanYears),
    loanRate: parseNonNegativeNumber(state.loanRate),
    fundingValue: parsePositiveNumber(state.fundingValue),
    estimatedBuyerCosts: parseNonNegativeNumber(state.estimatedBuyerCosts),
    renovationReserve: parseNonNegativeNumber(state.renovationReserve),
    availableLiquidCash: parseNonNegativeNumber(state.availableLiquidCash),
    monthlyHouseholdIncome: parseNonNegativeNumber(state.monthlyHouseholdIncome),
    monthlyFixedObligations: parseNonNegativeNumber(state.monthlyFixedObligations),
    monthlyOwnershipReserve: parseNonNegativeNumber(state.monthlyOwnershipReserve),
    userEstimatedValue: parsePositiveNumber(state.userEstimatedValue),
    userEstimatedTaxCost: parsePositiveNumber(state.userEstimatedTaxCost),
  };
  const financialInputs = useMemo(() => ({
    listingPrice: numeric.listingPrice,
    userEstimatedValue: numeric.userEstimatedValue,
    fundingMode: state.fundingMode,
    fundingValue: numeric.fundingValue,
    annualInterestRate: numeric.loanRate,
    loanYears: numeric.loanYears,
    estimatedBuyerCosts: numeric.estimatedBuyerCosts,
    renovationReserve: numeric.renovationReserve,
    availableLiquidCash: numeric.availableLiquidCash,
    monthlyHouseholdIncome: numeric.monthlyHouseholdIncome,
    monthlyFixedObligations: numeric.monthlyFixedObligations,
    monthlyOwnershipReserve: numeric.monthlyOwnershipReserve,
  }), [numeric.availableLiquidCash, numeric.estimatedBuyerCosts, numeric.fundingValue, numeric.listingPrice, numeric.loanRate, numeric.loanYears, numeric.monthlyFixedObligations, numeric.monthlyHouseholdIncome, numeric.monthlyOwnershipReserve, numeric.renovationReserve, numeric.userEstimatedValue, state.fundingMode]);
  const financialAnalysis = useMemo(() => buildPropertyCaseFinancialAnalysis(financialInputs), [financialInputs]);
  const financialScenarios = useMemo(
    () => buildPropertyCaseFinancialScenarios(financialInputs, state.scenarios.map(toScenarioInput)),
    [financialInputs, state.scenarios],
  );
  const dueDiligenceReadiness = useMemo(
    () => buildDueDiligenceReadiness(state.dueDiligenceItems, {
      decision_review_summary: state.decisionReviewSummary,
      decision_open_questions: state.decisionOpenQuestions,
      decision_next_step: state.decisionNextStep,
    }),
    [state.decisionNextStep, state.decisionOpenQuestions, state.decisionReviewSummary, state.dueDiligenceItems],
  );
  const dueDiligenceGroups = useMemo(() => groupDueDiligenceItems(state.dueDiligenceItems), [state.dueDiligenceItems]);
  const estimatedMonthlyPayment = financialAnalysis.monthlyPayment.value;
  const derivedLoanAmount = financialAnalysis.loanAmount.value;
  const derivedDownPayment = financialAnalysis.downPayment.value;
  const draft = useMemo(
    () => buildPropertyCaseDraft({
      caseName: state.caseName,
      address: state.address,
      propertyType: state.propertyType,
      listingPrice: numeric.listingPrice,
      floorAreaPing: numeric.floorAreaPing,
      buildingAgeYears: numeric.buildingAgeYears,
      notes: state.notes,
      downPayment: derivedDownPayment,
      loanAmount: derivedLoanAmount,
      loanYears: numeric.loanYears,
      loanRate: numeric.loanRate,
      fundingMode: state.fundingMode,
      fundingValue: numeric.fundingValue,
      estimatedBuyerCosts: numeric.estimatedBuyerCosts,
      renovationReserve: numeric.renovationReserve,
      availableLiquidCash: numeric.availableLiquidCash,
      monthlyHouseholdIncome: numeric.monthlyHouseholdIncome,
      monthlyFixedObligations: numeric.monthlyFixedObligations,
      monthlyOwnershipReserve: numeric.monthlyOwnershipReserve,
      estimatedMonthlyPayment,
      userEstimatedValue: numeric.userEstimatedValue,
      userEstimatedTaxCost: numeric.userEstimatedTaxCost,
      valuationNote: state.valuationNote,
      taxNote: state.taxNote,
      decisionStatus: state.decisionStatus,
      decisionNote: state.decisionNote,
      dueDiligenceItems: state.dueDiligenceItems,
      decisionReviewSummary: state.decisionReviewSummary,
      decisionOpenQuestions: state.decisionOpenQuestions,
      decisionNextStep: state.decisionNextStep,
      inputs: emptyInputs,
    }),
    [derivedDownPayment, derivedLoanAmount, estimatedMonthlyPayment, numeric.availableLiquidCash, numeric.buildingAgeYears, numeric.estimatedBuyerCosts, numeric.floorAreaPing, numeric.fundingValue, numeric.listingPrice, numeric.loanRate, numeric.loanYears, numeric.monthlyFixedObligations, numeric.monthlyHouseholdIncome, numeric.monthlyOwnershipReserve, numeric.renovationReserve, numeric.userEstimatedTaxCost, numeric.userEstimatedValue, state],
  );
  const readiness = buildPropertyCaseReadiness(draft);

  function update<K extends keyof CommandCenterState>(key: K, value: CommandCenterState[K]) {
    setState((current) => ({ ...current, [key]: value }));
  }

  function updateScenario(id: string, patch: Partial<FinancialScenarioState>) {
    setState((current) => ({
      ...current,
      scenarios: current.scenarios.map((scenario) => scenario.id === id ? { ...scenario, ...patch } : scenario),
    }));
  }

  function addScenario() {
    setState((current) => ({
      ...current,
      scenarios: [...current.scenarios, emptyScenario(`scenario-${Date.now()}`, `Scenario ${current.scenarios.length + 1}`)],
    }));
  }

  function removeScenario(id: string) {
    setState((current) => ({ ...current, scenarios: current.scenarios.filter((scenario) => scenario.id !== id) }));
  }

  function updateDueDiligenceItem(itemId: string, patch: Partial<DueDiligenceItem>) {
    setState((current) => ({
      ...current,
      dueDiligenceItems: current.dueDiligenceItems.map((item) => item.item_id === itemId ? { ...item, ...patch } : item),
    }));
  }

  return <main className="min-h-screen bg-stone-50 px-4 py-8 text-slate-900 sm:px-6 lg:px-8">
    <section className="mx-auto max-w-6xl space-y-6">
      <header className="rounded-3xl border border-stone-200 bg-white p-5 shadow-sm">
        <p className="text-xs font-bold tracking-[0.2em] text-cyan-700">PROPERTY CASE COMMAND CENTER</p>
        <div className="mt-3 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-black">案件工作台</h1>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600">
              單一案件的人工整理區。這裡只整理你輸入或既有分析可得的資訊，不自動查詢外部資料，也不把市場、通勤、地勢或估價結果改寫成買賣建議。
            </p>
            <p className="mt-2 text-xs text-slate-400">Route caseId: {caseId}</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => window.print()} disabled={!draft.readiness.print_ready} className="rounded-xl bg-cyan-700 px-4 py-2 text-sm font-bold text-white disabled:cursor-not-allowed disabled:opacity-45">列印目前摘要</button>
            <a href="/" className="rounded-xl border border-stone-300 bg-white px-4 py-2 text-sm font-bold text-slate-700">回首頁流程</a>
          </div>
        </div>
      </header>

      <div className="grid gap-5 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-5">
          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <SectionHeading eyebrow="A. BASIC" title="基本案件資料" />
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <TextField label="案件名稱（必填）" value={state.caseName} onChange={(value) => update("caseName", value)} placeholder="例如：信義區 A 案" />
              <TextField label="物件地址／識別（必填）" value={state.address} onChange={(value) => update("address", value)} placeholder="縣市、行政區、路段或明確物件識別" />
              <TextField label="物件類型" value={state.propertyType} onChange={(value) => update("propertyType", value)} placeholder="住宅大樓、公寓、透天..." />
              <TextField label="開價（萬元）" value={state.listingPrice} onChange={(value) => update("listingPrice", value)} inputMode="decimal" />
              <TextField label="坪數" value={state.floorAreaPing} onChange={(value) => update("floorAreaPing", value)} inputMode="decimal" />
              <TextField label="屋齡" value={state.buildingAgeYears} onChange={(value) => update("buildingAgeYears", value)} inputMode="decimal" />
            </div>
            <TextArea label="案件備註" value={state.notes} onChange={(value) => update("notes", value)} placeholder="只記錄你已確認的人工觀察，不放 provider raw data。" />
          </section>

          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <SectionHeading eyebrow="B. FINANCING" title="資金與貸款參考" />
            <div className="mt-4 rounded-2xl border border-cyan-100 bg-cyan-50 p-4">
              <div className="grid gap-3 md:grid-cols-4">
                <MetricCard label="總承諾金額" metric={financialAnalysis.totalCommitment} formatter={formatWanMetric} />
                <MetricCard label="每月房貸" metric={financialAnalysis.monthlyPayment} formatter={formatYuanMetric} />
                <MetricCard label="每月總負擔" metric={financialAnalysis.monthlyBurden} formatter={formatYuanMetric} />
                <MetricCard label="購屋後現金" metric={financialAnalysis.postPurchaseCash} formatter={formatWanMetric} />
              </div>
              <p className="mt-3 text-xs leading-5 text-cyan-900">
                財務資料與決策試算僅根據使用者輸入計算，不代表核貸、估價、稅務、法律、投資或購買建議。
              </p>
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <label className="block text-xs font-bold text-slate-500">資金模式
                <select value={state.fundingMode} onChange={(event) => update("fundingMode", event.target.value as FundingMode)} className="mt-1 w-full rounded-xl border border-stone-300 px-3 py-2 text-sm text-slate-900">
                  <option value="loan_amount">以貸款金額推算自備款</option>
                  <option value="down_payment">以自備款推算貸款金額</option>
                </select>
              </label>
              <TextField label={state.fundingMode === "loan_amount" ? "貸款金額（萬元）" : "自備款（萬元）"} value={state.fundingValue} onChange={(value) => update("fundingValue", value)} inputMode="decimal" />
              <TextField label="貸款年限" value={state.loanYears} onChange={(value) => update("loanYears", value)} inputMode="decimal" />
              <TextField label="利率（%）" value={state.loanRate} onChange={(value) => update("loanRate", value)} inputMode="decimal" />
              <TextField label="買方交易成本（萬元）" value={state.estimatedBuyerCosts} onChange={(value) => update("estimatedBuyerCosts", value)} inputMode="decimal" />
              <TextField label="裝修預備金（萬元）" value={state.renovationReserve} onChange={(value) => update("renovationReserve", value)} inputMode="decimal" />
              <TextField label="可動用現金（萬元）" value={state.availableLiquidCash} onChange={(value) => update("availableLiquidCash", value)} inputMode="decimal" />
              <TextField label="家庭月收入（元）" value={state.monthlyHouseholdIncome} onChange={(value) => update("monthlyHouseholdIncome", value)} inputMode="decimal" />
              <TextField label="每月固定支出（元）" value={state.monthlyFixedObligations} onChange={(value) => update("monthlyFixedObligations", value)} inputMode="decimal" />
              <TextField label="每月持有預備金（元）" value={state.monthlyOwnershipReserve} onChange={(value) => update("monthlyOwnershipReserve", value)} inputMode="decimal" />
            </div>

            <div className="mt-4 grid gap-3 md:grid-cols-3">
              <MetricCard label="推算貸款金額" metric={financialAnalysis.loanAmount} formatter={formatWanMetric} />
              <MetricCard label="推算自備款" metric={financialAnalysis.downPayment} formatter={formatWanMetric} />
              <MetricCard label="購屋所需現金" metric={financialAnalysis.cashNeeded} formatter={formatWanMetric} />
              <MetricCard label="每月結餘" metric={financialAnalysis.monthlyResidual} formatter={formatYuanMetric} />
              <MetricCard label="LTV 參考" metric={financialAnalysis.ltvRatio} formatter={formatPercentMetric} />
              <MetricCard label="開價與自估差距" metric={financialAnalysis.userValueGap} formatter={formatWanMetric} />
            </div>

            {financialAnalysis.warnings.length > 0 && <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">
              {financialAnalysis.warnings.map((warning) => <p key={warning}>{warning}</p>)}
            </div>}

            <div className="mt-5 rounded-2xl border border-stone-200 p-4">
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div>
                  <h3 className="text-sm font-black text-slate-900">情境比較</h3>
                  <p className="mt-1 text-xs leading-5 text-slate-500">可新增或刪除情境；空白欄位會沿用上方基礎財務輸入。</p>
                </div>
                <button type="button" onClick={addScenario} className="rounded-xl border border-cyan-200 px-3 py-2 text-xs font-bold text-cyan-800">新增情境</button>
              </div>
              <div className="mt-4 space-y-3">
                {state.scenarios.map((scenario) => <div key={scenario.id} className="rounded-xl bg-stone-50 p-3">
                  <div className="grid gap-2 md:grid-cols-4">
                    <TextField label="情境名稱" value={scenario.scenarioName} onChange={(value) => updateScenario(scenario.id, { scenarioName: value })} />
                    <TextField label="開價覆寫（萬元）" value={scenario.optionalListingPrice} onChange={(value) => updateScenario(scenario.id, { optionalListingPrice: value })} inputMode="decimal" />
                    <TextField label="利率覆寫（%）" value={scenario.optionalAnnualInterestRate} onChange={(value) => updateScenario(scenario.id, { optionalAnnualInterestRate: value })} inputMode="decimal" />
                    <TextField label="買方成本覆寫（萬元）" value={scenario.optionalEstimatedBuyerCosts} onChange={(value) => updateScenario(scenario.id, { optionalEstimatedBuyerCosts: value })} inputMode="decimal" />
                    <TextField label="裝修預備覆寫（萬元）" value={scenario.optionalRenovationReserve} onChange={(value) => updateScenario(scenario.id, { optionalRenovationReserve: value })} inputMode="decimal" />
                    <TextField label="月收入覆寫（元）" value={scenario.optionalMonthlyHouseholdIncome} onChange={(value) => updateScenario(scenario.id, { optionalMonthlyHouseholdIncome: value })} inputMode="decimal" />
                    <TextField label="固定支出覆寫（元）" value={scenario.optionalMonthlyFixedObligations} onChange={(value) => updateScenario(scenario.id, { optionalMonthlyFixedObligations: value })} inputMode="decimal" />
                    <TextField label="持有預備覆寫（元）" value={scenario.optionalMonthlyOwnershipReserve} onChange={(value) => updateScenario(scenario.id, { optionalMonthlyOwnershipReserve: value })} inputMode="decimal" />
                  </div>
                  <button type="button" onClick={() => removeScenario(scenario.id)} className="mt-3 text-xs font-bold text-slate-500">刪除此情境</button>
                </div>)}
                {state.scenarios.length === 0 && <p className="rounded-xl bg-stone-50 px-3 py-2 text-xs text-slate-500">尚未建立情境；可只保留基礎試算。</p>}
              </div>
              {financialScenarios.length > 0 && <div className="mt-4 overflow-x-auto">
                <table className="min-w-[760px] text-left text-xs">
                  <thead className="text-slate-500"><tr><th className="py-2">情境</th><th>所需現金</th><th>月付</th><th>月負擔</th><th>月結餘</th><th>購屋後現金</th><th>LTV</th></tr></thead>
                  <tbody className="divide-y divide-stone-100">
                    {financialScenarios.map((scenario) => <tr key={scenario.scenarioName}>
                      <td className="py-2 font-bold text-slate-700">{scenario.scenarioName}</td>
                      <td>{formatWanMetric(scenario.cashNeeded)}</td>
                      <td>{formatYuanMetric(scenario.monthlyPayment)}</td>
                      <td>{formatYuanMetric(scenario.monthlyBurden)}</td>
                      <td>{formatYuanMetric(scenario.monthlyResidual)}</td>
                      <td>{formatWanMetric(scenario.postPurchaseCash)}</td>
                      <td>{formatPercentMetric(scenario.ltvRatio)}</td>
                    </tr>)}
                  </tbody>
                </table>
              </div>}
            </div>
          </section>

          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <SectionHeading eyebrow="C. VALUE & TAX" title="估價、成本與稅費手動欄位" />
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <TextField label="使用者估計價值（萬元）" value={state.userEstimatedValue} onChange={(value) => update("userEstimatedValue", value)} inputMode="decimal" />
              <TextField label="使用者估計稅費／交易成本（萬元）" value={state.userEstimatedTaxCost} onChange={(value) => update("userEstimatedTaxCost", value)} inputMode="decimal" />
            </div>
            <TextArea label="估價備註" value={state.valuationNote} onChange={(value) => update("valuationNote", value)} placeholder="例如：待補官方 PLVR 可比成交、估價區間或議價假設。" />
            <TextArea label="稅費備註" value={state.taxNote} onChange={(value) => update("taxNote", value)} placeholder="例如：待補 TaxOracle、契稅、持有成本或人工稅務確認。" />
          </section>

          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <SectionHeading eyebrow="D. LOCATION & MARKET" title="位置、通勤、地勢與市場資料" />
            <p className="mt-2 text-sm leading-6 text-slate-600">
              若需要市場資料，請手動使用 Market Insight 的 Direct Market Query Mode（county 必填、district 選填）。這個工作台不會自動呼叫 market query、read model refresh、通勤、地勢或地圖 provider。
            </p>
            <TextArea label="位置／市場人工註記" value={state.locationMarketNote} onChange={(value) => update("locationMarketNote", value)} placeholder="例如：已查市場資料但仍需人工確認；可自行整理後貼入案件備註或決策備註。" />
            <p className="mt-2 text-xs leading-5 text-slate-500">可將人工判讀後的重點貼到備註或決策備註，但不會自動寫入案件判斷。</p>
            <div className="mt-3 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">
              市場、通勤與地勢資料僅供看房風險參考；unavailable、unknown、not assessed 或資料不足不代表低風險、低價格或適合購買。
            </div>
          </section>

          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <SectionHeading eyebrow="E. DUE DILIGENCE" title="盡職調查與決策審查板" />
            <p className="mt-2 text-sm leading-6 text-slate-600">
              這個區塊只整理使用者確認進度、待補資料、卡關原因與下一步；不會自動查詢市場、通勤、地勢、地圖或任何外部服務，也不會改變案件決策狀態。
            </p>
            <div className="mt-4 grid gap-3 md:grid-cols-5">
              <ReviewStat label="已確認" value={dueDiligenceReadiness.confirmed_count} />
              <ReviewStat label="檢查中" value={dueDiligenceReadiness.reviewing_count} />
              <ReviewStat label="卡關" value={dueDiligenceReadiness.blocked_count} />
              <ReviewStat label="不適用" value={dueDiligenceReadiness.not_applicable_count} />
              <ReviewStat label="下一步" value={dueDiligenceReadiness.open_next_action_count} />
            </div>
            <div className="mt-4 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">
              狀態代表使用者的檢查進度，不是安全、通過、核准、推薦或購買結論。卡關項目只代表仍需補資料或專業確認。
            </div>
            <div className="mt-5 space-y-4">
              {dueDiligenceGroups.map((group) => <details key={group.category_id} className="rounded-2xl border border-stone-200 bg-stone-50" open={group.category_id === "basic_property"}>
                <summary className="cursor-pointer px-4 py-3 text-sm font-black text-slate-800">{group.category_label}</summary>
                <div className="space-y-3 border-t border-stone-200 p-4">
                  {group.items.map((item) => <div key={item.item_id} className="rounded-xl bg-white p-3 shadow-sm">
                    <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_180px]">
                      <div>
                        <p className="text-sm font-black text-slate-900">{item.label}</p>
                        <p className="mt-1 text-xs leading-5 text-slate-500">{item.prompt}</p>
                      </div>
                      <label className="block text-xs font-bold text-slate-500">檢查狀態
                        <select value={item.status} onChange={(event) => updateDueDiligenceItem(item.item_id, { status: event.target.value as DueDiligenceStatus })} className="mt-1 w-full rounded-xl border border-stone-300 px-3 py-2 text-sm text-slate-900">
                          {DUE_DILIGENCE_STATUS_OPTIONS.map((status) => <option key={status} value={status}>{DUE_DILIGENCE_STATUS_LABELS[status]}</option>)}
                        </select>
                      </label>
                    </div>
                    <div className="mt-3 grid gap-3 md:grid-cols-2">
                      <TextArea label="使用者確認備註" value={item.note} onChange={(value) => updateDueDiligenceItem(item.item_id, { note: value })} placeholder="只記錄使用者確認內容，不放外部 provider raw data。" />
                      <TextArea label="參考依據備註" value={item.reference_note} onChange={(value) => updateDueDiligenceItem(item.item_id, { reference_note: value })} placeholder="例如：待看文件、待詢問仲介、待專業確認；不要貼 URL、token 或原始資料。" />
                      <TextArea label="下一步行動" value={item.next_action} onChange={(value) => updateDueDiligenceItem(item.item_id, { next_action: value })} placeholder="例如：請賣方補文件、請銀行確認、下次看屋確認。" />
                      <TextField label="目標日期（YYYY-MM-DD）" value={item.target_date} onChange={(value) => updateDueDiligenceItem(item.item_id, { target_date: value })} placeholder="YYYY-MM-DD" />
                    </div>
                    {item.status === "blocked" && <p className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">此項目暫時卡關，代表仍需補資料或專業確認；不代表案件自動被拒絕或風險變低。</p>}
                  </div>)}
                </div>
              </details>)}
            </div>
            <div className="mt-5 rounded-2xl border border-cyan-100 bg-cyan-50 p-4">
              <h3 className="text-sm font-black text-cyan-950">決策審查摘要</h3>
              <TextArea label="目前審查摘要" value={state.decisionReviewSummary} onChange={(value) => update("decisionReviewSummary", value)} placeholder="彙整已確認與仍待確認的重點，不產生買賣建議。" />
              <TextArea label="未解問題" value={state.decisionOpenQuestions} onChange={(value) => update("decisionOpenQuestions", value)} placeholder="列出仍待補資料、待查證或待專業確認的問題。" />
              <TextArea label="下一步" value={state.decisionNextStep} onChange={(value) => update("decisionNextStep", value)} placeholder="例如：補文件、安排再次看屋、請銀行或專業人士確認。" />
              <p className="mt-3 text-xs leading-5 text-cyan-900">
                審查摘要不會自動修改 draft/reviewing/shortlisted/rejected/purchased，也不會使用市場、通勤、地勢或位置資料改變案件結論。
              </p>
            </div>
          </section>
        </div>

        <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start">
          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <SectionHeading eyebrow="READINESS" title="案件完整度" />
            <dl className="mt-4 space-y-2 text-sm">
              <ReadinessRow label="基本資料" ready={draft.readiness.draft_ready} />
              <ReadinessRow label="資金資料" ready={financialAnalysis.isReadyForScenarioComparison} />
              <ReadinessRow label="估價／稅費" ready={Boolean(draft.valuation_tax_input.user_estimated_value || draft.valuation_tax_input.user_estimated_tax_cost || draft.valuation_tax_input.valuation_note || draft.valuation_tax_input.tax_note)} />
              <ReadinessRow label="位置／市場" ready={Boolean(state.locationMarketNote.trim())} />
              <ReadinessRow label="盡職調查" ready={draft.readiness.due_diligence === "completed"} />
            </dl>
            <p className="mt-2 rounded-xl bg-cyan-50 px-3 py-2 text-xs leading-5 text-cyan-900">Due diligence readiness: {draft.readiness.due_diligence}</p>
            <p className="mt-4 rounded-xl bg-stone-50 px-3 py-2 text-xs leading-5 text-slate-600">{readiness.primaryMessage}</p>
            {draft.readiness.missing_required.length > 0 && <p className="mt-2 text-xs text-amber-700">待補：{draft.readiness.missing_required.join(", ")}</p>}
          </section>

          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <SectionHeading eyebrow="DECISION" title="狀態與下一步" />
            <label className="mt-4 block text-xs font-bold text-slate-500">決策狀態
              <select value={state.decisionStatus} onChange={(event) => update("decisionStatus", event.target.value as PropertyDecisionStatus)} className="mt-1 w-full rounded-xl border border-stone-300 px-3 py-2 text-sm">
                {DECISION_STATUS_OPTIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
            <TextArea label="決策備註" value={state.decisionNote} onChange={(value) => update("decisionNote", value)} placeholder="手動記錄下一步，不自動產生買賣建議。" />
            <div className="mt-3 rounded-xl bg-stone-50 px-3 py-2 text-xs leading-5 text-slate-600">
              審查摘要：{state.decisionReviewSummary.trim() || "尚未填寫"}；下一步：{state.decisionNextStep.trim() || "尚未填寫"}
            </div>
            <div className="mt-3 rounded-xl border border-amber-100 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">
              案件完整度不是投資評分、購買建議、核貸機率或預測報酬率。
            </div>
          </section>

          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm print:border-none">
            <SectionHeading eyebrow="PRINT SUMMARY" title="目前摘要" />
            <p className="mt-3 rounded-xl bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">{PARTIAL_CASE_PRINT_NOTICE}</p>
            <ul className="mt-4 space-y-2 text-xs leading-5 text-slate-600">
              <li>案件：{draft.case_name || "待補案件名稱"}</li>
              <li>地址／識別：{draft.property_input.address || "待補物件地址／識別"}</li>
              <li>開價或估計價值：{draft.property_input.listing_price ? `${draft.property_input.listing_price.toLocaleString()} 萬元` : "待補"}</li>
              <li>財務試算：月付 {formatYuanMetric(financialAnalysis.monthlyPayment)}；所需現金 {formatWanMetric(financialAnalysis.cashNeeded)}</li>
              <li>情境比較：{financialScenarios.length > 0 ? `${financialScenarios.length} 組` : "未建立情境"}</li>
              <li>盡職調查：{dueDiligenceReadiness.confirmed_count} 項已確認、{dueDiligenceReadiness.reviewing_count} 項檢查中、{dueDiligenceReadiness.blocked_count} 項卡關</li>
              <li>審查下一步：{state.decisionNextStep.trim() || "待補"}</li>
              <li>決策狀態：{state.decisionStatus}</li>
              <li>可比較：{draft.readiness.compare_ready ? "yes" : "no"}</li>
              <li>可列印目前摘要：{draft.readiness.print_ready ? "yes" : "no"}</li>
            </ul>
          </section>
        </aside>
      </div>
    </section>
  </main>;
}

function SectionHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return <div><p className="text-[10px] font-bold tracking-[0.18em] text-cyan-700">{eyebrow}</p><h2 className="mt-1 text-lg font-black text-slate-950">{title}</h2></div>;
}

function TextField({ label, value, onChange, placeholder = "", inputMode }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string; inputMode?: "decimal" }) {
  return <label className="block text-xs font-bold text-slate-500">{label}<input value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} inputMode={inputMode} className="mt-1 w-full rounded-xl border border-stone-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-100" /></label>;
}

function TextArea({ label, value, onChange, placeholder = "" }: { label: string; value: string; onChange: (value: string) => void; placeholder?: string }) {
  return <label className="mt-4 block text-xs font-bold text-slate-500">{label}<textarea value={value} onChange={(event) => onChange(event.target.value)} placeholder={placeholder} rows={3} className="mt-1 w-full rounded-xl border border-stone-300 px-3 py-2 text-sm text-slate-900 outline-none focus:border-cyan-500 focus:ring-2 focus:ring-cyan-100" /></label>;
}

function ReadinessRow({ label, ready }: { label: string; ready: boolean }) {
  return <div className="flex items-center justify-between rounded-xl bg-stone-50 px-3 py-2"><dt className="font-bold text-slate-700">{label}</dt><dd className={ready ? "font-bold text-emerald-700" : "font-bold text-amber-700"}>{ready ? "ready" : "pending"}</dd></div>;
}

function ReviewStat({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl bg-stone-50 px-3 py-3">
    <p className="text-[10px] font-bold tracking-[0.12em] text-slate-500">{label}</p>
    <p className="mt-1 text-lg font-black text-slate-950">{value}</p>
  </div>;
}

function MetricCard({ label, metric, formatter }: { label: string; metric: FinancialMetric; formatter: (metric: FinancialMetric) => string }) {
  return <div className="rounded-xl border border-white/70 bg-white px-3 py-3 shadow-sm">
    <p className="text-[10px] font-bold tracking-[0.12em] text-slate-500">{label}</p>
    <p className="mt-1 text-sm font-black text-slate-950">{formatter(metric)}</p>
    {metric.status !== "available" && <p className="mt-1 text-[10px] leading-4 text-amber-700">{metric.message}</p>}
  </div>;
}

function emptyScenario(id: string, scenarioName: string): FinancialScenarioState {
  return {
    id,
    scenarioName,
    optionalListingPrice: "",
    optionalAnnualInterestRate: "",
    optionalEstimatedBuyerCosts: "",
    optionalRenovationReserve: "",
    optionalMonthlyHouseholdIncome: "",
    optionalMonthlyFixedObligations: "",
    optionalMonthlyOwnershipReserve: "",
  };
}

function toScenarioInput(scenario: FinancialScenarioState): PropertyCaseFinancialScenarioInput {
  return {
    scenarioName: scenario.scenarioName,
    optionalListingPrice: parsePositiveNumber(scenario.optionalListingPrice),
    optionalAnnualInterestRate: parseNonNegativeNumber(scenario.optionalAnnualInterestRate),
    optionalEstimatedBuyerCosts: parseNonNegativeNumber(scenario.optionalEstimatedBuyerCosts),
    optionalRenovationReserve: parseNonNegativeNumber(scenario.optionalRenovationReserve),
    optionalMonthlyHouseholdIncome: parseNonNegativeNumber(scenario.optionalMonthlyHouseholdIncome),
    optionalMonthlyFixedObligations: parseNonNegativeNumber(scenario.optionalMonthlyFixedObligations),
    optionalMonthlyOwnershipReserve: parseNonNegativeNumber(scenario.optionalMonthlyOwnershipReserve),
  };
}

function parsePositiveNumber(value: string): number | null {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function parseNonNegativeNumber(value: string): number | null {
  if (!value.trim()) return null;
  const number = Number(value);
  return Number.isFinite(number) && number >= 0 ? number : null;
}

function formatWanMetric(metric: FinancialMetric): string {
  return metric.value === null ? "待補" : `${metric.value.toLocaleString()} 萬元`;
}

function formatYuanMetric(metric: FinancialMetric): string {
  return metric.value === null ? "待補" : `${metric.value.toLocaleString()} 元`;
}

function formatPercentMetric(metric: FinancialMetric): string {
  return metric.value === null ? "待補" : `${(metric.value * 100).toFixed(1)}%`;
}
