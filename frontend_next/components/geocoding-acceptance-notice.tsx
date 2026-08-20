"use client";

import type { GeocodingAcceptance } from "@/lib/api";
import { useExperienceLocale } from "@/components/experience-locale-provider";

export function GeocodingAcceptanceNotice({ acceptance, onConfirm }: { acceptance: GeocodingAcceptance; onConfirm?: () => void }) {
  const { locale } = useExperienceLocale();
  if (acceptance.accepted_for_analysis) return null;
  const copy = acceptanceCopy(locale);
  const coordinates = acceptance.resolved_lat !== null && acceptance.resolved_lng !== null
    ? `${acceptance.resolved_lat.toFixed(6)}, ${acceptance.resolved_lng.toFixed(6)}`
    : copy.unavailable;
  return <section data-testid="geocoding-acceptance-gate" className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-amber-950">
    <h3 className="text-sm font-black">{copy.title}</h3>
    <p className="mt-1 text-xs leading-5">{copy.message}</p>
    <dl className="mt-3 grid min-w-0 gap-2 text-[11px] sm:grid-cols-2">
      <Evidence label={copy.original} value={acceptance.original_query || copy.unavailable} />
      <Evidence label={copy.resolved} value={acceptance.normalized_address || copy.unavailable} />
      <Evidence label={copy.quality} value={acceptance.match_quality} />
      <Evidence label={copy.source} value={acceptance.geocoding_source || copy.unavailable} />
      <Evidence label={copy.coordinates} value={coordinates} />
      <Evidence label={copy.reasons} value={acceptance.mismatch_reasons.map((reason) => copy.reason[reason as keyof typeof copy.reason] ?? reason).join(" · ") || copy.unavailable} />
    </dl>
    <p className="mt-3 text-xs font-bold leading-5">{acceptance.message}</p>
    {onConfirm && acceptance.requires_confirmation && <button type="button" data-testid="confirm-geocoding-match" onClick={onConfirm} className="mt-3 rounded-lg bg-amber-900 px-3 py-2 text-xs font-bold text-white focus:outline-none focus:ring-2 focus:ring-amber-600 focus:ring-offset-2">{copy.confirm}</button>}
  </section>;
}

function Evidence({ label, value }: { label: string; value: string }) {
  return <div className="min-w-0 rounded-lg border border-amber-200 bg-white/70 p-2"><dt className="font-bold text-amber-800">{label}</dt><dd className="mt-1 break-words text-slate-800">{value}</dd></div>;
}

function acceptanceCopy(locale: "zh-TW" | "en" | "ja" | "ko") {
  const rows = {
    "zh-TW": {
      title: "定位結果需要確認",
      message: "此結果尚未被視為目前物件位置；確認或修正前，不會查詢周邊設施或地勢證據。",
      original: "原始輸入", resolved: "定位地址", quality: "符合程度", source: "定位來源", coordinates: "定位座標", reasons: "需確認原因", unavailable: "無資料", confirm: "我已確認使用此定位",
      reason: { house_number_mismatch: "門牌號碼不一致", house_number_missing: "定位缺少門牌", street_mismatch: "路街不一致", street_missing: "定位缺少路街", city_mismatch: "縣市不一致", district_mismatch: "行政區不一致", district_missing: "定位缺少行政區", city_only_resolution: "只定位到縣市", lower_specificity_than_input: "定位精度低於輸入", approximate_provider_location: "服務僅提供近似位置", named_place_not_preserved: "地標名稱未保留", low_text_similarity: "輸入與結果相似度低", provider_partial_match: "服務標示為部分符合" },
    },
    en: {
      title: "Location match needs confirmation",
      message: "This result is not yet treated as the property location. Nearby and terrain evidence stay blocked until it is confirmed or corrected.",
      original: "Original query", resolved: "Resolved address", quality: "Match quality", source: "Geocoding source", coordinates: "Resolved coordinates", reasons: "Reasons to review", unavailable: "Unavailable", confirm: "Confirm this resolved location",
      reason: { house_number_mismatch: "House number differs", house_number_missing: "House number is missing", street_mismatch: "Street differs", street_missing: "Street is missing", city_mismatch: "City differs", district_mismatch: "District differs", district_missing: "District is missing", city_only_resolution: "Resolved only to city level", lower_specificity_than_input: "Result is less specific than the query", approximate_provider_location: "Provider returned an approximate location", named_place_not_preserved: "Landmark name was not preserved", low_text_similarity: "Query and result differ materially", provider_partial_match: "Provider marked a partial match" },
    },
    ja: {
      title: "位置情報の確認が必要です",
      message: "この結果はまだ物件位置として確定されていません。確認または修正するまで周辺施設・地形情報を取得しません。",
      original: "入力内容", resolved: "解決された住所", quality: "一致品質", source: "位置情報源", coordinates: "解決座標", reasons: "確認理由", unavailable: "データなし", confirm: "この位置を確認して使用",
      reason: { house_number_mismatch: "番地が一致しません", house_number_missing: "番地がありません", street_mismatch: "道路名が一致しません", street_missing: "道路名がありません", city_mismatch: "市県が一致しません", district_mismatch: "行政区が一致しません", district_missing: "行政区がありません", city_only_resolution: "市県レベルのみの位置です", lower_specificity_than_input: "入力より精度が低い結果です", approximate_provider_location: "概略位置です", named_place_not_preserved: "地名が保持されていません", low_text_similarity: "入力と結果が大きく異なります", provider_partial_match: "一部一致の結果です" },
    },
    ko: {
      title: "위치 결과 확인이 필요합니다",
      message: "이 결과는 아직 해당 물건의 위치로 확정되지 않았습니다. 확인하거나 수정하기 전에는 주변 시설과 지형 근거를 조회하지 않습니다.",
      original: "원래 입력", resolved: "확인된 주소", quality: "일치 품질", source: "위치 출처", coordinates: "확인된 좌표", reasons: "확인 사유", unavailable: "자료 없음", confirm: "이 위치를 확인하여 사용",
      reason: { house_number_mismatch: "번지가 일치하지 않음", house_number_missing: "번지가 없음", street_mismatch: "도로명이 일치하지 않음", street_missing: "도로명이 없음", city_mismatch: "도시가 일치하지 않음", district_mismatch: "행정구역이 일치하지 않음", district_missing: "행정구역이 없음", city_only_resolution: "도시 수준으로만 확인됨", lower_specificity_than_input: "입력보다 구체성이 낮음", approximate_provider_location: "근사 위치만 제공됨", named_place_not_preserved: "장소명이 유지되지 않음", low_text_similarity: "입력과 결과가 크게 다름", provider_partial_match: "부분 일치 결과임" },
    },
  } as const;
  return rows[locale];
}
