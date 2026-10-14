import { CommutePlanner } from "@/components/places/commute-planner";
import { placesCopy } from "@/lib/my-places-copy";
export default async function CaseCommutePlannerPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  return <CommutePlanner key={caseId} caseId={caseId} catalogue={placesCopy} />;
}
