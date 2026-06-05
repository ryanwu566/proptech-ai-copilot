"use client";

import { useEffect, useState } from "react";
import { api, downloadTaxReport, MarketResult, TaxCase, TaxResult } from "@/lib/api";
import { Badge, Button, Card, Metric, Notice } from "@/components/ui";

type Page = "儀表板" | "TaxOracle" | "Market Insight Lite" | "Aegis-Credit Lite" | "LexProp Lite" | "歷史案件";
const pages: Page[] = ["儀表板", "TaxOracle", "Market Insight Lite", "Aegis-Credit Lite", "LexProp Lite", "歷史案件"];
const icons = ["▦", "◆", "▥", "◒", "◎", "≡"];

export default function Home() {
  const [page, setPage] = useState<Page>("儀表板");
  return (
    <div className="min-h-screen bg-canvas">
      <aside className="fixed inset-y-0 left-0 w-64 border-r border-slate-200 bg-slate-950 px-4 py-6 text-white">
        <div className="mb-8 px-2">
          <p className="text-xs font-bold tracking-[0.22em] text-blue-300">PROPTECH AI</p>
          <h1 className="mt-2 text-lg font-bold">Copilot Console</h1>
          <p className="mt-2 text-xs text-slate-400">產品化競賽展示版本</p>
        </div>
        <nav className="space-y-1">
          {pages.map((item, index) => (
            <button key={item} onClick={() => setPage(item)} className={`flex w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm transition ${page === item ? "bg-blue-600 font-bold" : "text-slate-300 hover:bg-slate-900"}`}>
              <span>{icons[index]}</span>{item}
            </button>
          ))}
        </nav>
        <div className="absolute bottom-6 left-4 right-4 rounded-xl border border-slate-800 p-3 text-xs text-slate-400">
          Mock data mode<br /><span className="text-emerald-400">● FastAPI backend</span>
        </div>
      </aside>
      <main className="ml-64 min-w-0">
        <Header page={page} />
        <div className="mx-auto max-w-[1366px] p-8">{renderPage(page, setPage)}</div>
      </main>
    </div>
  );
}

function renderPage(page: Page, setPage: (page: Page) => void) {
  if (page === "TaxOracle") return <TaxOracle />;
  if (page === "Market Insight Lite") return <MarketInsight />;
  if (page === "Aegis-Credit Lite") return <AegisCredit />;
  if (page === "LexProp Lite") return <LexProp />;
  if (page === "歷史案件") return <History />;
  return <Dashboard setPage={setPage} />;
}

function Header({ page }: { page: Page }) {
  return <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-8"><div><p className="text-xs font-semibold text-slate-400">PropTech AI Copilot</p><h2 className="text-lg font-bold">{page}</h2></div><Badge value="mock-data" /></header>;
}

function Title({ title, subtitle }: { title: string; subtitle: string }) {
  return <div className="mb-7"><h2 className="text-3xl font-bold tracking-tight">{title}</h2><p className="mt-2 max-w-4xl text-sm leading-6 text-muted">{subtitle}</p></div>;
}

function Dashboard({ setPage }: { setPage: (page: Page) => void }) {
  const steps = [
    ["01", "選擇 TaxOracle demo case", "低、中、高風險案例清楚對應 green、yellow、red。"],
    ["02", "執行分析", "資格由 TX001-TX009 deterministic rule engine 產生。"],
    ["03", "下載 HTML report", "將結果、補件與五年列管整理成客戶溝通報告。"],
  ];
  return <>
    <Title title="營運儀表板" subtitle="TaxOracle 是主展示線，其他模組提供 Lite 情境補強。推薦以競賽展示模式快速走完完整流程。" />
    <div className="grid gap-4 md:grid-cols-3"><Metric label="核心引擎" value="TX001-TX009" note="deterministic rule engine" /><Metric label="展示案例" value="3 組" note="eligible / manual_review / not_eligible" /><Metric label="資料模式" value="Offline Mock" note="不串政府 API" /></div>
    <Card className="mt-6 border-blue-200 bg-gradient-to-br from-white to-blue-50">
      <div className="flex items-start justify-between gap-6"><div><p className="text-xs font-bold tracking-widest text-blue-600">DEMO MODE</p><h3 className="mt-2 text-2xl font-bold">競賽展示模式</h3><p className="mt-2 text-sm text-muted">三步驟完成 TaxOracle 產品展示，適合 3 分鐘簡報。</p></div><Button onClick={() => setPage("TaxOracle")}>開始展示</Button></div>
      <div className="mt-6 grid gap-4 md:grid-cols-3">{steps.map(([number, title, detail]) => <div key={number} className="rounded-2xl border border-blue-100 bg-white p-4"><p className="text-xs font-bold text-blue-600">{number}</p><h4 className="mt-2 font-bold">{title}</h4><p className="mt-2 text-xs leading-5 text-muted">{detail}</p></div>)}</div>
    </Card>
    <div className="mt-6 grid gap-5 lg:grid-cols-3">
      <Card className="lg:col-span-2"><p className="text-xs font-bold text-blue-600">PRIMARY WORKFLOW</p><h3 className="mt-3 text-2xl font-bold">TaxOracle 稅務先知</h3><p className="mt-2 text-sm leading-7 text-muted">展示重購退稅資格、風險燈號、補件清單、五年列管與 HTML 報告。</p></Card>
      <Card><p className="text-xs font-bold text-emerald-600">LITE INSIGHT</p><h3 className="mt-3 text-xl font-bold">Market Insight Lite</h3><p className="mt-2 text-sm leading-7 text-muted">區域行情、POI 生活機能、ESG / SDG 11 Lite。</p><div className="mt-5"><Button secondary onClick={() => setPage("Market Insight Lite")}>查看區域洞察</Button></div></Card>
    </div>
  </>;
}

function TaxOracle() {
  const [cases, setCases] = useState<TaxCase[]>([]);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState<TaxResult>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  useEffect(() => { api.demoCases().then((rows) => { setCases(rows); setSelected(rows[0]?.case_id ?? ""); }).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
  const taxCase = cases.find((item) => item.case_id === selected);
  async function analyze() { if (!taxCase) return; setAnalyzing(true); setError(""); try { setResult(await api.analyzeTax(taxCase)); } catch (e) { setError((e as Error).message); } finally { setAnalyzing(false); } }
  return <>
    <Title title="TaxOracle 稅務先知" subtitle="稅務資格快篩與五年列管提醒。AI 只負責說明，資格判斷由 Python deterministic rule engine 完成。" />
    {error && <Notice tone="error">{error}</Notice>}
    <Card className="mt-4"><div className="flex flex-wrap items-end gap-4"><label className="min-w-64 flex-1 text-sm font-bold">選擇 demo case<select disabled={loading} value={selected} onChange={(e) => { setSelected(e.target.value); setResult(undefined); }} className="mt-2 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal">{cases.map((item) => <option key={item.case_id}>{item.case_id}</option>)}</select></label><Button disabled={loading || analyzing || !taxCase} onClick={analyze}>{analyzing ? "分析中..." : "執行 TaxOracle 分析"}</Button></div>{loading && <p className="mt-4 text-sm text-muted">載入 demo case 中...</p>}</Card>
    {result && taxCase && <TaxResultView result={result} taxCase={taxCase} />}
  </>;
}

function TaxResultView({ result, taxCase }: { result: TaxResult; taxCase: TaxCase }) {
  const [downloadError, setDownloadError] = useState("");
  const [downloading, setDownloading] = useState(false);
  async function download() { setDownloading(true); setDownloadError(""); try { await downloadTaxReport(taxCase); } catch (e) { setDownloadError((e as Error).message); } finally { setDownloading(false); } }
  return <div className="mt-6 space-y-5">
    <div className="grid gap-4 md:grid-cols-3"><Metric label="資格結論" value={<Badge value={result.eligibility_status} />} /><Metric label="風險分數" value={result.risk_score} /><Metric label="風險燈號" value={<Badge value={result.signal_color} />} /></div>
    <Card><div className="flex flex-wrap items-start justify-between gap-4"><div><h3 className="font-bold">為什麼是這個結果？</h3><p className="mt-2 text-sm text-muted">{result.ai_explanation.headline}</p><p className="mt-3 text-xs font-bold text-blue-700">AI 只負責說明，資格判斷由 TX001-TX009 rule engine 完成。</p></div><Button disabled={downloading} onClick={download}>{downloading ? "產生報告中..." : "下載 HTML report"}</Button></div>{downloadError && <div className="mt-4"><Notice tone="error">{downloadError}</Notice></div>}</Card>
    <Card><h3 className="font-bold">Rule Trace</h3><div className="mt-4 overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">規則</th><th className="px-3">項目</th><th className="px-3">結果</th><th className="px-3">說明</th><th className="px-3">分數</th></tr></thead><tbody>{result.rule_traces.map((row) => <tr key={row.code} className="border-b border-slate-100"><td className="px-3 py-3 font-bold">{row.code}</td><td className="px-3">{row.title}</td><td className="px-3"><Badge value={row.outcome} /></td><td className="px-3 text-muted">{row.detail}</td><td className="px-3">{row.risk_points}</td></tr>)}</tbody></table></div></Card>
    <div className="grid gap-4 md:grid-cols-2"><Card><h3 className="font-bold">補件清單</h3><ul className="mt-3 list-disc space-y-2 pl-5 text-sm text-muted">{(result.missing_docs.length ? result.missing_docs : ["目前無補件項目"]).map((item) => <li key={item}>{item}</li>)}</ul></Card><Card><h3 className="font-bold">五年列管 Timeline</h3><ul className="mt-3 space-y-2 text-sm text-muted">{result.reminder_timeline.map((item) => <li key={item}>{item}</li>)}</ul></Card></div>
    <Notice tone="warning">{result.disclaimer}</Notice>
  </div>;
}

function MarketInsight() {
  const [regions, setRegions] = useState<{city:string;district:string}[]>([]);
  const [selected, setSelected] = useState("");
  const [result, setResult] = useState<MarketResult>();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => { api.marketRegions().then(async (rows) => { setRegions(rows); const first = rows[0]; if (first) { setSelected(`${first.city}|${first.district}`); setResult(await api.marketInsight(first.city, first.district)); } }).catch((e) => setError(e.message)).finally(() => setLoading(false)); }, []);
  async function change(value:string) { setSelected(value); setLoading(true); setError(""); const [city,district] = value.split("|"); try { setResult(await api.marketInsight(city,district)); } catch (e) { setError((e as Error).message); } finally { setLoading(false); } }
  return <><Title title="Market Insight Lite" subtitle="延續 OmniUrbanAI v2 保留概念，只使用離線 mock data，不代表正式估價或投資建議。" />{error && <Notice tone="error">{error}</Notice>}<Card className="mt-4"><label className="text-sm font-bold">選擇區域<select disabled={loading} value={selected} onChange={(e) => change(e.target.value)} className="mt-2 w-full rounded-xl border border-slate-200 px-3 py-2 font-normal">{regions.map((r) => <option key={`${r.city}|${r.district}`} value={`${r.city}|${r.district}`}>{r.city} {r.district}</option>)}</select></label>{loading && <p className="mt-3 text-sm text-muted">載入區域洞察中...</p>}</Card>{result && <div className="mt-6 space-y-5"><div className="grid gap-4 md:grid-cols-4"><Metric label="平均單價" value={`${result.avg_price_per_ping} 萬 / 坪`} /><Metric label="交易量" value={result.transaction_volume} /><Metric label="生活機能" value={result.livability_score} /><Metric label="ESG Lite" value={result.esg_lite_score} /></div><Card><h3 className="font-bold">六期行情趨勢</h3><div className="mt-4 flex h-36 items-end gap-3">{result.trend.map((value,index) => <div key={index} className="flex flex-1 flex-col items-center gap-2"><span className="text-xs font-bold">{value}</span><div className="w-full rounded-t bg-blue-500" style={{height:`${value}%`}} /><span className="text-xs text-muted">第 {index+1} 期</span></div>)}</div></Card><Card><h3 className="font-bold">POI 生活機能分數</h3><div className="mt-4 grid gap-3 md:grid-cols-5">{Object.entries(result.poi_breakdown).map(([key,value]) => <div key={key} className="rounded-xl bg-slate-50 p-4"><p className="text-xs text-muted">{key}</p><p className="mt-2 text-xl font-bold">{value}</p></div>)}</div></Card><Card><h3 className="font-bold">ESG / SDG 11 Lite</h3><p className="mt-2 text-sm text-muted">{result.sdg11_note}</p><p className="mt-4 text-xs font-bold text-amber-700">{result.disclaimer}</p></Card></div>}</>;
}

function AegisCredit() {
  const [result,setResult]=useState<{risk_score:number;signal_color:string;traces:string[]}>();
  const [loading,setLoading]=useState(false); const [error,setError]=useState("");
  async function run(){setLoading(true);setError("");try{setResult(await api.aegis({monthly_income:90000,monthly_debt:15000,cash:3500000,property_count:0,mortgage_count:0,property_price:22000000}));}catch(e){setError((e as Error).message);}finally{setLoading(false);}}
  return <><Title title="Aegis-Credit Lite" subtitle="房貸風險展示型 heuristic，不代表銀行核貸。" />{error&&<Notice tone="error">{error}</Notice>}<Card className="mt-4"><p className="text-sm text-muted">第一階段使用預設買方情境，快速展示 heuristic 結果。</p><div className="mt-4"><Button disabled={loading} onClick={run}>{loading?"分析中...":"執行示範分析"}</Button></div></Card>{result&&<div className="mt-5 grid gap-4 md:grid-cols-2"><Metric label="風險分數" value={result.risk_score}/><Metric label="燈號" value={<Badge value={result.signal_color}/>} /></div>}</>;
}

function LexProp() {
  const [result,setResult]=useState<{risk_score:number;match_count:number;summary:string}>();
  const [loading,setLoading]=useState(false); const [error,setError]=useState("");
  async function run(){setLoading(true);setError("");try{setResult(await api.lexprop({city:"台北市",district:"信義區",road_masked:"松仁路***號",community:"信義首席"}));}catch(e){setError((e as Error).message);}finally{setLoading(false);}}
  return <><Title title="LexProp Lite" subtitle="公開判決摘要模糊比對，不輸出完整門牌與個資。" />{error&&<Notice tone="error">{error}</Notice>}<Card className="mt-4"><p className="text-sm text-muted">第一階段使用匿名化預設案例，不代表正式法律判斷。</p><div className="mt-4"><Button disabled={loading} onClick={run}>{loading?"查詢中...":"查詢匿名化風險"}</Button></div></Card>{result&&<div className="mt-5 grid gap-4 md:grid-cols-2"><Metric label="比對筆數" value={result.match_count}/><Metric label="風險分數" value={result.risk_score}/><Card className="md:col-span-2"><p className="text-sm text-muted">{result.summary}</p></Card></div>}</>;
}

function History() {
  const [rows,setRows]=useState<Record<string,string|number>[]>([]); const [loading,setLoading]=useState(true); const [error,setError]=useState("");
  useEffect(()=>{api.history().then(setRows).catch((e)=>setError(e.message)).finally(()=>setLoading(false));},[]);
  return <><Title title="歷史案件" subtitle="SQLite 保存的 TaxOracle 分析結果。" />{error&&<Notice tone="error">{error}</Notice>}<Card className="mt-4">{loading?<p className="text-sm text-muted">載入歷史案件中...</p>:<div className="overflow-x-auto"><table className="w-full min-w-[720px] text-left text-sm"><thead className="border-b bg-slate-50 text-xs uppercase text-slate-500"><tr><th className="px-3 py-3">案件</th><th className="px-3">客戶</th><th className="px-3">資格</th><th className="px-3">分數</th><th className="px-3">燈號</th><th className="px-3">建立時間</th></tr></thead><tbody>{rows.map((row)=><tr key={row.id} className="border-b border-slate-100"><td className="px-3 py-3 font-bold">{row.case_id}</td><td className="px-3">{row.client_name}</td><td className="px-3"><Badge value={String(row.eligibility_status)}/></td><td className="px-3">{row.risk_score}</td><td className="px-3"><Badge value={String(row.signal_color)}/></td><td className="px-3 text-muted">{row.created_at}</td></tr>)}</tbody></table></div>}</Card></>;
}
