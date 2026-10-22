import type { PropertyCaseWorkspace } from "./workspace/workspace-model";
import type { RoomRead } from "./decision-room-store";
// @ts-expect-error Native Node tests use source extensions.
import { isOutstanding } from "./decision-room-store.ts";
import type { ExperienceLocale } from "./experience-i18n";
// @ts-expect-error Native Node tests use source extensions.
import { commandPaletteCopy, type CommandCopyKey } from "./command-palette-copy.ts";

export type CaseCommand = {
  id: string; title: string; context?: string; aliases: string; href?: string; action?: "tour"; current: boolean;
};
type CommandContext = { pathname: string; workspace: PropertyCaseWorkspace | null; room: RoomRead | null; locale: ExperienceLocale };
const aliases: Record<string, string> = {
  new: "new create case 新案件 新規 새", saved: "saved cases open 已儲存 案件 保存 저장",
  compare: "compare comparison 比較 比较 比較 비교", account: "account profile 帳戶 アカウント 계정", tour: "tour guide onboarding 導覽 ガイド 가이드",
  overview: "overview case summary 總覽 概要 개요", market: "market price valuation 價格 市場 価格 가격 시장",
  location: "location commute map 區位 位置 通勤 立地 입지 통근", risk: "risk environment 風險 環境 リスク 위험",
  finance: "finance money loan cost 資金 持有成本 貸款 資金 자금 비용",
  "decision-room": "decision room tasks outstanding 決策室 待辦 意思決定 미완료 의사결정",
  report: "report 報告 レポート 보고서", "confirm-location": "confirm location 確認位置 位置確認 위치 확인",
  "risk-review": "risk unresolved verification 風險 待查證 リスク 위험", "market-evidence": "market evidence saved 市場證據 市場根拠 시장 근거",
};

/** Pure projection of validated local state. No IO, writers, provider clients, or readiness score. */
export function buildCaseCommands({ pathname, workspace, room, locale }: CommandContext): CaseCommand[] {
  const copy = commandPaletteCopy[locale];
  const label = (key: CommandCopyKey, count?: number) => copy[key].replace("{{count}}", String(count ?? 0));
  const command = (id: CommandCopyKey, href?: string, context?: string): CaseCommand => ({
    id, title: label(id), href, context, aliases: aliases[id] ?? "", current: href?.split(/[?#]/)[0] === pathname,
    ...(id === "tour" ? { action: "tour" as const } : {}),
  });
  const globals = [command("new", "/#commercial-address"), command("saved", "/cases"), command("compare", "/compare"), command("account", "/account"), command("tour")];
  const match = /^\/cases\/([^/]+)(?:\/|$)/.exec(pathname);
  let caseId: string | undefined;
  try { caseId = match ? decodeURIComponent(match[1]) : undefined; } catch { /* Malformed routes have no active case. */ }
  if (!workspace || workspace.caseId !== caseId) return globals;
  const base = `/cases/${encodeURIComponent(workspace.caseId)}`;
  const context = `${copy.savedContext} · ${workspace.title}`;
  const sections = ["overview", "market", "location", "risk", "finance", "decision-room", "report"] as const;
  const list = sections.map((id) => command(id, `${base}/${id}`, context));
  globals.find((c) => c.id === "compare")!.href = `/compare?cases=${encodeURIComponent(workspace.caseId)}`;
  list.push(...globals);

  const openItems = room?.status === "ready" && room.room.caseId === workspace.caseId
    ? room.room.items.filter(isOutstanding).length : 0;
  if (openItems) list.find((c) => c.id === "decision-room")!.title = label("outstanding", openItems);

  const unconfirmed = workspace.identity.state === "unconfirmed";
  if (unconfirmed) list.push(command("confirm-location", `${base}/location`, context));
  const riskActions = workspace.risk?.overview.outstandingVerificationActions.length ?? 0;
  const unresolvedRisk = riskActions > 0 || (workspace.risk?.unknownEvidenceCount ?? 0) > 0;
  if (unresolvedRisk) list.push(command("risk-review", `${base}/risk`, riskActions ? label("riskCount", riskActions) : copy.evidence));
  if (workspace.evidence.market.query === "succeeded") list.push(command("market-evidence", `${base}/market`, copy.evidence));

  // Saved summaries in three distinct domains justify surfacing synthesis routes, not a readiness claim.
  const domains = [
    workspace.evidence.market.query === "succeeded" || workspace.evidence.valuation.query === "succeeded",
    workspace.evidence.location.query === "succeeded" || workspace.evidence.commute.query === "succeeded",
    workspace.evidence.risk.query === "succeeded", workspace.evidence.finance.query === "succeeded",
  ];
  const priority = unconfirmed ? ["confirm-location", "overview", "saved"]
    : unresolvedRisk ? ["risk-review", "decision-room", "report"]
    : domains.filter(Boolean).length >= 3 ? ["decision-room", "compare", "report"] : [];
  const rank = (c: CaseCommand) => priority.includes(c.id) ? priority.indexOf(c.id) : c.current ? 101 : 100;
  return list.sort((a, b) => rank(a) - rank(b));
}

const normalize = (text: string) => text.normalize("NFKC").toLocaleLowerCase().trim();
export function filterCaseCommands(commands: CaseCommand[], query: string): CaseCommand[] {
  const tokens = normalize(query).split(/\s+/).filter(Boolean);
  return commands.filter((command) => {
    const searchable = normalize(`${command.id} ${command.title} ${command.context ?? ""} ${command.aliases}`);
    return tokens.every((token) => searchable.includes(token));
  });
}
