"use client";

import { useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { journeyPriceBasisLabel, type JourneyPriceBasis } from "@/lib/closed-loop-journey";

export function PriceBasisSelector({ basis, askingPriceWan, valuationPriceWan, activePriceWan, manualPriceWan, onChange }: { basis: JourneyPriceBasis; askingPriceWan?: number; valuationPriceWan?: number; activePriceWan?: number; manualPriceWan?: number; onChange: (basis: JourneyPriceBasis, manualPriceWan?: number) => void }) {
  const { locale, formatNumber } = useExperienceLocale();
  const [draftManual, setDraftManual] = useState<number | "">(manualPriceWan ?? "");
  const heading = locale === "en" ? "Active affordability price basis" : locale === "ja" ? "資金計画に使う価格基準" : locale === "ko" ? "자금 계산에 사용할 가격 기준" : "資金試算使用的價格基準";
  const explanation = locale === "en" ? "Changing the basis clears dependent affordability results; it never changes location evidence." : locale === "ja" ? "基準を変更すると依存する資金結果をクリアします。位置の根拠は変更しません。" : locale === "ko" ? "기준을 바꾸면 종속된 자금 결과가 초기화되며 위치 근거는 바뀌지 않습니다." : "切換基準會清除相依的資金結果，但不會改變位置證據。";
  const unavailable = locale === "en" ? "Not available" : locale === "ja" ? "利用不可" : locale === "ko" ? "이용 불가" : "目前不可用";
  const apply = locale === "en" ? "Use manual price" : locale === "ja" ? "手動価格を使用" : locale === "ko" ? "수동 가격 사용" : "使用手動價格";
  return <section data-testid="journey-price-basis" aria-labelledby="journey-price-basis-heading" className="min-w-0 rounded-xl border border-violet-200 bg-violet-50/50 p-4">
    <h3 id="journey-price-basis-heading" className="text-sm font-black text-slate-950">{heading}</h3>
    <p className="mt-1 text-xs leading-5 text-slate-600">{explanation}</p>
    <div className="mt-3 grid min-w-0 gap-2 sm:grid-cols-3">
      <BasisButton label={journeyPriceBasisLabel("asking", locale)} value={askingPriceWan} selected={basis === "asking"} disabled={!askingPriceWan} unavailable={unavailable} onClick={() => onChange("asking")} />
      <BasisButton label={journeyPriceBasisLabel("valuation", locale)} value={valuationPriceWan} selected={basis === "valuation"} disabled={!valuationPriceWan} unavailable={unavailable} onClick={() => onChange("valuation")} />
      <button type="button" aria-pressed={basis === "manual"} onClick={() => onChange("manual", typeof draftManual === "number" ? draftManual : undefined)} className={`min-w-0 rounded-lg border p-3 text-left text-xs ${basis === "manual" ? "border-violet-600 bg-white ring-2 ring-violet-200" : "border-stone-200 bg-white"}`}><span className="block font-black text-slate-900">{journeyPriceBasisLabel("manual", locale)}</span><span className="mt-1 block break-words text-slate-600">{manualPriceWan ? formatNumber(manualPriceWan) : unavailable}</span></button>
    </div>
    <div className="mt-3 flex min-w-0 flex-col gap-2 sm:flex-row">
      <input data-testid="journey-manual-price" aria-label={journeyPriceBasisLabel("manual", locale)} type="number" min="0.01" value={draftManual} onChange={(event) => setDraftManual(event.target.value === "" ? "" : Number(event.target.value))} className="min-w-0 flex-1 rounded-lg border border-stone-300 bg-white px-3 py-2 text-sm" />
      <button type="button" disabled={draftManual === "" || draftManual <= 0} onClick={() => onChange("manual", typeof draftManual === "number" ? draftManual : undefined)} className="rounded-lg bg-violet-700 px-3 py-2 text-xs font-bold text-white disabled:opacity-40">{apply}</button>
    </div>
    <p data-testid="journey-active-price" className="mt-3 break-words text-sm font-black text-violet-950">{journeyPriceBasisLabel(basis, locale)}: {activePriceWan ? formatNumber(activePriceWan) : unavailable}</p>
  </section>;
}

function BasisButton({ label, value, selected, disabled, unavailable, onClick }: { label: string; value?: number; selected: boolean; disabled: boolean; unavailable: string; onClick: () => void }) {
  const { formatNumber } = useExperienceLocale();
  return <button type="button" aria-pressed={selected} disabled={disabled} onClick={onClick} className={`min-w-0 rounded-lg border p-3 text-left text-xs disabled:cursor-not-allowed disabled:opacity-45 ${selected ? "border-violet-600 bg-white ring-2 ring-violet-200" : "border-stone-200 bg-white"}`}><span className="block font-black text-slate-900">{label}</span><span className="mt-1 block break-words text-slate-600">{value ? formatNumber(value) : unavailable}</span></button>;
}
