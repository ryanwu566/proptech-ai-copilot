import type { ExperienceLocale } from "./experience-i18n";
import type { JourneyPropertyIdentityAnchorV1 } from "./journey-property-identity";

const copy = {
  "zh-TW": { title: "地址與座標關聯", kicker: "瀏覽器案件關聯", address: "地址", location: "行政區", village: "村里", confidence: "地址關聯信心", parcel: "地號證據", building: "建物證據", sources: "來源", aligned: "地址與座標已關聯", stale: "需要重新確認", unavailable: "尚無可用證據", manual: "使用者手動確認；非官方驗證", candidate: "候選資料，尚未驗證", other: "目前無可驗證證據", boundary: "僅用於瀏覽器流程的地址與位置關聯；不代表官方地號、建物、所有權或法律身分確認。", conflict: "目前資料與已接受的物件資料不一致；請重新執行位置分析並確認地址。", high: "高", medium: "中", low: "低", unknown: "未知", scope: "僅限地址與位置證據", savedSource: "已保存來源", selection: "使用者選擇", villageSource: "國土測繪村里界", provided: "已提供定位點" },
  en: { title: "Address and coordinate association", kicker: "Browser case association", address: "Address", location: "Administrative area", village: "Village", confidence: "Address confidence", parcel: "Parcel evidence", building: "Building evidence", sources: "Sources", aligned: "Address and coordinates associated", stale: "Needs revalidation", unavailable: "No usable evidence", manual: "User-confirmed; not officially verified", candidate: "Candidate; unverified", other: "No verifiable evidence currently", boundary: "Address and location association for this browser workflow only; it does not confirm official parcel, building, ownership or legal identity.", conflict: "Current evidence conflicts with the accepted property context; rerun Location analysis and confirm the address.", high: "High", medium: "Medium", low: "Low", unknown: "Unknown", scope: "Address and location evidence only", savedSource: "Saved source", selection: "User selection", villageSource: "NLSC village boundary", provided: "Provided map point" },
  ja: { title: "住所と座標の関連付け", kicker: "ブラウザー内の物件関連付け", address: "住所", location: "行政区", village: "村里", confidence: "住所の確度", parcel: "土地番号の根拠", building: "建物の根拠", sources: "出典", aligned: "住所と座標を関連付け済み", stale: "再確認が必要", unavailable: "利用可能な根拠なし", manual: "利用者による確認・公的検証なし", candidate: "候補・未検証", other: "検証可能な根拠なし", boundary: "このブラウザー内で住所と位置を関連付けるための情報です。公的な土地番号、建物、所有権、法的身分の確認を意味しません。", conflict: "現在の情報が既存の物件情報と一致しません。位置分析を再実行し、住所を確認してください。", high: "高", medium: "中", low: "低", unknown: "不明", scope: "住所と位置の根拠のみ", savedSource: "保存済み出典", selection: "利用者の選択", villageSource: "NLSC 村里境界", provided: "提供された位置" },
  ko: { title: "주소와 좌표 연결", kicker: "브라우저 사례 연결", address: "주소", location: "행정 구역", village: "마을", confidence: "주소 신뢰도", parcel: "필지 근거", building: "건물 근거", sources: "출처", aligned: "주소와 좌표가 연결됨", stale: "재확인 필요", unavailable: "사용 가능한 근거 없음", manual: "사용자 확인・공식 검증 없음", candidate: "후보・미검증", other: "검증 가능한 근거 없음", boundary: "이 브라우저에서 주소와 위치를 연결하는 정보입니다. 공식 필지, 건물, 소유권 또는 법적 신원을 확인하지 않습니다.", conflict: "현재 정보가 기존 부동산 정보와 일치하지 않습니다. 위치 분석을 다시 실행하고 주소를 확인하세요.", high: "높음", medium: "중간", low: "낮음", unknown: "알 수 없음", scope: "주소 및 위치 근거만 해당", savedSource: "저장된 출처", selection: "사용자 선택", villageSource: "NLSC 마을 경계", provided: "제공된 위치" },
};
export function journeyIdentityCopy(locale: ExperienceLocale) { return copy[locale]; }
export function journeyIdentityEvidenceLabel(status: string | undefined, locale: ExperienceLocale) {
  const c = copy[locale];
  return status === "manual_confirmed" ? c.manual : status === "candidate" ? c.candidate : status === "unavailable" || !status ? c.unavailable : c.other;
}
export function isJourneyAddressAssociated(anchor: JourneyPropertyIdentityAnchorV1): boolean {
  return Boolean(anchor.coordinates && anchor.revalidation.status === "current");
}
export function journeyIdentitySourceLabel(sourceId: string, locale: ExperienceLocale): string {
  const c = copy[locale];
  const labels: Record<string, string> = { property_selection: c.selection, google_geocoding: "Google geocoding", tgos_geocoding: "TGOS geocoding", provided_coordinates: c.provided, nlsc_village_boundary: c.villageSource };
  return labels[sourceId] ?? c.savedSource;
}
