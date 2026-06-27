import { AlertTriangle, Building2, CheckCircle2, Clock3, Database, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const zh = (codes: number[]) => String.fromCodePoint(...codes);
const copy = {
  title: zh([0x9019,0x9593,0x623f,0x503c,0x5f97,0x53bb,0x770b,0x55ce,0xff1f]),
  start: zh([0x958b,0x59cb,0x8a55,0x4f30,0x7269,0x4ef6]),
  intro: zh([0x6574,0x5408,0x7a05,0x8cbb,0x3001,0x8cb8,0x6b3e,0x8207,0x6587,0x4ef6,0x98a8,0x96aa,0xff0c,0x5354,0x52a9,0x5224,0x65b7,0x662f,0x5426,0x503c,0x5f97,0x9032,0x4e00,0x6b65,0x770b,0x623f,0x3002]),
  note: zh([0x5efa,0x8b70,0x4f9d,0x5e8f,0x5b8c,0x6210,0x4e09,0x9805,0x6aa2,0x67e5,0x3002,0x7f3a,0x5c11,0x7684,0x8cc7,0x6599,0x6703,0x660e,0x78ba,0x5217,0x51fa,0xff0c,0x4e0d,0x6703,0x88ab,0x7576,0x6210,0x4f4e,0x98a8,0x96aa,0x3002]),
  first: zh([0x958b,0x59cb,0x7b2c,0x4e00,0x6b65,0xff1a,0x7a05,0x8cbb,0x6aa2,0x67e5]),
  order: zh([0x5efa,0x8b70,0x4f7f,0x7528,0x9806,0x5e8f]),
  orderDesc: zh([0x5148,0x5f9e,0x6210,0x672c,0x8207,0x53ef,0x8cb8,0x6027,0x958b,0x59cb,0xff0c,0x518d,0x6aa2,0x67e5,0x6587,0x4ef6,0x8207,0x4f7f,0x7528,0x9650,0x5236,0x3002]),
  tax: zh([0x7a05,0x8cbb]),
  loan: zh([0x8cb8,0x6b3e]),
  lex: zh([0x6cd5,0x898f,0xff0f,0x6587,0x4ef6]),
  taxDesc: zh([0x5148,0x4f30,0x7a05,0x52d9,0x689d,0x4ef6,0x8207,0x53ef,0x80fd,0x9700,0x8981,0x88dc,0x9f4a,0x7684,0x6587,0x4ef6,0x3002]),
  loanDesc: zh([0x6aa2,0x67e5,0x8cb8,0x6b3e,0x91d1,0x984d,0x3001,0x6536,0x5165,0x8207,0x58d3,0x529b,0x6e2c,0x8a66,0x3002]),
  lexDesc: zh([0x6aa2,0x67e5,0x6b0a,0x5229,0x3001,0x4f7f,0x7528,0x9650,0x5236,0x8207,0x722d,0x8b70,0x7dda,0x7d22,0x3002]),
  startButton: zh([0x958b,0x59cb]),
};

const metrics = [
  { label: "Properties Watched", value: "0", icon: Building2 },
  { label: "Open Risk Signals", value: "0", icon: AlertTriangle },
  { label: "Reviews Pending", value: "0", icon: Clock3 },
  { label: "System Status", value: "Ready", icon: CheckCircle2 },
];

const queue = ["Connect database models", "Add authenticated workspace", "Prepare review history views", "Define production analysis engines"];

const modules = [
  { name: "TaxOracle", label: copy.tax, href: "/tax-oracle", description: copy.taxDesc, step: "1" },
  { name: "Aegis-Credit", label: copy.loan, href: "/aegis-credit", description: copy.loanDesc, step: "2" },
  { name: "LexProp", label: copy.lex, href: "/lex-prop", description: copy.lexDesc, step: "3" },
];

export default function DashboardPage() {
  return (
    <main className="min-h-screen">
      <section className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex min-w-0 items-center gap-3"><div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground"><ShieldCheck className="size-5" aria-hidden="true" /></div><div className="min-w-0"><p className="text-sm text-muted-foreground">PropGuard AI</p><h1 className="text-xl font-semibold leading-tight">{copy.title}</h1></div></div>
          <Badge className="w-fit" variant="secondary">Viewing Decision v1</Badge>
        </div>
      </section>
      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 sm:py-8">
        <Card className="border-primary/20"><CardHeader><CardTitle>{copy.start}</CardTitle><CardDescription>{copy.intro}</CardDescription></CardHeader><CardContent className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-center"><p className="text-sm text-muted-foreground">{copy.note}</p><Button asChild className="w-full lg:w-auto"><Link href="/tax-oracle">{copy.first}</Link></Button></CardContent></Card>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{metrics.map((metric) => <Card key={metric.label}><CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2"><CardDescription>{metric.label}</CardDescription><metric.icon className="size-4 text-muted-foreground" aria-hidden="true" /></CardHeader><CardContent><p className="text-2xl font-semibold">{metric.value}</p></CardContent></Card>)}</div>
        <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]"><Card><CardHeader><CardTitle>{copy.order}</CardTitle><CardDescription>{copy.orderDesc}</CardDescription></CardHeader><CardContent><div className="grid gap-3">{modules.map((module) => <div key={module.name} className="flex flex-col gap-4 rounded-md border bg-muted/30 p-4 sm:flex-row sm:items-center sm:justify-between"><div className="flex min-w-0 gap-3"><div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground"><span className="text-sm font-semibold">{module.step}</span></div><div className="min-w-0"><h2 className="break-words font-semibold">{module.name} <span className="text-muted-foreground">{module.label}</span></h2><p className="mt-1 text-sm text-muted-foreground">{module.description}</p></div></div><Button asChild className="w-full sm:w-auto"><Link href={module.href}>{copy.startButton}</Link></Button></div>)}</div></CardContent></Card>
          <Card><CardHeader><CardTitle>Build Queue</CardTitle><CardDescription>Next implementation checkpoints.</CardDescription></CardHeader><CardContent className="space-y-3">{queue.map((item) => <div key={item} className="flex min-w-0 items-center gap-3 rounded-md border bg-card px-3 py-2 text-sm"><Database className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" /><span className="min-w-0 break-words">{item}</span></div>)}</CardContent></Card></div>
      </section>
    </main>
  );
}
