import { ExperienceStatePanel } from "@/components/experience-state-panel";

export function ChartUnavailableState() {
  return <ExperienceStatePanel state="unavailable" title="圖表資料暫時不可用" explanation="目前無法取得足夠資料，因此不顯示空白圖表。" />;
}
