"use client";

import type { OfficialDataSourceStatus } from "@/lib/api";
import { useExperienceLocale } from "@/components/experience-locale-provider";

type TaxTrace = {
  rule_version: string;
  jurisdiction: string;
  effective_date: string | null;
  source_name: string;
  source_status: string;
  calculation_kind: string;
  limitation: string;
};

const copy = {
  "zh-TW": { sourceTitle: "官方資料來源狀態", status: "狀態", version: "版本", effective: "生效日", access: "存取方式", auth: "認證", notChecked: "尚未檢查", limitation: "限制", terrainNote: "來源狀態不等於已完成風險評估；未涵蓋或不可用不代表沒有風險。", taxTitle: "官方規則來源與計算邊界", ruleVersion: "規則版本", jurisdiction: "jurisdiction", calculation: "輸出類型", preliminary: "初步篩選", taxNote: "TaxOracle 只使用使用者輸入做初步篩選，不是官方核定或個人稅務紀錄。" },
  en: { sourceTitle: "Official data source status", status: "Status", version: "Version", effective: "Effective", access: "Access", auth: "Auth", notChecked: "Not checked", limitation: "Limitation", terrainNote: "Source status is not a completed risk assessment. Missing or unavailable coverage does not mean no risk.", taxTitle: "Official rule source and calculation boundary", ruleVersion: "Rule version", jurisdiction: "Jurisdiction", calculation: "Output type", preliminary: "Preliminary screening", taxNote: "TaxOracle uses user-provided facts for preliminary screening only; it is not an official assessment or personal tax record." },
  ja: { sourceTitle: "公式データソースの状態", status: "状態", version: "バージョン", effective: "発効日", access: "アクセス", auth: "認証", notChecked: "未確認", limitation: "制限", terrainNote: "ソース状態はリスク評価の完了を意味しません。対象外や利用不可はリスクがないことを意味しません。", taxTitle: "公式ルールのソースと計算境界", ruleVersion: "ルールバージョン", jurisdiction: "管轄", calculation: "出力種別", preliminary: "予備スクリーニング", taxNote: "TaxOracleは入力情報による予備確認のみで、公式査定や個人の税務記録ではありません。" },
  ko: { sourceTitle: "공식 데이터 출처 상태", status: "상태", version: "버전", effective: "시행일", access: "접근 방식", auth: "인증", notChecked: "확인하지 않음", limitation: "제한", terrainNote: "출처 상태는 위험 평가 완료를 뜻하지 않습니다. 미포함 또는 사용 불가는 위험이 없다는 뜻이 아닙니다.", taxTitle: "공식 규칙 출처와 계산 경계", ruleVersion: "규칙 버전", jurisdiction: "관할", calculation: "출력 유형", preliminary: "예비 심사", taxNote: "TaxOracle은 입력 사실을 이용한 예비 심사일 뿐 공식 판정이나 개인 세무 기록이 아닙니다." },
} as const;

export function OfficialDataStatusCard({ sources }: { sources: OfficialDataSourceStatus[] }) {
  const { locale } = useExperienceLocale();
  const t = copy[locale] ?? copy["zh-TW"];
  if (!sources.length) return null;
  return <details className="rounded-xl border border-slate-200 bg-slate-50"><summary className="cursor-pointer px-3 py-2.5 text-xs font-bold text-slate-800">{t.sourceTitle}</summary><div className="space-y-2 px-3 pb-3 text-[11px] leading-5 text-slate-700"><p>{t.terrainNote}</p>{sources.map((source) => <div key={source.provider_id} className="rounded-lg border border-slate-200 bg-white p-3"><div className="flex flex-wrap items-center justify-between gap-2"><strong>{source.dataset_name}</strong><span className="rounded-full bg-slate-100 px-2 py-0.5">{source.runtime_status === "not_checked" ? t.notChecked : source.runtime_status}</span></div><p className="mt-1">{source.agency} · {t.status}: {source.runtime_status === "not_checked" ? t.notChecked : source.runtime_status}</p><p>{t.version}: {source.published_version ?? "unknown"} · {t.effective}: {source.effective_date ?? "unknown"}</p><p>{t.access}: {source.access_mode} · {t.auth}: {source.authentication_mode}</p><p className="mt-1 text-amber-800">{t.limitation}: {source.limitation_summary}</p></div>)}</div></details>;
}

export function OfficialTaxRuleStatusCard({ trace }: { trace?: TaxTrace }) {
  const { locale } = useExperienceLocale();
  const t = copy[locale] ?? copy["zh-TW"];
  if (!trace) return null;
  return <details className="rounded-xl border border-violet-200 bg-violet-50/60"><summary className="cursor-pointer px-3 py-2.5 text-xs font-bold text-violet-900">{t.taxTitle}</summary><div className="space-y-1 px-3 pb-3 text-[11px] leading-5 text-violet-950"><p>{t.ruleVersion}: {trace.rule_version} · {t.jurisdiction}: {trace.jurisdiction} · {t.effective}: {trace.effective_date ?? "unknown"}</p><p>{t.status}: {trace.source_status === "not_checked" ? t.notChecked : trace.source_status} · {t.calculation}: {t.preliminary}</p><p>{t.taxNote}</p><p className="text-violet-800">{trace.limitation}</p></div></details>;
}
