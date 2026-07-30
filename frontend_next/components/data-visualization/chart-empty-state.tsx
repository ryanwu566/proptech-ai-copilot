import { ExperienceStatePanel } from "@/components/experience-state-panel";

export function ChartEmptyState({ title = "目前沒有足夠資料可呈現圖表" }: { title?: string }) {
  return <ExperienceStatePanel state="partial" title={title} explanation="資料不足以形成有意義的視覺化，不會以零值補上缺口。" nextAction="查看資料來源與限制，或先完成必要的分析。" />;
}
