import { expandCopyGroups } from "@/lib/runtime-copy-groups";
import type { ExperienceLocale } from "@/lib/experience-i18n";

type ExperienceOverride = Partial<Record<string, string>>;

const ja: ExperienceOverride = expandCopyGroups({
  "app": { "tagline": "物件判断を支えるアシスタント" },
  "journey": { "eyebrow": "GUIDED PROPERTY DECISION JOURNEY", "title": "内見判断を5つの手順で整理", "description": "どの手順にも移動できます。データ状態、ソース、制限を確認しながら進めます。", "current": "現在の手順", "step": "手順", "tools": "利用できるツール", "expertSummary": "専門ツールと直接入力", "progressTitle": "進行状況", "statusCurrent": "現在", "statusVisited": "確認済み", "statusNotVisited": "未確認", "mobileSummary": "手順を選択", "finish": "このフローを終了", "property.title": "物件情報を整理", "property.question": "どの物件を確認しますか？", "property.description": "位置、価格、資金、判断の情報を確認する前に物件情報を入力します。", "property.next": "位置と生活機能を確認", "location.title": "位置と根拠", "location.question": "位置と利用できる根拠は何を示しますか？", "location.description": "位置、通勤、地形の情報は参考根拠です。データ不足は未知または利用不可のまま扱います。", "location.next": "価格の根拠を確認", "price.title": "価格と査定の根拠", "price.question": "利用できる根拠は価格について何を示しますか？", "price.description": "査定、比較、推移を確認します。デモや不完全なデータは公式査定の根拠ではありません。", "price.next": "資金と保有コストを確認", "affordability.title": "資金と保有コスト", "affordability.question": "利用できる資金と保有情報は何ですか？", "affordability.description": "ローン、保有コスト、税務は独立した参考情報であり、承認や正式な助言ではありません。", "affordability.next": "内見判断の要約を確認", "decision.title": "内見判断の要約", "decision.question": "次に何を確認しますか？", "decision.description": "購入や安全の結論を作らず、利用できる根拠と不足項目を整理します。", "decision.next": "このフローを終了" },
  "trust": { "fundingBoundary": "ローン、保有コスト、税務の結果は参考情報であり、承認や正式な助言ではありません。", "referenceOnly": "地形・災害データは内見時のリスク参考情報です。データ不足や利用不可はリスクがないことを意味しません。", "noPurchase": "このツールは根拠と確認事項を整理するもので、購入を推奨しません。" },
});

const ko: ExperienceOverride = expandCopyGroups({
  "app": { "tagline": "매물 판단을 돕는 어시스턴트" },
  "journey": { "eyebrow": "GUIDED PROPERTY DECISION JOURNEY", "title": "내방 판단을 다섯 단계로 정리", "description": "어떤 단계로든 이동할 수 있습니다. 데이터 상태, 출처와 제한을 확인하면서 진행합니다.", "current": "현재 단계", "step": "단계", "tools": "사용 가능한 도구", "expertSummary": "전문 도구와 직접 입력", "progressTitle": "진행 상황", "statusCurrent": "현재", "statusVisited": "확인함", "statusNotVisited": "확인하지 않음", "mobileSummary": "단계 선택", "finish": "흐름 종료", "property.title": "매물 정보 정리", "property.question": "어떤 매물을 확인하나요?", "property.description": "위치, 가격, 자금과 판단 정보를 확인하기 전에 매물 정보를 입력합니다.", "property.next": "위치와 생활 편의 확인", "location.title": "위치와 근거", "location.question": "위치와 이용 가능한 근거는 무엇을 보여주나요?", "location.description": "위치, 통근과 지형 정보는 참고 근거입니다. 데이터 부족은 미확인 또는 이용 불가로 유지합니다.", "location.next": "가격 근거 확인", "price.title": "가격과 평가 근거", "price.question": "이용 가능한 근거는 가격에 대해 무엇을 보여주나요?", "price.description": "평가, 비교와 추이를 확인합니다. 데모나 불완전한 데이터는 공식 평가 근거가 아닙니다.", "price.next": "자금과 보유 비용 확인", "affordability.title": "자금과 보유 비용", "affordability.question": "이용 가능한 자금과 보유 정보는 무엇인가요?", "affordability.description": "대출, 보유 비용과 세무는 독립적인 참고 정보이며 승인이나 공식 자문이 아닙니다.", "affordability.next": "내방 판단 요약 확인", "decision.title": "내방 판단 요약", "decision.question": "다음에 무엇을 확인해야 하나요?", "decision.description": "구매 또는 안전 결론을 만들지 않고 이용 가능한 근거와 누락 항목을 정리합니다.", "decision.next": "흐름 종료" },
  "trust": { "fundingBoundary": "대출, 보유 비용과 세무 결과는 참고 정보이며 승인이나 공식 자문이 아닙니다.", "referenceOnly": "지형·재해 데이터는 내방 위험 참고 정보입니다. 데이터 부족이나 이용 불가는 위험이 없다는 뜻이 아닙니다.", "noPurchase": "이 도구는 근거와 확인 사항을 정리하며 구매를 권고하지 않습니다." },
});

const jaProduction: ExperienceOverride = expandCopyGroups({
  "app": { "openMenu": "メニューを開く", "closeMenu": "メニューを閉じる", "tour": "プロダクトツアー", "currentView": "現在の画面", "language": "言語" },
  "nav": { "core": "基本機能", "tools": "ツール", "analysis": "分析", "system": "システム", "status": "システム状態", "ready": "利用可能" },
  "page": { "dashboard": "ダッシュボード", "tax": "TaxOracle 税務確認", "market": "市場インサイト", "map": "地図インサイト", "valuation": "価格査定", "credit": "Aegis-Credit ローン計算", "terrain": "地形・災害リスク", "history": "保存案件" },
  "journey": { "openTool": "ツールを開く" },
});

const koProduction: ExperienceOverride = expandCopyGroups({
  "app": { "openMenu": "메뉴 열기", "closeMenu": "메뉴 닫기", "tour": "제품 둘러보기", "currentView": "현재 화면", "language": "언어" },
  "nav": { "core": "기본 기능", "tools": "도구", "analysis": "분석", "system": "시스템", "status": "시스템 상태", "ready": "사용 가능" },
  "page": { "dashboard": "대시보드", "tax": "TaxOracle 세무 확인", "market": "시장 인사이트", "map": "지도 인사이트", "valuation": "가격 추정", "credit": "Aegis-Credit 대출 계산", "terrain": "지형·재해 위험", "history": "저장한 사례" },
  "journey": { "openTool": "도구 열기" },
});

const overrides: Partial<Record<ExperienceLocale, ExperienceOverride>> = {
  ja: { ...ja, ...jaProduction },
  ko: { ...ko, ...koProduction },
};

export function getExperienceOverride(locale: ExperienceLocale, key: string) {
  return overrides[locale]?.[key];
}
