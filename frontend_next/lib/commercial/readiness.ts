// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { READINESS_STATE_REGISTRY, type CommercialLocale, type LocalizedLabel, type TaskReadinessState } from "./state.ts";

export type CommercialTask = "viewing_preparation" | "comparison" | "client_discussion" | "report" | "offer_preparation";

const taskLabels: Record<CommercialTask, LocalizedLabel> = {
  viewing_preparation: { "zh-TW": "看屋前準備", en: "viewing preparation", ja: "内見準備", ko: "현장 방문 준비" },
  comparison: { "zh-TW": "物件比較", en: "property comparison", ja: "物件比較", ko: "매물 비교" },
  client_discussion: { "zh-TW": "初步客戶討論", en: "initial client discussion", ja: "初回顧客相談", ko: "초기 고객 논의" },
  report: { "zh-TW": "產生分析摘要", en: "analysis summary generation", ja: "分析サマリー作成", ko: "분석 요약 생성" },
  offer_preparation: { "zh-TW": "出價前準備", en: "offer preparation", ja: "提示前準備", ko: "가격 제안 준비" },
};

export type NamedTaskReadiness = {
  task: CommercialTask;
  value: TaskReadinessState;
  label: LocalizedLabel;
  meaning: string;
  role: (typeof READINESS_STATE_REGISTRY)[TaskReadinessState]["role"];
  actionable: boolean;
  recognized: boolean;
};

export function resolveTaskReadiness(
  task: CommercialTask,
  value: unknown,
  detail: { limitation?: string; blocker?: string } = {},
): NamedTaskReadiness {
  const recognized = typeof value === "string" && Object.hasOwn(READINESS_STATE_REGISTRY, value);
  const state = (recognized ? value : "blocked") as TaskReadinessState;
  const contract = READINESS_STATE_REGISTRY[state];
  const rendered = {} as LocalizedLabel;
  for (const locale of ["zh-TW", "en", "ja", "ko"] as CommercialLocale[]) {
    const taskName = taskLabels[task][locale];
    rendered[locale] = readinessLabel(locale, state, taskName, detail);
  }
  return { task, value: state, label: rendered, meaning: contract.meaning, role: contract.role, actionable: contract.actionable, recognized };
}
function readinessLabel(locale: CommercialLocale, state: TaskReadinessState, task: string, detail: { limitation?: string; blocker?: string }): string {
  if (locale === "zh-TW") {
    if (state === "not_ready") return `尚不足以進行「${task}」`;
    if (state === "ready_with_limits") return `可進行「${task}」，但仍有${detail.limitation ? `「${detail.limitation}」` : "限制"}`;
    if (state === "ready") return `可進行「${task}」`;
    return `需先解決「${detail.blocker?.trim() || "待確認事項"}」，才能進行「${task}」`;
  }
  if (locale === "ja") {
    if (state === "not_ready") return `「${task}」を実行する準備が整っていません`;
    if (state === "ready_with_limits") return `「${task}」を制約付きで実行できます${detail.limitation ? `：${detail.limitation}` : ""}`;
    if (state === "ready") return `「${task}」を実行できます`;
    return `「${detail.blocker?.trim() || "阻害要因"}」を解決してから「${task}」を実行してください`;
  }
  if (locale === "ko") {
    if (state === "not_ready") return `‘${task}’을(를) 진행할 준비가 부족합니다`;
    if (state === "ready_with_limits") return `‘${task}’을(를) 제한적으로 진행할 수 있습니다${detail.limitation ? `: ${detail.limitation}` : ""}`;
    if (state === "ready") return `‘${task}’을(를) 진행할 수 있습니다`;
    return `‘${detail.blocker?.trim() || "차단 사항"}’을(를) 해결한 뒤 ‘${task}’을(를) 진행하세요`;
  }
  if (state === "not_ready") return `Not ready for ${task}`;
  if (state === "ready_with_limits") return `Ready for ${task} with limits${detail.limitation ? `: ${detail.limitation}` : ""}`;
  if (state === "ready") return `Ready for ${task}`;
  return `Resolve ${detail.blocker?.trim() || "the blocker"} before ${task}`;
}
