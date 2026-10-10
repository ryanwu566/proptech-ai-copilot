import { expandCopyGroups } from "@/lib/runtime-copy-groups";
import type { ExperienceLocale } from "@/lib/experience-i18n";

type RuntimeCopyOverride = Partial<Record<string, string>>;

const ja = expandCopyGroups({
  "map": { "baseStandard": "標準地図", "baseLight": "ライト地図", "baseSatellite": "衛星画像", "advanced": "詳細な場所設定", "partialNotice": "一部の周辺カテゴリは一時利用できません。利用可能な結果は保持しています。", "progressTitle": "地図分析の進行状況", "progressAccepted": "住所を受け付けました", "progressDispatched": "位置リクエストを送信しました", "progressWaiting": "地図と周辺データの応答待ち", "progressReceived": "地図の応答を受信しました", "progressRendering": "地図と結果を表示中", "progressComplete": "地図結果を表示しました" },
  "location": { "title": "位置情報インサイト", "description": "1つの物件住所から、位置、地形・災害リスク、通勤、生活機能を順に確認します。", "address": "物件住所", "radius": "分析半径（m）", "propertyPrice": "物件価格（万TWD、任意）", "area": "面積（坪、任意）", "start": "位置分析を開始", "analyzing": "分析中…", "empty": "物件住所を入力して位置分析を開始してください。", "changeNotice": "住所を変更すると、以前の位置・地形・通勤結果は無効になります。再度分析してください。", "noResult": "利用できる位置結果がありません。", "error": "位置データを一時的に取得できません。後でもう一度お試しください。", "map": "地図で見る", "results": "位置分析結果", "score": "位置スコア", "strengths": "位置の強み", "weaknesses": "位置の制限", "poiDetails": "周辺POIの詳細を見る", "buyerFit": "利用場面の参考", "dataQuality": "データ品質と制限を見る", "transit": "交通", "convenience": "生活利便性", "education": "教育", "green": "緑地", "medical": "医療", "risk": "リスクデータ" },
  "finder": { "search": "内見候補を検索", "searching": "検索中…", "demo": "デモ条件を読み込む", "sourceNote": "既存の公式PLVR履歴のみを使用します。現在売り出し中の物件を示すものではありません。", "empty": "物件検索はまだ開始されていません", "emptyDetail": "検索前に予算と場所を入力するか、デモ条件を読み込んでください。", "budgetRequired": "検索するには予算上限を入力してください。", "error": "物件検索データを一時的に取得できません。", "noData": "条件に一致する公式取引データがありません。", "results": "物件検索結果", "districts": "候補の区・郡", "roads": "候補の道路", "transactions": "取引サンプルを見る", "useValuation": "この道路を査定する", "useLoan": "この価格で返済額を計算", "useHolding": "月間コストを見積もる", "useLocation": "周辺の生活機能を見る", "tableSwipe": "表を左右にスワイプできます" },
  "commute": { "title": "通勤と生活機能", "description": "最寄りのMRT駅と公式スナップショット時刻だけを確認します。リスクや内見判断は変更しません。", "empty": "物件住所を入力してください。", "noData": "データ不足", "station": "最寄りのMRT駅", "lines": "路線", "distance": "歩行前の直線距離（m）", "updated": "ソース／更新日時", "source": "TDX", "idle": "まだ検索していません", "error": "通勤データを読み込めませんでした。" },
  "loan": { "title": "Aegis-Credit ローン試算", "description": "透明な計算式で頭金、月々の返済額、利息合計、金利感度を試算します。入力だけで送信されることはありません。", "propertyPrice": "物件価格（万TWD）", "downPayment": "頭金比率", "rate": "年利（%）", "years": "返済期間（年）", "grace": "据置期間（年）", "income": "月収（万TWD、任意）", "calculate": "返済額を計算", "calculating": "計算中…", "invalid": "有効な価格と返済期間を入力してください。", "empty": "試算はまだ開始されていません", "emptyDetail": "価格、金利、返済期間を入力して返済額を計算してください。", "error": "ローン試算を一時的に利用できません。" },
  "tax": { "title": "TaxOracle 税務スクリーニング", "description": "再投資税制の適用可能性、5年間の確認事項、説明用レポートを整理します。", "help": "例または条件を入力して、既存のTaxOracle APIでルールを確認します。", "select": "案件を選択または入力", "example": "例示案件", "custom": "カスタム案件", "start": "税務チェックを開始", "running": "ルールを確認中…", "reset": "リセット", "error": "税務データを一時的に利用できません。", "empty": "結果はまだありません", "emptyDetail": "案件を選択して税務チェックを開始してください。" },
  "case": { "title": "保存案件", "description": "物件の入力、分析結果、次の確認事項をローカルに整理します。", "save": "案件を保存", "recent": "保存案件を見る", "clearCurrent": "現在の案件を解除", "clearAll": "保存案件をすべて削除", "empty": "保存案件はありません。", "compare": "比較", "compareCount": "{{selected}}件を選択中", "load": "読み込む", "delete": "削除", "confirmDelete": "削除を確認", "export": "HTMLを出力", "missing": "不足：{{items}}", "address": "物件住所", "price": "価格データ" },
});

const ko = expandCopyGroups({
  "map": { "baseStandard": "기본 지도", "baseLight": "밝은 지도", "baseSatellite": "위성 이미지", "advanced": "고급 위치 설정", "partialNotice": "일부 주변 카테고리를 일시적으로 사용할 수 없습니다. 사용 가능한 결과는 유지됩니다.", "progressTitle": "지도 분석 진행", "progressAccepted": "주소를 받았습니다", "progressDispatched": "위치 요청을 보냈습니다", "progressWaiting": "지도와 주변 데이터 응답 대기 중", "progressReceived": "지도 응답을 받았습니다", "progressRendering": "지도와 결과 표시 중", "progressComplete": "지도 결과가 표시되었습니다" },
  "location": { "title": "위치 인사이트", "description": "하나의 매물 주소로 위치, 지형·재해 위험, 통근, 생활 편의를 순서대로 확인합니다.", "address": "매물 주소", "radius": "분석 반경(m)", "propertyPrice": "매물 가격(만 TWD, 선택)", "area": "면적(평, 선택)", "start": "위치 분석 시작", "analyzing": "분석 중…", "empty": "매물 주소를 입력하고 위치 분석을 시작하세요.", "changeNotice": "주소를 바꾸면 이전 위치·지형·통근 결과가 무효화됩니다. 다시 분석하세요.", "noResult": "사용 가능한 위치 결과가 없습니다.", "error": "위치 데이터를 일시적으로 가져올 수 없습니다.", "map": "지도에서 보기", "results": "위치 분석 결과", "score": "위치 점수", "strengths": "위치 장점", "weaknesses": "위치 제한", "poiDetails": "주변 POI 상세 보기", "buyerFit": "활용 상황 참고", "dataQuality": "데이터 품질과 제한 보기", "transit": "교통", "convenience": "생활 편의", "education": "교육", "green": "녹지", "medical": "의료", "risk": "위험 데이터" },
  "finder": { "search": "매물 방향 검색", "searching": "검색 중…", "demo": "데모 조건 불러오기", "sourceNote": "기존 공식 PLVR 이력만 사용하며 현재 매물 여부를 의미하지 않습니다.", "empty": "매물 검색을 시작하지 않았습니다", "emptyDetail": "예산과 위치를 입력하거나 데모 조건을 불러온 뒤 검색하세요.", "budgetRequired": "검색하려면 최대 예산을 입력하세요.", "error": "매물 검색 데이터를 일시적으로 가져올 수 없습니다.", "noData": "조건에 맞는 공식 거래 데이터가 없습니다.", "results": "매물 검색 결과", "districts": "추천 구·군", "roads": "추천 도로", "transactions": "거래 샘플 보기", "useValuation": "이 도로 평가하기", "useLoan": "이 가격으로 상환액 계산", "useHolding": "월 비용 추정", "useLocation": "주변 생활 편의 보기", "tableSwipe": "표를 좌우로 스와이프하세요" },
  "commute": { "title": "통근과 생활 편의", "description": "가까운 MRT 역과 공식 스냅샷 시간만 확인하며 위험이나 매물 판단을 바꾸지 않습니다.", "empty": "매물 주소를 입력하세요.", "noData": "데이터 부족", "station": "가까운 MRT 역", "lines": "노선", "distance": "도보 전 직선거리(m)", "updated": "출처／업데이트 시간", "source": "TDX", "idle": "아직 조회하지 않음", "error": "통근 데이터를 불러오지 못했습니다." },
  "loan": { "title": "Aegis-Credit 대출 계산", "description": "투명한 공식으로 계약금, 월 상환액, 총이자와 금리 민감도를 계산합니다. 입력만으로 전송되지 않습니다.", "propertyPrice": "매물 가격(만 TWD)", "downPayment": "계약금 비율", "rate": "연 이자율(%)", "years": "대출 기간(년)", "grace": "거치 기간(년)", "income": "월소득(만 TWD, 선택)", "calculate": "상환액 계산", "calculating": "계산 중…", "invalid": "유효한 가격과 대출 기간을 입력하세요.", "empty": "계산을 시작하지 않았습니다", "emptyDetail": "가격, 금리, 기간을 입력하고 상환액을 계산하세요.", "error": "대출 계산을 일시적으로 사용할 수 없습니다." },
  "tax": { "title": "TaxOracle 세무 확인", "description": "재투자 세금 자격, 5년 확인 알림과 안내 보고서를 정리합니다.", "help": "예시 또는 조건을 입력한 뒤 기존 TaxOracle API로 규칙을 확인합니다.", "select": "사례 선택 또는 입력", "example": "예시 사례", "custom": "사용자 사례", "start": "세무 확인 시작", "running": "규칙 확인 중…", "reset": "초기화", "error": "세무 데이터를 일시적으로 사용할 수 없습니다.", "empty": "아직 결과가 없습니다", "emptyDetail": "사례를 선택하고 세무 확인을 시작하세요." },
  "case": { "title": "저장된 사례", "description": "매물 입력, 분석 결과와 다음 확인 사항을 로컬에 정리합니다.", "save": "사례 저장", "recent": "저장된 사례 보기", "clearCurrent": "현재 사례 지우기", "clearAll": "저장된 사례 모두 삭제", "empty": "저장된 사례가 없습니다.", "compare": "비교", "compareCount": "{{selected}}개 선택", "load": "불러오기", "delete": "삭제", "confirmDelete": "삭제 확인", "export": "HTML 내보내기", "missing": "누락: {{items}}", "address": "매물 주소", "price": "가격 데이터" },
});

const jaProduction = expandCopyGroups({
  "locale": { "switcherLabel": "言語を選択" },
  "common": { "optional": "任意", "noData": "利用できるデータがありません", "unavailable": "現在利用できません", "notStarted": "未開始", "yes": "はい", "no": "いいえ", "source": "データソース", "updated": "更新日", "period": "期間", "count": "件数", "records": "件", "dataLimit": "データの制限", "tableSwipe": "表を横にスクロールして確認", "selectCounty": "市・県を選択", "selectDistrict": "区・郡を選択", "selectRoad": "道路を選択" },
  "action": { "open": "開く", "search": "検索", "loading": "読み込み中…", "retry": "再試行" },
  "map": { "kicker": "地図と生活機能", "title": "地図インサイト", "description": "場所を検索し、周辺の生活機能とデータソースを確認します。", "help": "地図の結果は位置情報の参考です。データの範囲と利用状況により制限される場合があります。", "quickMode": "候補から選択", "manualMode": "手動入力", "city": "市・県", "district": "区・郡", "road": "道路または場所", "searchPlaceholder": "住所、ランドマーク、道路を入力", "radius": "検索範囲（メートル）", "search": "場所を検索", "searching": "検索中…", "empty": "まだ場所を検索していません", "emptyDetail": "場所を入力して検索すると、地図と周辺データを確認できます。", "nearby": "周辺の生活機能", "nearbyDescription": "結果はカテゴリと距離ごとに整理しています。参考情報です。", "noResult": "利用できる地図結果がありません。", "searchError": "地図データを取得できません。しばらくしてから再試行してください。", "healthUnavailable": "地図サービスの状態を確認できません。", "sourceNote": "ソースと利用状況は現在のサービス応答に基づきます。", "selected": "選択した場所", "distance": "距離", "rating": "評価" },
  "commute": { "check": "通勤情報を確認", "checking": "通勤情報を確認中…", "unavailable": "通勤データを現在利用できません。しばらくしてから再試行してください。", "unresolved": "この住所から信頼できる通勤参考結果を取得できません。" },
});

const koProduction = expandCopyGroups({
  "locale": { "switcherLabel": "언어 선택" },
  "common": { "optional": "선택 사항", "noData": "사용 가능한 데이터 없음", "unavailable": "현재 사용할 수 없음", "notStarted": "시작하지 않음", "yes": "예", "no": "아니요", "source": "데이터 출처", "updated": "업데이트", "period": "기간", "count": "건수", "records": "건", "dataLimit": "데이터 제한", "tableSwipe": "표를 좌우로 밀어 확인하세요", "selectCounty": "시·현 선택", "selectDistrict": "구·군 선택", "selectRoad": "도로 선택" },
  "action": { "open": "열기", "search": "검색", "loading": "불러오는 중…", "retry": "다시 시도" },
  "map": { "kicker": "지도와 생활 편의", "title": "지도 인사이트", "description": "위치를 검색하고 주변 생활 편의와 데이터 출처를 확인합니다.", "help": "지도 결과는 위치 참고용입니다. 데이터 범위와 사용 가능 여부에 따라 제한될 수 있습니다.", "quickMode": "빠른 선택", "manualMode": "직접 입력", "city": "시·현", "district": "구·군", "road": "도로 또는 장소", "searchPlaceholder": "주소, 랜드마크 또는 도로 입력", "radius": "검색 반경(미터)", "search": "위치 검색", "searching": "검색 중…", "empty": "아직 검색한 위치가 없습니다", "emptyDetail": "위치를 입력하고 검색하면 지도와 주변 데이터를 확인할 수 있습니다.", "nearby": "주변 생활 편의", "nearbyDescription": "결과는 카테고리와 거리별로 정리한 참고 정보입니다.", "noResult": "사용 가능한 지도 결과가 없습니다.", "searchError": "지도 데이터를 가져올 수 없습니다. 잠시 후 다시 시도하세요.", "healthUnavailable": "지도 서비스 상태를 확인할 수 없습니다.", "sourceNote": "출처와 사용 가능 여부는 현재 서비스 응답을 따릅니다.", "selected": "선택한 위치", "distance": "거리", "rating": "평점" },
  "commute": { "check": "통근 정보 확인", "checking": "통근 정보 확인 중…", "unavailable": "통근 데이터를 현재 사용할 수 없습니다. 잠시 후 다시 시도하세요.", "unresolved": "이 주소에서 신뢰할 수 있는 통근 참고 결과를 가져올 수 없습니다." },
});

export const RUNTIME_COPY_OVERRIDES = {
  ja: { ...ja, ...jaProduction },
  ko: { ...ko, ...koProduction },
};

const overrides: Partial<Record<ExperienceLocale, RuntimeCopyOverride>> = RUNTIME_COPY_OVERRIDES;

export function getRuntimeCopyOverride(locale: ExperienceLocale, key: string, values: Record<string, string | number> = {}) {
  const template = overrides[locale]?.[key];
  if (!template) return undefined;
  return Object.entries(values).reduce((text, [name, value]) => text.replaceAll(`{{${name}}}`, String(value)), template);
}
