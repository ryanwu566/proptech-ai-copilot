import { ExperienceStatePanel } from "@/components/experience-state-panel";
import type { ExperienceState } from "@/lib/experience-architecture";

export function VisualDataUnavailableState({ message, state = "unavailable" }: { message?: string; state?: ExperienceState }) {
  return <ExperienceStatePanel state={state} explanation={message} />;
}
