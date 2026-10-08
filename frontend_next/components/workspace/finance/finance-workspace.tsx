"use client";

import { useEffect, useMemo, useState } from "react";
import type { HoldingCostResult, LoanCalculationResult } from "@/lib/api";
import { useWorkspace } from "@/components/workspace/workspace-provider";
import { CommercialButton } from "@/components/design-system/button";
import { DetailsDisclosure } from "@/components/design-system/disclosure";
import { Message } from "@/components/design-system/message";
import { ActionSection, Panel, Section } from "@/components/design-system/section";
import { MetricItem, MetricRow, SummaryStrip } from "@/components/design-system/summary-strip";
import { StatusLabel } from "@/components/design-system/status-label";
import { formatMissing, formatPercent, formatTwd, formatWan } from "@/lib/commercial/formatters";
import { updateSavedCaseFinanceEvidence, type SavedCaseIdentityExpectation } from "@/lib/case-storage";
import { buildFinanceModel, type FinanceModel } from "@/lib/workspace/finance-model";
import { createStoredFinanceEvidence } from "@/lib/workspace/finance-persistence";
import { HoldingAssumptionForm, LoanAssumptionForm } from "./finance-assumption-forms";

function monthly(value: number | null): string {
  return value === null ? formatMissing("not_estimated") : `${formatTwd(value)}／月`;
}

function annual(value: number | null): string {
  return value === null ? formatMissing("not_estimated") : `${formatTwd(value)}／年`;
}

function basisLabel(value: FinanceModel["priceBasis"]["basis"]): string {
  return value === "asking" ? "開價" : value === "estimate" ? "成交資料推估" : "使用者輸入價格";
}

function taxOutcome(value: FinanceModel["tax"]["summary"]): string {
  if (!value) return "尚未進行";
  return value.outcome === "eligible" ? "目前條件初步符合" : value.outcome === "not_eligible" ? "目前有條件未符合" : "需專業複核";
}

function identityExpectation(model: ReturnType<typeof useWorkspace>): SavedCaseIdentityExpectation | null {
  const anchor = model.identity.anchor;
  if (!anchor?.coordinates) return null;
  return {
    journeyAnchorId: anchor.journey_anchor_id,
    normalizedAddress: anchor.normalized_address,
    coordinates: { latitude: anchor.coordinates.latitude, longitude: anchor.coordinates.longitude },
  };
}

function mergeFinanceEvidence(base: FinanceModel, live: FinanceModel, hasLoanResult: boolean, hasHoldingResult: boolean): FinanceModel {
  const loan = hasLoanResult ? live.loan : base.loan;
  const holding = hasHoldingResult ? live.holding : base.holding;
  const affordability = hasHoldingResult
    ? live.affordability.status === "assessed" || hasLoanResult || base.affordability.basis !== "loan_payment" ? live.affordability : base.affordability
    : hasLoanResult ? live.affordability : base.affordability;
  const missingCosts = hasHoldingResult ? live.missingCosts : base.missingCosts;
  const unresolvedActions = live.unresolvedActions.filter((item) => {
    if (loan.status !== "not_started" && item === "尚未完成房貸試算") return false;
    if (holding.status !== "not_started" && item === "尚未估算持有成本") return false;
    return true;
  });
  const knownRecurringMonthlyTwd = holding.knownMonthlySubtotalTwd ?? loan.monthlyPaymentTwd;
  return {
    ...live,
    loan,
    holding,
    affordability,
    tax: base.tax,
    missingCosts,
    unresolvedActions,
    overview: {
      ...live.overview,
      monthlyPaymentTwd: loan.monthlyPaymentTwd,
      knownRecurringMonthlyTwd,
      missingCosts,
      affordabilityStatus: affordability.status,
      unresolvedActions,
    },
    comparison: {
      ...live.comparison,
      downPaymentWan: loan.downPaymentWan,
      loanPrincipalWan: loan.principalWan,
      monthlyPaymentTwd: loan.monthlyPaymentTwd,
      knownRecurringMonthlyTwd,
      missingCosts,
    },
  };
}

export function FinanceWorkspace() {
  const workspace = useWorkspace();
  const activePriceWan = workspace.assumptions.activePriceWan ?? null;
  const baseFinance = workspace.finance ?? buildFinanceModel({
    caseId: workspace.caseId,
    revision: workspace.revision,
    identityAnchorId: workspace.identity.anchor?.journey_anchor_id ?? null,
    identityState: workspace.identity.state,
    activePriceBasis: workspace.assumptions.activePriceBasis,
    activePriceWan,
    areaPing: workspace.assumptions.areaPing ?? null,
  });
  const [loanResult, setLoanResult] = useState<LoanCalculationResult | null>(null);
  const [holdingResult, setHoldingResult] = useState<HoldingCostResult | null>(null);
  const savedAreaPing = baseFinance.holding.assumptions.areaPing ?? workspace.assumptions.areaPing ?? null;
  const [holdingAreaPing, setHoldingAreaPing] = useState<number | null>(savedAreaPing);
  const [calculatedAt, setCalculatedAt] = useState<string | null>(null);
  const [loanDirty, setLoanDirty] = useState(false);
  const [holdingDirty, setHoldingDirty] = useState(false);
  const [saveStatus, setSaveStatus] = useState<"idle" | "saved" | "failed">("idle");

  useEffect(() => {
    setLoanResult(null);
    setHoldingResult(null);
    setHoldingAreaPing(baseFinance.holding.assumptions.areaPing ?? workspace.assumptions.areaPing ?? null);
    setCalculatedAt(null);
    setLoanDirty(false);
    setHoldingDirty(false);
    setSaveStatus("idle");
  }, [baseFinance.holding.assumptions.areaPing, workspace.caseId, workspace.revision, workspace.finance?.inputFingerprint, workspace.assumptions.activePriceWan, workspace.assumptions.areaPing]);

  const finance = useMemo(() => {
    if (!loanResult && !holdingResult) return baseFinance;
    const computed = buildFinanceModel({
      caseId: workspace.caseId,
      revision: workspace.revision,
      identityAnchorId: workspace.identity.anchor?.journey_anchor_id ?? null,
      identityState: workspace.identity.state,
      activePriceBasis: workspace.assumptions.activePriceBasis,
      activePriceWan,
      askingPriceWan: workspace.assumptions.askingPriceWan,
      areaPing: holdingAreaPing,
      loanResult,
      holdingResult,
      calculatedAt,
    });
    return mergeFinanceEvidence(baseFinance, computed, loanResult !== null, holdingResult !== null);
  }, [activePriceWan, baseFinance, calculatedAt, holdingAreaPing, holdingResult, loanResult, workspace]);

  if (activePriceWan === null) return <div data-testid="finance-workspace" className="min-w-0 space-y-6">
    <header className="space-y-2"><p className="text-meta">案件財務情境</p><h1 className="text-page">資金與持有成本</h1><p className="text-body">在不改動案件價格的前提下，計算房貸、持有成本與仍待補充的費用。</p></header>
    <Message variant="warning" title="需要可用的物件價格">請先回到「價格與市場」確認開價、推估價格或手動價格基準。</Message>
  </div>;

  const expectation = identityExpectation(workspace);
  const saveDisabled = loanDirty || holdingDirty || finance.freshness.status !== "current" || finance.freshness.calculatedAt === null || finance.calculation.query !== "succeeded" || !expectation;

  function onLoanCalculated(result: LoanCalculationResult) {
    setLoanResult(result);
    setHoldingResult(null);
    setCalculatedAt(new Date().toISOString());
    setLoanDirty(false);
    setHoldingDirty(baseFinance.holding.status !== "not_started");
    setSaveStatus("idle");
  }

  function onHoldingCalculated(result: HoldingCostResult, areaPing: number | null) {
    setHoldingResult(result);
    setHoldingAreaPing(areaPing);
    setCalculatedAt(new Date().toISOString());
    setHoldingDirty(false);
    setSaveStatus("idle");
  }

  function saveFinance() {
    if (saveDisabled || !expectation) return;
    try {
      const evidence = createStoredFinanceEvidence(finance, { caseId: workspace.caseId, revision: workspace.revision, areaPing: holdingAreaPing });
      setSaveStatus(updateSavedCaseFinanceEvidence(workspace.caseId, evidence, expectation) ? "saved" : "failed");
    } catch {
      setSaveStatus("failed");
    }
  }

  return <div data-testid="finance-workspace" className="workspace-view">
    <header className="space-y-2">
      <p className="text-meta">案件財務情境</p>
      <h1 className="text-page">資金與持有成本</h1>
      <p className="text-body">這個物件在目前假設下，需要多少自備款、每月房貸與已知持有成本？哪些費用仍未估算？</p>
    </header>

    <Section title="價格與融資基準" description="價格沿用案件目前選定的基準；本頁只讀取，不會改寫開價、手動價格或價格推估。">
      <div data-testid="finance-price-basis"><SummaryStrip label="價格與融資基準">
        <MetricItem label={basisLabel(workspace.assumptions.activePriceBasis)} value={formatWan(activePriceWan)} primary note="沿用案件價格" />
        <MetricItem label="自備款" value={formatWan(finance.loan.downPaymentWan)} note="未含稅費、仲介、代書與其他交易費用" />
        <MetricItem label="坪數" value={workspace.assumptions.areaPing ? `${workspace.assumptions.areaPing.toLocaleString("zh-TW", { maximumFractionDigits: 1 })} 坪` : "未提供"} note="僅影響依坪數估算的持有成本" />
      </SummaryStrip></div>
      <Freshness model={finance} dirty={loanDirty || holdingDirty} />
    </Section>

    <Section title="主要每月結果" description="房貸與持有成本使用相同價格情境；一次性交易成本不會混入每月小計。">
      <SummaryStrip label="主要每月結果" className="commercial-finance-summary">
        <MetricItem label="每月房貸支出" value={monthly(finance.loan.monthlyPaymentTwd)} primary note={finance.loan.status === "stale" ? "舊條件結果，需重新計算" : "依目前房貸假設"} />
        <MetricItem label={finance.holding.totalKind === "known_subtotal" ? "已估算成本小計" : "每月持有成本估算"} value={monthly(finance.holding.knownMonthlySubtotalTwd)} note={finance.holding.totalKind === "known_subtotal" ? "尚有未估算項目，不是完整總額" : "含目前明細中的月支出"} />
        <MetricItem label="利率／年期" value={`${finance.loan.annualInterestRate ?? "—"}%／${finance.loan.loanYears ?? "—"} 年`} note={`自備款比例：${finance.loan.downPaymentRatio === null ? "未提供" : formatPercent(finance.loan.downPaymentRatio)}`} />
        <MetricItem label="負擔能力" value={finance.affordability.status === "assessed" ? formatPercent(finance.affordability.ratio) : "未評估"} note={finance.affordability.reason ?? "依已提供的月收入與支出"} />
      </SummaryStrip>
    </Section>

    <Section title="房貸假設與結果" description="這是還款情境試算，不是銀行核貸或額度承諾。">
      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(280px,360px)_minmax(0,1fr)]">
        <div className="min-w-0"><LoanAssumptionForm key={`loan-${workspace.caseId}-${baseFinance.inputFingerprint}`} propertyPriceWan={activePriceWan} initial={baseFinance.loan} onDirty={() => { setLoanDirty(true); setHoldingDirty(true); setSaveStatus("idle"); }} onCalculated={onLoanCalculated} /></div>
        <LoanSummary model={finance} dirty={loanDirty} />
      </div>
    </Section>

    <Section title="持有成本明細" description="每月與每年費用分開呈現；缺少坪數時，依坪數計算的項目保持未估算。">
      <div className="grid min-w-0 gap-6 lg:grid-cols-[minmax(280px,360px)_minmax(0,1fr)]">
        <div className="min-w-0"><HoldingAssumptionForm key={`holding-${workspace.caseId}-${baseFinance.inputFingerprint}`} propertyPriceWan={activePriceWan} initialLoanPaymentTwd={loanResult?.monthly_payment ?? finance.loan.monthlyPaymentTwd} initialAreaPing={savedAreaPing} initial={baseFinance.holding.assumptions} onDirty={() => { setHoldingDirty(true); setSaveStatus("idle"); }} onCalculated={onHoldingCalculated} /></div>
        <HoldingSummary model={finance} dirty={holdingDirty} />
      </div>
    </Section>

    <Section title="一次性、稅務與交易成本" description="一次性交易費用與每月持有成本使用不同時間基準，不合併成單一總額。">
      <div className="grid gap-5 lg:grid-cols-2">
        <Panel variant="plain">
          <h3 className="text-subsection">已知一次性成本</h3>
          <p className="mt-2 text-body">目前沒有可安全計算的一次性交易成本金額。</p>
          <p className="mt-2 text-helper">契稅、登記規費、仲介、代書與其他交易成本尚未納入。</p>
        </Panel>
        <TaxSummary model={finance} />
      </div>
    </Section>

    <Section title="負擔能力假設">
      <div data-testid="affordability-status">
        {finance.affordability.status === "assessed"
          ? <Message variant="information" title={`${finance.affordability.basis === "total_housing_cost" ? "已估算住宅支出" : "房貸支出"}占月收入比例：${formatPercent(finance.affordability.ratio)}`}>此比例只反映已納入的目前假設，不代表銀行審核結果或適合購買。</Message>
          : <Message variant="warning" title="未評估（未提供月收入）">房貸或持有成本可以完成計算，但沒有月收入就不能判斷負擔能力。</Message>}
      </div>
    </Section>

    <Section title="未估算或未納入的成本">
      <ul className="list-disc space-y-2 pl-5 text-body">{finance.missingCosts.map((item) => <li key={item}>{item}</li>)}</ul>
    </Section>

    <Section title="下一步">
      <ol className="list-decimal space-y-2 pl-5 text-body">{finance.unresolvedActions.length > 0 ? finance.unresolvedActions.map((item) => <li key={item}>{item}</li>) : <li>檢查假設後儲存目前的財務摘要。</li>}</ol>
      <ActionSection id="finance-save-section" className="mt-5">
        <CommercialButton onClick={saveFinance} disabled={saveDisabled} data-testid="finance-save">儲存財務假設與摘要</CommercialButton>
        {saveDisabled && <p className="text-helper">需先完成一項目前條件下的計算，且物件資料不可為待重新確認。</p>}
      </ActionSection>
      <div data-testid="finance-save-status" className="mt-3" aria-live="polite">
        {saveStatus === "saved" && <Message variant="success">已儲存財務假設與摘要。</Message>}
        {saveStatus === "failed" && <Message variant="error">財務摘要儲存失敗；目前畫面結果仍保留，請再試一次。</Message>}
      </div>
    </Section>

    <DetailsDisclosure summary="計算方法、假設與限制">
      <div className="space-y-3 text-body">
        <p>房貸試算沿用既有本息攤還計算服務；持有成本沿用既有管理費、修繕準備、稅費與保險估算服務。</p>
        <p>所有計算金額以新臺幣為準；物件總價與部分輸入以萬元呈現，欄位單位均明確標示。</p>
        <p>估算不等於報價、帳單、銀行核貸、主管機關核定或稅務／法律意見。請在交易前向銀行與專業人員確認。</p>
      </div>
    </DetailsDisclosure>
  </div>;
}

function Freshness({ model, dirty }: { model: FinanceModel; dirty: boolean }) {
  const stale = dirty || model.freshness.status === "stale";
  return <div data-testid="freshness-status" className="mt-4">
    {stale ? <Message variant="warning" title="條件已變更，需重新計算">舊結果保留供辨識，但不再視為目前條件的有效結果。</Message>
      : model.freshness.source === "saved_snapshot" ? <Message variant="information" title="已儲存的計算摘要">計算時間：{model.freshness.calculatedAt ?? "未提供"}。這不是本次開啟後重新計算的即時結果。</Message>
        : model.freshness.source === "live_calculation" ? <Message variant="information" title="本次計算尚未儲存">檢查假設後，可儲存財務摘要供下次開啟。</Message>
          : <Message variant="information" title="尚未計算">先設定房貸或持有成本假設，再計算需要的結果。</Message>}
  </div>;
}

function LoanSummary({ model, dirty }: { model: FinanceModel; dirty: boolean }) {
  return <Panel variant="plain" data-testid="loan-summary" className="min-w-0">
    <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-subsection">房貸結果</h3><StatusLabel semanticRole={dirty || model.loan.status === "stale" ? "warning" : model.loan.status === "available" ? "information" : "neutral"}>{dirty ? "待重新計算" : model.loan.status === "available" ? "房貸試算完成" : model.loan.status === "stale" ? "舊條件結果" : "尚未計算"}</StatusLabel></div>
    {model.loan.monthlyPaymentTwd === null ? <p className="mt-5 text-body">尚未有可用的房貸結果。</p> : <div className="mt-5 space-y-2">
      <MetricRow label="自備款" value={formatWan(model.loan.downPaymentWan)} />
      <MetricRow label="貸款本金" value={formatWan(model.loan.principalWan)} />
      <MetricRow label="每月房貸支出" value={monthly(model.loan.monthlyPaymentTwd)} />
      <MetricRow label="總利息估算" value={formatTwd(model.loan.totalInterestTwd)} />
      <MetricRow label="利率／年期" value={`${model.loan.annualInterestRate ?? "—"}%／${model.loan.loanYears ?? "—"} 年`} />
      {(model.loan.gracePeriodYears ?? 0) > 0 && <MetricRow label="寬限期／期間月付" value={`${model.loan.gracePeriodYears} 年／${monthly(model.loan.gracePeriodMonthlyPaymentTwd)}`} />}
      {(model.loan.gracePeriodYears ?? 0) > 0 && <MetricRow label="寬限期後月付" value={monthly(model.loan.postGraceMonthlyPaymentTwd ?? model.loan.monthlyPaymentTwd)} />}
    </div>}
  </Panel>;
}

function HoldingSummary({ model, dirty }: { model: FinanceModel; dirty: boolean }) {
  return <Panel variant="plain" data-testid="holding-summary" className="min-w-0">
    <div className="flex flex-wrap items-center justify-between gap-3"><h3 className="text-subsection">持有成本結果</h3><StatusLabel semanticRole={dirty || model.holding.status === "stale" ? "warning" : model.holding.status === "available" ? "information" : "neutral"}>{dirty ? "待重新計算" : model.holding.status === "available" ? "持有成本估算完成" : model.holding.status === "stale" ? "舊條件結果" : "尚未估算"}</StatusLabel></div>
    {model.holding.knownMonthlySubtotalTwd === null ? <p className="mt-5 text-body">尚未有可用的持有成本結果。</p> : <>
      <div className="mt-5"><SummaryStrip label="持有成本小計"><MetricItem label={model.holding.totalKind === "known_subtotal" ? "已估算成本小計" : "每月持有成本估算"} value={monthly(model.holding.knownMonthlySubtotalTwd)} primary /><MetricItem label="每年換算" value={annual(model.holding.knownAnnualSubtotalTwd)} note="每月估算乘以 12" /></SummaryStrip></div>
      <div className="mt-5 max-w-full overflow-x-auto" data-testid="holding-breakdown">
        <table className="w-full min-w-[480px] border-collapse text-dense" aria-label="每月持有成本明細">
          <caption className="ds-visually-hidden">每月持有成本明細</caption>
          <thead><tr className="border-b border-[color:var(--border-strong)] text-left"><th scope="col" className="px-2 py-3">項目</th><th scope="col" className="px-2 py-3">估算狀態</th><th scope="col" className="px-2 py-3 text-right">每月金額</th></tr></thead>
          <tbody>{model.holding.breakdown.map((row) => <tr key={row.key} className="border-b border-[color:var(--border-subtle)]"><th scope="row" className="px-2 py-3 text-left font-medium">{row.label}</th><td className="px-2 py-3">{row.status === "estimated" ? "已估算" : `尚未估算（${row.missingReason}）`}</td><td className="px-2 py-3 text-right tabular-nums">{row.monthlyAmountTwd === null ? "—" : monthly(row.monthlyAmountTwd)}</td></tr>)}</tbody>
        </table>
      </div>
    </>}
  </Panel>;
}

function TaxSummary({ model }: { model: FinanceModel }) {
  return <Panel variant="plain" data-testid="tax-summary">
    <h3 className="text-subsection">稅務條件初步檢查</h3>
    <p className="mt-2 text-number font-semibold">{taxOutcome(model.tax.summary)}</p>
    {model.tax.query === "failed" && <div className="mt-3"><Message variant="error">稅務檢查暫時無法完成；房貸與持有成本結果仍保留。</Message></div>}
    {model.tax.summary ? <dl className="mt-4 space-y-2 text-body">
      <MetricRow label="未符合條件" value={model.tax.summary.failedConditionCount.toLocaleString("zh-TW")} />
      <MetricRow label="需複核項目" value={model.tax.summary.reviewItemCount.toLocaleString("zh-TW")} />
      <MetricRow label="缺少資訊" value={model.tax.summary.missingInformationCount.toLocaleString("zh-TW")} />
      <MetricRow label="來源／生效日" value={`${model.tax.summary.sourceName ?? "未提供"}／${model.tax.summary.effectiveDate ?? "未提供"}`} />
    </dl> : <p className="mt-3 text-body">目前沒有已儲存的稅務條件檢查摘要。</p>}
    <p className="mt-4 text-helper">依目前輸入與固定規則進行初步篩選，不是主管機關核定、個人稅務紀錄或稅務／法律意見。</p>
  </Panel>;
}
