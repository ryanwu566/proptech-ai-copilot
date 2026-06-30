"use client";

import { useMemo, useState } from "react";
import { PARTIAL_CASE_PRINT_NOTICE, buildPropertyCaseDraft, type PropertyDecisionStatus } from "@/lib/property-case";
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
  userEstimatedValue: string;
  userEstimatedTaxCost: string;
  valuationNote: string;
  taxNote: string;
  decisionStatus: PropertyDecisionStatus;
  decisionNote: string;
  locationMarketNote: string;
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
  userEstimatedValue: "",
  userEstimatedTaxCost: "",
  valuationNote: "",
  taxNote: "",
  decisionStatus: "draft",
  decisionNote: "",
  locationMarketNote: "",
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
    loanRate: parsePositiveNumber(state.loanRate),
    userEstimatedValue: parsePositiveNumber(state.userEstimatedValue),
    userEstimatedTaxCost: parsePositiveNumber(state.userEstimatedTaxCost),
  };
  const estimatedMonthlyPayment = estimateMonthlyPayment(numeric.loanAmount, numeric.loanYears, numeric.loanRate);
  const draft = useMemo(
    () => buildPropertyCaseDraft({
      caseName: state.caseName,
      address: state.address,
      propertyType: state.propertyType,
      listingPrice: numeric.listingPrice,
      floorAreaPing: numeric.floorAreaPing,
      buildingAgeYears: numeric.buildingAgeYears,
      notes: state.notes,
      downPayment: numeric.downPayment,
      loanAmount: numeric.loanAmount,
      loanYears: numeric.loanYears,
      loanRate: numeric.loanRate,
      estimatedMonthlyPayment,
      userEstimatedValue: numeric.userEstimatedValue,
      userEstimatedTaxCost: numeric.userEstimatedTaxCost,
      valuationNote: state.valuationNote,
      taxNote: state.taxNote,
      decisionStatus: state.decisionStatus,
      decisionNote: state.decisionNote,
      inputs: emptyInputs,
    }),
    [estimatedMonthlyPayment, numeric.buildingAgeYears, numeric.downPayment, numeric.floorAreaPing, numeric.listingPrice, numeric.loanAmount, numeric.loanRate, numeric.loanYears, numeric.userEstimatedTaxCost, numeric.userEstimatedValue, state],
  );
  const readiness = buildPropertyCaseReadiness(draft);

  function update<K extends keyof CommandCenterState>(key: K, value: CommandCenterState[K]) {
    setState((current) => ({ ...current, [key]: value }));
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
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              <TextField label="自備款（萬元）" value={state.downPayment} onChange={(value) => update("downPayment", value)} inputMode="decimal" />
              <TextField label="貸款金額（萬元）" value={state.loanAmount} onChange={(value) => update("loanAmount", value)} inputMode="decimal" />
              <TextField label="貸款年限" value={state.loanYears} onChange={(value) => update("loanYears", value)} inputMode="decimal" />
              <TextField label="利率（%）" value={state.loanRate} onChange={(value) => update("loanRate", value)} inputMode="decimal" />
            </div>
            <div className="mt-4 rounded-xl border border-cyan-100 bg-cyan-50 px-4 py-3 text-sm text-cyan-900">
              估算月付：<strong>{estimatedMonthlyPayment ? `${estimatedMonthlyPayment.toLocaleString()} 元` : "待補貸款金額、年限與利率"}</strong>
              <p className="mt-1 text-xs leading-5">此為前端等額本息粗估，不取代銀行核貸、授信或正式貸款試算。</p>
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
        </div>

        <aside className="space-y-5 lg:sticky lg:top-6 lg:self-start">
          <section className="rounded-2xl border border-stone-200 bg-white p-5 shadow-sm">
            <SectionHeading eyebrow="READINESS" title="案件完整度" />
            <dl className="mt-4 space-y-2 text-sm">
              <ReadinessRow label="基本資料" ready={draft.readiness.draft_ready} />
              <ReadinessRow label="資金資料" ready={Boolean(draft.financial_input.estimated_holding_cost || draft.financial_input.loan_amount || draft.financial_input.down_payment)} />
              <ReadinessRow label="估價／稅費" ready={Boolean(draft.valuation_tax_input.user_estimated_value || draft.valuation_tax_input.user_estimated_tax_cost || draft.valuation_tax_input.valuation_note || draft.valuation_tax_input.tax_note)} />
              <ReadinessRow label="位置／市場" ready={Boolean(state.locationMarketNote.trim())} />
            </dl>
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

function parsePositiveNumber(value: string): number | null {
  const number = Number(value);
  return Number.isFinite(number) && number > 0 ? number : null;
}

function estimateMonthlyPayment(loanAmountWan: number | null, years: number | null, annualRatePercent: number | null): number | null {
  if (!loanAmountWan || !years || !annualRatePercent) return null;
  const principal = loanAmountWan * 10000;
  const months = Math.round(years * 12);
  const monthlyRate = annualRatePercent / 100 / 12;
  if (months <= 0 || monthlyRate <= 0) return null;
  return Math.round(principal * monthlyRate * (1 + monthlyRate) ** months / ((1 + monthlyRate) ** months - 1));
}
