"use client";

import { useEffect, useState } from "react";
import { CaseComparisonPanel } from "@/components/case-comparison-panel";
import { clearCurrentCase, clearSavedCases, deleteSavedCase, loadSavedCase, readSavedCases, saveCase, type SaveCaseInput, type SavedCase } from "@/lib/case-storage";

type Props = {
  current?: SaveCaseInput;
  listOnly?: boolean;
  onSaved?: (saved: SavedCase) => void;
  onLoaded?: (saved: SavedCase) => void;
  onCleared?: () => void;
  onExport?: (saved: SavedCase) => void;
};

export function CaseManager({ current, listOnly = false, onSaved, onLoaded, onCleared, onExport }: Props) {
  const [cases, setCases] = useState<SavedCase[]>([]);
  const [feedback, setFeedback] = useState("");
  const [confirmDelete, setConfirmDelete] = useState("");
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [open, setOpen] = useState(listOnly);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);
  useEffect(() => setCases(readSavedCases()), []);

  function refresh(message: string) { setCases(readSavedCases()); setFeedback(message); }
  function save() { if (current) { const saved = saveCase(current); refresh("案件已保存，可稍後繼續分析"); onSaved?.(saved); } }
  function load(saved: SavedCase) { loadSavedCase(saved); setFeedback("已載入案件，可繼續分析"); onLoaded?.(saved); }
  function remove(id: string) {
    if (confirmDelete !== id) return setConfirmDelete(id);
    deleteSavedCase(id); setSelectedIds((rows) => rows.filter((row) => row !== id)); setConfirmDelete(""); refresh("案件已刪除");
  }
  function clearAll() {
    if (!confirmClearAll) return setConfirmClearAll(true);
    clearSavedCases(); setSelectedIds([]); setCompareOpen(false); setConfirmClearAll(false); refresh("最近案件已清空");
  }
  function clearCurrent() { clearCurrentCase(); setFeedback("目前案件已清除"); onCleared?.(); }
  function toggleCompare(id: string) {
    setFeedback("");
    setSelectedIds((rows) => rows.includes(id) ? rows.filter((row) => row !== id) : rows.length >= 4 ? (setFeedback("最多只能選擇四個案件"), rows) : [...rows, id]);
  }

  return <section className="min-w-0 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm" aria-label="案件保存與最近分析紀錄">
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div><p className="text-[10px] font-bold tracking-wider text-cyan-700">LOCAL CASES</p><h2 className="mt-1 font-bold text-slate-950">案件保存 / 最近分析紀錄</h2><p className="mt-1 text-xs text-slate-500">只保存在此瀏覽器，不會寫入資料庫。</p></div>
      {!listOnly && <div className="grid grid-cols-2 gap-2 sm:flex"><button type="button" disabled={!current} title={current ? "保存目前分析案件" : "完成任一步後即可保存"} onClick={save} className="rounded-lg bg-cyan-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-40">保存案件</button><button type="button" onClick={() => setOpen((value) => !value)} className="rounded-lg border border-stone-200 px-3 py-2 text-xs font-bold text-slate-700">最近案件</button><button type="button" onClick={clearCurrent} className="col-span-2 rounded-lg border border-stone-200 px-3 py-2 text-xs font-bold text-slate-500 sm:col-auto">清除目前案件</button></div>}
    </div>
    {feedback && <p className="mt-3 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs text-cyan-900" role="status">{feedback}</p>}
    {(open || listOnly) && <div className="mt-4 border-t border-stone-100 pt-4">
      {cases.length === 0 ? <p className="rounded-xl bg-stone-50 p-4 text-xs text-slate-500">尚未保存案件，請先完成任一步並保存至少一筆案件。</p> : <>
        <div className="mb-3 flex flex-col gap-2 rounded-xl bg-stone-50 p-3 sm:flex-row sm:items-center sm:justify-between"><p className="text-xs text-slate-600">勾選 2–4 個案件後進行候選排序，目前已選 {selectedIds.length} 個。少於兩筆時請至少保存並選擇兩筆案件。</p><button type="button" disabled={selectedIds.length < 2} title={selectedIds.length < 2 ? "請至少選擇兩個案件" : "開啟案件比較"} onClick={() => setCompareOpen((value) => !value)} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800 disabled:cursor-not-allowed disabled:opacity-45">比較案件</button></div>
        <div className="grid gap-3 lg:grid-cols-2">{cases.map((saved) => <CaseCard key={saved.id} saved={saved} selected={selectedIds.includes(saved.id)} confirmDelete={confirmDelete === saved.id} onToggle={() => toggleCompare(saved.id)} onLoad={() => load(saved)} onExport={onExport} onDelete={() => remove(saved.id)} />)}</div>
        {compareOpen && <CaseComparisonPanel savedCases={cases} selectedIds={selectedIds} />}
      </>}
      <button type="button" disabled={cases.length === 0} onClick={clearAll} className="mt-4 text-xs font-bold text-rose-700 disabled:opacity-40">{confirmClearAll ? "再次點擊確認清空全部案件" : "清空全部案件"}</button>
    </div>}
  </section>;
}

function CaseCard({ saved, selected, confirmDelete, onToggle, onLoad, onExport, onDelete }: { saved: SavedCase; selected: boolean; confirmDelete: boolean; onToggle: () => void; onLoad: () => void; onExport?: (saved: SavedCase) => void; onDelete: () => void }) {
  return <article className="min-w-0 rounded-xl border border-stone-200 p-3"><div className="flex items-start justify-between gap-2"><label className="flex min-w-0 cursor-pointer items-start gap-2"><input type="checkbox" checked={selected} onChange={onToggle} className="mt-1 shrink-0" aria-label={`選擇比較 ${saved.title}`} /><span className="min-w-0"><span className="block truncate text-sm font-bold text-slate-900">{saved.title}</span><span className="mt-1 block text-[10px] text-slate-400">{new Date(saved.updatedAt).toLocaleString("zh-TW")} · {saved.progress}%</span></span></label><span className="shrink-0 rounded-full bg-cyan-50 px-2 py-1 text-[9px] font-bold text-cyan-800">{saved.activeWizardStep}</span></div><p className="mt-2 text-[11px] text-slate-600">{saved.inputSummary.propertyPrice ? `${saved.inputSummary.propertyPrice.toLocaleString()} 萬` : "尚未估價"}{saved.inputSummary.areaPing ? ` · ${saved.inputSummary.areaPing} 坪` : ""}</p><div className="mt-3 grid grid-cols-2 gap-2 sm:flex"><button type="button" onClick={onLoad} className="rounded-lg bg-cyan-700 px-3 py-2 text-xs font-bold text-white">載入</button>{onExport && <button type="button" disabled={!saved.data.valuation} title={saved.data.valuation ? "匯出此案件報告" : "請先完成估價"} onClick={() => onExport(saved)} className="rounded-lg border border-stone-200 px-3 py-2 text-xs font-bold text-slate-700 disabled:opacity-40">匯出 HTML 報告</button>}<button type="button" onClick={onDelete} className="rounded-lg border border-rose-200 px-3 py-2 text-xs font-bold text-rose-700">{confirmDelete ? "再次點擊確認刪除" : "刪除"}</button></div></article>;
}
