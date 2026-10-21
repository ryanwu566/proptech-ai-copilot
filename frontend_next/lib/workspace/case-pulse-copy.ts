import type { ExperienceLocale } from "../experience-i18n";

const en = {
  title: "Case Pulse", location: "Location", market: "Market", risk: "Risk", money: "Money", decision: "Decision", nearby: "Nearby evidence",
  unconfirmed: "Location unconfirmed", located: "Address linked", reconfirm: "Reconfirm location", nearbySaved: "Nearby evidence saved", nearbyLimited: "Partial nearby evidence",
  notQueried: "Not queried", available: "Evidence saved", limited: "Saved · limited evidence", stale: "Saved · outdated", insufficient: "Insufficient evidence", unavailable: "Unavailable",
  unknown: "Risk unknown", riskReview: "{matched} matched · {verification} to verify · {unknown} unknown", noMatch: "No matches in saved evidence", moneySaved: "Assumptions saved",
  outstanding: "{outstanding} outstanding", noActions: "No recorded actions", noOpenActions: "No open actions", evidenceActivity: "Latest evidence: {section}", roomActivity: "Latest update: {section}",
};
export type PulseMessage = Exclude<keyof typeof en, "title" | "location" | "market" | "risk" | "money" | "decision" | "nearby" | "evidenceActivity" | "roomActivity">;
export const casePulseCopy: Record<ExperienceLocale, Record<keyof typeof en, string>> = {
  en,
  "zh-TW": {
    title: "案件動態", location: "位置", market: "市場", risk: "風險", money: "資金", decision: "決策室", nearby: "周邊證據",
    unconfirmed: "尚未確認位置", located: "地址座標已關聯", reconfirm: "需重新確認位置", nearbySaved: "已有周邊證據", nearbyLimited: "周邊證據有限",
    notQueried: "尚未查詢", available: "已有保存證據", limited: "已保存・證據有限", stale: "已保存・資料過期", insufficient: "證據不足", unavailable: "目前無法取得",
    unknown: "風險仍無法判定", riskReview: "{matched} 項符合・{verification} 項待查・{unknown} 項未知", noMatch: "保存證據未命中", moneySaved: "已保存試算假設",
    outstanding: "{outstanding} 項待處理", noActions: "尚未記錄事項", noOpenActions: "目前無待辦事項", evidenceActivity: "最近證據：{section}", roomActivity: "最近更新：{section}",
  },
  ja: {
    title: "案件の動き", location: "所在地", market: "市場", risk: "リスク", money: "資金", decision: "意思決定", nearby: "周辺の根拠",
    unconfirmed: "所在地未確認", located: "住所と座標を関連付け", reconfirm: "所在地の再確認が必要", nearbySaved: "周辺の根拠を保存済み", nearbyLimited: "周辺の根拠は一部のみ",
    notQueried: "未照会", available: "根拠を保存済み", limited: "保存済み・根拠に制約", stale: "保存済み・情報が古い", insufficient: "根拠不足", unavailable: "取得できません",
    unknown: "リスクは未判定", riskReview: "{matched} 件該当・{verification} 件要確認・{unknown} 件不明", noMatch: "保存した根拠に該当なし", moneySaved: "試算の前提を保存済み",
    outstanding: "{outstanding} 件未対応", noActions: "記録した項目なし", noOpenActions: "未対応の項目なし", evidenceActivity: "最新の根拠：{section}", roomActivity: "最近の更新：{section}",
  },
  ko: {
    title: "매물 현황", location: "위치", market: "시장", risk: "위험", money: "자금", decision: "의사결정", nearby: "주변 근거",
    unconfirmed: "위치 미확인", located: "주소와 좌표 연결됨", reconfirm: "위치 재확인 필요", nearbySaved: "주변 근거 저장됨", nearbyLimited: "주변 근거 일부만 있음",
    notQueried: "조회 전", available: "근거 저장됨", limited: "저장됨 · 근거 제한", stale: "저장됨 · 오래된 자료", insufficient: "근거 부족", unavailable: "이용 불가",
    unknown: "위험 판단 불가", riskReview: "{matched}건 일치 · {verification}건 확인 필요 · {unknown}건 미상", noMatch: "저장된 근거에 일치 없음", moneySaved: "계산 가정 저장됨",
    outstanding: "{outstanding}건 미처리", noActions: "기록된 항목 없음", noOpenActions: "미처리 항목 없음", evidenceActivity: "최근 근거: {section}", roomActivity: "최근 변경: {section}",
  },
};
