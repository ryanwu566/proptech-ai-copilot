import { ScenarioLabEntry } from "@/components/evidence/evidence-entry";
import { scenarioCopy } from "@/lib/workspace/scenario-copy";

export default function PropertyScenariosPage() {
  return <ScenarioLabEntry catalogue={scenarioCopy} />;
}
