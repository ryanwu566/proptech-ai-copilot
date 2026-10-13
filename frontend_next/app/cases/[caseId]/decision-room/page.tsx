import { DecisionRoomPage } from "@/components/decision-room/decision-room";

export default async function PropertyDecisionRoomPage({ params }: { params: Promise<{ caseId: string }> }) {
  const { caseId } = await params;
  return <DecisionRoomPage key={caseId} caseId={caseId} />;
}
