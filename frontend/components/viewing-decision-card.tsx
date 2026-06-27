import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { buildViewingDecision, type ModuleAssessment, type ViewingDecision } from "@/lib/viewing-decision";

type ViewingDecisionCardProps = { assessments?: ModuleAssessment[]; decision?: ViewingDecision };

const zh = (codes: number[]) => String.fromCodePoint(...codes);
const title = zh([0x9019,0x9593,0x623f,0x503c,0x5f97,0x53bb,0x770b,0x55ce,0xff1f]);
const completed = zh([0x5df2,0x5b8c,0x6210]);
const reminders = zh([0x5df2,0x77e5,0x63d0,0x9192]);
const missing = zh([0x5c1a,0x672a,0x5b8c,0x6210]);
const nextStep = zh([0x5efa,0x8b70,0x4e0b,0x4e00,0x6b65]);
const disclaimer = zh([0x9019,0x4efd,0x7d50,0x679c,0x53ea,0x80fd,0x5354,0x52a9,0x4f60,0x521d,0x6b65,0x7be9,0x9078,0xff0c,0x4ecd,0x5efa,0x8b70,0x770b,0x5c4b,0x524d,0x6838,0x5c0d,0x6b0a,0x72c0,0x3001,0x73fe,0x6cc1,0x8207,0x8cb8,0x6b3e,0x689d,0x4ef6,0x3002]);
const emptyDone = zh([0x5c1a,0x672a,0x5b8c,0x6210,0x4efb,0x4f55,0x5206,0x6790,0x3002]);
const emptyReminder = zh([0x76ee,0x524d,0x6c92,0x6709,0x53ef,0x8b80,0x53d6,0x7684,0x63d0,0x9192,0x3002]);
const emptyMissing = zh([0x4e09,0x9805,0x4e3b,0x8981,0x6aa2,0x67e5,0x90fd,0x5df2,0x6709,0x7d50,0x679c,0x3002]);

const tone = {
  continue_viewing: "border-sky-200 bg-sky-50 text-sky-900",
  needs_more_information: "border-amber-200 bg-amber-50 text-amber-900",
  clarify_risk_first: "border-rose-200 bg-rose-50 text-rose-900",
};

export function ViewingDecisionCard({ assessments = [], decision = buildViewingDecision(assessments) }: ViewingDecisionCardProps) {
  return (
    <Card className="border-primary/20">
      <CardHeader>
        <CardDescription>Viewing Decision Summary</CardDescription>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <CardTitle className="text-xl">{title}</CardTitle>
          <Badge className={`w-fit border ${tone[decision.status]}`} variant="secondary">{decision.label}</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{decision.basis}</p>
        <div className="grid gap-3 md:grid-cols-3">
          <SummaryBlock emptyText={emptyDone} items={decision.completedItems} title={completed} />
          <SummaryBlock emptyText={emptyReminder} items={decision.knownReminders.slice(0, 3)} title={reminders} />
          <SummaryBlock emptyText={emptyMissing} items={decision.missingChecks} title={missing} />
        </div>
        <div className="rounded-md border bg-muted/30 p-4">
          <p className="text-sm font-semibold">{nextStep}</p>
          <p className="mt-1 text-sm text-muted-foreground">{disclaimer}</p>
          <Button asChild className="mt-3 w-full sm:w-auto"><Link href={decision.nextAction.href}>{decision.nextAction.label}</Link></Button>
        </div>
      </CardContent>
    </Card>
  );
}

function SummaryBlock({ emptyText, items, title }: { emptyText: string; items: string[]; title: string }) {
  return (
    <div className="rounded-md border bg-background p-3">
      <p className="text-sm font-semibold">{title}</p>
      {items.length ? <ul className="mt-2 space-y-1 text-sm text-muted-foreground">{items.map((item) => <li key={item}>- {item}</li>)}</ul> : <p className="mt-2 text-sm text-muted-foreground">{emptyText}</p>}
    </div>
  );
}
