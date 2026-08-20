"use client";

import dynamic from "next/dynamic";
import { useEffect, useRef, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { HelpCallout } from "@/components/help-callout";
import { HeroIntro } from "@/components/hero-intro";
import { HoldingCostCalculator, HoldingCostPrefill, HOLDING_COST_SESSION_KEY, prefillHoldingCost } from "@/components/holding-cost-calculator";
import { LoanCalculator } from "@/components/loan-calculator";
import { LOCATION_INSIGHT_SESSION_KEY, prefillLocationInsight } from "@/components/location-insight";
import { TerrainRiskAnalysis } from "@/components/terrain-risk-analysis";
import { publishWorkspaceContext, WORKSPACE_CONTEXT_SESSION_KEY, type WorkspaceContext } from "@/components/immersive-viewing-workspace";
import { PropertyFinder, PropertyFinderSelection } from "@/components/property-finder";
import { AppPage } from "@/components/sidebar";
import { WorkflowStepper } from "@/components/workflow-stepper";
import { WorkflowEntryCards } from "@/components/workflow-entry-cards";
import { CaseManager } from "@/components/case-manager";
import { CASE_CLEARED_EVENT, CASE_LOADED_EVENT, type SavedCase } from "@/lib/case-storage";
import { Badge, Button, EmptyState, Notice } from "@/components/ui";
import { CaseCard, DecisionHero, ErrorState, LoadingState, MetricTile, ModuleTile, PageHeader, ResultSummaryPanel, SectionCard } from "@/components/product-ui";
import { api, BankInstitution, BankRateResult, downloadTaxReport, GoogleHealth, HoldingCostResult, LoanCalculationResult, MapNearbyResult, MapSearchResult, MarketRegion, MarketRegionCatalog, MarketRequestError, MarketRequestReason, MarketResult, MortgageRateReference, NearbyCategory, NearbyPlace, PropertySearchResult, TaxCase, TaxResult, ValuationDataStatus, ValuationResult, ValuationTrendResult } from "@/lib/api";
import { getMarketDisplayState } from "@/lib/market-result-state";
import { buildMarketInsightVisualModel } from "@/lib/market-insight-visualization";
import { getMarketInsightCopy } from "@/lib/market-insight-copy";
import { DataStatusBadge } from "@/components/data-visualization/data-status-badge";
import { EvidenceDetails } from "@/components/data-visualization/evidence-details";
import { EvidenceSummary } from "@/components/data-visualization/evidence-summary";
import { FreshnessIndicator } from "@/components/data-visualization/freshness-indicator";
import { TrendLineChart } from "@/components/data-visualization/trend-line-chart";
import { VolumeBarChart } from "@/components/data-visualization/volume-bar-chart";
import { MarketInsightEvidencePanel } from "@/components/data-visualization/market-insight-evidence-panel";
import { buildValuationShareUrl, buildValuationSummaryHtml, parseValuationShareParams, valuationSummaryFilename, ValuationInputs } from "@/lib/valuation-share";
import { buildRiskSummary } from "@/lib/risk-summary";
import { buildWorkflowStatus, markTaxOracleCompleted, markWorkflowReportCompleted, OPEN_TAXORACLE_EVENT, readWorkflowSession, type WorkflowStatus } from "@/lib/workflow-status";
import { GUIDED_DEMO_PENDING_KEY, GUIDED_DEMO_RESULT_EVENT, type DemoResults } from "@/lib/demo-runner";
import { DetailDisclosure } from "@/components/detail-disclosure";
import { ViewingDecisionPanel } from "@/components/viewing-decision-panel";
import { ValuationDataFreshness } from "@/components/valuation-data-freshness";
import { getValuationDisplayState, getValuationTrendDisplayState } from "@/lib/valuation-result-state";
import { buildValuationVisualModel } from "@/lib/valuation-visualization";
import { ValuationVisualPanel } from "@/components/data-visualization/valuation-visual-panel";
import { TaxDecisionVisualPanel } from "@/components/data-visualization/tax-decision-visual-panel";
import { OfficialTaxRuleStatusCard } from "@/components/official-data-status-card";
import { ValuationResultBoundary } from "@/components/valuation-result-boundary";
import { buildViewingDecision, type ViewingDecision } from "@/lib/viewing-decision";
import { TAIWAN_COUNTIES, getDistrictsForCounty, normalizeTaiwanCounty, normalizeTaiwanDistrict } from "@/lib/taiwan-admin-areas";
import { GuidedPropertyJourney } from "@/components/guided-journey/guided-property-journey";
import { JourneyToolCard } from "@/components/guided-journey/journey-tool-card";
import { LocationMarketStage } from "@/components/guided-journey/location-market-stage";
import type { JourneyRenderActions, JourneyStepId } from "@/lib/guided-journey";
import type { VoiceAction } from "@/lib/voice-input";
import { getSafeJourneyPropertyContext, type JourneyPropertyContext, type LocationMarketDisplayStatus } from "@/lib/location-market-journey";
import { PriceDecisionStage } from "@/components/guided-journey/price-decision-stage";
import { AffordabilityDecisionStage } from "@/components/guided-journey/affordability-decision-stage";
import { DecisionCaseStage } from "@/components/guided-journey/decision-case-stage";
import { PropertyCaseCommandCenter } from "@/components/property-case-command-center";
import { getSafePriceContext, type JourneyAffordabilityContext, type PriceJourneyDisplayStatus } from "@/lib/price-affordability-journey";
import { hasSearchablePlaceQuery, normalizeTaiwanPlaceQuery } from "@/lib/map-search";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { RuntimeCopyKey } from "@/lib/runtime-copy";
import { getLocalizedCountyLabel, getLocalizedDistrictLabel, getLocalizedRoadLabel, getLocalizedSourceLabel, getLocalizedStateLabel, localizeStructuredSelects } from "@/lib/structured-options";
import { CompetitionTaxOracleDemo } from "@/components/competition-taxoracle-demo";
import { capabilities, COMPETITION_NOTICE, getCompetitionCopy } from "@/lib/competition-release";
import { PilotEvidenceCenter, ProfessionalReviewCenter } from "@/components/pilot-evidence-center";


const GeoMap = dynamic(() => import("@/components/map/geo-map"), { ssr: false, loading: () => <LoadingState label="" /> });
type ResultTab = "原因" | "規則追蹤" | "補件清單" | "五年列管" | "AI 說明";

export default function Home() {
  const { t, locale, copy } = useExperienceLocale();
  useEffect(() => {
    let applying = false;
    const localize = () => {
      if (applying) return;
      applying = true;
      localizeStructuredSelects(document, locale);
      applying = false;
    };
    localize();
    const observer = new MutationObserver((records) => {
      const hasStructuredSelect = records.some((record) => Array.from(record.addedNodes).some((node) => node instanceof Element && (node.matches("select[data-localize-structured-select]") || Boolean(node.querySelector("select[data-localize-structured-select]")))));
      if (hasStructuredSelect) localize();
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [locale]);
  const [page, setPage] = useState<AppPage>("儀表板");
  const [requestedCase, setRequestedCase] = useState("");
  const [journeyPropertyContext, setJourneyPropertyContext] = useState<JourneyPropertyContext>(() => getSafeJourneyPropertyContext(undefined));
  const [journeyValuationResult, setJourneyValuationResult] = useState<ValuationResult>();
  const [journeyPricePrefill, setJourneyPricePrefill] = useState<number>();
  const [journeySecondaryTool, setJourneySecondaryTool] = useState<"holding" | "tax">();
  const [journeyHoldingPrefill, setJourneyHoldingPrefill] = useState<HoldingCostPrefill>();
  const [journeyAffordabilityContext, setJourneyAffordabilityContext] = useState<JourneyAffordabilityContext>(() => ({ loanStatus: "not_started", holdingCostStatus: "not_started", taxOracleStatus: "not_started", missingDataLabels: [copy("dashboard.affordMissingPrice"), copy("dashboard.affordMissingLoan"), copy("dashboard.affordMissingHolding"), copy("dashboard.affordMissingTax")] }));
  useEffect(() => { if (parseValuationShareParams(window.location.search)) setPage("房價估算"); }, []);
  useEffect(() => { const open=()=>setPage("TaxOracle");window.addEventListener(OPEN_TAXORACLE_EVENT,open);return()=>window.removeEventListener(OPEN_TAXORACLE_EVENT,open);}, []);
  const openTax = (caseId = "") => { setRequestedCase(caseId); setPage("TaxOracle"); };
  const openViewingFlow = (target: string) => { window.sessionStorage.setItem("proptech:pending-section", target); setPage("房價估算"); };
  function renderJourneyStep(step: JourneyStepId, actions: JourneyRenderActions) {
    // The property flow does not auto-run analysis or save a case.
    // 不會自動執行估價或保存案件。
    if (step === "property") return <div className="space-y-4"><JourneyToolCard title={t("journey.property.title")} productLabel="Property Finder · Property Search" description={t("journey.property.description")} onOpen={() => openViewingFlow("property-finder")} primary /><p className="rounded-xl bg-stone-50 p-3 text-xs leading-5 text-slate-600">{t("journey.property.contextNote")}</p></div>;
    if (step === "location") return <LocationMarketStage onBackToProperty={() => actions.goToTool("property-finder")} onContinueToPrice={(context) => { setJourneyPropertyContext(context); actions.goToNextStep(); }} onPropertyContextChange={setJourneyPropertyContext} onMap={() => setPage("Map Insight Lite")} renderMarket={(context: JourneyPropertyContext, handlers: { onStatusChange: (status: LocationMarketDisplayStatus) => void; onResult: (result: MarketResult | null) => void }) => <MarketInsight embedded initialCounty={context.city} initialDistrict={context.district} onMap={() => setPage("Map Insight Lite")} onStatusChange={handlers.onStatusChange} onResult={handlers.onResult} />} />;
    if (step === "price") return <PriceDecisionStage propertyContext={journeyPropertyContext} onBackToLocation={() => actions.goToTool("location-insight")} onContinueToAffordability={actions.goToNextStep} onTransferToLoan={(priceWan) => { setJourneyPricePrefill(priceWan); setJourneySecondaryTool(undefined); setJourneyHoldingPrefill(undefined); actions.goToNextStep(); }} onTransferToHolding={(priceWan, areaPing) => { setJourneyPricePrefill(priceWan); setJourneySecondaryTool("holding"); setJourneyHoldingPrefill({ property_price: priceWan, area_ping: areaPing }); actions.goToNextStep(); }} renderValuation={(context, handlers) => <ValuationPage embedded initialContext={context} onResult={(result) => { setJourneyValuationResult(result); handlers.onResult(result); }} onStatusChange={handlers.onStatusChange} />} renderPropertySearch={() => <PropertyFinder embedded onUseForValuation={() => actions.goToTool("valuation")} onUseForLoan={(priceWan) => { setJourneyPricePrefill(priceWan); actions.goToNextStep(); }} onUseForHoldingCost={(priceWan, areaPing) => { setJourneyPricePrefill(priceWan); setJourneySecondaryTool("holding"); setJourneyHoldingPrefill({ property_price: priceWan, area_ping: areaPing }); actions.goToNextStep(); }} onUseForLocationInsight={() => actions.goToTool("location-insight")} />} />;
    if (step === "affordability") return <div><p className="rounded-lg bg-amber-50 px-3 py-2 text-xs leading-5 text-amber-900">{t("trust.fundingBoundary")}</p><AffordabilityDecisionStage propertyContext={journeyPropertyContext} priceContext={getSafePriceContext({ propertyContext: journeyPropertyContext, result: journeyValuationResult })} explicitPriceWan={journeyPricePrefill} initialSecondaryTool={journeySecondaryTool} initialHoldingPrefill={journeyHoldingPrefill} renderLoan={(priceWan, handlers) => <LoanCalculator embedded propertyPriceWan={priceWan} onResult={handlers.onResult} onHoldingCost={handlers.onHoldingCost} />} renderHolding={(prefill, handlers) => <HoldingCostCalculator embedded prefill={prefill} onResult={handlers.onResult} />} renderTax={(handlers) => <TaxOracle embedded requestedCase="" onResult={handlers.onResult} />} onContextChange={setJourneyAffordabilityContext} onBackToPrice={() => actions.goToTool("valuation")} onContinueToDecision={actions.goToNextStep} /></div>;
    return <DecisionCaseStage propertyContext={journeyPropertyContext} priceContext={getSafePriceContext({ propertyContext: journeyPropertyContext, result: journeyValuationResult })} affordabilityContext={journeyAffordabilityContext} renderCommandCenter={() => <PropertyCaseCommandCenter embedded caseId="journey-decision" showComparison={false} />} renderSavedCases={() => <CaseManager listOnly />} onBackToProperty={() => actions.goToTool("property-finder")} onBackToPrice={() => actions.goToTool("valuation")} onBackToAffordability={() => actions.goToTool("loan")} onNavigateToAction={(action) => { if (action === "property") actions.goToTool("property-finder"); if (action === "price") actions.goToTool("valuation"); if (action === "affordability") actions.goToTool("loan"); }} />;
  }
  const handleTourAction = (action: "tax-low" | "map" | "explore") => {
    if (action === "tax-low") openTax("DEMO-LOW");
    if (action === "map") setPage("Map Insight Lite");
  };
  const handleVoiceAction = (action: VoiceAction) => {
    if (action.type === "navigate_step") {
      setPage("儀表板");
      window.dispatchEvent(new CustomEvent("proptech:select-journey-step", { detail: action.step }));
    }
    if (action.type === "focus_field") document.getElementById(action.field)?.focus();
    if (action.type === "stop_read_aloud") window.dispatchEvent(new Event("proptech:stop-read-aloud"));
    if (action.type === "repeat_summary") window.dispatchEvent(new Event("proptech:repeat-read-aloud"));
  };
  return <AppShell page={page} onNavigate={setPage} onTourAction={handleTourAction} onVoiceAction={handleVoiceAction}>{page === "儀表板" ? <><CompetitionMvpBanner onDemo={() => setPage("Competition Demo" as AppPage)} onEvidence={() => setPage("Evidence Center" as AppPage)} onPilot={() => setPage("Closed Pilot")} /><GuidedPropertyJourney renderStep={renderJourneyStep} /></> : renderPage(page, setPage, openTax, requestedCase)}</AppShell>;
}

function renderPage(page: AppPage, setPage: (page: AppPage) => void, openTax: (caseId?: string) => void, requestedCase: string) {
  if (page === ("Competition Demo" as AppPage)) return <CompetitionTaxOracleDemo onEvidence={() => setPage("Evidence Center" as AppPage)} onPrivacy={() => setPage("Privacy" as AppPage)} onTerms={() => setPage("Terms" as AppPage)} />;
  if (page === ("Evidence Center" as AppPage)) return <EvidenceCenter onBack={() => setPage("Competition Demo" as AppPage)} onPilot={() => setPage("Closed Pilot")} />;
  if (page === ("Privacy" as AppPage)) return <PublicPolicyPage kind="privacy" onBack={() => setPage("Competition Demo" as AppPage)} />;
  if (page === ("Terms" as AppPage)) return <PublicPolicyPage kind="terms" onBack={() => setPage("Competition Demo" as AppPage)} />;
  if (page === "Closed Pilot") return <PilotEvidenceCenter />;
  if (page === "Professional Review") return <ProfessionalReviewCenter />;
  if (page === "TaxOracle") return <TaxOracle requestedCase={requestedCase} />;
  if (page === "Market Insight Lite") return <MarketInsight onMap={() => setPage("Map Insight Lite")} />;
  if (page === "Map Insight Lite") return <MapInsight />;
  if (page === "房價估算") return <ValuationPage onMap={() => setPage("Map Insight Lite")} />;
  if (page === "Aegis-Credit Lite") return <AegisCredit />;
  if (page === "Terrain Risk") return <TerrainRiskPage />;
  return <Dashboard setPage={setPage} openTax={openTax} />;
}

function EvidenceCenter({ onBack, onPilot }: { onBack: () => void; onPilot: () => void }) {
  const { locale } = useExperienceLocale();
  const copy = getCompetitionCopy(locale);
  return <div className="space-y-5" data-testid="evidence-center"><PageHeader kicker="Evidence" title={copy.evidence} description="A canonical capability matrix distinguishes implemented, tested, source-dependent and planned surfaces." /><div className="grid gap-3 md:grid-cols-2">{capabilities.map((item) => <article key={item.id} className="rounded-xl border border-stone-200 bg-white p-4"><div className="flex items-start justify-between gap-3"><h2 className="text-sm font-bold text-slate-950">{item.name}</h2><span className={`rounded-full px-2 py-1 text-[10px] font-bold ${item.implementation === "planned" ? "bg-stone-100 text-slate-600" : "bg-cyan-50 text-cyan-800"}`}>{item.implementation}</span></div><p className="mt-2 text-xs leading-5 text-slate-600">Role: {item.role}; browser: {item.browser}; source: {item.source}; validation: {item.validation}; production: {item.production}.</p><p className="mt-2 text-xs leading-5 text-slate-500">{item.limitation}</p></article>)}</div><div className="grid gap-4 lg:grid-cols-2"><section className="rounded-xl border border-stone-200 bg-white p-4"><h2 className="font-bold text-slate-950">Method and evidence record</h2><p className="mt-2 text-sm leading-6 text-slate-600">Calculations use existing deterministic services. Rule IDs, version, source status, missing facts and limitations are shown with each result. Customer interviews, paid pilots, accuracy and time-saving evidence are not yet validated.</p></section><section className="rounded-xl border border-stone-200 bg-white p-4"><h2 className="font-bold text-slate-950">Human review boundary</h2><p className="mt-2 text-sm leading-6 text-slate-600">Tax professionals, banks, appraisers, lawyers and relevant government agencies remain the source of final decisions. No feature here produces a purchase recommendation.</p></section></div><div className="flex flex-wrap gap-2"><Button onClick={onPilot}>Join closed pilot</Button><Button secondary onClick={onBack}>{copy.primary}</Button></div></div>;
}

function PublicPolicyPage({ kind, onBack }: { kind: "privacy" | "terms"; onBack: () => void }) {
  const { locale } = useExperienceLocale();
  const copy = getCompetitionCopy(locale);
  const privacy = kind === "privacy";
  return <div className="mx-auto max-w-3xl space-y-5" data-testid={privacy ? "privacy-page" : "terms-page"}><PageHeader kicker="Public policy" title={privacy ? copy.privacy : copy.terms} description={privacy ? "Current storage and browser behavior, stated without promises beyond the product." : COMPETITION_NOTICE} /><section className="space-y-4 rounded-xl border border-stone-200 bg-white p-5 text-sm leading-7 text-slate-700">{privacy ? <><p>Property Cases contain user-entered case facts and selected analysis outputs. Browser-only interaction such as speech recognition uses the browser-native capability; audio is not sent by this product to an external speech provider.</p><p>Runtime provider responses, raw coordinates and raw provider payloads are not intentionally stored as a public case record. Saved case behavior is limited by the current browser storage implementation; users should remove saved cases from the product when available.</p><p>No contact or deletion channel is configured in this release. Do not enter secrets or information you are not authorized to process. Provider availability and retention behavior can change.</p></> : <><p>TaxOracle is a preliminary screening and rule-trace surface. It is not an official tax assessment, legal opinion, appraisal, loan approval, safety guarantee, investment score or purchase recommendation.</p><p>Holding Cost is an illustrative current-input estimate, not an actual bill or quote. Location, terrain, market and financing modules are supporting reference tools and do not replace professional review.</p><p>Missing, stale or unavailable data must be treated as unresolved. Users are responsible for confirming facts with tax professionals, banks, appraisers, lawyers, land agents and government agencies before acting.</p></>}</section><Button secondary onClick={onBack}>{copy.primary}</Button></div>;
}

function Dashboard({ setPage, openTax }: { setPage: (page: AppPage) => void; openTax: (caseId?: string) => void }) {
  const { copy } = useExperienceLocale();
  const [selectedCase, setSelectedCase] = useState("DEMO-LOW");
  const [reportReady, setReportReady] = useState(false);
  const [workflowStatus,setWorkflowStatus]=useState<WorkflowStatus>(()=>buildWorkflowStatus({}));
  const [viewingDecision,setViewingDecision]=useState<ViewingDecision>(()=>buildViewingDecision({}));
  useEffect(()=>{try{const stored=window.sessionStorage.getItem(WORKSPACE_CONTEXT_SESSION_KEY),context=stored?JSON.parse(stored) as WorkspaceContext:undefined;const holdingValue=window.sessionStorage.getItem(HOLDING_COST_SESSION_KEY),locationValue=window.sessionStorage.getItem(LOCATION_INSIGHT_SESSION_KEY),holding=holdingValue?JSON.parse(holdingValue) as HoldingCostResult:undefined,location=locationValue?JSON.parse(locationValue):undefined,riskSummary=buildRiskSummary({propertySearch:context?.propertySearch,valuation:context?.valuation,trend:context?.trend,loan:context?.loan,holding,location}),session=readWorkflowSession();setReportReady(Boolean(context?.valuation));setWorkflowStatus(buildWorkflowStatus({propertySearch:context?.propertySearch,valuation:context?.valuation,loan:context?.loan,holding,location,riskSummary,...session}));setViewingDecision(buildViewingDecision({valuation:context?.valuation,loan:context?.loan,holding,location,riskSummary,taxOracleResult:session.taxOracleResult}));}catch{setReportReady(false);setViewingDecision(buildViewingDecision({}));}},[]);
  function openViewingFlow(target: string) { window.sessionStorage.setItem("proptech:pending-section", target); setPage("房價估算"); }
  function openViewingDecisionTarget(target: string) { if (target === "taxoracle") { setPage("TaxOracle"); return; } if (target === "terrain-risk-analysis") { setPage("Terrain Risk"); return; } openViewingFlow(target); }
  function continueWorkflow(){if(workflowStatus.nextActionTargetId==="taxoracle"){setPage("TaxOracle");return;}openViewingFlow(workflowStatus.nextActionTargetId);}
  function openAdvanced(){const advanced=document.getElementById("advanced-tools") as HTMLDetailsElement|null;if(advanced){advanced.open=true;advanced.scrollIntoView({behavior:"smooth",block:"start"});}}
  function openCaseComparison(){document.getElementById("recent-cases")?.scrollIntoView({behavior:"smooth",block:"start"});}
  function startGuidedDemo(){window.sessionStorage.setItem(GUIDED_DEMO_PENDING_KEY,"true");openViewingFlow("immersive-workspace");}
  function exportSavedCase(saved:SavedCase){if(!saved.data.valuation)return;const html=buildValuationSummaryHtml(saved.data.inputs,saved.data.valuation,saved.data.trend,saved.data.propertySearch,saved.data.loan,saved.data.holdingCost,saved.data.locationInsight,saved.data.terrainReference);const url=URL.createObjectURL(new Blob([html],{type:"text/html;charset=utf-8"})),link=document.createElement("a");link.href=url;link.download=valuationSummaryFilename();link.click();URL.revokeObjectURL(url);}
  return <div className="space-y-6">
    <CompetitionMvpBanner onDemo={() => setPage("Competition Demo" as AppPage)} onEvidence={() => setPage("Evidence Center" as AppPage)} onPilot={() => setPage("Closed Pilot")} />
    <HeroIntro onStart={() => openViewingFlow("property-finder")} onWorkspace={() => openViewingFlow("immersive-workspace")} reportReady={reportReady} onReport={() => openViewingFlow("decision-report")} workflowStatus={workflowStatus} />
    <details id="secondary-entry-points" className="rounded-2xl border border-stone-200 bg-white shadow-sm">
      <summary className="cursor-pointer px-5 py-4 text-sm font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-cyan-500">{copy("dashboard.otherTools")}</summary>
      <div className="space-y-4 border-t border-stone-100 p-4 sm:p-5"><DecisionFlowEntry onStart={() => openViewingFlow("property-finder")} onDemo={startGuidedDemo} /><DecisionWorkspaceSteps onFinder={() => openViewingFlow("property-finder")} onLocation={() => openViewingFlow("location-insight-calculator")} onMap={() => setPage("Map Insight Lite")} onValuation={() => setPage("房價估算")} onDecision={() => openViewingFlow("decision-report")} onTax={() => openTax(selectedCase)} onCases={openCaseComparison} /></div>
    </details>
    <section className="rounded-2xl border border-stone-200 bg-white p-4 shadow-sm sm:p-5"><div className="mb-3 flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-[10px] font-bold tracking-wider text-cyan-700">STEP 4</p><h2 className="text-base font-bold text-slate-950">{copy("dashboard.viewingDecision")}</h2></div><p className="text-xs leading-5 text-slate-500">{copy("dashboard.viewingDisclaimer")}</p></div><ViewingDecisionPanel decision={viewingDecision} onNext={openViewingDecisionTarget} /></section>
    <details id="decision-next-actions" className="rounded-2xl border border-stone-200 bg-white shadow-sm"><summary className="cursor-pointer px-5 py-4 text-sm font-bold text-slate-800">{copy("dashboard.nextActions")}</summary><div className="space-y-4 border-t border-stone-100 p-4 sm:p-5"><WorkflowEntryCards onStartBuying={continueWorkflow} onOpenTax={() => openTax(selectedCase)} onOpenAdvanced={openAdvanced} onGuidedDemo={startGuidedDemo} onOpenCompare={openCaseComparison} /><div id="recent-cases" className="scroll-mt-20"><CaseManager listOnly onLoaded={(saved) => saved.activeWizardStep === "tax" ? openTax() : setPage("房價估算")} onExport={exportSavedCase} /></div></div></details>
    <HelpCallout>{copy("dashboard.helpMain")}</HelpCallout>
    <details id="advanced-tools" className="scroll-mt-20 rounded-2xl border border-stone-200 bg-white shadow-sm"><summary className="cursor-pointer px-5 py-4 text-sm font-bold text-slate-800">{copy("dashboard.advancedTools")}</summary><div className="space-y-6 border-t border-stone-100 p-4 sm:p-5"><DecisionHero onPrimary={() => openTax(selectedCase)} onSecondary={() => setPage("Map Insight Lite")} /><section><SectionTitle title={copy("dashboard.taxExamples")} note={copy("dashboard.taxExamplesNote")} /><div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3"><CaseCard title={copy("dashboard.caseLow")} status="eligible" signal="green" description={copy("dashboard.caseLowDesc")} selected={selectedCase === "DEMO-LOW"} onSelect={() => setSelectedCase("DEMO-LOW")} onOpen={() => openTax("DEMO-LOW")} /><CaseCard title={copy("dashboard.caseMedium")} status="manual_review" signal="yellow" description={copy("dashboard.caseMediumDesc")} selected={selectedCase === "DEMO-MEDIUM"} onSelect={() => setSelectedCase("DEMO-MEDIUM")} onOpen={() => openTax("DEMO-MEDIUM")} /><CaseCard title={copy("dashboard.caseHigh")} status="not_eligible" signal="red" description={copy("dashboard.caseHighDesc")} selected={selectedCase === "DEMO-HIGH"} onSelect={() => setSelectedCase("DEMO-HIGH")} onOpen={() => openTax("DEMO-HIGH")} /></div></section><section><SectionTitle title={copy("dashboard.supplementTools")} note={copy("dashboard.supplementToolsNote")} /><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5"><ModuleTile hint="TAX" title={copy("dashboard.taxModule")} description={copy("dashboard.taxModuleDesc")} tone="cyan" onClick={() => openTax(selectedCase)} /><ModuleTile hint="MAP" title={copy("dashboard.mapModule")} description={copy("dashboard.mapModuleDesc")} tone="green" onClick={() => setPage("Map Insight Lite")} /><ModuleTile hint="MARKET" title={copy("dashboard.marketModule")} description={copy("dashboard.marketModuleDesc")} tone="amber" onClick={() => setPage("Market Insight Lite")} /><ModuleTile hint="RATE" title={copy("dashboard.rateModule")} description={copy("dashboard.rateModuleDesc")} tone="violet" onClick={() => setPage("Aegis-Credit Lite")} /><ModuleTile hint="VALUE" title={copy("dashboard.valuationModule")} description={copy("dashboard.valuationModuleDesc")} tone="cyan" onClick={() => setPage("房價估算")} /></div></section></div></details>
  </div>;
}

function CompetitionMvpBanner({ onDemo, onEvidence, onPilot }: { onDemo: () => void; onEvidence: () => void; onPilot: () => void }) {
  const { locale } = useExperienceLocale();
  const copy = getCompetitionCopy(locale);
  return <section data-testid="competition-mvp-banner" className="rounded-2xl border border-cyan-200 bg-cyan-50/80 p-4 shadow-sm sm:p-5"><div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between"><div><p className="text-[10px] font-bold tracking-[0.16em] text-cyan-800">{copy.eyebrow}</p><h2 className="mt-1 text-xl font-black text-slate-950">{copy.title}</h2><p className="mt-2 max-w-3xl text-sm leading-6 text-slate-700">{copy.description}</p><p className="mt-2 text-xs font-semibold text-amber-800">{copy.boundary}</p></div><div className="flex shrink-0 flex-col gap-2 sm:flex-row"><span data-testid="competition-demo-start"><Button onClick={onDemo}>{copy.primary}</Button></span><Button secondary onClick={onEvidence}>{copy.evidence}</Button><Button secondary onClick={onPilot}>Join closed pilot</Button></div></div></section>;
}

function DecisionFlowEntry({ onStart, onDemo }: { onStart: () => void; onDemo: () => void }) {
  const { copy } = useExperienceLocale();
  return <section className="rounded-2xl border border-cyan-100 bg-white p-4 shadow-sm sm:p-5"><div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_320px] lg:items-center"><div><p className="text-[10px] font-bold tracking-wider text-cyan-700">{copy("dashboard.flowDetailDescription")}</p><h2 className="mt-1 text-2xl font-black tracking-tight text-slate-950">{copy("dashboard.flowHeading")}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{copy("dashboard.flowDescription")}</p><div className="mt-4 flex flex-col gap-2 sm:flex-row sm:flex-wrap"><Button className="w-full sm:w-auto" onClick={onStart}>{copy("dashboard.startFinder")}</Button><Button secondary className="w-full sm:w-auto" onClick={onDemo}>{copy("dashboard.runDemo")}</Button></div></div><div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2 lg:grid-cols-1"><FlowStep number="1" title={copy("dashboard.step1")} note={copy("dashboard.step1Note")} /><FlowStep number="2" title={copy("dashboard.step2")} note={copy("dashboard.step2Note")} /><FlowStep number="3" title={copy("dashboard.step3")} note={copy("dashboard.step3Note")} /><FlowStep number="4" title={copy("dashboard.step4")} note={copy("dashboard.step4Note")} /></div></div></section>;
}

function DecisionWorkspaceSteps({ onFinder, onLocation, onMap, onValuation, onDecision, onTax, onCases }: { onFinder: () => void; onLocation: () => void; onMap: () => void; onValuation: () => void; onDecision: () => void; onTax: () => void; onCases: () => void }) {
  const { copy } = useExperienceLocale();
  return <section aria-label={copy("dashboard.flowDetailDescription")} className="space-y-3">
    <WorkspaceStep number="1" title={copy("dashboard.ws1Title")} summary={copy("dashboard.ws1Summary")} actionLabel={copy("dashboard.ws1Action")} onAction={onFinder} defaultOpen>
      <CapabilityPills items={["Property Finder", "實價登錄候選路段", "帶入估價／貸款／區位"]} />
      <p className="text-xs leading-5 text-slate-500">{copy("dashboard.ws1Note")}</p>
    </WorkspaceStep>
    <WorkspaceStep number="2" title={copy("dashboard.ws2Title")} summary={copy("dashboard.ws2Summary")} actionLabel={copy("dashboard.ws2Action")} onAction={onLocation} secondaryLabel={copy("dashboard.ws2Secondary")} onSecondary={onMap}>
      <CapabilityPills items={["Location Insight", "Terrain Risk", "風險資料來源與限制", "Commute Livability Card"]} />
      <p className="text-xs leading-5 text-amber-700">{copy("dashboard.ws2Note")}</p>
    </WorkspaceStep>
    <WorkspaceStep number="3" title={copy("dashboard.ws3Title")} summary={copy("dashboard.ws3Summary")} actionLabel={copy("dashboard.ws3Action")} onAction={onValuation} secondaryLabel={copy("dashboard.ws3Secondary")} onSecondary={onTax}>
      <CapabilityPills items={["Valuation 價格合理性", "Aegis Credit／貸款", "Holding Cost", "TaxOracle 稅務快篩", "Market Insight"]} />
      <p className="text-xs leading-5 text-slate-500">{copy("dashboard.ws3Note")}</p>
    </WorkspaceStep>
    <WorkspaceStep number="4" title={copy("dashboard.ws4Title")} summary={copy("dashboard.ws4Summary")} actionLabel={copy("dashboard.ws4Action")} onAction={onDecision} secondaryLabel={copy("dashboard.ws4Secondary")} onSecondary={onCases}>
      <CapabilityPills items={["Viewing Decision Panel", "Decision Report", "Case Manager", "Case Comparison", "列印／另存 PDF"]} />
      <p className="text-xs leading-5 text-slate-500">{copy("dashboard.ws4Note")}</p>
    </WorkspaceStep>
  </section>;
}

function FlowStep({ number, title, note }: { number: string; title: string; note: string }) {
  return <div className="rounded-xl border border-cyan-100 bg-white/80 p-3"><div className="flex items-start gap-3"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-cyan-700 text-xs font-black text-white">{number}</span><span><strong className="block text-slate-900">{title}</strong><span className="text-[11px] leading-5 text-slate-500">{note}</span></span></div></div>;
}

function WorkspaceStep({ number, title, summary, actionLabel, onAction, secondaryLabel, onSecondary, defaultOpen, children }: { number: string; title: string; summary: string; actionLabel: string; onAction: () => void; secondaryLabel?: string; onSecondary?: () => void; defaultOpen?: boolean; children: ReactNode }) {
  const { copy } = useExperienceLocale();
  return <details className="rounded-2xl border border-stone-200 bg-white shadow-sm" open={defaultOpen}><summary className="cursor-pointer px-4 py-3"><span className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between"><span className="flex items-center gap-3"><span className="grid h-7 w-7 shrink-0 place-items-center rounded-full bg-slate-900 text-xs font-black text-white">{number}</span><span><span className="block text-sm font-bold text-slate-950">{title}</span><span className="block text-xs font-normal leading-5 text-slate-500">{summary}</span></span></span><span className="text-[10px] font-bold text-cyan-700">{copy("dashboard.expand")}</span></span></summary><div className="space-y-3 border-t border-stone-100 p-4">{children}<div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap"><Button className="w-full sm:w-auto" onClick={onAction}>{actionLabel}</Button>{secondaryLabel && onSecondary && <Button secondary className="w-full sm:w-auto" onClick={onSecondary}>{secondaryLabel}</Button>}</div></div></details>;
}

function CapabilityPills({ items }: { items: string[] }) {
  return <div className="flex flex-wrap gap-1.5">{items.map((item) => <span key={item} className="rounded-full bg-stone-100 px-2.5 py-1 text-[10px] font-bold text-slate-600">{item}</span>)}</div>;
}

function SectionTitle({ title, note }: { title: string; note: string }) {
  return <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-4 gap-y-1"><h2 className="text-base font-bold text-slate-950">{title}</h2><p className="break-words text-xs text-slate-500">{note}</p></div>;
}

function TaxOracle(props: { requestedCase: string; embedded?: boolean; onResult?: (result: TaxResult) => void }) {
  const { locale } = useExperienceLocale();
  return <div className="space-y-3"><Notice tone="warning">{getLocalizedStateLabel("reference_only", locale)}. {locale === "en" ? "Tax output is an advisory reference, not an official ruling." : locale === "ja" ? "税務結果は参考情報であり、公式な判断ではありません。" : locale === "ko" ? "세금 결과는 참고용이며 공식 판정이 아닙니다." : "稅務結果僅供參考，不是官方核定。"}</Notice><LegacyTaxOracle {...props} /></div>;
}

function LegacyTaxOracle({ requestedCase, embedded = false, onResult }: { requestedCase: string; embedded?: boolean; onResult?: (result: TaxResult) => void }) {
  const { copy } = useExperienceLocale();
  const [cases, setCases] = useState<TaxCase[]>([]), [selectedCase, setSelectedCase] = useState(""), [customInput, setCustomInput] = useState<TaxCase>(emptyCustomTaxCase()), [result, setResult] = useState<TaxResult>(), [error, setError] = useState(""), [loading, setLoading] = useState(true), [isRunning, setIsRunning] = useState(false), [tab, setTab] = useState<ResultTab>("原因");
  useEffect(() => { api.demoCases().then((rows) => { setCases(rows); setSelectedCase(requestedCase && rows.some((r) => r.case_id === requestedCase) ? requestedCase : rows[0]?.case_id ?? ""); }).catch(() => setError(copy("tax.errorLoad"))).finally(() => setLoading(false)); }, [requestedCase]);
  const taxCase = selectedCase === "CUSTOM" ? customInput : cases.find((item) => item.case_id === selectedCase);
  const activeStep = isRunning ? 2 : result ? 3 : 1;
  async function analyze() { if (!taxCase) return; setIsRunning(true); setError(""); setResult(undefined); try { const next=await api.runTaxOracleCase(taxCase);setResult(next);onResult?.(next);markTaxOracleCompleted(next);setTab("原因"); } catch { setError(copy("tax.errorApi")); } finally { setIsRunning(false); } }
  function selectCase(caseId:string){setSelectedCase(caseId);setResult(undefined);setError("");setTab("原因");}
  function reset() { setResult(undefined); setSelectedCase(cases[0]?.case_id ?? ""); setCustomInput(emptyCustomTaxCase()); setError(""); setTab("原因"); }
  return <div id="taxoracle" className="scroll-mt-20 space-y-5">
    {!embedded && <PageHeader kicker={copy("tax.kicker")} title={copy("tax.title")} description={copy("tax.description")} />}
    {!embedded && <HelpCallout>{copy("tax.help")}</HelpCallout>}
    {!embedded && <WorkflowStepper activeStep={activeStep} />}
    {error && <ErrorState message={error} />}
    <div className="grid items-start gap-4 lg:grid-cols-[38%_minmax(0,62%)]">
      <SectionCard title={copy("tax.select")} description={copy("tax.help")}>
        <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">{cases.map((item, index) => <button key={item.case_id} disabled={loading} onClick={() => selectCase(item.case_id)} className={`flex items-center justify-between rounded-lg border px-3 py-2.5 text-left transition ${selectedCase === item.case_id ? "border-cyan-500 bg-cyan-50 ring-2 ring-cyan-100" : "border-stone-200 bg-white hover:border-stone-300"}`}><span><span className="block text-[9px] font-bold tracking-wider text-slate-400">{copy("tax.caseLabel")}</span><span className="mt-0.5 block text-xs font-bold text-slate-800">{[copy("dashboard.caseLow"), copy("dashboard.caseMedium"), copy("dashboard.caseHigh")][index] ?? item.case_id}</span><span className="mt-0.5 block text-[10px] text-slate-400">{item.case_id}</span></span><span className={`h-2 w-2 rounded-full ${index === 0 ? "bg-emerald-500" : index === 1 ? "bg-amber-500" : "bg-rose-500"}`} /></button>)}<button type="button" onClick={()=>selectCase("CUSTOM")} className={`rounded-lg border px-3 py-3 text-left transition ${selectedCase==="CUSTOM"?"border-violet-500 bg-violet-50 ring-2 ring-violet-100":"border-stone-200 bg-white hover:border-violet-300"}`}><span className="block text-[9px] font-bold tracking-wider text-violet-600">{copy("tax.customEditable")}</span><span className="mt-1 block text-xs font-bold text-slate-800">{copy("tax.customCase")}</span></button></div>
        {loading ? <div className="mt-4"><LoadingState label={copy("action.loading")} /></div> : selectedCase==="CUSTOM" ? <CustomTaxCaseForm value={customInput} onChange={(next)=>{setCustomInput(next);setResult(undefined);}} /> : taxCase && <CasePreview taxCase={taxCase} />}
        <div className="mt-4 flex flex-col gap-2 sm:flex-row"><Button disabled={loading || isRunning || !taxCase} onClick={analyze} className="w-full flex-1 bg-cyan-700 hover:bg-cyan-800">{isRunning ? copy("tax.running") : copy("tax.start")}</Button><button onClick={reset} className="px-2 py-2 text-xs font-bold text-slate-400 hover:text-slate-700">{copy("tax.reset")}</button></div>
        <p className="mt-2 text-[10px] leading-5 text-slate-400">{copy("tax.apiNote")}</p>
      </SectionCard>
      <TaxSummary result={result} taxCase={taxCase} isRunning={isRunning} />
    </div>
    {result ? <TaxResultTabs result={result} tab={tab} setTab={setTab} /> : <EmptyState title={isRunning?copy("tax.runningTitle"):copy("tax.waitingTitle")} detail={isRunning?copy("tax.runningDetail"):copy("tax.waitingDetail")} />}
  </div>;
}

function CasePreview({ taxCase }: { taxCase: TaxCase }) {
  const { copy } = useExperienceLocale();
  const items = [[copy("tax.previewCase"), taxCase.case_id], [copy("tax.previewClient"), taxCase.client_name], [copy("tax.previewSoldSelf"), yesNo(taxCase.sold_self_occupied, copy)], [copy("tax.previewPurchasedSelf"), yesNo(taxCase.purchased_self_occupied, copy)], [copy("tax.previewDocs"), yesNo(taxCase.required_docs_complete, copy)], [copy("tax.previewMonitor"), yesNo(taxCase.enters_five_year_monitoring, copy)]];
  return <div className="mt-4 divide-y divide-slate-100 border-y border-slate-200">{items.map(([label, value]) => <div key={label} className="flex justify-between py-2.5 text-xs"><span className="text-slate-500">{label}</span><span className="font-bold text-slate-800">{value}</span></div>)}</div>;
}
const yesNo = (value: boolean, copy: RuntimeCopy) => value ? copy("common.yes") : copy("common.no");

function emptyCustomTaxCase():TaxCase{return{case_id:"CUSTOM-001",client_name:"自訂案件",sold_self_occupied:true,residency_condition_met:true,purchase_within_reasonable_period:true,purchased_self_occupied:true,same_owner:true,land_value_available:true,required_docs_complete:true,enters_five_year_monitoring:true,exceptional_circumstances:false};}

function CustomTaxCaseForm({value,onChange}:{value:TaxCase;onChange:(value:TaxCase)=>void}){
  const { copy } = useExperienceLocale();
  const fields:[Exclude<keyof TaxCase,"case_id"|"client_name">,string][]=[["sold_self_occupied",copy("tax.fieldSold")],["residency_condition_met",copy("tax.fieldResidency")],["purchase_within_reasonable_period",copy("tax.fieldPeriod")],["purchased_self_occupied",copy("tax.fieldPurchased")],["same_owner",copy("tax.fieldOwner")],["land_value_available",copy("tax.fieldLandValue")],["required_docs_complete",copy("tax.fieldDocs")],["enters_five_year_monitoring",copy("tax.fieldMonitor")],["exceptional_circumstances",copy("tax.fieldException")]];
  return <div className="mt-4 rounded-xl border border-violet-200 bg-violet-50/40 p-3"><div className="grid gap-2 sm:grid-cols-2"><label className="text-xs text-slate-500">{copy("tax.caseIdLabel")}<input className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs" value={value.case_id} onChange={(e)=>onChange({...value,case_id:e.target.value})}/></label><label className="text-xs text-slate-500">{copy("tax.caseNameLabel")}<input className="mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2 text-xs" value={value.client_name} onChange={(e)=>onChange({...value,client_name:e.target.value})}/></label></div><div className="mt-3 grid gap-2 sm:grid-cols-2">{fields.map(([key,label])=><label key={key} className="flex items-center justify-between gap-3 rounded-lg border border-stone-200 bg-white px-3 py-2 text-xs text-slate-600"><span>{label}</span><select className="rounded-md border border-stone-300 px-2 py-1 text-xs font-bold" value={String(value[key])} onChange={(e)=>onChange({...value,[key]:e.target.value==="true"})}><option value="true">{copy("common.yes")}</option><option value="false">{copy("common.no")}</option></select></label>)}</div></div>;
}

function TaxSummary({ result, taxCase, isRunning }: { result?: TaxResult; taxCase?: TaxCase; isRunning: boolean }) {
  const { copy } = useExperienceLocale();
  const [downloading, setDownloading] = useState(false), [error, setError] = useState("");
  async function download() { if (!taxCase) return; setDownloading(true); setError(""); try { await downloadTaxReport(taxCase); } catch { setError(copy("tax.reportUnavailable")); } finally { setDownloading(false); } }
  return !result ? <ResultSummaryPanel className="lg:sticky lg:top-16"><div className="p-5">{isRunning ? <LoadingState label={copy("tax.running")} /> : <><EmptyState title={copy("tax.waitingTitle")} detail={copy("tax.waitingDetail")} /><Button disabled className="mt-3 w-full">{copy("tax.reportDisabled")}</Button></>}</div></ResultSummaryPanel> : <div className="space-y-3"><TaxDecisionVisualPanel result={result} taxCase={taxCase} downloading={downloading} error={error} onDownload={download} /><OfficialTaxRuleStatusCard trace={result.official_rule_trace} /></div>;
}

function RiskGauge({ score, signal }: { score: number; signal: string }) { const { copy } = useExperienceLocale(); const color = signal === "green" ? "#10b981" : signal === "yellow" ? "#f59e0b" : "#f43f5e"; return <div role="img" aria-label={`${copy("tax.riskScore")} ${score}, ${signal}`} className="grid place-items-center"><div className="grid h-32 w-32 place-items-center rounded-full" style={{ background: `conic-gradient(${color} ${score * 3.6}deg, #e7e5e4 0deg)` }}><div className="grid h-24 w-24 place-items-center rounded-full bg-white text-center"><div><p className="text-3xl font-bold text-slate-950">{score}</p><p className="text-[9px] font-bold text-slate-400">{copy("tax.riskScore")}</p></div></div></div><p className="mt-2 text-xs text-slate-700">{copy("tax.signalNote", { signal })}</p></div>; }

function TaxResultTabs({ result, tab, setTab }: { result: TaxResult; tab: ResultTab; setTab: (tab: ResultTab) => void }) {
  const { copy } = useExperienceLocale();
  const tabs: ResultTab[] = ["原因", "規則追蹤", "補件清單", "五年列管", "AI 說明"];
  const tabLabels: Record<ResultTab, string> = { "原因": copy("tax.tabReason"), "規則追蹤": copy("tax.tabTrace"), "補件清單": copy("tax.tabMissing"), "五年列管": copy("tax.tabMonitor"), "AI 說明": copy("tax.tabAi") };
  return <section className="border border-slate-200 bg-white"><div className="flex overflow-x-auto border-b border-slate-200">{tabs.map((item) => <button key={item} onClick={() => setTab(item)} className={`border-b-2 px-4 py-2.5 text-xs font-bold ${tab === item ? "border-cyan-700 text-cyan-800" : "border-transparent text-slate-500 hover:text-slate-800"}`}>{tabLabels[item]}</button>)}</div><div className="p-4">{tab === "原因" && <p className="text-sm leading-7 text-slate-600">{result.ai_explanation.headline}</p>}{tab === "規則追蹤" && <RuleTable result={result} />}{tab === "補件清單" && <SimpleList items={result.missing_docs.length ? result.missing_docs : [copy("tax.noMissing")]} />}{tab === "五年列管" && <SimpleList items={result.reminder_timeline} numbered />}{tab === "AI 說明" && <div><p className="text-sm leading-7 text-slate-700">{result.ai_explanation.customer_script}</p><p className="mt-4 border-l-2 border-cyan-600 pl-3 text-xs font-bold text-cyan-800">{copy("tax.aiNotice")}</p></div>}</div><div className="border-t border-amber-200 bg-amber-50 px-4 py-2.5 text-xs leading-5 text-amber-800">{result.disclaimer}</div></section>;
}

function RuleTable({ result }: { result: TaxResult }) {
  const { copy } = useExperienceLocale();
  return <DetailDisclosure title={copy("tax.ruleTitle")}><div className="max-h-[65vh] space-y-2 overflow-y-auto overscroll-contain pr-1">{result.rule_traces.map((row)=><details key={row.code} className="rounded-lg border border-stone-200 bg-white" open={false}><summary className="flex cursor-pointer list-none flex-wrap items-center justify-between gap-2 px-3 py-2.5 text-xs"><span><strong className="text-cyan-800">{row.code}</strong> · {row.title}</span><span className="flex items-center gap-2"><Badge value={row.outcome}/><strong>{row.risk_points} 分</strong></span></summary><div className="border-t border-stone-100 bg-stone-50 px-3 py-2.5 text-xs leading-5 text-slate-600">{copy("tax.tabReason")}：{row.detail}</div></details>)}</div></DetailDisclosure>;
}

function SimpleList({ items, numbered = false }: { items: string[]; numbered?: boolean }) {
  return <ul className={numbered ? "relative ml-2 border-l border-cyan-200" : "space-y-2"}>{items.map((item, index) => <li key={item} className={`flex gap-3 text-sm text-slate-600 ${numbered ? "relative pb-4 pl-5" : "rounded-lg bg-stone-50 px-3 py-2.5"}`}><span className={`${numbered ? "absolute -left-3 grid h-6 w-6 place-items-center rounded-full border border-cyan-200 bg-white text-[10px]" : "grid h-5 w-5 shrink-0 place-items-center rounded-md bg-emerald-100 text-[10px] text-emerald-700"} font-bold`}>{numbered ? index + 1 : "✓"}</span>{item}</li>)}</ul>;
}

function MapInsight() {
  const { copy, locale } = useExperienceLocale();
  const categoryKeys = ["transport", "school", "park", "medical", "shopping", "food"];
  const categoryLabels: Record<string, string> = { transport: copy("location.transit"), school: copy("location.education"), park: copy("location.green"), medical: copy("location.medical"), shopping: copy("location.convenience"), food: copy("location.convenience") };
  const [query, setQuery] = useState("");
  const [location, setLocation] = useState<MapSearchResult>();
  const [result, setResult] = useState<MapNearbyResult>();
  const [health, setHealth] = useState<GoogleHealth>();
  const [active, setActive] = useState<string[]>(categoryKeys);
  const [selectedPlace, setSelectedPlace] = useState<NearbyPlace>();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searchMode, setSearchMode] = useState<"quick" | "manual">("quick");
  const [cities, setCities] = useState<string[]>([]);
  const [districts, setDistricts] = useState<string[]>([]);
  const [roads, setRoads] = useState<string[]>([]);
  const [city, setCity] = useState("");
  const [district, setDistrict] = useState("");
  const [road, setRoad] = useState("");
  const [roadLoading, setRoadLoading] = useState(true);
  const roadRequestRef = useRef(0);

  useEffect(() => {
    api.mapGoogleHealth().then(setHealth).catch(() => setHealth({ google_key_configured: false, geocoding_enabled: false, places_enabled: false, last_error: "", mode: "mock", safe_message: copy("map.healthUnavailable") }));
    api.roadCities().then((data) => setCities(data.cities)).finally(() => setRoadLoading(false));
  }, []);

  async function search(next = query) {
    const normalized = normalizeTaiwanPlaceQuery(next, locale);
    if (!hasSearchablePlaceQuery(normalized)) {
      setError(copy("map.emptyDetail"));
      return;
    }
    setQuery(next);
    setLoading(true);
    setError("");
    setSelectedPlace(undefined);
    try {
      const found = await api.mapSearch(normalized);
      if (!found.matched || !found.center) throw new Error("not_matched");
      setLocation(found);
      setResult(await api.mapNearby(found.center, categoryKeys));
    } catch {
      setError(copy("map.searchError"));
      setResult(undefined);
    } finally {
      setLoading(false);
    }
  }

  async function selectCity(value: string) {
    const requestId = ++roadRequestRef.current;
    setCity(value);
    setDistrict("");
    setRoad("");
    setRoads([]);
    setRoadLoading(true);
    try {
      const data = await api.roadDistricts(value);
      if (requestId === roadRequestRef.current) setDistricts(data.districts);
    } catch {
      if (requestId === roadRequestRef.current) setDistricts([]);
    } finally {
      if (requestId === roadRequestRef.current) setRoadLoading(false);
    }
  }

  async function selectDistrict(value: string) {
    const requestId = ++roadRequestRef.current;
    setDistrict(value);
    setRoad("");
    setRoadLoading(true);
    try {
      const data = await api.roads(city, value);
      if (requestId === roadRequestRef.current) setRoads(data.roads);
    } catch {
      if (requestId === roadRequestRef.current) setRoads([]);
    } finally {
      if (requestId === roadRequestRef.current) setRoadLoading(false);
    }
  }

  function locateQuick() {
    const next = `${city}${district}${road}`;
    setQuery(next);
    void search(next);
  }

  const categories = result?.categories.filter((group) => active.includes(group.category)) ?? [];
  const allSelected = active.length === categoryKeys.length;
  const totalPlaces = result?.categories.reduce((sum, group) => sum + group.count, 0) ?? 0;

  return <div id="map-insight" className="scroll-mt-20 space-y-4">
    <PageHeader kicker={copy("map.kicker")} title={copy("map.title")} description={copy("map.description")} />
    <HelpCallout>{copy("map.help")}</HelpCallout>
    {error && <div className="rounded-xl border border-amber-200 bg-amber-50 p-3"><ErrorState message={error} /><p className="mt-2 text-[10px] text-amber-700">{copy("map.sourceNote")}</p></div>}
    <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-[0_14px_40px_rgba(71,85,105,0.12)] xl:grid xl:min-h-[720px] xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="relative h-[min(72vh,720px)] min-h-[520px] min-w-0 sm:h-[620px] xl:h-auto">
        {result ? <GeoMap center={result.center} zoom={15} categories={categories} selectedPlace={selectedPlace} onSelectPlace={setSelectedPlace} /> : <div className="grid h-full place-items-center bg-gradient-to-br from-stone-100 via-cyan-50 to-stone-200 p-6 text-center"><EmptyState title={copy("map.empty")} detail={copy("map.emptyDetail")} /></div>}
        <MapSearchPanel mode={searchMode} setMode={setSearchMode} query={query} setQuery={setQuery} onManual={() => void search()} onQuick={locateQuick} loading={loading} roadLoading={roadLoading} cities={cities} districts={districts} roads={roads} city={city} district={district} road={road} setCity={selectCity} setDistrict={selectDistrict} setRoad={setRoad} />
        {result && <div className="absolute bottom-3 left-3 z-[500] max-w-[calc(100%-1.5rem)] rounded-xl border border-white/80 bg-white/92 px-3 py-2 shadow-md backdrop-blur-md"><div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px]"><strong className="min-w-0 break-words text-slate-800">{location?.formatted_address || query}</strong><span className="text-slate-500">{copy("map.city")}:</span><SourceBadge source={location?.source ?? "mock"} /><span className="text-slate-500">{copy("map.nearby")}:</span><SourceBadge source={result.source} /><span className="text-slate-500">{copy("map.radius")} {result.radius_m}m</span></div><MapLegend labels={categoryLabels} /></div>}
      </div>
      <details open className="min-w-0 border-t border-stone-200 bg-white xl:open xl:max-h-[720px] xl:overflow-y-auto xl:border-l xl:border-t-0">
        <summary className="cursor-pointer border-b border-stone-200 px-4 py-3 text-xs font-bold text-slate-900 xl:hidden">{copy("map.nearby")}</summary>
        <aside className="min-w-0 p-4">
          <div data-assistive-panel className={`mb-4 rounded-lg px-3 py-2 text-[10px] font-medium ${health?.mode === "google" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700"}`}>{health?.mode === "google" ? getLocalizedSourceLabel("google_places", locale) : copy("map.healthUnavailable")} {health?.mode === "google" ? copy("map.sourceNote") : copy("common.dataLimit")}</div>
          {result ? <>
            <div className="rounded-xl border border-cyan-100 bg-cyan-50/70 p-3"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><p className="text-[10px] font-bold tracking-wider text-cyan-700">{copy("map.nearby")}</p><h2 className="mt-1 break-words text-base font-bold text-slate-950">{location?.formatted_address || location?.district || location?.road || copy("map.empty")}</h2><p className="mt-1 text-[9px] text-slate-500">{result.score_summary}</p></div><div className="shrink-0 text-right"><p className="text-4xl font-bold text-cyan-800">{result.livability_score}</p><span className="rounded-full bg-white px-2 py-1 text-[9px] font-bold text-cyan-800">{result.livability_level}</span></div></div><div className="mt-2 flex gap-1"><SourceBadge source={result.source} /></div></div>
            <h3 className="mt-5 text-xs font-bold text-slate-900">{copy("map.city")}</h3><div className="mt-2 flex flex-wrap gap-1.5"><button onClick={() => setActive(allSelected ? [] : categoryKeys)} className={`rounded-full border px-2.5 py-1.5 text-[10px] font-bold ${allSelected ? "border-slate-700 bg-slate-800 text-white" : "border-stone-200 bg-white text-slate-500"}`}>{copy("action.open")} {totalPlaces}</button>{result.categories.map((group) => <button key={group.category} onClick={() => setActive((items) => items.includes(group.category) ? items.filter((x) => x !== group.category) : [...items, group.category])} className={`rounded-full border px-2.5 py-1.5 text-[10px] font-bold ${active.includes(group.category) ? "border-cyan-300 bg-cyan-50 text-cyan-800" : "border-stone-200 bg-white text-slate-400"}`}>{categoryLabels[group.category] ?? group.label} {group.count}</button>)}</div>
            <h3 className="mt-5 text-xs font-bold text-slate-900">{copy("location.results")}</h3><div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-1">{result.category_scores.map((metric) => <CategoryMetric key={metric.category} metric={metric} />)}</div><ScoringCriteria criteria={result.scoring_criteria} labels={categoryLabels} />
            <h3 className="mt-5 text-xs font-bold text-slate-900">{copy("map.nearby")}</h3><div className="mt-2 grid gap-2">{result.nearest_places?.slice(0, 3).map((place) => <button key={place.place_id} onClick={() => setSelectedPlace(place)} className="flex min-w-0 items-center justify-between rounded-lg bg-stone-50 px-3 py-2 text-left hover:bg-cyan-50"><span className="min-w-0"><span className="block truncate text-[11px] font-bold text-slate-800">{place.name}</span><span className="text-[9px] text-slate-500">{categoryLabels[place.category] ?? place.category} · {place.rating === null ? copy("common.noData") : `${copy("map.rating")} ${place.rating}`}</span></span><strong className="shrink-0 text-[10px] text-cyan-700">{Math.round(place.distance_m)}m</strong></button>)}</div>
            <h3 className="mt-5 text-xs font-bold text-slate-900">{copy("location.results")}</h3><PlaceList categories={categories} selected={selectedPlace} onSelect={setSelectedPlace} />
            <div className="mt-5 border-l-2 border-cyan-500 pl-3"><h3 className="text-xs font-bold text-slate-900">{copy("location.buyerFit")}</h3><p className="mt-1 text-[11px] leading-5 text-slate-600">{result.recommendation_text}</p></div>
            <p className="mt-4 border-t border-stone-200 pt-3 text-[9px] leading-4 text-slate-500">{result.disclaimer}</p>
          </> : <p className="rounded-xl bg-stone-50 p-4 text-xs leading-5 text-slate-600">{copy("map.emptyDetail")}</p>}
        </aside>
      </details>
    </div>
  </div>;
}

function LegacyMapInsight() {
  const { copy, locale } = useExperienceLocale();
  const categoryKeys = ["transport", "school", "park", "medical", "shopping", "food"];
  const categoryLabels: Record<string, string> = { transport: copy("location.transit"), school: copy("location.education"), park: copy("location.green"), medical: copy("location.medical"), shopping: copy("location.convenience"), food: copy("location.convenience") };
  const [query, setQuery] = useState("台北市大安區和平東路二段"), [location, setLocation] = useState<MapSearchResult>(), [result, setResult] = useState<MapNearbyResult>(), [health, setHealth] = useState<GoogleHealth>(), [active, setActive] = useState<string[]>(categoryKeys), [selectedPlace, setSelectedPlace] = useState<NearbyPlace>(), [loading, setLoading] = useState(true), [error, setError] = useState("");
  const [searchMode, setSearchMode] = useState<"quick" | "manual">("quick"), [cities, setCities] = useState<string[]>([]), [districts, setDistricts] = useState<string[]>([]), [roads, setRoads] = useState<string[]>([]), [city, setCity] = useState("台北市"), [district, setDistrict] = useState("大安區"), [road, setRoad] = useState("和平東路二段"), [roadLoading, setRoadLoading] = useState(true);
  async function search(next = query) { setLoading(true); setError(""); setSelectedPlace(undefined); try { const found = await api.mapSearch(next); if (!found.matched || !found.center) throw new Error("not_matched"); setLocation(found); setResult(await api.mapNearby(found.center, categoryKeys)); } catch { setError(copy("map.searchError")); } finally { setLoading(false); } }
  useEffect(() => { api.mapGoogleHealth().then(setHealth).catch(() => setHealth({ google_key_configured: false, geocoding_enabled: false, places_enabled: false, last_error: "", mode: "mock", safe_message: copy("map.healthUnavailable") })); api.roadCities().then((data) => setCities(data.cities)).finally(() => setRoadLoading(false)); api.roadDistricts("台北市").then((data) => setDistricts(data.districts)); api.roads("台北市", "大安區").then((data) => setRoads(data.roads)); search("台北市大安區和平東路二段"); }, []);
  async function selectCity(value: string) { setCity(value); setDistrict(""); setRoad(""); setRoads([]); setRoadLoading(true); try { setDistricts((await api.roadDistricts(value)).districts); } finally { setRoadLoading(false); } }
  async function selectDistrict(value: string) { setDistrict(value); setRoad(""); setRoadLoading(true); try { setRoads((await api.roads(city, value)).roads); } finally { setRoadLoading(false); } }
  function locateQuick() { const next = `${city}${district}${road}`; setQuery(next); search(next); }
  const categories = result?.categories.filter((group) => active.includes(group.category)) ?? [];
  const allSelected = active.length === categoryKeys.length;
  const totalPlaces = result?.categories.reduce((sum, group) => sum + group.count, 0) ?? 0;
  return <div id="map-insight" className="scroll-mt-20 space-y-4"><PageHeader kicker={copy("map.kicker")} title={copy("map.title")} description={copy("map.description")} />
    <HelpCallout>{copy("map.help")}</HelpCallout>
    {error && <div className="rounded-xl border border-amber-200 bg-amber-50 p-3"><ErrorState message={error} /><p className="mt-2 text-[10px] text-amber-700">{copy("map.sourceNote")}</p></div>}
    {result ? <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-[0_14px_40px_rgba(71,85,105,0.12)] xl:grid xl:min-h-[720px] xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="relative h-[480px] min-w-0 sm:h-[560px] xl:h-auto"><GeoMap center={result.center} zoom={15} categories={categories} selectedPlace={selectedPlace} onSelectPlace={setSelectedPlace} />
        <MapSearchPanel mode={searchMode} setMode={setSearchMode} query={query} setQuery={setQuery} onManual={() => search()} onQuick={locateQuick} loading={loading} roadLoading={roadLoading} cities={cities} districts={districts} roads={roads} city={city} district={district} road={road} setCity={selectCity} setDistrict={selectDistrict} setRoad={setRoad} />
        <div className="absolute bottom-3 left-3 z-[500] max-w-[calc(100%-1.5rem)] rounded-xl border border-white/80 bg-white/92 px-3 py-2 shadow-md backdrop-blur-md"><div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px]"><strong className="text-slate-800">{location?.formatted_address || query}</strong><span className="text-slate-500">{copy("map.city")}:</span><SourceBadge source={location?.source ?? "mock"} /><span className="text-slate-500">POI:</span><SourceBadge source={result.source} /><span className="text-slate-500">{copy("map.radius")} {result.radius_m}m</span></div><MapLegend labels={categoryLabels} /><details className="mt-1 text-[8px] text-slate-400"><summary className="cursor-pointer font-bold">{copy("map.nearby")}</summary><p className="mt-1">{copy("map.radius")} {result.radius_m}m</p></details></div>
      </div>
      <aside className="min-w-0 border-t border-stone-200 bg-white p-4 xl:max-h-[720px] xl:overflow-y-auto xl:border-l xl:border-t-0">
        <div data-assistive-panel className={`mb-4 rounded-lg px-3 py-2 text-[10px] font-medium ${health?.mode === "google" ? "bg-blue-50 text-blue-700" : "bg-amber-50 text-amber-700"}`}>{health?.mode === "google" ? getLocalizedSourceLabel("google_places", locale) : copy("map.healthUnavailable")} {health?.mode === "google" ? copy("map.sourceNote") : copy("common.dataLimit")}</div>
        <div className="rounded-xl border border-cyan-100 bg-cyan-50/70 p-3"><div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-cyan-700">{copy("map.nearby")}</p><h2 className="mt-1 text-base font-bold text-slate-950">{location?.formatted_address || location?.district || location?.road || copy("map.empty")}</h2><p className="mt-1 text-[9px] text-slate-500">{result.score_summary}</p></div><div className="text-right"><p className="text-4xl font-bold text-cyan-800">{result.livability_score}</p><span className="rounded-full bg-white px-2 py-1 text-[9px] font-bold text-cyan-800">{result.livability_level}</span></div></div><div className="mt-2 flex gap-1"><SourceBadge source={result.source} /></div></div>
        <h3 className="mt-5 text-xs font-bold text-slate-900">{copy("map.city")}</h3><div className="mt-2 flex flex-wrap gap-1.5"><button onClick={() => setActive(allSelected ? [] : categoryKeys)} className={`rounded-full border px-2.5 py-1.5 text-[10px] font-bold ${allSelected ? "border-slate-700 bg-slate-800 text-white" : "border-stone-200 bg-white text-slate-500"}`}>{copy("action.open")} {totalPlaces}</button>{result.categories.map((group) => <button key={group.category} onClick={() => setActive((items) => items.includes(group.category) ? items.filter((x) => x !== group.category) : [...items, group.category])} className={`rounded-full border px-2.5 py-1.5 text-[10px] font-bold ${active.includes(group.category) ? "border-cyan-300 bg-cyan-50 text-cyan-800" : "border-stone-200 bg-white text-slate-400"}`}>{categoryLabels[group.category] ?? group.label} {group.count}</button>)}</div>
        <h3 className="mt-5 text-xs font-bold text-slate-900">{copy("location.results")}</h3><div className="mt-2 grid gap-2 sm:grid-cols-2 xl:grid-cols-1">{result.category_scores.map((metric) => <CategoryMetric key={metric.category} metric={metric} />)}</div><ScoringCriteria criteria={result.scoring_criteria} labels={categoryLabels} />
        <h3 className="mt-5 text-xs font-bold text-slate-900">{copy("map.nearby")}</h3><div className="mt-2 grid gap-2">{result.nearest_places?.slice(0, 3).map((place) => <button key={place.place_id} onClick={() => setSelectedPlace(place)} className="flex items-center justify-between rounded-lg bg-stone-50 px-3 py-2 text-left hover:bg-cyan-50"><span className="min-w-0"><span className="block truncate text-[11px] font-bold text-slate-800">{place.name}</span><span className="text-[9px] text-slate-500">{categoryLabels[place.category] ?? place.category} · {place.rating ? `★ ${place.rating}` : copy("common.noData")}</span></span><strong className="shrink-0 text-[10px] text-cyan-700">{Math.round(place.distance_m)}m</strong></button>)}</div>
        <div className="mt-5 border-l-2 border-cyan-500 pl-3"><h3 className="text-xs font-bold text-slate-900">{copy("location.buyerFit")}</h3><p className="mt-1 text-[11px] leading-5 text-slate-600">{result.recommendation_text}</p></div>
        <h3 className="mt-5 text-xs font-bold text-slate-900">{copy("map.nearby")}</h3><PlaceList categories={categories} selected={selectedPlace} onSelect={setSelectedPlace} />
        <p className="mt-4 border-t border-stone-200 pt-3 text-[9px] leading-4 text-slate-500">{result.disclaimer}</p>
      </aside>
    </div> : <MapLoadingSkeleton />}</div>;
}

type MapSearchPanelProps = { mode: "quick" | "manual"; setMode: (mode: "quick" | "manual") => void; query: string; setQuery: (value: string) => void; onManual: () => void; onQuick: () => void; loading: boolean; roadLoading: boolean; cities: string[]; districts: string[]; roads: string[]; city: string; district: string; road: string; setCity: (value: string) => void; setDistrict: (value: string) => void; setRoad: (value: string) => void };

function MapSearchPanel({ mode, setMode, query, setQuery, onManual, onQuick, loading, roadLoading, cities, districts, roads, city, district, road, setCity, setDistrict, setRoad }: MapSearchPanelProps) {
  return <LocalizedMapSearchPanel mode={mode} setMode={setMode} query={query} setQuery={setQuery} onManual={onManual} onQuick={onQuick} loading={loading} roadLoading={roadLoading} cities={cities} districts={districts} roads={roads} city={city} district={district} road={road} setCity={setCity} setDistrict={setDistrict} setRoad={setRoad} />;
}

function LocalizedMapSearchPanel({ mode, setMode, query, setQuery, onManual, onQuick, loading, roadLoading, cities, districts, roads, city, district, road, setCity, setDistrict, setRoad }: MapSearchPanelProps) {
  const { copy, locale } = useExperienceLocale();
  const selectClass = "min-w-0 rounded-lg border border-stone-200 bg-white px-2 py-2 text-[11px] outline-none focus:ring-2 focus:ring-cyan-200 disabled:bg-stone-100";
  return <div className="absolute left-2 right-2 top-2 z-[500] rounded-xl border border-white/80 bg-white/95 p-2 shadow-lg backdrop-blur-md sm:left-4 sm:right-auto sm:top-4 sm:w-[min(720px,calc(100%-2rem))]"><div className="mb-2 flex w-fit rounded-lg bg-stone-100 p-0.5"><button onClick={() => setMode("quick")} className={`rounded-md px-3 py-1.5 text-[10px] font-bold ${mode === "quick" ? "bg-white text-cyan-800 shadow-sm" : "text-slate-500"}`}>{copy("map.quickMode")}</button><button onClick={() => setMode("manual")} className={`rounded-md px-3 py-1.5 text-[10px] font-bold ${mode === "manual" ? "bg-white text-cyan-800 shadow-sm" : "text-slate-500"}`}>{copy("map.manualMode")}</button></div>{mode === "quick" ? <div className="grid gap-2 sm:grid-cols-[1fr_1fr_1.4fr_auto]"><select aria-label={copy("common.selectCounty")} value={city} disabled={roadLoading} onChange={(e) => setCity(e.target.value)} className={selectClass}><option value="">{copy("common.selectCounty")}</option>{cities.map((item) => <option key={item} value={item}>{getLocalizedCountyLabel(item, locale)}</option>)}</select><select aria-label={copy("common.selectDistrict")} value={district} disabled={!city || roadLoading} onChange={(e) => setDistrict(e.target.value)} className={selectClass}><option value="">{copy("common.selectDistrict")}</option>{districts.map((item) => <option key={item} value={item}>{getLocalizedDistrictLabel(item, locale)}</option>)}</select><select aria-label={copy("common.selectRoad")} value={road} disabled={!district || roadLoading} onChange={(e) => setRoad(e.target.value)} className={selectClass}><option value="">{copy("common.selectRoad")}</option>{roads.map((item) => <option key={item} value={item}>{getLocalizedRoadLabel(item, locale)}</option>)}</select><Button onClick={onQuick} disabled={!city || !district || !road || loading || roadLoading} className="w-full bg-cyan-700 hover:bg-cyan-800 sm:w-auto">{loading ? copy("action.loading") : copy("action.open")}</Button></div> : <form onSubmit={(e) => { e.preventDefault(); onManual(); }} className="flex flex-col gap-2 sm:flex-row"><input value={query} onChange={(e) => setQuery(e.target.value)} className="min-w-0 flex-1 rounded-lg bg-stone-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-cyan-200" placeholder={copy("map.searchPlaceholder")} /><Button disabled={loading} className="w-full bg-cyan-700 hover:bg-cyan-800 sm:w-auto">{loading ? copy("map.searching") : copy("map.search")}</Button></form>}</div>;
}

function LegacyMapSearchPanel(props: MapSearchPanelProps) {
  return <LocalizedMapSearchPanel {...props} />;
}

function CategoryMetric({ metric }: { metric: MapNearbyResult["category_scores"][number] }) {
  return <div className="rounded-lg border border-stone-200 bg-white p-2.5"><div className="flex items-start justify-between"><div><p className="text-[11px] font-bold text-slate-800">{metric.label} <span className="font-medium text-slate-400">{metric.weight}%</span></p><p className="mt-0.5 text-[9px] text-slate-500">{metric.poi_count} 個點 · 最近 {metric.nearest_distance_m ?? "無資料"}{metric.nearest_distance_m !== null ? "m" : ""}</p></div><div className="text-right"><strong className="text-lg text-cyan-800">{metric.score}</strong><p className="text-[8px] font-bold text-slate-500">{metric.level}</p></div></div><div className="mt-2 h-1 overflow-hidden rounded-full bg-stone-100"><div className="h-full bg-cyan-600" style={{ width: `${metric.score}%` }} /></div><p className="mt-2 text-[9px] leading-4 text-slate-500">{metric.explanation}</p></div>;
}

function ScoringCriteria({ criteria, labels }: { criteria: MapNearbyResult["scoring_criteria"]; labels: Record<string, string> }) {
  const { copy } = useExperienceLocale();
  return <details className="mt-3 rounded-lg border border-stone-200 bg-stone-50 p-2.5"><summary className="cursor-pointer text-[10px] font-bold text-slate-700">{copy("common.dataLimit")}</summary><div className="mt-2 space-y-2 text-[9px] leading-4 text-slate-500"><p>{copy("map.nearbyDescription")} {criteria.radius_m}m.</p><div className="flex flex-wrap gap-1">{Object.entries(criteria.category_weights).map(([key, value]) => <span key={key} className="rounded-full bg-white px-2 py-1">{labels[key]} {value}%</span>)}</div><ul>{criteria.distance_bands.map((band) => <li key={band.range}>{band.range}: {band.weight}</li>)}</ul><p>{criteria.disclaimer}</p></div></details>;
}

function MapLegend({ labels }: { labels: Record<string, string> }) {
  const items = [["transport", "bg-blue-600"], ["school", "bg-violet-600"], ["park", "bg-green-600"], ["medical", "bg-rose-600"], ["shopping", "bg-orange-600"], ["food", "bg-amber-600"]];
  return <div className="mt-1.5 flex flex-wrap gap-x-2 gap-y-1">{items.map(([key, color]) => <span key={key} className="flex items-center gap-1 text-[8px] text-slate-500"><i className={`h-1.5 w-1.5 rounded-full ${color}`} />{labels[key]}</span>)}</div>;
}

function MapLoadingSkeleton() {
  return <div className="grid min-h-[560px] animate-pulse overflow-hidden rounded-2xl border border-stone-200 bg-white xl:grid-cols-[minmax(0,1fr)_380px]"><div className="bg-gradient-to-br from-stone-100 via-cyan-50 to-stone-200" /><div className="space-y-4 border-l border-stone-200 p-4"><div className="h-8 w-2/3 rounded bg-stone-100" /><div className="h-16 rounded bg-stone-100" />{[1, 2, 3, 4, 5, 6].map((item) => <div key={item} className="h-8 rounded bg-stone-100" />)}</div></div>;
}

function SourceBadge({ source }: { source: string }) {
  const { locale } = useExperienceLocale();
  const isGoogle = source.startsWith("google");
  const isTgos = source === "tgos_geocoding";
  const label = getLocalizedSourceLabel(source, locale);
  return <span className={`rounded-full px-2 py-0.5 text-[8px] font-bold ${isGoogle ? "bg-blue-100 text-blue-700" : isTgos ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700"}`}>{label}</span>;
}

function PlaceList({ categories, selected, onSelect }: { categories: NearbyCategory[]; selected?: NearbyPlace; onSelect: (place: NearbyPlace) => void }) {
  const { copy } = useExperienceLocale();
  const [expanded, setExpanded] = useState<string[]>([]);
  return <div className="mt-2 space-y-3">{categories.length ? categories.map((group) => { const sorted = [...group.places].sort((a, b) => a.distance_m - b.distance_m || (b.rating ?? 0) - (a.rating ?? 0) || b.user_rating_count - a.user_rating_count); const shown = expanded.includes(group.category) ? sorted : sorted.slice(0, 5); return <div key={group.category}><div className="mb-1 flex items-center justify-between"><p className="text-[10px] font-bold text-slate-700">{group.label} · {group.count}</p>{sorted.length > 5 && <button onClick={() => setExpanded((items) => items.includes(group.category) ? items.filter((item) => item !== group.category) : [...items, group.category])} className="text-[9px] font-bold text-cyan-700">{expanded.includes(group.category) ? copy("action.clear") : copy("action.expand")}</button>}</div><div className="space-y-2">{shown.map((place) => <PlaceCard key={place.place_id} place={place} label={group.label} selected={selected?.place_id === place.place_id} onSelect={onSelect} />)}</div></div>; }) : <p className="rounded-lg bg-stone-50 p-3 text-[10px] text-slate-400">{copy("map.noResult")}</p>}</div>;
}

function PlaceCard({ place, label, selected, onSelect }: { place: NearbyPlace; label: string; selected: boolean; onSelect: (place: NearbyPlace) => void }) {
  const { copy, locale } = useExperienceLocale();
  return <button type="button" data-assistive-label={place.name} onClick={() => onSelect(place)} className={`w-full rounded-lg border p-2.5 text-left transition ${selected ? "border-cyan-500 bg-cyan-50 ring-2 ring-cyan-100" : "border-stone-200 bg-white hover:border-cyan-200"}`}><div className="flex items-start justify-between gap-2"><div className="min-w-0"><p className="truncate text-xs font-bold text-slate-800">{place.name}</p><div className="mt-1 flex flex-wrap items-center gap-1.5"><span className="rounded-full bg-cyan-50 px-1.5 py-0.5 text-[8px] font-bold text-cyan-700">{label}</span><span className="text-[9px] font-bold text-slate-500">{Math.round(place.distance_m)} m</span>{place.rating && <span className="text-[9px] font-bold text-amber-600">★ {place.rating} ({place.user_rating_count})</span>}</div></div><span className="shrink-0 text-[8px] font-bold text-emerald-700">{place.opening_status_label}</span></div><p className="mt-1.5 truncate text-[9px] text-slate-400">{place.address}</p><p className="mt-1 text-[8px] font-bold text-slate-400">{place.source === "google_places" ? getLocalizedSourceLabel("google_places", locale) : copy("map.sourceNote")}</p></button>;
}

function marketDisplayJourneyStatus(result: MarketResult): LocationMarketDisplayStatus {
  if (result.data_status === "no_data") return "no_data";
  if (result.data_status !== "available") return "unavailable";
  if (result.coverage_status === "partial") return "partial";
  if ((result as MarketResult & { freshness_status?: string }).freshness_status === "stale") return "stale";
  return getMarketDisplayState(result) === "available" ? "available" : "unavailable";
}

type MarketInsightUiState = "initial" | "loading" | "available" | "no_data" | "unavailable" | "network_error";

function isMarketNetworkFailure(reason: MarketRequestReason): boolean {
  return reason === "market_request_cors_failed"
    || reason === "market_request_timeout"
    || reason === "market_request_connection_failed";
}

function safeMarketSupportReference(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const reference = value.trim();
  return /^[A-Za-z0-9_-]{1,64}$/.test(reference) ? reference : null;
}

function MarketInsight({ onMap, embedded = false, initialCounty = "", initialDistrict = "", onStatusChange, onResult }: { onMap: () => void; embedded?: boolean; initialCounty?: string; initialDistrict?: string; onStatusChange?: (status: LocationMarketDisplayStatus) => void; onResult?: (result: MarketResult | null) => void }) {
  const { copy, locale } = useExperienceLocale();
  const marketCopy = getMarketInsightCopy(locale);
  const [county, setCounty] = useState(initialCounty);
  const [district, setDistrict] = useState(initialDistrict);
  const [result, setResult] = useState<MarketResult>();
  const [querying, setQuerying] = useState(false);
  const [uiState, setUiState] = useState<MarketInsightUiState>("initial");
  const [marketFailureReason, setMarketFailureReason] = useState<MarketRequestReason | null>(null);
  const marketQuerySeq = useRef(0);
  const marketRequestController = useRef<AbortController | undefined>(undefined);
  const canonicalCounty = normalizeTaiwanCounty(county);
  const canonicalDistrict = normalizeTaiwanDistrict(canonicalCounty, district);
  const districtOptions = getDistrictsForCounty(canonicalCounty);

  async function query() {
    if (querying) return;
    if (!canonicalCounty) {
      setResult(undefined);
      setUiState("initial");
      return;
    }
    if (!canonicalDistrict) {
      setResult(undefined);
      setUiState("initial");
      return;
    }
    const queryId = marketQuerySeq.current + 1;
    marketQuerySeq.current = queryId;
    setQuerying(true);
    setUiState("loading");
    onStatusChange?.("loading");
    setMarketFailureReason(null);
    setResult(undefined);
    const controller = new AbortController();
    marketRequestController.current = controller;
    const timeout = window.setTimeout(() => controller.abort("market_request_timeout"), 20000);
    try {
      const nextResult = await api.marketInsight(canonicalCounty, canonicalDistrict, undefined, controller.signal);
      if (marketQuerySeq.current !== queryId) return;
      const displayState = getMarketDisplayState(nextResult);
      setResult(nextResult);
      setUiState(displayState);
      onResult?.(nextResult);
      onStatusChange?.(marketDisplayJourneyStatus(nextResult));
    } catch (caught) {
      if (marketQuerySeq.current === queryId) {
        const reasonCode = caught instanceof MarketRequestError ? caught.reasonCode : "market_request_unknown_failure";
        setMarketFailureReason(reasonCode);
        setUiState(isMarketNetworkFailure(reasonCode) ? "network_error" : "unavailable");
        setResult(undefined);
        onResult?.(null);
        onStatusChange?.("unavailable");
      }
    } finally {
      window.clearTimeout(timeout);
      if (marketRequestController.current === controller) marketRequestController.current = undefined;
      if (marketQuerySeq.current === queryId) setQuerying(false);
    }
  }

  async function submitQuery(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await query();
  }

  function updateCounty(value: string) {
    marketRequestController.current?.abort("market_request_cancelled");
    marketRequestController.current = undefined;
    marketQuerySeq.current += 1;
    setCounty(normalizeTaiwanCounty(value));
    setDistrict("");
    setResult(undefined);
    onResult?.(null);
    onStatusChange?.("not_started");
    setUiState("initial");
    setMarketFailureReason(null);
  }

  function updateDistrict(value: string) {
    marketRequestController.current?.abort("market_request_cancelled");
    marketRequestController.current = undefined;
    marketQuerySeq.current += 1;
    setDistrict(normalizeTaiwanDistrict(canonicalCounty, value));
    setResult(undefined);
    onResult?.(null);
    onStatusChange?.("not_started");
    setUiState("initial");
    setMarketFailureReason(null);
  }

  const visualModel = buildMarketInsightVisualModel(result);
  const evidenceDisclosure = <><EvidenceSummary items={visualModel.evidence} /><EvidenceDetails items={visualModel.evidence} /></>;
  return <div className="space-y-5">
    {!embedded && <PageHeader kicker={copy("valuation.kicker")} title="Market Insight" description={copy("valuation.help")} action={<Button secondary onClick={onMap}>{copy("location.map")}</Button>} />}
    {!embedded && <HelpCallout>{copy("valuation.help")}</HelpCallout>}
    <SectionCard title={copy("action.search")} description={copy("map.help")}>
      <form onSubmit={submitQuery} aria-busy={querying} data-testid="market-insight-search-form" className="grid gap-3 md:grid-cols-[1fr_1fr_auto]">
        <label className="text-xs text-slate-500">{copy("common.selectCounty")}
          <select value={canonicalCounty} onChange={(event) => updateCounty(event.target.value)} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm">
            <option value="">{copy("common.selectCounty")}</option>
            {TAIWAN_COUNTIES.map((item) => <option key={item} value={item}>{getLocalizedCountyLabel(item, locale)}</option>)}
          </select>
        </label>
        <label className="text-xs text-slate-500">{copy("common.selectDistrict")}
          <select value={canonicalDistrict} onChange={(event) => updateDistrict(event.target.value)} disabled={!canonicalCounty} className="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm disabled:bg-stone-100 disabled:text-slate-400">
            <option value="">{canonicalCounty ? copy("common.selectDistrict") : copy("common.selectCounty")}</option>
            {districtOptions.map((item) => <option key={item} value={item}>{getLocalizedDistrictLabel(item, locale)}</option>)}
          </select>
        </label>
        <div className="flex items-end"><button type="submit" data-testid="market-insight-search-button" disabled={querying || !canonicalCounty || !canonicalDistrict} className="inline-flex min-h-11 items-center justify-center rounded-lg bg-slate-950 px-4 py-2.5 text-sm font-bold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">{querying ? marketCopy.loading : copy("action.search")}</button></div>
      </form>
      {uiState === "initial" && <p data-testid="market-insight-initial" role="status" className="mt-3 rounded-lg bg-stone-50 p-3 text-sm text-slate-600">{marketCopy.initial}</p>}
      {uiState === "loading" && <div data-testid="market-insight-loading" aria-live="polite" className="mt-3"><LoadingState label={marketCopy.loading} /></div>}
      {uiState === "network_error" && <div data-testid="market-insight-network-error" role="alert" data-market-failure-reason={marketFailureReason ?? undefined} className="mt-3"><ErrorState message={marketCopy.networkError} /></div>}
      {uiState === "unavailable" && !result && <div data-testid="market-insight-unavailable" role="alert" data-market-failure-reason={marketFailureReason ?? undefined} className="mt-3"><ErrorState message={marketCopy.unavailable} /></div>}
      <p className="mt-3 text-xs leading-5 text-slate-500">{copy("common.dataLimit")}</p>
    </SectionCard>
    {result && <MarketInsightVisualResult result={result} model={visualModel} uiState={uiState} evidenceDisclosure={evidenceDisclosure} />}
  </div>;
}

function MarketInsightVisualResult({ result, model, uiState, evidenceDisclosure }: { result: MarketResult; model: ReturnType<typeof buildMarketInsightVisualModel>; uiState: MarketInsightUiState; evidenceDisclosure: ReactNode }) {
  const { locale } = useExperienceLocale();
  const labels = getMarketInsightCopy(locale);
  const isAvailable = uiState === "available" && model.state === "available";
  const supportReference = safeMarketSupportReference(result.support_reference);
  if (!isAvailable) {
    const noData = uiState === "no_data" || model.state === "no_data";
    const message = noData ? labels.noData : labels.unavailable;
    return <div className="space-y-5" data-testid={noData ? "market-insight-no-data" : "market-insight-unavailable"}>
      <SectionCard title={noData ? labels.noData : labels.unavailable}>
        <div role={noData ? "status" : "alert"} className="text-sm leading-6 text-slate-700">{message}</div>
        {!noData && supportReference && <p className="mt-2 text-xs font-medium text-slate-600">{labels.supportReference}: <code>{supportReference}</code></p>}
        {result.caveat && result.caveat !== message && <p className="mt-3 text-xs leading-5 text-amber-900">{result.caveat}</p>}
        <p className="mt-3 text-xs leading-5 text-slate-500">{result.disclaimer || labels.boundary}</p>
      </SectionCard>
      {evidenceDisclosure}
    </div>;
  }
  return <div className="space-y-5" data-testid="market-insight-available">
    <SectionCard title={labels.summary} description={labels.boundary}>
      <div className="flex flex-wrap items-center gap-2"><DataStatusBadge status={model.state} /><DataStatusBadge status={model.coverage} />{model.freshness !== "unknown" && <FreshnessIndicator status={model.freshness} />}</div>
      <p className="mt-3 text-sm leading-6 text-slate-700">{result.summary}</p>
    </SectionCard>
    <MarketInsightEvidencePanel result={result} model={model} />
    <div className="grid min-w-0 gap-4 lg:grid-cols-2">
      <SectionCard title={labels.priceTrend}><TrendLineChart data={model.history} status={model.state} /></SectionCard>
      <SectionCard title={labels.volumeTrend}><VolumeBarChart data={model.history} status={model.state} /></SectionCard>
    </div>
    {evidenceDisclosure}
    <Notice tone="warning">{result.caveat || labels.boundary}</Notice>
  </div>;
}

function AegisCredit() {
  const { locale } = useExperienceLocale();
  return <div className="space-y-3"><Notice tone="warning">{getLocalizedStateLabel("heuristic", locale)} · {getLocalizedStateLabel("reference_only", locale)}. {locale === "en" ? "Inputs and results are a reference scenario, not a lending decision." : locale === "ja" ? "入力と結果は参考シナリオであり、融資判断ではありません。" : locale === "ko" ? "입력과 결과는 참고 시나리오이며 대출 심사가 아닙니다." : "輸入與結果為參考情境，不是核貸判定。"}</Notice><LegacyAegisCredit /></div>;
}

function LegacyAegisCredit() {
  const { copy } = useExperienceLocale();
  const [monthlyIncome,setMonthlyIncome]=useState(90000);
  const [monthlyDebt,setMonthlyDebt]=useState(15000);
  const [cash,setCash]=useState(3500000);
  const [propertyCount,setPropertyCount]=useState(0);
  const [mortgageCount,setMortgageCount]=useState(0);
  const [propertyPrice,setPropertyPrice]=useState(22000000);
  const [result,setResult]=useState<{risk_score:number;signal_color:string;traces:string[]}>(), [rate,setRate]=useState<MortgageRateReference>(), [banks,setBanks]=useState<BankInstitution[]>([]), [bankCode,setBankCode]=useState(""), [bankRate,setBankRate]=useState<BankRateResult>(), [loading,setLoading]=useState(false), [rateLoading,setRateLoading]=useState(true), [error,setError]=useState(""), [validationError,setValidationError]=useState("");
  const [holdingPrefill,setHoldingPrefill]=useState<HoldingCostPrefill>();
  useEffect(()=>{Promise.all([api.mortgageRate().then(setRate),api.bankInstitutions().then(async(data)=>{setBanks(data.institutions);const code=data.institutions[0]?.bank_code??"";setBankCode(code);if(code)setBankRate(await api.bankMortgageRates(code));})]).catch(()=>setError("市場利率參考暫時無法載入，風險分析仍可正常使用。")).finally(()=>setRateLoading(false));},[]);
  async function changeBank(code:string){setBankCode(code);setRateLoading(true);try{setBankRate(await api.bankMortgageRates(code));}finally{setRateLoading(false);}}
  function validate(): boolean {
    if (monthlyIncome <= 0) { setValidationError(copy("aegis.validationIncome")); return false; }
    if (monthlyDebt < 0) { setValidationError(copy("aegis.validationDebt")); return false; }
    if (cash < 0) { setValidationError(copy("aegis.validationCash")); return false; }
    if (propertyCount < 0 || !Number.isInteger(propertyCount)) { setValidationError(copy("aegis.validationPropertyCount")); return false; }
    if (mortgageCount < 0 || !Number.isInteger(mortgageCount)) { setValidationError(copy("aegis.validationMortgageCount")); return false; }
    if (propertyPrice <= 0) { setValidationError(copy("aegis.validationPrice")); return false; }
    setValidationError("");
    return true;
  }
  async function run(){if(!validate())return;setLoading(true);setError("");try{setResult(await api.aegis({monthly_income:monthlyIncome,monthly_debt:monthlyDebt,cash,property_count:propertyCount,mortgage_count:mortgageCount,property_price:propertyPrice}));}catch{setError("房貸風險分析暫時無法取得，請稍後再試。");}finally{setLoading(false);}}
  const inputClass="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm";
  return <SupportPage kicker="風險模組" title="房貸風險展示" description="快速了解買方條件的風險輪廓，搭配市場月資料與銀行牌告利率補充背景。" error={error} help="這是房貸風險展示型 heuristic，不代表銀行核貸；利率資料僅供市場背景參考。"><LoanCalculator onHoldingCost={(loan)=>setHoldingPrefill({property_price:loan.property_price_wan,loan_monthly_payment:loan.monthly_payment,monthly_income:loan.monthly_income_wan})}/><HoldingCostCalculator prefill={holdingPrefill}/><div className="grid items-start gap-4 lg:grid-cols-[1fr_380px]"><SectionCard title={copy("aegis.sectionTitle")}><p className="text-sm text-slate-500">{copy("aegis.sectionDescription")}</p><div data-testid="aegis-scenario-form" className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3"><fieldset className="space-y-3 rounded-lg border border-stone-200 p-3"><legend className="px-1 text-xs font-bold text-slate-700">{copy("aegis.groupIncome")}</legend><label className="block text-xs text-slate-600">{copy("aegis.monthlyIncome")}<input type="number" aria-label="月收入" value={monthlyIncome} onChange={(e)=>setMonthlyIncome(Number(e.target.value))} className={inputClass}/></label><label className="block text-xs text-slate-600">{copy("aegis.monthlyDebt")}<input type="number" aria-label="每月負債" value={monthlyDebt} onChange={(e)=>setMonthlyDebt(Number(e.target.value))} className={inputClass}/></label></fieldset><fieldset className="space-y-3 rounded-lg border border-stone-200 p-3"><legend className="px-1 text-xs font-bold text-slate-700">{copy("aegis.groupAssets")}</legend><label className="block text-xs text-slate-600">{copy("aegis.cash")}<input type="number" aria-label="可用現金" value={cash} onChange={(e)=>setCash(Number(e.target.value))} className={inputClass}/></label><label className="block text-xs text-slate-600">{copy("aegis.propertyCount")}<input type="number" aria-label="名下房屋數" min={0} step={1} value={propertyCount} onChange={(e)=>setPropertyCount(Number(e.target.value))} className={inputClass}/></label><label className="block text-xs text-slate-600">{copy("aegis.mortgageCount")}<input type="number" aria-label="既有房貸數" min={0} step={1} value={mortgageCount} onChange={(e)=>setMortgageCount(Number(e.target.value))} className={inputClass}/></label></fieldset><fieldset className="space-y-3 rounded-lg border border-stone-200 p-3"><legend className="px-1 text-xs font-bold text-slate-700">{copy("aegis.groupTarget")}</legend><label className="block text-xs text-slate-600">{copy("aegis.propertyPrice")}<input type="number" aria-label="物件價格" value={propertyPrice} onChange={(e)=>setPropertyPrice(Number(e.target.value))} className={inputClass}/></label></fieldset></div>{validationError&&<p className="mt-3 rounded-lg bg-rose-50 px-3 py-2 text-xs font-bold text-rose-800" role="alert">{validationError}</p>}<Button onClick={run} disabled={loading} className="mt-4">{loading?copy("aegis.loading"):copy("aegis.submit")}</Button>{result&&<div className="mt-5 space-y-3"><div className="grid gap-3 sm:grid-cols-2"><MetricTile label="風險分數" value={result.risk_score}/><MetricTile label="風險狀態" value={<Badge value={result.signal_color}/>} /></div><div className="rounded-lg bg-stone-50 p-3"><p className="text-xs font-bold text-slate-800">風險提示</p><ul className="mt-2 space-y-1 text-xs text-slate-600">{result.traces.map((trace)=><li key={trace}>• {trace}</li>)}</ul></div><div className="border-l-2 border-cyan-600 pl-3"><p className="text-xs font-bold text-slate-800">對客戶說明建議</p><p className="mt-1 text-xs leading-5 text-slate-600">可先用此風險摘要整理收入、負債比與自備款條件，再向銀行確認實際方案與利率。</p></div></div>}</SectionCard><div className="space-y-4"><BankRatePanel banks={banks} bankCode={bankCode} rate={bankRate} loading={rateLoading} onChange={changeBank}/><MortgageRatePanel rate={rate} loading={rateLoading}/></div></div></SupportPage>;
}

function BankRatePanel({banks,bankCode,rate,loading,onChange}:{banks:BankInstitution[];bankCode:string;rate?:BankRateResult;loading:boolean;onChange:(code:string)=>void}) {
  return <SectionCard title="銀行牌告利率查詢" description={`中央銀行 OpenData · 可查詢 ${banks.length} 家金融機構`}><select value={bankCode} disabled={loading} onChange={(e)=>onChange(e.target.value)} className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm">{banks.map((bank)=><option key={bank.bank_code} value={bank.bank_code}>{bank.bank_name}</option>)}</select>{loading?<div className="mt-3"><LoadingState label="查詢銀行牌告利率..." /></div>:rate&&<div className="mt-3"><div className="flex items-end justify-between"><div><p className="text-[10px] font-bold text-slate-500">{rate.bank_name}</p><p className="text-3xl font-bold">{rate.summary_rate?.toFixed(3)??"—"}<span className="text-sm text-slate-400">%</span></p><p className="text-[10px] text-slate-500">{rate.summary_label}</p></div><span className="rounded-full bg-blue-50 px-2 py-1 text-[9px] font-bold text-blue-700">{rate.source==="mock"?"目前使用展示資料":"中央銀行 OpenData"}</span></div><div className="mt-3 space-y-2">{rate.items.map((item)=><div key={`${item.raw_rate_name}-${item.effective_date}`} className="rounded-lg bg-stone-50 p-2 text-[10px]"><strong>{item.rate_name}</strong><dl className="mt-1 grid grid-cols-3 gap-2 text-slate-500"><div><dt>機動利率</dt><dd className="font-bold text-slate-800">{item.variable_rate??"—"}%</dd></div><div><dt>固定利率</dt><dd className="font-bold text-slate-800">{item.fixed_rate??"—"}%</dd></div><div><dt>生效日期</dt><dd className="font-bold text-slate-800">{item.effective_date||"未提供"}</dd></div></dl></div>)}</div><p className="mt-3 text-[9px] leading-4 text-amber-700">牌告利率僅供市場背景參考，不代表銀行實際核貸利率。</p></div>}</SectionCard>;
}

function MortgageRatePanel({ rate, loading }: { rate?: MortgageRateReference; loading: boolean }) {
  if (loading) return <SectionCard title="市場房貸利率參考"><LoadingState label="載入五大銀行月資料..." /></SectionCard>;
  if (!rate) return <SectionCard title="市場房貸利率參考"><p className="text-xs text-slate-500">目前無法取得市場參考資料，房貸風險分析仍可正常使用。</p></SectionCard>;
  return <SectionCard title="市場房貸利率參考" description="中央銀行 OpenData · 五大銀行月資料"><div className="flex items-end justify-between border-b border-stone-100 pb-3"><div><p className="text-4xl font-bold text-slate-950">{rate.reference_rate.toFixed(3)}<span className="ml-1 text-sm text-slate-400">%</span></p><p className="mt-1 text-[10px] text-slate-500">{rate.rate_type}</p></div><span className={`rounded-full px-2 py-1 text-[9px] font-bold ${rate.source === "mock" ? "bg-amber-100 text-amber-700" : "bg-blue-100 text-blue-700"}`}>{rate.source === "mock" ? "展示資料 fallback" : "中央銀行 OpenData"}</span></div><dl className="mt-3 grid gap-2 text-[10px]"><div className="flex justify-between"><dt className="text-slate-500">資料期間</dt><dd className="font-bold text-slate-800">{rate.period}</dd></div><div className="flex justify-between gap-4"><dt className="text-slate-500">更新時間</dt><dd className="text-right font-bold text-slate-800">{new Date(rate.fetched_at).toLocaleString("zh-TW")}</dd></div></dl><p className="mt-4 rounded-lg bg-amber-50 p-2.5 text-[10px] leading-5 text-amber-800">此利率僅作為市場參考，不代表銀行實際核貸利率。</p><ul className="mt-3 space-y-1 text-[9px] leading-4 text-slate-500">{rate.notes.map((note)=><li key={note}>• {note}</li>)}</ul></SectionCard>;
}

function ValuationPage({ onMap, embedded = false, initialContext, onResult, onStatusChange }: { onMap?: () => void; embedded?: boolean; initialContext?: JourneyPropertyContext; onResult?: (result: ValuationResult | undefined) => void; onStatusChange?: (status: PriceJourneyDisplayStatus) => void }) {
  const { copy } = useExperienceLocale();
  const [cities,setCities]=useState<string[]>([]),[districts,setDistricts]=useState<string[]>([]),[roads,setRoads]=useState<string[]>([]),[city,setCity]=useState("台北市"),[district,setDistrict]=useState("大安區"),[road,setRoad]=useState("和平東路二段"),[addressText,setAddressText]=useState(""),[area,setArea]=useState(30),[age,setAge]=useState(15),[type,setType]=useState("住宅大樓"),[floor,setFloor]=useState(8),[result,setResult]=useState<ValuationResult>(),[trend,setTrend]=useState<ValuationTrendResult>(),[dataStatus,setDataStatus]=useState<ValuationDataStatus>(),[loading,setLoading]=useState(false),[error,setError]=useState(""),[shareNotice,setShareNotice]=useState(""),[manualShare,setManualShare]=useState("");
  const [propertySearchResult,setPropertySearchResult]=useState<PropertySearchResult>();
  const [loanPriceWan,setLoanPriceWan]=useState<number>();
  const [loanResult,setLoanResult]=useState<LoanCalculationResult>();
  const [holdingPrefill,setHoldingPrefill]=useState<HoldingCostPrefill>();
  const [holdingResult,setHoldingResult]=useState<HoldingCostResult>();
  useEffect(() => {
    if (!result) return;
    onResult?.(result);
    const state = getValuationDisplayState(result);
    onStatusChange?.(state.kind);
  }, [result]);
  useEffect(() => {
    if (!initialContext) return;
    if (initialContext.city) setCity(initialContext.city);
    if (initialContext.district) setDistrict(initialContext.district);
    if (initialContext.road) setRoad(initialContext.road);
    if (initialContext.addressSummary) setAddressText(initialContext.addressSummary);
    if (initialContext.areaPing !== undefined) setArea(initialContext.areaPing);
    if (initialContext.buildingType) setType(initialContext.buildingType);
    if (initialContext.askingPriceWan !== undefined) setLoanPriceWan(initialContext.askingPriceWan);
  }, [initialContext]);
  useEffect(()=>{publishWorkspaceContext({inputs:{city,district,road,building_type:type,area_ping:area,building_age_years:age,floor},propertySearch:propertySearchResult,valuation:result,trend,loan:loanResult,holding:holdingResult});},[city,district,road,type,area,age,floor,propertySearchResult,result,trend,loanResult,holdingResult]);
  useEffect(()=>{const listener=(event:Event)=>{const demo=(event as CustomEvent<DemoResults>).detail;if(!demo)return;setCity(demo.inputs.city);setDistrict(demo.inputs.district);setRoad(demo.inputs.road);setType(demo.inputs.building_type);setArea(demo.inputs.area_ping);setAge(demo.inputs.building_age_years);setFloor(demo.inputs.floor);setPropertySearchResult(demo.propertySearch);setResult(demo.valuation);setTrend(demo.trend);setLoanPriceWan(demo.loan?.property_price_wan);setLoanResult(demo.loan);setHoldingResult(demo.holdingCost);setShareNotice("Demo 結果已寫入目前流程，可繼續手動調整、保存或匯出報告");};window.addEventListener(GUIDED_DEMO_RESULT_EVENT,listener);return()=>window.removeEventListener(GUIDED_DEMO_RESULT_EVENT,listener);},[]);
  useEffect(()=>{function applySaved(saved:SavedCase){const data=saved.data,input=data.inputs;setCity(input.city);setDistrict(input.district);setRoad(input.road);setType(input.building_type);setArea(input.area_ping);setAge(input.building_age_years);setFloor(input.floor);setPropertySearchResult(data.propertySearch);setResult(data.valuation);setTrend(data.trend);setLoanPriceWan(data.loan?.property_price_wan);setLoanResult(data.loan);setHoldingResult(data.holdingCost);setShareNotice("已載入案件，可繼續分析");}const listener=(event:Event)=>applySaved((event as CustomEvent<SavedCase>).detail);const clear=()=>{setPropertySearchResult(undefined);setResult(undefined);setTrend(undefined);setLoanPriceWan(undefined);setLoanResult(undefined);setHoldingResult(undefined);setShareNotice("目前案件已清除");};window.addEventListener(CASE_LOADED_EVENT,listener);window.addEventListener(CASE_CLEARED_EVENT,clear);try{const stored=window.sessionStorage.getItem(WORKSPACE_CONTEXT_SESSION_KEY);if(stored){const context=JSON.parse(stored) as WorkspaceContext;applySaved({data:{inputs:context.inputs,propertySearch:context.propertySearch,valuation:context.valuation,trend:context.trend,loan:context.loan,holdingCost:context.holding},inputSummary:{},id:"session",title:"",createdAt:"",updatedAt:"",version:1,workflowMode:"buying_wizard",activeWizardStep:"property_search",progress:0});}}catch{}return()=>{window.removeEventListener(CASE_LOADED_EVENT,listener);window.removeEventListener(CASE_CLEARED_EVENT,clear);};},[]);
  useEffect(()=>{prefillLocationInsight({city,district,road,area_ping:area,building_type:type,property_price:result?.price_range.mid});},[city,district,road,area,type,result]);
  useEffect(()=>{if(trend&&getValuationTrendDisplayState(trend).kind!=="available"){setTrend(undefined);setError("估價趨勢資料目前無法使用，請稍後再試。");}},[trend]);
  useEffect(()=>{const shared=parseValuationShareParams(window.location.search);const initialCity=shared?.city??"台北市",initialDistrict=shared?.district??"大安區";api.roadCities().then(x=>setCities(x.cities));api.roadDistricts(initialCity).then(x=>setDistricts(x.districts));api.roads(initialCity,initialDistrict).then(x=>setRoads(x.roads));api.valuationDataStatus().then(setDataStatus).catch(()=>setError("估價資料狀態暫時無法載入，仍可嘗試估算。"));if(shared){setCity(shared.city);setDistrict(shared.district);setRoad(shared.road);setType(shared.building_type);setArea(shared.area_ping);setAge(shared.building_age_years);setFloor(shared.floor);setShareNotice("已載入分享條件，可按下估價重新查詢");}},[]);
  useEffect(()=>{const target=window.sessionStorage.getItem("proptech:pending-section");if(!target)return;window.sessionStorage.removeItem("proptech:pending-section");window.setTimeout(()=>document.getElementById(target)?.scrollIntoView({behavior:"smooth",block:"start"}),120);},[]);
  async function changeCity(value:string){setCity(value);setDistrict("");setRoad("");setDistricts((await api.roadDistricts(value)).districts);}
  async function changeDistrict(value:string){setDistrict(value);setRoad("");setRoads((await api.roads(city,value)).roads);}
  function scrollToWorkflow(id:string){window.setTimeout(()=>document.getElementById(id)?.scrollIntoView({behavior:"smooth",block:"start"}),50);}
  async function usePropertyFinderSelection(selection:PropertyFinderSelection){setCity(selection.city||city);setDistrict(selection.district||district);setRoad(selection.road||road);setType(selection.building_type||type);setArea(selection.area_ping||area);setResult(undefined);setTrend(undefined);if(selection.city){setDistricts((await api.roadDistricts(selection.city)).districts);}if(selection.city&&selection.district){setRoads((await api.roads(selection.city,selection.district)).roads);}setShareNotice("已帶入估價條件，可按下估價重新查詢");scrollToWorkflow("valuation-calculator");}
  function useLoanPrice(priceWan:number){setLoanPriceWan(priceWan);setLoanResult(undefined);setShareNotice("已帶入貸款試算，可確認利率與年限後計算");scrollToWorkflow("loan-calculator");}
  function useHoldingCost(propertyPrice:number,areaPing?:number,loan:LoanCalculationResult|undefined=loanResult){const prefill={property_price:propertyPrice,area_ping:areaPing,loan_monthly_payment:loan?.monthly_payment,monthly_income:loan?.monthly_income_wan};setHoldingPrefill(prefill);prefillHoldingCost(prefill);setHoldingResult(undefined);setShareNotice("已帶入持有成本，可確認管理費與稅費假設後計算");scrollToWorkflow("holding-cost-calculator");}
  function useLocationInsight(selection:PropertyFinderSelection,priceWan:number){prefillLocationInsight({city:selection.city,district:selection.district,road:selection.road,area_ping:selection.area_ping,building_type:selection.building_type,property_price:priceWan});setShareNotice("已帶入區位分析，可按下分析區位");scrollToWorkflow("location-insight-calculator");}
  async function estimate(){setLoading(true);setError("");setTrend(undefined);try{const payload={city,district,road,address_text:addressText,building_type:type,area_ping:area,building_age_years:age,floor};const next=await api.valuation(payload);setResult(next);setDataStatus(next.data_status);api.valuationTrend({...payload,horizon_months:[6,12,36]}).then(setTrend).catch(()=>setError("估價已完成，但市場趨勢暫時無法載入。"));}catch{setError("估價資料暫時無法取得，請稍後再試。" );}finally{setLoading(false);}}
  const shareInputs:ValuationInputs={city,district,road,building_type:type,area_ping:area,building_age_years:age,floor};
  const valuationVisualModel = buildValuationVisualModel(result, trend);
  const valuationNeedsTrustNotice = Boolean(result && getValuationDisplayState(result).kind !== "available");
  async function copyShareLink(){const url=buildValuationShareUrl(`${window.location.origin}${window.location.pathname}`,shareInputs);setManualShare("");try{await navigator.clipboard.writeText(url);setShareNotice("分享連結已複製");window.setTimeout(()=>setShareNotice(""),2200);}catch{setManualShare(url);setShareNotice("無法自動複製，請手動複製下方連結");}}
  function downloadValuationSummary(){if(!result)return;const blob=new Blob([buildValuationSummaryHtml(shareInputs,result,trend,propertySearchResult,loanResult,holdingResult)],{type:"text/html;charset=utf-8"});const url=URL.createObjectURL(blob),link=document.createElement("a");link.href=url;link.download=valuationSummaryFilename();link.click();URL.revokeObjectURL(url);markWorkflowReportCompleted();}
  const select="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm";
  return <div className="min-w-0 space-y-5">{!embedded && <><PageHeader kicker={copy("valuation.kicker")} title={copy("valuation.title")} description={copy("valuation.description")} /><HelpCallout>{copy("valuation.help")}</HelpCallout></>}{shareNotice&&<Notice>{shareNotice}</Notice>}{manualShare&&<div className="break-all rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs text-cyan-900">{manualShare}</div>}{error&&<ErrorState message={error}/>} {dataStatus&&<ValuationDataStatusCard status={dataStatus}/>} {result&&<ValuationVisualPanel model={valuationVisualModel}/>}{!embedded && <details className="rounded-xl border border-stone-200 bg-white"><summary className="cursor-pointer px-4 py-3 text-sm font-bold text-slate-900">{copy("valuation.recheck")}</summary><div className="border-t border-stone-100 p-4"><PropertyFinder onUseForValuation={usePropertyFinderSelection} onUseForLoan={useLoanPrice} onUseForHoldingCost={useHoldingCost} onUseForLocationInsight={useLocationInsight} onResult={setPropertySearchResult}/></div></details>}{!embedded && <LoanCalculator propertyPriceWan={loanPriceWan} onResult={setLoanResult} onLocationMap={onMap}/>}<div className="grid min-w-0 items-start gap-4 lg:grid-cols-[360px_minmax(0,1fr)]"><div id="valuation-calculator" className="scroll-mt-20"><SectionCard title={copy("valuation.criteria")}><div className="grid gap-3"><select className={select} value={city} onChange={(e)=>changeCity(e.target.value)}>{cities.map(x=><option key={x}>{x}</option>)}</select><select className={select} value={district} onChange={(e)=>changeDistrict(e.target.value)}><option value="">{copy("common.selectDistrict")}</option>{districts.map(x=><option key={x}>{x}</option>)}</select><select className={select} value={road} onChange={(e)=>setRoad(e.target.value)}><option value="">{copy("common.selectRoad")}</option>{roads.map(x=><option key={x}>{x}</option>)}</select><input className={select} value={addressText} onChange={(e)=>setAddressText(e.target.value)} placeholder={copy("location.address")}/><label className="text-xs text-slate-500">{copy("finder.buildingType")}<select className={`${select} mt-1`} value={type} onChange={(e)=>setType(e.target.value)}><option>住宅大樓</option><option>華廈</option><option>公寓</option></select></label><div className="grid gap-2 sm:grid-cols-3"><NumberField label="坪數" value={area} setValue={setArea}/><NumberField label="屋齡" value={age} setValue={setAge}/><NumberField label="樓層" value={floor} setValue={setFloor}/></div><Button className="w-full" disabled={loading||!city||!district||!road} onClick={estimate}>{loading?copy("valuation.calculating"):copy("valuation.estimate")}</Button></div></SectionCard></div>{result?<div className="min-w-0 space-y-4"><SectionCard title={copy("valuation.share")} description={copy("valuation.shareDescription")}><div className="flex min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap"><Button secondary className="w-full sm:w-auto" onClick={copyShareLink}>{copy("valuation.copyShare")}</Button><Button className="w-full sm:w-auto" onClick={downloadValuationSummary}>{copy("valuation.download")}</Button><Button secondary className="w-full sm:w-auto" onClick={()=>useLoanPrice(result.price_range.mid)}>{copy("valuation.useMedian")}</Button></div></SectionCard><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricTile label={copy("valuation.estimateTotal")} value={`${result.estimate_total_price.toLocaleString()} 萬`} /><MetricTile label={copy("valuation.unitPrice")} value={`${result.estimate_unit_price_per_ping} 萬`} /><MetricTile label={copy("valuation.confidence")} value={result.confidence_score} note={result.confidence}/><MetricTile label={copy("valuation.level")} value={valuationLevelLabel(result.estimate_level, copy)} note={result.matched_community?.community_name??copy("valuation.noCommunity")}/></div><SectionCard title={copy("valuation.basis")} description={result.confidence_reason}><div className="grid gap-2 text-xs text-slate-600 sm:grid-cols-2 lg:grid-cols-3"><p>{copy("valuation.dataSource")}：<strong>Supabase/Postgres</strong></p><p>{copy("valuation.composition")}：<strong>{valuationCompositionLabel(result.data_status.data_composition, copy)}</strong></p><p>{copy("valuation.source")}：<strong>{result.estimate_source_label}</strong></p><p>{copy("valuation.usedRecords")}：<strong>{result.valuation_explanation.sample_count} {copy("common.records")}</strong></p><p>{copy("valuation.sameRoad")}：<strong>{result.valuation_explanation.same_road_count} {copy("common.records")}</strong></p><p>{copy("valuation.sameType")}：<strong>{result.valuation_explanation.same_building_type_count} {copy("common.records")}</strong></p><p>{copy("valuation.similarity")}：<strong>{result.valuation_explanation.average_similarity_score}</strong></p><p>{result.matched_community?copy("valuation.communityMatch", {name: result.matched_community.community_name, confidence: result.matched_community.confidence}):copy("valuation.noCommunity")}</p></div></SectionCard><SectionCard title={copy("valuation.range")}><div className="grid gap-3 text-center sm:grid-cols-3"><MetricTile label={copy("valuation.low")} value={`${result.price_range.low.toLocaleString()} 萬`}/><MetricTile label={copy("valuation.mid")} value={`${result.price_range.mid.toLocaleString()} 萬`}/><MetricTile label={copy("valuation.high")} value={`${result.price_range.high.toLocaleString()} 萬`}/></div></SectionCard>{trend&&<ValuationTrendPanel trend={trend}/>}<DetailDisclosure title={copy("valuation.comparables")}><SwipeHint/><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[900px] text-left text-[10px]"><thead><tr className="bg-stone-50"><th className="p-2">{copy("common.period")}</th><th>{copy("common.source")}</th><th>{copy("map.road")}</th><th>{copy("finder.buildingType")}</th><th>{copy("location.area")}</th><th>{copy("valuation.unitPrice")}</th><th>{copy("valuation.estimateTotal")}</th><th>{copy("valuation.similarity")}</th><th>{copy("location.radius")}</th><th>{copy("common.dataLimit")}</th></tr></thead><tbody>{result.comparables.map((row,index)=><tr key={`${row.transaction_period}-${index}`} className="border-t border-stone-100"><td className="whitespace-nowrap p-2">{row.transaction_period}</td><td><span className={`whitespace-nowrap rounded-full px-2 py-1 font-bold ${row.source==="official_plvr_opendata"?"bg-cyan-50 text-cyan-800":"bg-amber-50 text-amber-800"}`}>{row.source_label||copy("valuation.sample")}</span></td><td className="max-w-[140px] break-words">{row.road}</td><td className="max-w-[160px] break-words">{row.building_type}</td><td>{row.area_ping}</td><td>{row.unit_price_per_ping}</td><td>{row.total_price}</td><td>{row.similarity_score}</td><td className="whitespace-nowrap">{formatComparableDistance(row, copy)}</td><td className="max-w-[220px] break-words">{row.note}</td></tr>)}</tbody></table></div></DetailDisclosure><Notice tone="warning">{result.disclaimer}</Notice></div>:<EmptyState title={copy("valuation.empty")} detail={copy("valuation.emptyDetail")} />}</div></div>;
}

function ValuationTrendPanel({trend}:{trend:ValuationTrendResult}){const { copy } = useExperienceLocale();const scope={road:copy("valuation.sameRoad"),district_type:copy("valuation.sameType"),district:copy("valuation.level")}[trend.data_scope];const scenarios=[["conservative",copy("tour.caseLowRisk")],["base",copy("tour.review")],["optimistic",copy("tour.highRisk")]] as const;return <SectionCard title={copy("valuation.trend")} description={`${copy("valuation.trendDescription")} ${trend.confidence_reason}`}><div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4"><MetricTile label={copy("common.source")} value={scope} note={`${trend.sample_count} ${copy("valuation.usedRecords")}`}/><MetricTile label={copy("valuation.unknownPeriod")} value={trend.effective_period_min&&trend.effective_period_max?`${trend.effective_period_min} ~ ${trend.effective_period_max}`:copy("valuation.unknownData")} note={trend.raw_period_min&&trend.raw_period_max?`${copy("common.period")}: ${trend.raw_period_min} ~ ${trend.raw_period_max}`:undefined}/><MetricTile label={copy("valuation.mid")} value={`${trend.recent_median_unit_price} 萬/坪`}/><MetricTile label={copy("valuation.trend")} value={`${(trend.trend_annualized_rate*100).toFixed(1)}%`} note={`${trend.volatility===null?copy("valuation.unknownData"):`${(trend.volatility*100).toFixed(1)}%`} · ${trend.confidence_level}`}/></div><p className="mt-3 text-[10px] leading-5 text-slate-500">{copy("valuation.dataStatus")}：{trend.excluded_future_period_count} / {trend.excluded_out_of_window_count}</p><div className="mt-4"><SwipeHint/><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[680px] text-left text-[10px]"><thead><tr className="bg-stone-50"><th className="p-2">{copy("valuation.scenario")}</th><th>{copy("common.period")}</th><th>{copy("valuation.unitPriceScenario")}</th><th>{copy("valuation.totalPrice")}</th><th>{copy("valuation.annualRate")}</th></tr></thead><tbody>{scenarios.flatMap(([key,label])=>trend.scenario_forecast[key].map(item=><tr key={`${key}-${item.horizon_months}`} className="border-t border-stone-100"><td className="p-2 font-bold">{label}</td><td>{item.horizon_months} {copy("valuation.months")}</td><td>{item.projected_unit_price_per_ping} 萬</td><td>{item.projected_total_price.toLocaleString()} 萬</td><td>{(item.growth_rate_used*100).toFixed(1)}%</td></tr>))}</tbody></table></div></div><details className="mt-4"><summary className="cursor-pointer text-xs font-bold text-cyan-800">{copy("valuation.recentData")}</summary><div className="mt-2"><SwipeHint/><div className="max-w-full touch-pan-x overflow-x-auto"><table className="w-full min-w-[520px] text-left text-[10px]"><thead><tr className="bg-stone-50"><th className="p-2">{copy("common.period")}</th><th>{copy("valuation.mid")}</th><th>{copy("common.count")}</th></tr></thead><tbody>{trend.monthly_series.slice(-24).map(item=><tr key={item.period} className="border-t border-stone-100"><td className="p-2">{item.period}</td><td>{item.median_unit_price_per_ping} 萬</td><td>{item.transaction_count}</td></tr>)}</tbody></table></div></div></details><p className="mt-4 text-[10px] leading-5 text-slate-500">{trend.disclaimer}</p></SectionCard>}

function ValuationDataStatusCard({status}:{status:ValuationDataStatus}){const { copy } = useExperienceLocale();const composition=status.data_composition??(status.is_demo_data?"sample":"official");const compositionLabel={sample:copy("valuation.sample"),official:copy("valuation.official"),mixed:copy("valuation.mixed")}[composition];const rawPeriod=status.raw_official_period_min&&status.raw_official_period_max?`${status.raw_official_period_min} ~ ${status.raw_official_period_max}`:copy("valuation.unknownPeriod");const effectivePeriod=status.oldest_effective_period&&status.newest_effective_period?`${status.oldest_effective_period} ~ ${status.newest_effective_period}`:status.effective_trend_period_min&&status.effective_trend_period_max?`${status.effective_trend_period_min} ~ ${status.effective_trend_period_max}`:copy("valuation.unknownPeriod");return <SectionCard title={copy("valuation.dataStatus")} description={status.source_note}><div className="grid gap-3 text-xs sm:grid-cols-2 xl:grid-cols-4"><MetricTile label={copy("valuation.source")} value={valuationSourceLabel(status.active_source, copy)} note={compositionLabel}/><MetricTile label={`${copy("valuation.official")} / ${copy("valuation.sample")}`} value={`${status.official_records_count??0} / ${status.sample_records_count??0}`} note={`${status.coverage.records_count.toLocaleString()} ${copy("common.records")}`}/><MetricTile label={copy("valuation.unknownPeriod")} value={rawPeriod} note={`${copy("valuation.unknownData")} ${status.excluded_future_period_count??0}`}/><MetricTile label={copy("valuation.trend")} value={effectivePeriod} note={`${copy("valuation.unknownData")} ${status.records_outside_retention_count??status.excluded_too_old_period_count??0}`}/><MetricTile label={copy("valuation.dataStatus")} value={`${status.retention_policy_years??3} 年`} note={status.retention_cutoff_period?`保留起點：${status.retention_cutoff_period}`:"依目前月份計算"}/><MetricTile label={copy("location.dataQuality")} value={`${status.coverage_city_count??status.coverage.cities.length} 縣市 / ${status.coverage_district_count??status.coverage.districts.length} 行政區`} note={`${(status.coverage_road_count??status.coverage.roads_count).toLocaleString()} 路段`}/><MetricTile label={copy("valuation.source")} value={status.latest_import_scope||copy("valuation.unknownData")} note={status.latest_import_status||undefined}/><MetricTile label={copy("valuation.usedRecords")} value={(status.latest_import_inserted_rows??0).toLocaleString()} note={`${copy("valuation.unknownData")} ${(status.latest_import_skipped_duplicates??0).toLocaleString()}`}/></div>{!status.is_full_taiwan&&<p className="mt-3 rounded-lg bg-amber-50 px-3 py-2 text-[10px] font-bold leading-5 text-amber-800">{status.coverage_summary??(composition==="sample"?copy("valuation.sample"):copy("valuation.official"))} {status.coverage_note_short}</p>}<p className="mt-3 rounded-lg bg-cyan-50 px-3 py-2 text-[10px] leading-5 text-cyan-900">{status.retention_note??copy("valuation.help")} {status.data_quality_note??copy("valuation.unknownData")}</p><p className="mt-2 text-[10px] leading-5 text-slate-500">{status.user_message} {status.update_frequency_note}</p><ValuationDataFreshness status={status}/></SectionCard>}
function SwipeHint(){return <p className="mb-2 text-[10px] font-medium text-slate-400 sm:hidden">表格可左右滑動</p>}
type RuntimeCopy = (key: RuntimeCopyKey, values?: Record<string, string | number>) => string;
function valuationLevelLabel(level:ValuationResult["estimate_level"], copy: RuntimeCopy){return {community:copy("valuation.level"),road:copy("valuation.sameRoad"),district:copy("valuation.level"),city:copy("map.city"),fallback:copy("valuation.unknownData")} [level];}
function valuationSourceLabel(source:ValuationDataStatus["active_source"], copy: RuntimeCopy){return {real_price_sample:copy("valuation.sample"),sqlite_index:"SQLite Index",postgres:"Postgres",mock_fallback:copy("valuation.sample"),unknown:copy("common.unavailable")} [source];}
function valuationCompositionLabel(composition:ValuationDataStatus["data_composition"]|undefined, copy: RuntimeCopy){return {official:copy("valuation.official"),mixed:copy("valuation.mixed"),sample:copy("valuation.sample")} [composition??"sample"];}
function formatComparableDistance(row:ValuationResult["comparables"][number], copy: RuntimeCopy){return row.distance_m!==null?`${row.distance_m}m`:row.note.includes("同路段")?copy("valuation.sameRoad"):copy("valuation.unknownData");}

function NumberField({label,value,setValue}:{label:string;value:number;setValue:(value:number)=>void}){return <label className="text-[10px] text-slate-500">{label}<input type="number" value={value} onChange={(e)=>setValue(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-stone-300 px-2 py-2 text-sm"/></label>;}
function TerrainRiskPage() {
  const { t, copy } = useExperienceLocale();
  return <SupportPage kicker={t("page.terrain")} title={t("page.terrain")} description={copy("location.description")} error="" help={copy("map.help")}><TerrainRiskAnalysis /></SupportPage>;
}

function LegacyTerrainRiskPage() {
  return <SupportPage kicker="風險模組" title="地勢與災害風險分析" description="用官方公開圖資，初步檢查坡度、淹水、坡地災害與地質敏感風險。" error="" help="這不是正式地質調查或建築結構鑑定，只是買房前的公開資料初步檢查。"><TerrainRiskAnalysis /></SupportPage>;
}
function SupportPage({ kicker, title, description, error, help, children }: { kicker: string; title: string; description: string; error: string; help: string; children: ReactNode }) { return <div className="space-y-6"><PageHeader kicker={kicker} title={title} description={description} /><HelpCallout>{help}</HelpCallout>{error && <ErrorState message={error} />}{children}</div>; }
