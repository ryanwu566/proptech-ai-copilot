"use client";

import { useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { LoadingState, SectionCard } from "@/components/product-ui";
import { api, type MarketSegmentComparablesResult, type MarketSegmentFilters, type MarketSegmentResult } from "@/lib/api";
import type { ExperienceLocale } from "@/lib/experience-i18n";


type Copy = {
  segmentTitle: string; segmentDescription: string; comparableTitle: string; comparableDescription: string;
  buildingType: string; area: string; age: string; floor: string; period: string; all: string; knownOnly: string;
  low: string; middle: string; high: string; analyze: string; analyzing: string; custom: string; min: string; max: string;
  highValue: string; threshold: string; proxyNote: string; ageNote: string; floorNote: string; intervalNote: string;
  sample: string; median: string; range: string; average: string; averageTotal: string; evidencePeriod: string;
  source: string; updated: string; excluded: string; unknownAge: string; unknownFloor: string; filters: string;
  initial: string; noData: string; unavailable: string; lowSample: string; partial: string; available: string;
  rawCategories: string; transactionPeriod: string; location: string; type: string; areaPing: string; floorLabel: string;
  approximateAge: string; totalPrice: string; unitPrice: string; deltas: string; unknown: string; monthsAgo: string;
  noComparables: string; comparableUnavailable: string; boundary: string; countUnit: string; pingUnit: string;
  wan: string; wanPerPing: string; years: string; yearsApprox: string; retryGuidance: string;
};

const COPY: Record<ExperienceLocale, Copy> = {
  "zh-TW": {
    segmentTitle: "市場區隔分析", segmentDescription: "用目前官方 PLVR 歷史成交，查看特定建物與面積條件的價格分布。", comparableTitle: "可比成交", comparableDescription: "依明確條件與實際差異排序，不使用 AI 或不透明相似度分數。",
    buildingType: "建物型態", area: "建物移轉面積", age: "近似屋齡", floor: "樓層位置", period: "成交期間", all: "不限", knownOnly: "全部已知屋齡", low: "低樓層", middle: "中樓層", high: "高樓層", analyze: "分析此市場區隔", analyzing: "分析中…", custom: "自訂範圍", min: "最小坪數", max: "最大坪數",
    highValue: "高總價住宅成交", threshold: "總價門檻（萬元）", proxyNote: "這是產品定義的高總價住宅代理條件，不是政府認定或官方分類。", ageNote: "屋齡是匯入時依年份推算的近似欄位；0 或以下視為未知，絕不當作新屋。", floorNote: "只分類有效已知樓層：樓層／總樓層 ≤ 0.33 為低、> 0.33 且 < 0.67 為中、≥ 0.67 為高。", intervalNote: "面積採下限包含、上限不包含，例如 30–40 坪代表 [30, 40)。",
    sample: "符合成交筆數", median: "每坪單價中位數", range: "第 25–75 百分位", average: "平均每坪單價", averageTotal: "平均總價", evidencePeriod: "實際成交期別", source: "資料來源", updated: "來源更新", excluded: "未符合篩選", unknownAge: "未知屋齡", unknownFloor: "未知樓層", filters: "本次條件",
    initial: "設定條件後開始分析；未選的條件不會被假設。", noData: "目前條件沒有可用的官方歷史成交。請放寬條件後再查。", unavailable: "市場區隔資料目前無法使用；舊結果已清除。", lowSample: "樣本有限，價格分布波動可能較大。", partial: "部分欄位涵蓋不完整；以下只呈現可證明的成交證據。", available: "此區隔有可用的官方歷史成交證據。",
    rawCategories: "來源建物型態對照", transactionPeriod: "成交期別", location: "路段", type: "建物型態", areaPing: "坪數", floorLabel: "樓層", approximateAge: "近似屋齡", totalPrice: "總價", unitPrice: "每坪單價", deltas: "與條件差異", unknown: "未知", monthsAgo: "個月前", noComparables: "目前條件沒有足夠的實際可比成交。", comparableUnavailable: "可比成交目前無法使用；未保留先前結果。", boundary: "歷史成交僅供市場決策參考，不是估價、核貸、購買建議或成交保證。", countUnit: "筆", pingUnit: "坪", wan: "萬元", wanPerPing: "萬元／坪", years: "年", yearsApprox: "年（近似）", retryGuidance: "請調整條件或稍後再試。",
  },
  en: {
    segmentTitle: "Segment analysis", segmentDescription: "Use current official PLVR history to inspect price distributions for a specific building and area segment.", comparableTitle: "Comparable transactions", comparableDescription: "Ordered by explicit filters and actual deltas—never an AI or opaque similarity score.",
    buildingType: "Building type", area: "Transferred building area", age: "Approximate building age", floor: "Floor position", period: "Transaction window", all: "Any", knownOnly: "All known ages", low: "Low", middle: "Middle", high: "High", analyze: "Analyze this segment", analyzing: "Analyzing…", custom: "Custom range", min: "Minimum ping", max: "Maximum ping",
    highValue: "High-value residential transactions", threshold: "Total-price threshold (NT$10k)", proxyNote: "This is a product-defined high-value residential proxy, not an official government classification.", ageNote: "Age is an approximate imported field calculated by year. Values at or below zero are unknown, never evidence of a new building.", floorNote: "Only valid known floors are classified: floor/total floors ≤ 0.33 low, > 0.33 and < 0.67 middle, and ≥ 0.67 high.", intervalNote: "Area uses an inclusive lower and exclusive upper bound; 30–40 ping means [30, 40).",
    sample: "Matching transactions", median: "Median unit price", range: "25th–75th percentile", average: "Average unit price", averageTotal: "Average total price", evidencePeriod: "Observed transaction period", source: "Source", updated: "Source updated", excluded: "Excluded by filters", unknownAge: "Unknown age", unknownFloor: "Unknown floor", filters: "Active filters",
    initial: "Set the filters to begin. Unselected attributes are not assumed.", noData: "No usable official historical transactions match these filters. Broaden them and try again.", unavailable: "Segment data is unavailable; the previous result has been cleared.", lowSample: "The sample is limited, so the distribution may vary substantially.", partial: "Some field coverage is incomplete; only provable evidence is shown below.", available: "Official historical transaction evidence is available for this segment.",
    rawCategories: "Source building-type mapping", transactionPeriod: "Period", location: "Road", type: "Building type", areaPing: "Area", floorLabel: "Floor", approximateAge: "Approx. age", totalPrice: "Total price", unitPrice: "Unit price", deltas: "Filter deltas", unknown: "Unknown", monthsAgo: "months ago", noComparables: "There are not enough actual comparable transactions for these filters.", comparableUnavailable: "Comparables are unavailable; no prior result is retained.", boundary: "Historical transactions support market decisions only; they are not an appraisal, lending decision, purchase recommendation, or guarantee.", countUnit: "records", pingUnit: "ping", wan: "NT$10k", wanPerPing: "NT$10k/ping", years: "years", yearsApprox: "years (approx.)", retryGuidance: "Adjust the filters or try again later.",
  },
  ja: {
    segmentTitle: "市場セグメント分析", segmentDescription: "現在の公式 PLVR 成約履歴から、建物タイプと面積条件別の価格分布を確認します。", comparableTitle: "比較可能な成約", comparableDescription: "明示した条件と実測差分で並べ、AI や不透明な類似度スコアは使いません。",
    buildingType: "建物タイプ", area: "建物移転面積", age: "概算築年数", floor: "階位置", period: "成約期間", all: "指定なし", knownOnly: "築年数が既知の全件", low: "低層", middle: "中層", high: "高層", analyze: "このセグメントを分析", analyzing: "分析中…", custom: "範囲を指定", min: "最小坪数", max: "最大坪数",
    highValue: "高価格帯住宅成約", threshold: "総額しきい値（万元）", proxyNote: "製品独自の高価格帯住宅プロキシであり、政府・公式の分類ではありません。", ageNote: "築年数は取込年から算出した概算値です。0 以下は不明であり、新築とは扱いません。", floorNote: "有効で既知の階のみ分類します。階／総階数が ≤0.33 は低層、>0.33 かつ <0.67 は中層、≥0.67 は高層です。", intervalNote: "面積は下限を含み上限を含みません。30–40 坪は [30, 40) です。",
    sample: "一致成約件数", median: "坪単価中央値", range: "25–75 パーセンタイル", average: "平均坪単価", averageTotal: "平均総額", evidencePeriod: "実成約期間", source: "出典", updated: "出典更新日", excluded: "条件外", unknownAge: "築年数不明", unknownFloor: "階不明", filters: "適用条件",
    initial: "条件を設定して分析を開始してください。未選択の属性は推定しません。", noData: "この条件に一致する利用可能な公式成約履歴はありません。条件を広げてください。", unavailable: "セグメントデータを利用できません。以前の結果は消去されました。", lowSample: "サンプルが少ないため、価格分布の変動が大きい可能性があります。", partial: "一部項目の網羅性が不十分です。証明できる成約根拠だけを表示します。", available: "このセグメントには公式成約履歴の根拠があります。",
    rawCategories: "元データ建物タイプ対応", transactionPeriod: "成約期", location: "道路", type: "建物タイプ", areaPing: "坪数", floorLabel: "階", approximateAge: "概算築年数", totalPrice: "総額", unitPrice: "坪単価", deltas: "条件との差", unknown: "不明", monthsAgo: "か月前", noComparables: "この条件では実際の比較可能成約が不足しています。", comparableUnavailable: "比較可能成約を利用できません。以前の結果は保持していません。", boundary: "成約履歴は市場判断の参考情報であり、鑑定・融資判断・購入推奨・成約保証ではありません。", countUnit: "件", pingUnit: "坪", wan: "万元", wanPerPing: "万元／坪", years: "年", yearsApprox: "年（概算）", retryGuidance: "条件を調整するか、後でもう一度お試しください。",
  },
  ko: {
    segmentTitle: "시장 세그먼트 분석", segmentDescription: "현재 공식 PLVR 거래 이력으로 건물 유형과 면적 조건별 가격 분포를 확인합니다.", comparableTitle: "비교 거래", comparableDescription: "명시적 조건과 실제 차이로 정렬하며 AI 또는 불투명한 유사도 점수를 사용하지 않습니다.",
    buildingType: "건물 유형", area: "건물 이전 면적", age: "근사 건물 연령", floor: "층 위치", period: "거래 기간", all: "제한 없음", knownOnly: "연령이 알려진 전체", low: "저층", middle: "중층", high: "고층", analyze: "이 세그먼트 분석", analyzing: "분석 중…", custom: "범위 직접 설정", min: "최소 평", max: "최대 평",
    highValue: "고가 주거 거래", threshold: "총액 기준(만 NTD)", proxyNote: "제품이 정의한 고가 주거 프록시이며 정부 또는 공식 분류가 아닙니다.", ageNote: "건물 연령은 가져온 연도를 기준으로 계산한 근사 필드입니다. 0 이하는 알 수 없음이며 신축으로 간주하지 않습니다.", floorNote: "유효하고 알려진 층만 분류합니다. 층/총층수 ≤0.33은 저층, >0.33 및 <0.67은 중층, ≥0.67은 고층입니다.", intervalNote: "면적은 하한을 포함하고 상한을 제외합니다. 30–40평은 [30, 40)입니다.",
    sample: "일치 거래 수", median: "평당 단가 중앙값", range: "25–75 백분위", average: "평균 평당 단가", averageTotal: "평균 총액", evidencePeriod: "실제 거래 기간", source: "출처", updated: "출처 업데이트", excluded: "필터 제외", unknownAge: "연령 불명", unknownFloor: "층 불명", filters: "적용 필터",
    initial: "조건을 설정해 분석을 시작하세요. 선택하지 않은 속성은 추정하지 않습니다.", noData: "이 조건에 맞는 사용 가능한 공식 거래 이력이 없습니다. 조건을 완화해 보세요.", unavailable: "세그먼트 데이터를 사용할 수 없습니다. 이전 결과는 삭제되었습니다.", lowSample: "표본이 적어 가격 분포 변동이 클 수 있습니다.", partial: "일부 필드의 범위가 불완전합니다. 확인 가능한 거래 근거만 표시합니다.", available: "이 세그먼트에 공식 거래 이력 근거가 있습니다.",
    rawCategories: "원본 건물 유형 매핑", transactionPeriod: "거래 기간", location: "도로", type: "건물 유형", areaPing: "면적", floorLabel: "층", approximateAge: "근사 연령", totalPrice: "총액", unitPrice: "평당 단가", deltas: "조건 차이", unknown: "알 수 없음", monthsAgo: "개월 전", noComparables: "이 조건에는 실제 비교 거래가 충분하지 않습니다.", comparableUnavailable: "비교 거래를 사용할 수 없으며 이전 결과는 유지되지 않습니다.", boundary: "거래 이력은 시장 판단 참고용이며 감정평가, 대출 결정, 구매 권고 또는 거래 보장이 아닙니다.", countUnit: "건", pingUnit: "평", wan: "만 NTD", wanPerPing: "만 NTD/평", years: "년", yearsApprox: "년(근사)", retryGuidance: "조건을 조정하거나 나중에 다시 시도하세요.",
  },
};

const BUILDING_TYPES = ["住宅大樓", "華廈", "公寓", "透天厝", "套房", "店面", "其他/未分類"] as const;
const BUILDING_LABELS: Record<ExperienceLocale, Record<string, string>> = {
  "zh-TW": { 住宅大樓: "住宅大樓", 華廈: "華廈", 公寓: "公寓", 透天厝: "透天厝", 套房: "套房", 店面: "店面", "其他/未分類": "其他／未分類" },
  en: { 住宅大樓: "Residential tower", 華廈: "Mid-rise elevator building", 公寓: "Walk-up apartment", 透天厝: "Townhouse", 套房: "Studio", 店面: "Storefront", "其他/未分類": "Other / unclassified" },
  ja: { 住宅大樓: "高層集合住宅", 華廈: "中層エレベーター住宅", 公寓: "低層アパート", 透天厝: "戸建て", 套房: "ワンルーム", 店面: "店舗", "其他/未分類": "その他／未分類" },
  ko: { 住宅大樓: "고층 공동주택", 華廈: "중층 엘리베이터 주택", 公寓: "저층 아파트", 透天厝: "단독주택", 套房: "원룸", 店面: "점포", "其他/未分類": "기타 / 미분류" },
};

const AREA_PRESETS: Record<string, [number, number]> = {
  "under-20": [0.1, 20], "20-30": [20, 30], "30-40": [30, 40], "40-60": [40, 60], "60-plus": [60, 500],
};
const AGE_BANDS: Record<string, { min: number | null; max: number | null; known: boolean }> = {
  all: { min: null, max: null, known: false }, known: { min: null, max: null, known: true },
  "0-5": { min: 0, max: 5, known: true }, "6-10": { min: 6, max: 10, known: true },
  "11-20": { min: 11, max: 20, known: true }, "21-30": { min: 21, max: 30, known: true },
  "30-plus": { min: 30, max: 200, known: true },
};

export function MarketSegmentationPanel({ county, district }: { county: string; district: string }) {
  const { locale, formatNumber } = useExperienceLocale();
  const copy = COPY[locale];
  const [periodMonths, setPeriodMonths] = useState(36);
  const [buildingType, setBuildingType] = useState("住宅大樓");
  const [areaPreset, setAreaPreset] = useState("30-40");
  const [areaMin, setAreaMin] = useState(30);
  const [areaMax, setAreaMax] = useState(40);
  const [ageBand, setAgeBand] = useState("all");
  const [floorPosition, setFloorPosition] = useState<"" | "low" | "middle" | "high">("");
  const [highValueOnly, setHighValueOnly] = useState(false);
  const [highValueThreshold, setHighValueThreshold] = useState(3000);
  const [segment, setSegment] = useState<MarketSegmentResult>();
  const [comparables, setComparables] = useState<MarketSegmentComparablesResult>();
  const [loading, setLoading] = useState(false);
  const [segmentError, setSegmentError] = useState(false);
  const [comparableError, setComparableError] = useState(false);
  const querySequence = useRef(0);
  const requestController = useRef<AbortController | undefined>(undefined);

  function clearEvidence() {
    requestController.current?.abort("market_segment_filter_changed");
    requestController.current = undefined;
    querySequence.current += 1;
    setLoading(false);
    setSegment(undefined);
    setComparables(undefined);
    setSegmentError(false);
    setComparableError(false);
  }

  useEffect(() => {
    requestController.current?.abort("market_segment_region_changed");
    requestController.current = undefined;
    querySequence.current += 1;
    setLoading(false);
    setSegment(undefined);
    setComparables(undefined);
    setSegmentError(false);
    setComparableError(false);
  }, [county, district]);

  useEffect(() => () => requestController.current?.abort("market_segment_unmounted"), []);

  function payload(): MarketSegmentFilters {
    const age = AGE_BANDS[ageBand];
    return {
      county, district, period_months: periodMonths, building_type: buildingType,
      area_min_ping: areaMin, area_max_ping: areaMax,
      age_min_years: age.min, age_max_years: age.max, known_age_only: age.known,
      floor_position: floorPosition, high_value_only: highValueOnly,
      high_value_threshold_wan: highValueThreshold, target_area_ping: (areaMin + areaMax) / 2,
      target_age_years: age.min !== null && age.max !== null ? (age.min + age.max) / 2 : null,
    };
  }

  async function analyze(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (loading || !county || !district || areaMin <= 0 || areaMin >= areaMax) return;
    const queryId = querySequence.current + 1;
    querySequence.current = queryId;
    const controller = new AbortController();
    requestController.current = controller;
    setLoading(true);
    setSegment(undefined);
    setComparables(undefined);
    setSegmentError(false);
    setComparableError(false);
    const filters = payload();
    try {
      const nextSegment = await api.marketSegment(filters, controller.signal);
      if (querySequence.current !== queryId) return;
      setSegment(nextSegment);
      if (nextSegment.state === "unavailable") {
        setSegmentError(true);
        return;
      }
      if (nextSegment.state === "no_data") return;
      try {
        const nextComparables = await api.marketSegmentComparables({ ...filters, limit: 8 }, controller.signal);
        if (querySequence.current !== queryId) return;
        setComparables(nextComparables);
        setComparableError(nextComparables.state === "unavailable");
      } catch {
        if (querySequence.current !== queryId) return;
        setComparables(undefined);
        setComparableError(true);
      }
    } catch {
      if (querySequence.current !== queryId) return;
      setSegment(undefined);
      setComparables(undefined);
      setSegmentError(true);
      setComparableError(false);
    } finally {
      if (requestController.current === controller) requestController.current = undefined;
      if (querySequence.current === queryId) setLoading(false);
    }
  }

  function changeAreaPreset(value: string) {
    clearEvidence();
    setAreaPreset(value);
    const preset = AREA_PRESETS[value];
    if (preset) {
      setAreaMin(preset[0]);
      setAreaMax(preset[1]);
    }
  }

  const stateText = segment?.state === "available" ? copy.available : segment?.state === "low_sample" ? copy.lowSample : segment?.state === "partial" ? copy.partial : segment?.state === "no_data" ? copy.noData : copy.unavailable;
  const activeFilters = [
    BUILDING_LABELS[locale][buildingType] ?? buildingType,
    `[${formatCompact(areaMin)}, ${formatCompact(areaMax)}) ${copy.pingUnit}`,
    `${periodMonths} ${locale === "en" ? "months" : locale === "ja" ? "か月" : locale === "ko" ? "개월" : "個月"}`,
    ageBand !== "all" ? ageBand === "known" ? copy.knownOnly : `${ageBand.replace("-plus", "+")} ${copy.yearsApprox}` : "",
    floorPosition ? copy[floorPosition] : "",
    highValueOnly ? `${copy.highValue} ≥ ${formatNumber(highValueThreshold)} ${copy.wan}` : "",
  ].filter(Boolean);

  return <div className="space-y-5" data-testid="market-segmentation-engine">
    <SectionCard title={copy.segmentTitle} description={copy.segmentDescription}>
      <form onSubmit={analyze} aria-busy={loading} data-testid="market-segment-form" className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <Field label={copy.buildingType}><select data-testid="segment-building-type" value={buildingType} onChange={(event) => { clearEvidence(); setBuildingType(event.target.value); }} className={controlClass}>{BUILDING_TYPES.map((value) => <option key={value} value={value}>{BUILDING_LABELS[locale][value]}</option>)}</select></Field>
          <Field label={copy.area}><select data-testid="segment-area-preset" value={areaPreset} onChange={(event) => changeAreaPreset(event.target.value)} className={controlClass}><option value="under-20">&lt;20 {copy.pingUnit}</option><option value="20-30">20–30 {copy.pingUnit}</option><option value="30-40">30–40 {copy.pingUnit}</option><option value="40-60">40–60 {copy.pingUnit}</option><option value="60-plus">60–&lt;500 {copy.pingUnit}</option><option value="custom">{copy.custom}</option></select></Field>
          <Field label={copy.age}><select data-testid="segment-age-band" value={ageBand} onChange={(event) => { clearEvidence(); setAgeBand(event.target.value); }} className={controlClass}><option value="all">{copy.all}</option><option value="known">{copy.knownOnly}</option><option value="0-5">0–5 {copy.yearsApprox}</option><option value="6-10">6–10 {copy.yearsApprox}</option><option value="11-20">11–20 {copy.yearsApprox}</option><option value="21-30">21–30 {copy.yearsApprox}</option><option value="30-plus">30+ {copy.yearsApprox}</option></select></Field>
          <Field label={copy.floor}><select data-testid="segment-floor-position" value={floorPosition} onChange={(event) => { clearEvidence(); setFloorPosition(event.target.value as typeof floorPosition); }} className={controlClass}><option value="">{copy.all}</option><option value="low">{copy.low}</option><option value="middle">{copy.middle}</option><option value="high">{copy.high}</option></select></Field>
          <Field label={copy.period}><select data-testid="segment-period-window" value={periodMonths} onChange={(event) => { clearEvidence(); setPeriodMonths(Number(event.target.value)); }} className={controlClass}>{[12, 24, 36, 60, 120].map((months) => <option key={months} value={months}>{months} {locale === "en" ? "months" : locale === "ja" ? "か月" : locale === "ko" ? "개월" : "個月"}</option>)}</select></Field>
        </div>
        {areaPreset === "custom" && <div className="grid gap-3 sm:max-w-md sm:grid-cols-2"><Field label={copy.min}><input data-testid="segment-area-min" type="number" min="0.1" max="499.9" step="0.1" value={areaMin} onChange={(event) => { clearEvidence(); setAreaMin(Number(event.target.value)); }} className={controlClass} /></Field><Field label={copy.max}><input data-testid="segment-area-max" type="number" min="0.2" max="500" step="0.1" value={areaMax} onChange={(event) => { clearEvidence(); setAreaMax(Number(event.target.value)); }} className={controlClass} /></Field></div>}
        <div className="rounded-xl border border-stone-200 bg-stone-50 p-3">
          <label className="flex items-start gap-3 text-xs font-bold text-slate-800"><input data-testid="segment-high-value-toggle" type="checkbox" checked={highValueOnly} onChange={(event) => { clearEvidence(); setHighValueOnly(event.target.checked); }} className="mt-0.5 h-4 w-4" /><span>{copy.highValue}<span className="mt-1 block font-normal leading-5 text-slate-600">{copy.proxyNote}</span></span></label>
          {highValueOnly && <label className="mt-3 block max-w-xs text-xs font-bold text-slate-700">{copy.threshold}<input data-testid="segment-high-value-threshold" type="number" min="1" max="100000" step="100" value={highValueThreshold} onChange={(event) => { clearEvidence(); setHighValueThreshold(Number(event.target.value)); }} className={controlClass} /></label>}
        </div>
        <div data-testid="segment-active-filters" className="flex flex-wrap gap-2">{activeFilters.map((label) => <span key={label} className="rounded-full bg-cyan-50 px-2.5 py-1 text-[11px] font-bold text-cyan-900">{label}</span>)}</div>
        <p className="text-[11px] leading-5 text-slate-600">{copy.intervalNote} {copy.ageNote} {copy.floorNote}</p>
        <button type="submit" data-testid="market-segment-submit" disabled={loading || areaMin <= 0 || areaMin >= areaMax} className="inline-flex min-h-11 items-center justify-center rounded-lg bg-cyan-700 px-4 py-2.5 text-sm font-bold text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50">{loading ? copy.analyzing : copy.analyze}</button>
      </form>

      {loading && <div className="mt-4" data-testid="market-segment-loading"><LoadingState label={copy.analyzing} /></div>}
      {!loading && !segment && !segmentError && <p data-testid="market-segment-initial" className="mt-4 rounded-lg bg-stone-50 p-3 text-sm text-slate-600">{copy.initial}</p>}
      {!loading && segmentError && <p data-testid="market-segment-unavailable" role="alert" className="mt-4 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-bold text-rose-900">{copy.unavailable} {copy.retryGuidance}</p>}
      {!loading && segment && <div className="mt-5 space-y-4" data-testid={`market-segment-${segment.state}`}>
        <p data-testid="market-segment-guidance" className={`rounded-lg border p-3 text-sm font-bold leading-6 ${segment.state === "available" ? "border-emerald-200 bg-emerald-50 text-emerald-950" : segment.state === "no_data" ? "border-stone-200 bg-stone-50 text-slate-700" : "border-amber-200 bg-amber-50 text-amber-950"}`}>{stateText}</p>
        {segment.matching_transaction_count !== null && segment.state !== "no_data" && <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4" data-testid="market-segment-metrics">
            <Metric label={copy.sample} value={`${formatNumber(segment.matching_transaction_count)} ${copy.countUnit}`} />
            <Metric prominent label={copy.median} value={formatPrice(segment.median_unit_price_per_ping, copy)} />
            <Metric label={copy.range} value={segment.p25_unit_price_per_ping !== null && segment.p75_unit_price_per_ping !== null ? `${formatNumber(segment.p25_unit_price_per_ping)}–${formatNumber(segment.p75_unit_price_per_ping)} ${copy.wanPerPing}` : copy.unknown} />
            <Metric label={copy.average} value={formatPrice(segment.average_unit_price_per_ping, copy)} />
          </div>
          <dl className="grid gap-2 rounded-xl border border-stone-200 bg-stone-50 p-3 text-xs text-slate-700 sm:grid-cols-2 xl:grid-cols-4">
            <Evidence label={copy.averageTotal} value={segment.average_total_price_wan === null ? copy.unknown : `${formatNumber(segment.average_total_price_wan)} ${copy.wan}`} />
            <Evidence label={copy.evidencePeriod} value={segment.period_min && segment.period_max ? `${segment.period_min} – ${segment.period_max}` : copy.unknown} />
            <Evidence label={copy.source} value={segment.source} />
            <Evidence label={copy.updated} value={segment.source_updated_at ?? copy.unknown} />
            <Evidence label={copy.excluded} value={segment.excluded_transaction_count === null ? copy.unknown : `${formatNumber(segment.excluded_transaction_count)} ${copy.countUnit}`} />
            <Evidence label={copy.unknownAge} value={segment.unknown_age_count === null ? copy.unknown : `${formatNumber(segment.unknown_age_count)} ${copy.countUnit}`} />
            <Evidence label={copy.unknownFloor} value={segment.unknown_floor_count === null ? copy.unknown : `${formatNumber(segment.unknown_floor_count)} ${copy.countUnit}`} />
          </dl>
          {segment.building_type_distribution.length > 0 && <details className="rounded-xl border border-stone-200 p-3"><summary className="cursor-pointer text-xs font-bold text-slate-800">{copy.rawCategories}</summary><ul className="mt-2 space-y-1 text-xs text-slate-600">{segment.building_type_distribution.map((item) => <li key={item.category}>{BUILDING_LABELS[locale][item.category] ?? item.category}: {formatNumber(item.count)} {copy.countUnit} · {item.raw_values.join("、")}</li>)}</ul></details>}
        </>}
        <p className="text-[11px] leading-5 text-slate-600">{copy.boundary}</p>
      </div>}
    </SectionCard>

    <SectionCard title={copy.comparableTitle} description={copy.comparableDescription} collapsible={false} className="min-w-0">
      {loading && <p data-testid="market-comparables-loading" className="text-sm text-slate-600">{copy.analyzing}</p>}
      {!loading && comparableError && <p data-testid="market-comparables-unavailable" role="alert" className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm font-bold text-rose-900">{copy.comparableUnavailable}</p>}
      {!loading && segment?.state === "no_data" && <p data-testid="market-comparables-no-data" className="rounded-lg bg-stone-50 p-3 text-sm text-slate-600">{copy.noComparables}</p>}
      {!loading && segment && segment.state !== "no_data" && !comparables && !comparableError && <p data-testid="market-comparables-initial" className="text-sm text-slate-600">{copy.initial}</p>}
      {!loading && comparables && comparables.comparables.length === 0 && !comparableError && <p data-testid="market-comparables-no-data" className="rounded-lg bg-stone-50 p-3 text-sm text-slate-600">{copy.noComparables}</p>}
      {!loading && comparables && comparables.comparables.length > 0 && <div data-testid={`market-comparables-${comparables.state}`} className="w-full min-w-0 max-w-full touch-pan-x overflow-x-auto">
        <table className="w-full min-w-[980px] text-left text-xs" aria-label={copy.comparableTitle}><thead><tr className="bg-stone-50 text-slate-600"><th className="p-2">{copy.transactionPeriod}</th><th>{copy.location}</th><th>{copy.type}</th><th>{copy.areaPing}</th><th>{copy.floorLabel}</th><th>{copy.approximateAge}</th><th>{copy.totalPrice}</th><th>{copy.unitPrice}</th><th>{copy.deltas}</th></tr></thead><tbody>{comparables.comparables.map((row) => <tr key={`${row.transaction_period}-${row.road}-${row.area_ping}-${row.total_price_wan}`} className="border-t border-stone-100 text-slate-700"><td className="p-2 font-bold">{row.transaction_period}</td><td>{row.location_display || copy.unknown}</td><td>{BUILDING_LABELS[locale][row.building_type] ?? row.building_type}</td><td>{row.area_ping === null ? copy.unknown : `${formatNumber(row.area_ping)} ${copy.pingUnit}`}</td><td>{row.floor === null || row.total_floor === null ? copy.unknown : `${row.floor}/${row.total_floor} · ${row.floor_position ? copy[row.floor_position] : copy.unknown}`}</td><td>{row.approximate_building_age_years === null ? copy.unknown : `${formatNumber(row.approximate_building_age_years)} ${copy.yearsApprox}`}</td><td>{row.total_price_wan === null ? copy.unknown : `${formatNumber(row.total_price_wan)} ${copy.wan}`}</td><td>{formatPrice(row.unit_price_per_ping, copy)}</td><td>{row.area_difference_ping === null ? copy.unknown : `Δ ${formatNumber(row.area_difference_ping)} ${copy.pingUnit}`}{row.age_difference_years !== null ? ` · Δ ${formatNumber(row.age_difference_years)} ${copy.years}` : ""}{row.period_recency_months !== null ? ` · ${row.period_recency_months} ${copy.monthsAgo}` : ""}</td></tr>)}</tbody></table>
      </div>}
      <p className="mt-3 text-[11px] leading-5 text-slate-600">{copy.boundary}</p>
    </SectionCard>
  </div>;
}

const controlClass = "mt-1 w-full rounded-lg border border-stone-300 bg-white px-3 py-2.5 text-sm text-slate-900 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500";

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block text-xs font-bold text-slate-700">{label}{children}</label>;
}

function Metric({ label, value, prominent = false }: { label: string; value: string; prominent?: boolean }) {
  return <div className={`rounded-xl border p-3 ${prominent ? "border-cyan-300 bg-cyan-50" : "border-stone-200 bg-white"}`}><p className="text-[11px] font-bold text-slate-500">{label}</p><p className={`${prominent ? "text-2xl" : "text-lg"} mt-1 font-black text-slate-950`}>{value}</p></div>;
}

function Evidence({ label, value }: { label: string; value: string }) {
  return <div><dt className="font-bold text-slate-500">{label}</dt><dd className="mt-0.5 break-words font-semibold text-slate-800">{value}</dd></div>;
}

function formatPrice(value: number | null, copy: Copy): string {
  return value === null ? copy.unknown : `${new Intl.NumberFormat().format(value)} ${copy.wanPerPing}`;
}

function formatCompact(value: number): string {
  return Number.isInteger(value) ? String(value) : String(Number(value.toFixed(1)));
}
