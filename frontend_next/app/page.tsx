"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { AppShell } from "@/components/app-shell";
import { HelpCallout } from "@/components/help-callout";
import { AppPage } from "@/components/sidebar";
import { WorkflowStepper } from "@/components/workflow-stepper";
import { Badge, Button, EmptyState, Notice } from "@/components/ui";
import { CaseCard, DecisionHero, ErrorState, LoadingState, MetricTile, ModuleTile, PageHeader, ResultSummaryPanel, SectionCard } from "@/components/product-ui";
import { API_BASE, api, downloadTaxReport, MapNearbyResult, MapSearchResult, MarketResult, NearbyCategory, NearbyPlace, TaxCase, TaxResult } from "@/lib/api";

const GeoMap = dynamic(() => import("@/components/map/geo-map"), { ssr: false, loading: () => <LoadingState label="地圖載入中..." /> });
type ResultTab = "原因" | "規則追蹤" | "補件清單" | "五年列管" | "AI 說明";

export default function Home() {
  const [page, setPage] = useState<AppPage>("儀表板");
  const [requestedCase, setRequestedCase] = useState("");
  const openTax = (caseId = "") => { setRequestedCase(caseId); setPage("TaxOracle"); };
  return <AppShell page={page} onNavigate={setPage}>{renderPage(page, setPage, openTax, requestedCase)}</AppShell>;
}

function renderPage(page: AppPage, setPage: (page: AppPage) => void, openTax: (caseId?: string) => void, requestedCase: string) {
  if (page === "TaxOracle") return <TaxOracle requestedCase={requestedCase} />;
  if (page === "Market Insight Lite") return <MarketInsight onMap={() => setPage("Map Insight Lite")} />;
  if (page === "Map Insight Lite") return <MapInsight />;
  if (page === "Aegis-Credit Lite") return <AegisCredit />;
  if (page === "LexProp Lite") return <LexProp />;
  if (page === "歷史案件") return <History />;
  return <Dashboard setPage={setPage} openTax={openTax} />;
}

function Dashboard({ setPage, openTax }: { setPage: (page: AppPage) => void; openTax: (caseId?: string) => void }) {
  const [selectedCase, setSelectedCase] = useState("DEMO-LOW");
  return <div className="space-y-6">
    <DecisionHero onPrimary={() => openTax(selectedCase)} onSecondary={() => setPage("Map Insight Lite")} />
    <HelpCallout>第一次使用建議先選一筆展示案件，進入 TaxOracle 快篩。</HelpCallout>
    <section><SectionTitle title="選一筆案件開始" note="先選擇決策情境，再進入稅務快篩。" /><div className="mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3"><CaseCard title="低風險換屋案" status="eligible" signal="green" description="展示完整可行流程與報告輸出" selected={selectedCase === "DEMO-LOW"} onSelect={() => setSelectedCase("DEMO-LOW")} onOpen={() => openTax("DEMO-LOW")} /><CaseCard title="中風險持分案" status="manual_review" signal="yellow" description="展示人工補件與資格複核" selected={selectedCase === "DEMO-MEDIUM"} onSelect={() => setSelectedCase("DEMO-MEDIUM")} onOpen={() => openTax("DEMO-MEDIUM")} /><CaseCard title="高風險非自住案" status="not_eligible" signal="red" description="展示規則阻擋與關鍵風險" selected={selectedCase === "DEMO-HIGH"} onSelect={() => setSelectedCase("DEMO-HIGH")} onOpen={() => openTax("DEMO-HIGH")} /></div></section>
    <section><SectionTitle title="分析流程" note="從案件條件一路整理成可溝通的決策報告。" /><div className="mt-3"><WorkflowStepper /></div></section>
    <section><SectionTitle title="下一步可以補強什麼？" note="搭配地圖、行情與風險摘要，補齊客戶說明。" /><div className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-4"><ModuleTile hint="TAX" title="稅務快篩" description="判斷資格與補件" tone="cyan" onClick={() => openTax(selectedCase)} /><ModuleTile hint="MAP" title="地圖洞察" description="查看區域與 POI" tone="green" onClick={() => setPage("Map Insight Lite")} /><ModuleTile hint="MARKET" title="區域行情" description="補充市場背景" tone="amber" onClick={() => setPage("Market Insight Lite")} /><ModuleTile hint="RISK" title="風險摘要" description="房貸與判決風險" tone="violet" onClick={() => setPage("Aegis-Credit Lite")} /></div></section>
  </div>;
}

function SectionTitle({ title, note }: { title: string; note: string }) {
  return <div className="flex min-w-0 flex-wrap items-baseline justify-between gap-x-4 gap-y-1"><h2 className="text-base font-bold text-slate-950">{title}</h2><p className="break-words text-xs text-slate-500">{note}</p></div>;
}

function TaxOracle({ requestedCase }: { requestedCase: string }) {
  const [cases, setCases] = useState<TaxCase[]>([]), [selected, setSelected] = useState(""), [result, setResult] = useState<TaxResult>(), [error, setError] = useState(""), [loading, setLoading] = useState(true), [analyzing, setAnalyzing] = useState(false), [tab, setTab] = useState<ResultTab>("原因");
  useEffect(() => { api.demoCases().then((rows) => { setCases(rows); setSelected(requestedCase && rows.some((r) => r.case_id === requestedCase) ? requestedCase : rows[0]?.case_id ?? ""); }).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, [requestedCase]);
  const taxCase = cases.find((item) => item.case_id === selected);
  async function analyze() { if (!taxCase) return; setAnalyzing(true); setError(""); try { setResult(await api.analyzeTax(taxCase)); setTab("原因"); } catch (e) { setError((e as Error).message); } finally { setAnalyzing(false); } }
  function reset() { setResult(undefined); setSelected(cases[0]?.case_id ?? ""); setError(""); }
  return <div className="space-y-5">
    <PageHeader kicker="案件決策" title="TaxOracle 稅務先知" description="重購退稅資格快篩、五年列管提醒與客戶溝通報告" />
    <HelpCallout>先載入展示案例，再執行分析；右側會顯示資格、風險與報告下載。</HelpCallout>
    <WorkflowStepper />
    {error && <ErrorState message={error} />}
    <div className="grid items-start gap-4 lg:grid-cols-[38%_minmax(0,62%)]">
      <SectionCard title="選擇案件" description="載入案件條件並執行規則快篩">
        <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-1">{cases.map((item, index) => <button key={item.case_id} disabled={loading} onClick={() => { setSelected(item.case_id); setResult(undefined); }} className={`flex items-center justify-between rounded-lg border px-3 py-2.5 text-left transition ${selected === item.case_id ? "border-cyan-500 bg-cyan-50 ring-2 ring-cyan-100" : "border-stone-200 bg-white hover:border-stone-300"}`}><span><span className="block text-xs font-bold text-slate-800">{["低風險換屋案", "中風險持分案", "高風險非自住案"][index] ?? item.case_id}</span><span className="mt-0.5 block text-[10px] text-slate-400">{item.case_id}</span></span><span className={`h-2 w-2 rounded-full ${index === 0 ? "bg-emerald-500" : index === 1 ? "bg-amber-500" : "bg-rose-500"}`} /></button>)}</div>
        {loading ? <div className="mt-4"><LoadingState label="載入案例中..." /></div> : taxCase && <CasePreview taxCase={taxCase} />}
        <div className="mt-4 flex flex-col gap-2 sm:flex-row"><Button disabled={loading || analyzing || !taxCase} onClick={analyze} className="w-full flex-1 bg-cyan-700 hover:bg-cyan-800">{analyzing ? "分析中..." : "開始稅務快篩"}</Button><button onClick={reset} className="px-2 py-2 text-xs font-bold text-slate-400 hover:text-slate-700">重設</button></div>
      </SectionCard>
      <TaxSummary result={result} taxCase={taxCase} />
    </div>
    {result ? <TaxResultTabs result={result} tab={tab} setTab={setTab} /> : <EmptyState title="尚未產生結果" detail="選擇案例並執行分析，結果原因、規則追蹤與補件清單將顯示在這裡。" />}
  </div>;
}

function CasePreview({ taxCase }: { taxCase: TaxCase }) {
  const items = [["案件", taxCase.case_id], ["客戶", taxCase.client_name], ["出售自住", yesNo(taxCase.sold_self_occupied)], ["換購自住", yesNo(taxCase.purchased_self_occupied)], ["文件完整", yesNo(taxCase.required_docs_complete)], ["五年列管", yesNo(taxCase.enters_five_year_monitoring)]];
  return <div className="mt-4 divide-y divide-slate-100 border-y border-slate-200">{items.map(([label, value]) => <div key={label} className="flex justify-between py-2.5 text-xs"><span className="text-slate-500">{label}</span><span className="font-bold text-slate-800">{value}</span></div>)}</div>;
}
const yesNo = (value: boolean) => value ? "是" : "否";

function TaxSummary({ result, taxCase }: { result?: TaxResult; taxCase?: TaxCase }) {
  const [downloading, setDownloading] = useState(false), [error, setError] = useState("");
  async function download() { if (!taxCase) return; setDownloading(true); setError(""); try { await downloadTaxReport(taxCase); } catch (e) { setError((e as Error).message); } finally { setDownloading(false); } }
  const statusLabel = result?.eligibility_status === "eligible" ? "可行" : result?.eligibility_status === "manual_review" ? "需複核" : "高風險";
  const keyReasons = result?.rule_traces.filter((row) => row.outcome !== "passed").slice(0, 3) ?? [];
  return <ResultSummaryPanel className="lg:sticky lg:top-16"><div className="flex items-center justify-between border-b border-stone-100 px-5 py-4"><div><p className="text-[10px] font-bold tracking-wider text-slate-400">DECISION SUMMARY</p><h2 className="mt-1 font-bold text-slate-950">案件決策摘要</h2></div>{result && <Badge value={result.signal_color} />}</div>{!result ? <div className="p-5"><EmptyState title="等待稅務快篩" detail="完成分析後，資格、風險原因與報告入口會集中顯示在這裡。" /></div> : <div className="p-5"><div className="grid gap-5 sm:grid-cols-[150px_1fr]"><RiskGauge score={result.risk_score} signal={result.signal_color} /><div><p className="text-[10px] font-bold text-slate-400">資格判斷</p><p className="mt-1 text-3xl font-bold tracking-tight text-slate-950">{statusLabel}</p><p className="mt-2 text-sm leading-6 text-slate-600">{result.ai_explanation.headline}</p><div className="mt-3 flex gap-2"><Badge value={result.eligibility_status} /><Badge value={result.signal_color} /></div></div></div><div className="mt-5 rounded-xl bg-stone-50 p-3.5"><p className="text-xs font-bold text-slate-700">關鍵原因</p><ul className="mt-2 space-y-2">{keyReasons.length ? keyReasons.map((row) => <li key={row.code} className="flex gap-2 text-xs text-slate-600"><span className="font-bold text-cyan-700">{row.code}</span><span>{row.title}</span></li>) : <li className="text-xs text-emerald-700">主要資格條件皆已通過。</li>}</ul></div><Button onClick={download} disabled={downloading} className="mt-4 w-full bg-cyan-700 hover:bg-cyan-800">{downloading ? "產生報告中..." : "下載客戶溝通報告"}</Button><p className="mt-3 text-center text-[10px] text-slate-400">AI 僅做語言化說明，資格由規則引擎判斷。</p>{error && <div className="mt-3"><ErrorState message={error} /></div>}</div>}</ResultSummaryPanel>;
}

function RiskGauge({ score, signal }: { score: number; signal: string }) {
  const color = signal === "green" ? "#10b981" : signal === "yellow" ? "#f59e0b" : "#f43f5e";
  return <div className="grid place-items-center"><div className="grid h-32 w-32 place-items-center rounded-full" style={{ background: `conic-gradient(${color} ${score * 3.6}deg, #e7e5e4 0deg)` }}><div className="grid h-24 w-24 place-items-center rounded-full bg-white text-center"><div><p className="text-3xl font-bold text-slate-950">{score}</p><p className="text-[9px] font-bold text-slate-400">風險分數 / 100</p></div></div></div></div>;
}

function TaxResultTabs({ result, tab, setTab }: { result: TaxResult; tab: ResultTab; setTab: (tab: ResultTab) => void }) {
  const tabs: ResultTab[] = ["原因", "規則追蹤", "補件清單", "五年列管", "AI 說明"];
  return <section className="border border-slate-200 bg-white"><div className="flex overflow-x-auto border-b border-slate-200">{tabs.map((item) => <button key={item} onClick={() => setTab(item)} className={`border-b-2 px-4 py-2.5 text-xs font-bold ${tab === item ? "border-cyan-700 text-cyan-800" : "border-transparent text-slate-500 hover:text-slate-800"}`}>{item}</button>)}</div><div className="p-4">{tab === "原因" && <p className="text-sm leading-7 text-slate-600">{result.ai_explanation.headline}</p>}{tab === "規則追蹤" && <RuleTable result={result} />}{tab === "補件清單" && <SimpleList items={result.missing_docs.length ? result.missing_docs : ["目前無補件項目"]} />}{tab === "五年列管" && <SimpleList items={result.reminder_timeline} numbered />}{tab === "AI 說明" && <div><p className="text-sm leading-7 text-slate-700">{result.ai_explanation.customer_script}</p><p className="mt-4 border-l-2 border-cyan-600 pl-3 text-xs font-bold text-cyan-800">AI 只做語言化說明，資格由規則引擎 TX001–TX009 判斷。</p></div>}</div><div className="border-t border-amber-200 bg-amber-50 px-4 py-2.5 text-xs leading-5 text-amber-800">{result.disclaimer}</div></section>;
}

function RuleTable({ result }: { result: TaxResult }) {
  return <div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-[11px]"><thead className="bg-stone-50 text-slate-500"><tr><th className="px-3 py-2">規則</th><th className="px-3">檢查項目</th><th className="px-3">結果</th><th className="px-3">說明</th><th className="px-3 text-right">分數</th></tr></thead><tbody>{result.rule_traces.map((row) => <tr key={row.code} className="border-t border-stone-100"><td className="px-3 py-2.5 font-bold">{row.code}</td><td className="px-3 font-medium">{row.title}</td><td className="px-3"><Badge value={row.outcome} /></td><td className="max-w-md px-3 text-slate-500">{row.detail}</td><td className="px-3 text-right font-bold">{row.risk_points}</td></tr>)}</tbody></table></div>;
}

function SimpleList({ items, numbered = false }: { items: string[]; numbered?: boolean }) {
  return <ul className={numbered ? "relative ml-2 border-l border-cyan-200" : "space-y-2"}>{items.map((item, index) => <li key={item} className={`flex gap-3 text-sm text-slate-600 ${numbered ? "relative pb-4 pl-5" : "rounded-lg bg-stone-50 px-3 py-2.5"}`}><span className={`${numbered ? "absolute -left-3 grid h-6 w-6 place-items-center rounded-full border border-cyan-200 bg-white text-[10px]" : "grid h-5 w-5 shrink-0 place-items-center rounded-md bg-emerald-100 text-[10px] text-emerald-700"} font-bold`}>{numbered ? index + 1 : "✓"}</span>{item}</li>)}</ul>;
}

function MapInsight() {
  const categoryKeys = ["transport", "school", "park", "medical", "shopping", "food"];
  const categoryLabels: Record<string, string> = { transport: "交通", school: "學校", park: "公園", medical: "醫療", shopping: "商圈", food: "餐飲" };
  const [query, setQuery] = useState("台北市大安區和平東路二段"), [location, setLocation] = useState<MapSearchResult>(), [result, setResult] = useState<MapNearbyResult>(), [active, setActive] = useState<string[]>(categoryKeys), [selectedPlace, setSelectedPlace] = useState<NearbyPlace>(), [loading, setLoading] = useState(true), [error, setError] = useState("");
  async function search(next = query) { setLoading(true); setError(""); setSelectedPlace(undefined); try { const found = await api.mapSearch(next); if (!found.matched || !found.center) throw new Error("找不到符合的地址，請改用範例地址或行政區。"); setLocation(found); setResult(await api.mapNearby(found.center, categoryKeys)); } catch (e) { setError((e as Error).message); } finally { setLoading(false); } }
  useEffect(() => { search("台北市大安區和平東路二段"); }, []);
  const categories = result?.categories.filter((group) => active.includes(group.category)) ?? [];
  const allSelected = active.length === categoryKeys.length;
  const totalPlaces = result?.categories.reduce((sum, group) => sum + group.count, 0) ?? 0;
  return <div className="space-y-4"><PageHeader kicker="區域洞察" title="Map Insight 周遭生活機能" description="搜尋地址，查看 800 公尺生活圈的交通、採買、餐飲與公共設施。" />
    <HelpCallout>輸入地址或路段，系統會顯示周遭設施與生活機能摘要。</HelpCallout>
    {error && <div className="rounded-xl border border-amber-200 bg-amber-50 p-3"><ErrorState message={error} /><p className="mt-2 break-all text-[10px] text-amber-700">目前連線來源：{API_BASE || "尚未設定"}</p></div>}
    {result ? <div className="overflow-hidden rounded-2xl border border-stone-200 bg-white shadow-[0_14px_40px_rgba(71,85,105,0.12)] xl:grid xl:min-h-[720px] xl:grid-cols-[minmax(0,1fr)_380px]">
      <div className="relative h-[480px] min-w-0 sm:h-[560px] xl:h-auto"><GeoMap center={result.center} zoom={15} categories={categories} selectedPlace={selectedPlace} onSelectPlace={setSelectedPlace} />
        <form onSubmit={(e) => { e.preventDefault(); search(); }} className="absolute left-2 right-2 top-2 z-[500] flex min-w-0 flex-col gap-2 rounded-xl border border-white/80 bg-white/95 p-2 shadow-lg backdrop-blur-md sm:left-4 sm:right-auto sm:top-4 sm:w-[min(650px,calc(100%-2rem))] sm:flex-row"><input value={query} onChange={(e) => setQuery(e.target.value)} className="min-w-0 flex-1 rounded-lg bg-stone-50 px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-cyan-200" placeholder="輸入地址、行政區或路段，例如：台北市大安區和平東路二段" /><Button disabled={loading} className="w-full bg-cyan-700 hover:bg-cyan-800 sm:w-auto">{loading ? "定位中..." : "搜尋區域"}</Button></form>
        <div className="absolute bottom-3 left-3 z-[500] max-w-[calc(100%-1.5rem)] rounded-xl border border-white/80 bg-white/92 px-3 py-2 shadow-md backdrop-blur-md"><div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[10px]"><strong className="text-slate-800">{location ? `${location.city}${location.district}${location.road}` : query}</strong><SourceBadge source={location?.source ?? result.source} /><span className="text-slate-500">半徑 {result.radius_m}m</span></div><MapLegend /></div>
      </div>
      <aside className="min-w-0 border-t border-stone-200 bg-white p-4 xl:max-h-[720px] xl:overflow-y-auto xl:border-l xl:border-t-0">
        <div className="flex items-start justify-between gap-3"><div><p className="text-[10px] font-bold tracking-wider text-cyan-700">區域總評</p><h2 className="mt-1 text-base font-bold text-slate-950">{location?.district || location?.road || "區域總覽"}</h2></div><div className="rounded-xl bg-cyan-50 px-3 py-2 text-right"><p className="text-3xl font-bold text-cyan-800">{result.livability_score}</p><p className="text-[9px] font-bold text-cyan-700">生活機能分數</p></div></div>
        <p className="mt-3 text-xs leading-5 text-slate-600">{result.summary}</p>
        <h3 className="mt-5 text-xs font-bold text-slate-900">設施分類</h3><div className="mt-2 flex flex-wrap gap-1.5"><button onClick={() => setActive(allSelected ? [] : categoryKeys)} className={`rounded-full border px-2.5 py-1.5 text-[10px] font-bold ${allSelected ? "border-slate-700 bg-slate-800 text-white" : "border-stone-200 bg-white text-slate-500"}`}>全部 {totalPlaces}</button>{result.categories.map((group) => <button key={group.category} onClick={() => setActive((items) => items.includes(group.category) ? items.filter((x) => x !== group.category) : [...items, group.category])} className={`rounded-full border px-2.5 py-1.5 text-[10px] font-bold ${active.includes(group.category) ? "border-cyan-300 bg-cyan-50 text-cyan-800" : "border-stone-200 bg-white text-slate-400"}`}>{group.label} {group.count}</button>)}</div>
        <h3 className="mt-5 text-xs font-bold text-slate-900">分數拆解</h3><div className="mt-2 space-y-2">{categoryKeys.map((key) => <ScoreBar key={key} label={categoryLabels[key]} score={result.category_scores?.[key] ?? 0} />)}</div><p className="mt-2 text-[9px] leading-4 text-slate-400">{result.score_explanation}</p>
        <h3 className="mt-5 text-xs font-bold text-slate-900">最近設施</h3><div className="mt-2 grid gap-2">{result.nearest_places?.slice(0, 3).map((place) => <button key={place.place_id} onClick={() => setSelectedPlace(place)} className="flex items-center justify-between rounded-lg bg-stone-50 px-3 py-2 text-left hover:bg-cyan-50"><span className="min-w-0"><span className="block truncate text-[11px] font-bold text-slate-800">{place.name}</span><span className="text-[9px] text-slate-500">{categoryLabels[place.category]} · {place.rating ? `★ ${place.rating}` : "尚無評分"}</span></span><strong className="shrink-0 text-[10px] text-cyan-700">{Math.round(place.distance_m)}m</strong></button>)}</div>
        <div className="mt-5 border-l-2 border-cyan-500 pl-3"><h3 className="text-xs font-bold text-slate-900">客戶說明建議</h3><p className="mt-1 text-[11px] leading-5 text-slate-600">{result.recommendation_text}</p></div>
        <h3 className="mt-5 text-xs font-bold text-slate-900">附近地點</h3><PlaceList categories={categories} selected={selectedPlace} onSelect={setSelectedPlace} />
        <p className="mt-4 border-t border-stone-200 pt-3 text-[9px] leading-4 text-slate-500">{result.source === "mock" ? "目前使用展示資料。 " : ""}{result.disclaimer}</p>
      </aside>
    </div> : <MapLoadingSkeleton />}</div>;
}

function ScoreBar({ label, score }: { label: string; score: number }) {
  return <div><div className="mb-1 flex justify-between text-[10px]"><span className="font-medium text-slate-600">{label}</span><strong className="text-slate-800">{score}</strong></div><div className="h-1.5 overflow-hidden rounded-full bg-stone-100"><div className="h-full rounded-full bg-cyan-600 transition-all" style={{ width: `${score}%` }} /></div></div>;
}

function MapLegend() {
  const items = [["交通", "bg-blue-600"], ["學校", "bg-violet-600"], ["公園", "bg-green-600"], ["醫療", "bg-rose-600"], ["商圈", "bg-orange-600"], ["餐飲", "bg-amber-600"]];
  return <div className="mt-1.5 flex flex-wrap gap-x-2 gap-y-1">{items.map(([label, color]) => <span key={label} className="flex items-center gap-1 text-[8px] text-slate-500"><i className={`h-1.5 w-1.5 rounded-full ${color}`} />{label}</span>)}</div>;
}

function MapLoadingSkeleton() {
  return <div className="grid min-h-[560px] animate-pulse overflow-hidden rounded-2xl border border-stone-200 bg-white xl:grid-cols-[minmax(0,1fr)_380px]"><div className="bg-gradient-to-br from-stone-100 via-cyan-50 to-stone-200" /><div className="space-y-4 border-l border-stone-200 p-4"><div className="h-8 w-2/3 rounded bg-stone-100" /><div className="h-16 rounded bg-stone-100" />{[1, 2, 3, 4, 5, 6].map((item) => <div key={item} className="h-8 rounded bg-stone-100" />)}</div></div>;
}

function SourceBadge({ source }: { source: string }) {
  const isGoogle = source.startsWith("google");
  return <span className={`rounded-full px-2 py-0.5 text-[8px] font-bold ${isGoogle ? "bg-blue-100 text-blue-700" : "bg-amber-100 text-amber-700"}`}>{isGoogle ? "Google" : "Mock fallback"}</span>;
}

function PlaceList({ categories, selected, onSelect }: { categories: NearbyCategory[]; selected?: NearbyPlace; onSelect: (place: NearbyPlace) => void }) {
  const places = categories.flatMap((group) => group.places.map((place) => ({ ...place, label: group.label })));
  return <div className="mt-2 space-y-2">{places.length ? places.map((place) => <button key={place.place_id} onClick={() => onSelect(place)} className={`w-full rounded-lg border p-2.5 text-left transition ${selected?.place_id === place.place_id ? "border-cyan-500 bg-cyan-50 ring-2 ring-cyan-100" : "border-stone-200 bg-white hover:border-cyan-200"}`}><div className="flex items-start justify-between gap-2"><div className="min-w-0"><p className="truncate text-xs font-bold text-slate-800">{place.name}</p><div className="mt-1 flex flex-wrap items-center gap-1.5"><span className="rounded-full bg-cyan-50 px-1.5 py-0.5 text-[8px] font-bold text-cyan-700">{place.label}</span><span className="text-[9px] font-bold text-slate-500">{Math.round(place.distance_m)} 公尺</span>{place.rating && <span className="text-[9px] font-bold text-amber-600">★ {place.rating} ({place.user_rating_count})</span>}</div></div><span className="shrink-0 text-[8px] text-emerald-700">{place.business_status === "OPERATIONAL" ? "營業中" : place.business_status}</span></div><p className="mt-1.5 truncate text-[9px] text-slate-400">{place.address}</p><p className="mt-1 text-[8px] font-bold text-slate-400">{place.source === "google_places" ? "Google Places" : "展示資料"}</p></button>) : <p className="rounded-lg bg-stone-50 p-3 text-[10px] text-slate-400">目前分類沒有找到周遭設施。</p>}</div>;
}

function MarketInsight({ onMap }: { onMap: () => void }) {
  const [regions, setRegions] = useState<{city:string;district:string}[]>([]), [selected, setSelected] = useState(""), [result, setResult] = useState<MarketResult>(), [loading, setLoading] = useState(true), [error, setError] = useState("");
  useEffect(() => { api.marketRegions().then(async (rows) => { setRegions(rows); const first = rows[0]; if (first) { setSelected(`${first.city}|${first.district}`); setResult(await api.marketInsight(first.city, first.district)); } }).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
  async function change(value:string) { setSelected(value); setLoading(true); try { const [city,district] = value.split("|"); setResult(await api.marketInsight(city,district)); } catch (e) { setError((e as Error).message); } finally { setLoading(false); } }
  return <div className="space-y-6"><PageHeader kicker="區域洞察" title="Market Insight 區域行情" description="比較區域行情、交易量與生活機能。" action={<Button secondary onClick={onMap}>查看地圖洞察</Button>} /><HelpCallout>用來補充區域行情與趨勢，不取代正式估價。</HelpCallout>{error && <ErrorState message={error} />}<SectionCard><select disabled={loading} value={selected} onChange={(e) => change(e.target.value)} className="w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm">{regions.map((r) => <option key={`${r.city}|${r.district}`} value={`${r.city}|${r.district}`}>{r.city} {r.district}</option>)}</select></SectionCard>{loading ? <LoadingState /> : result && <><div className="grid gap-3 md:grid-cols-4"><MetricTile label="平均單價" value={`${result.avg_price_per_ping} 萬 / 坪`} /><MetricTile label="交易量" value={result.transaction_volume} /><MetricTile label="生活機能" value={result.livability_score} /><MetricTile label="ESG 輔助分數" value={result.esg_lite_score} /></div><SectionCard title="六期行情趨勢"><div className="flex h-36 items-end gap-3">{result.trend.map((value,index) => <div key={index} className="flex flex-1 flex-col items-center gap-1"><span className="text-[10px] font-bold">{value}</span><div className="w-full bg-cyan-600" style={{height:`${value}%`}} /><span className="text-[10px] text-slate-400">第 {index+1} 期</span></div>)}</div></SectionCard><Notice tone="warning">{result.disclaimer}</Notice></>}</div>;
}

function AegisCredit() {
  const [result,setResult]=useState<{risk_score:number;signal_color:string;traces:string[]}>(), [loading,setLoading]=useState(false), [error,setError]=useState("");
  async function run(){setLoading(true);try{setResult(await api.aegis({monthly_income:90000,monthly_debt:15000,cash:3500000,property_count:0,mortgage_count:0,property_price:22000000}));}catch(e){setError((e as Error).message);}finally{setLoading(false);}}
  return <SupportPage kicker="風險模組" title="房貸風險展示" description="快速了解買方條件的風險輪廓，不代表銀行核貸。" error={error} help="展示型風險摘要，不代表銀行核貸或正式授信結論。"><SectionCard><p className="text-sm text-slate-500">使用預設買方情境進行展示型評估。</p><Button onClick={run} disabled={loading} className="mt-4">{loading?"分析中...":"執行分析"}</Button></SectionCard>{result&&<div className="grid gap-3 md:grid-cols-2"><MetricTile label="風險分數" value={result.risk_score}/><MetricTile label="風險狀態" value={<Badge value={result.signal_color}/>} /></div>}</SupportPage>;
}
function LexProp() {
  const [result,setResult]=useState<{risk_score:number;match_count:number;summary:string}>(), [loading,setLoading]=useState(false), [error,setError]=useState("");
  async function run(){setLoading(true);try{setResult(await api.lexprop({city:"台北市",district:"信義區",road_masked:"松仁路***號",community:"信義首席"}));}catch(e){setError((e as Error).message);}finally{setLoading(false);}}
  return <SupportPage kicker="風險模組" title="判決風險摘要" description="以匿名化條件比對公開判決摘要，不輸出完整門牌與個資。" error={error} help="展示型風險摘要，不代表正式法律結論。"><SectionCard><p className="text-sm text-slate-500">使用預設匿名化案例查詢潛在風險。</p><Button onClick={run} disabled={loading} className="mt-4">{loading?"查詢中...":"查詢摘要"}</Button></SectionCard>{result&&<><div className="grid gap-3 md:grid-cols-2"><MetricTile label="比對筆數" value={result.match_count}/><MetricTile label="風險分數" value={result.risk_score}/></div><SectionCard title="摘要"><p className="text-sm leading-7 text-slate-600">{result.summary}</p></SectionCard></>}</SupportPage>;
}
function SupportPage({ kicker, title, description, error, help, children }: { kicker: string; title: string; description: string; error: string; help: string; children: ReactNode }) { return <div className="space-y-6"><PageHeader kicker={kicker} title={title} description={description} /><HelpCallout>{help}</HelpCallout>{error && <ErrorState message={error} />}{children}</div>; }

function History() {
  const [rows,setRows]=useState<Record<string,string|number>[]>([]), [loading,setLoading]=useState(true), [error,setError]=useState("");
  useEffect(()=>{api.history().then(setRows).catch((e)=>setError(e.message)).finally(()=>setLoading(false));},[]);
  return <div className="space-y-6"><PageHeader kicker="紀錄" title="歷史案件" description="查看已完成的 TaxOracle 分析結果。" />{error&&<ErrorState message={error}/>} {loading?<LoadingState/>:<section className="overflow-x-auto border border-slate-200 bg-white"><table className="w-full min-w-[720px] text-left text-xs"><thead className="bg-slate-50 text-slate-500"><tr><th className="px-4 py-3">案件</th><th>客戶</th><th>資格</th><th>分數</th><th>燈號</th><th>建立時間</th></tr></thead><tbody>{rows.map((row)=><tr key={row.id} className="border-t border-slate-100"><td className="px-4 py-3 font-bold">{row.case_id}</td><td>{row.client_name}</td><td><Badge value={String(row.eligibility_status)}/></td><td className="font-bold">{row.risk_score}</td><td><Badge value={String(row.signal_color)}/></td><td className="text-slate-500">{row.created_at}</td></tr>)}</tbody></table></section>}</div>;
}
