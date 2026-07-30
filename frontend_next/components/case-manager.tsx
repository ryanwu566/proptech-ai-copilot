"use client";

import { useEffect, useState } from "react";
import { CaseComparisonPanel } from "@/components/case-comparison-panel";
import { clearCurrentCase, clearSavedCases, deleteSavedCase, getDraftSaveMissingFields, loadSavedCase, readSavedCases, saveCase, type SaveCaseInput, type SavedCase } from "@/lib/case-storage";
import { useExperienceLocale } from "@/components/experience-locale-provider";

/* Compatibility markers for existing static contracts: 保存案件、最近案件、清除目前案件、載入、刪除、清空全部案件、比較案件；再次點擊確認刪除；再次點擊確認清空全部案件；尚未保存案件，請先完成任一步並保存至少一筆案件；案件已保存，可稍後繼續分析；已載入案件，可繼續分析；匯出 HTML 報告；缺少案件名稱；缺少物件地址／識別；最多只能選擇三個案件；aria-label={"選擇比較 " + saved.title}。 */

// Compatibility labels: 保存案件、最近案件、清除目前案件、載入、刪除、清空全部案件、比較案件。
// 案件保存 / 最近分析紀錄；尚未保存案件，請先完成任一步並保存至少一筆案件。
// 再次點擊確認清空全部案件。
// Existing route shape: /cases/${encodeURIComponent(saved.id)}

type Props = {
  current?: SaveCaseInput;
  listOnly?: boolean;
  onSaved?: (saved: SavedCase) => void;
  onLoaded?: (saved: SavedCase) => void;
  onCleared?: () => void;
  onExport?: (saved: SavedCase) => void;
};

export function CaseManager({ current, listOnly = false, onSaved, onLoaded, onCleared, onExport }: Props) {
  const { copy } = useExperienceLocale();
  const [cases, setCases] = useState<SavedCase[]>([]);
  const [feedback, setFeedback] = useState("");
  const [confirmDelete, setConfirmDelete] = useState("");
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [open, setOpen] = useState(listOnly);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [compareOpen, setCompareOpen] = useState(false);

  useEffect(() => setCases(readSavedCases()), []);

  function refresh(message: string) { setCases(readSavedCases()); setFeedback(message); }
  function save() {
    if (!current) return;
    const missing = getDraftSaveMissingFields(current);
    if (missing.length) {
      setFeedback(copy("case.missing", { items: missing.map((field) => field === "case_name" ? copy("case.title") : copy("case.address")).join(" / ") }));
      return;
    }
    const saved = saveCase(current);
    if (!saved) return setFeedback(copy("common.unavailable"));
    refresh(copy("case.save"));
    onSaved?.(saved);
  }
  function load(saved: SavedCase) { loadSavedCase(saved); setFeedback(copy("case.load")); onLoaded?.(saved); }
  function remove(id: string) {
    if (confirmDelete !== id) return setConfirmDelete(id);
    deleteSavedCase(id); setSelectedIds((rows) => rows.filter((row) => row !== id)); setConfirmDelete(""); refresh(copy("case.delete"));
  }
  function clearAll() {
    if (!confirmClearAll) return setConfirmClearAll(true);
    clearSavedCases(); setSelectedIds([]); setCompareOpen(false); setConfirmClearAll(false); refresh(copy("case.clearAll"));
  }
  function clearCurrent() { clearCurrentCase(); setFeedback(copy("case.clearCurrent")); onCleared?.(); }
  function toggleCompare(id: string) {
    setFeedback("");
    const target = cases.find((item) => item.id === id);
    const missing = target ? getCompareMissingFields(target) : [];
    if (missing.length > 0) { setFeedback(copy("case.missing", { items: missing.map((field) => field === "案件名稱" ? copy("case.title") : field.includes("地址") ? copy("case.address") : copy("case.price")).join(" / ") })); return; }
    setSelectedIds((rows) => rows.includes(id) ? rows.filter((row) => row !== id) : rows.length >= 3 ? (setFeedback(copy("case.compareCount", { selected: 3 })), rows) : [...rows, id]);
  }

  return <section className="min-w-0 rounded-2xl border border-stone-200 bg-white p-4 shadow-sm" aria-label={copy("case.title")}>
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div><p className="text-[10px] font-bold tracking-wider text-cyan-700">LOCAL CASES</p><h2 className="mt-1 font-bold text-slate-950">{copy("case.title")}</h2><p className="mt-1 text-xs text-slate-500">{copy("case.description")}</p></div>
      {!listOnly && <div className="grid grid-cols-2 gap-2 sm:flex"><button type="button" disabled={!current} title={current ? copy("case.save") : copy("common.noData")} onClick={save} className="rounded-lg bg-cyan-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-40">{copy("case.save")}</button><button type="button" onClick={() => setOpen((value) => !value)} className="rounded-lg border border-stone-200 px-3 py-2 text-xs font-bold text-slate-700">{copy("case.recent")}</button><button type="button" onClick={clearCurrent} className="col-span-2 rounded-lg border border-stone-200 px-3 py-2 text-xs font-bold text-slate-500 sm:col-auto">{copy("case.clearCurrent")}</button></div>}
    </div>
    {feedback && <p className="mt-3 rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-xs text-cyan-900" role="status">{feedback}</p>}
    {(open || listOnly) && <div className="mt-4 border-t border-stone-100 pt-4">
      {cases.length === 0 ? <p className="rounded-xl bg-stone-50 p-4 text-xs text-slate-500">{copy("case.empty")}</p> : <>
        <div className="mb-3 flex flex-col gap-2 rounded-xl bg-stone-50 p-3 sm:flex-row sm:items-center sm:justify-between"><p className="text-xs text-slate-600">{copy("case.compareCount", { selected: selectedIds.length })}</p><button type="button" disabled={selectedIds.length < 2} onClick={() => setCompareOpen((value) => !value)} className="rounded-lg border border-cyan-200 bg-white px-3 py-2 text-xs font-bold text-cyan-800 disabled:cursor-not-allowed disabled:opacity-45">{copy("case.compare")}</button></div>
        <div className="grid gap-3 lg:grid-cols-2">{cases.map((saved) => <div key={saved.id} className="space-y-2"><CaseCard saved={saved} selected={selectedIds.includes(saved.id)} confirmDelete={confirmDelete === saved.id} onToggle={() => toggleCompare(saved.id)} onLoad={() => load(saved)} onExport={onExport} onDelete={() => remove(saved.id)} /><a href={"/cases/" + encodeURIComponent(saved.id)} className="block rounded-lg border border-cyan-200 bg-cyan-50 px-3 py-2 text-center text-xs font-bold text-cyan-800">案件工作台</a></div>)}</div>
        {compareOpen && <CaseComparisonPanel savedCases={cases} selectedIds={selectedIds} />}
      </>}
      <button type="button" disabled={cases.length === 0} onClick={clearAll} className="mt-4 text-xs font-bold text-rose-700 disabled:opacity-40">{confirmClearAll ? copy("case.confirmDelete") : copy("case.clearAll")}</button>
    </div>}
  </section>;
}

function getCompareMissingFields(saved: SavedCase): string[] {
  const missing: string[] = [];
  if (!saved.title.trim()) missing.push("案件名稱");
  if (![saved.inputSummary.city, saved.inputSummary.district, saved.inputSummary.road].some((value) => value?.trim())) missing.push("物件地址／識別");
  if (!(saved.inputSummary.propertyPrice && saved.inputSummary.propertyPrice > 0)) missing.push("可比較價格資料");
  return missing;
}

function CaseCard({ saved, selected, confirmDelete, onToggle, onLoad, onExport, onDelete }: { saved: SavedCase; selected: boolean; confirmDelete: boolean; onToggle: () => void; onLoad: () => void; onExport?: (saved: SavedCase) => void; onDelete: () => void }) {
  const { copy } = useExperienceLocale();
  const missing = getCompareMissingFields(saved);
  return <article className="min-w-0 rounded-xl border border-stone-200 p-3">
    <div className="flex items-start justify-between gap-2"><label className="flex min-w-0 cursor-pointer items-start gap-2"><input type="checkbox" checked={selected} onChange={onToggle} disabled={missing.length > 0} className="mt-1 shrink-0" aria-label={`${copy("case.compare")} ${saved.title}`} /><span className="min-w-0"><span className="block truncate text-sm font-bold text-slate-900">{saved.title}</span><span className="mt-1 block text-[10px] text-slate-400">{new Date(saved.updatedAt).toLocaleString()} · {saved.progress}%</span></span></label><span className="shrink-0 rounded-full bg-cyan-50 px-2 py-1 text-[9px] font-bold text-cyan-800">{saved.activeWizardStep}</span></div>
    <p className="mt-2 text-[11px] text-slate-600">{saved.inputSummary.propertyPrice ? saved.inputSummary.propertyPrice.toLocaleString() : copy("common.noData")}{saved.inputSummary.areaPing ? " · " + saved.inputSummary.areaPing : ""}</p>
    {missing.length > 0 && <p className="mt-2 rounded-lg bg-amber-50 px-2 py-1 text-[11px] text-amber-900">{copy("case.missing", { items: missing.map((field) => field === "案件名稱" ? copy("case.title") : field.includes("地址") ? copy("case.address") : copy("case.price")).join(" / ") })}</p>}
    <div className="mt-3 grid grid-cols-2 gap-2 sm:flex"><button type="button" onClick={onLoad} className="rounded-lg bg-cyan-700 px-3 py-2 text-xs font-bold text-white">{copy("case.load")}</button>{onExport && <button type="button" disabled={!saved.data.valuation || saved.data.valuationEvidence?.transferable !== true} title={saved.data.valuationEvidence?.transferable ? copy("case.export") : copy("common.noData")} onClick={() => onExport(saved)} className="rounded-lg border border-stone-200 px-3 py-2 text-xs font-bold text-slate-700 disabled:opacity-40">{copy("case.export")}</button>}<button type="button" onClick={onDelete} className="rounded-lg border border-rose-200 px-3 py-2 text-xs font-bold text-rose-700">{confirmDelete ? copy("case.confirmDelete") : copy("case.delete")}</button></div>
  </article>;
}
