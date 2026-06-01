import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  Clock3,
  Database,
  FileText,
  ShieldCheck,
} from "lucide-react";
import Link from "next/link";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

const metrics = [
  { label: "Properties Watched", value: "0", icon: Building2 },
  { label: "Open Risk Signals", value: "0", icon: AlertTriangle },
  { label: "Reviews Pending", value: "0", icon: Clock3 },
  { label: "System Status", value: "Ready", icon: CheckCircle2 },
];

const queue = [
  "Connect database models",
  "Add authenticated workspace",
  "Prepare review history views",
  "Define production analysis engines",
];

const modules = [
  {
    name: "Aegis-Credit",
    label: "房貸風險",
    href: "/aegis-credit",
    description: "Mortgage risk intake with deterministic result storage.",
  },
  {
    name: "TaxOracle",
    label: "稅務精算",
    href: "/tax-oracle",
    description: "Tax scenario intake with deterministic repurchase refund rules.",
  },
  {
    name: "LexProp",
    label: "產權風險",
    href: "/lex-prop",
    description: "Title risk intake for liens, easements, and dispute notes.",
  },
];

export default function DashboardPage() {
  return (
    <main className="min-h-screen">
      <section className="border-b bg-card">
        <div className="mx-auto flex max-w-7xl flex-col gap-4 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground">
              <ShieldCheck className="size-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <p className="text-sm text-muted-foreground">PropGuard AI</p>
              <h1 className="text-xl font-semibold leading-tight">Risk Operations Dashboard</h1>
            </div>
          </div>
          <Badge className="w-fit" variant="secondary">
            Skeleton
          </Badge>
        </div>
      </section>

      <section className="mx-auto grid max-w-7xl gap-6 px-4 py-6 sm:px-6 sm:py-8">
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {metrics.map((metric) => (
            <Card key={metric.label}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardDescription>{metric.label}</CardDescription>
                <metric.icon className="size-4 text-muted-foreground" aria-hidden="true" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-semibold">{metric.value}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <Card>
            <CardHeader>
              <CardTitle>Monitoring Workspace</CardTitle>
              <CardDescription>
                Basic module entry points for local assessment records.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid gap-3">
                {modules.map((module) => (
                  <div
                    key={module.name}
                    className="flex flex-col gap-4 rounded-md border bg-muted/30 p-4 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="flex min-w-0 gap-3">
                      <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
                        <FileText className="size-5" aria-hidden="true" />
                      </div>
                      <div className="min-w-0">
                        <h2 className="break-words font-semibold">
                          {module.name} <span className="text-muted-foreground">{module.label}</span>
                        </h2>
                        <p className="mt-1 text-sm text-muted-foreground">{module.description}</p>
                      </div>
                    </div>
                    <Button asChild className="w-full sm:w-auto">
                      <Link href={module.href}>Open Form</Link>
                    </Button>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Build Queue</CardTitle>
              <CardDescription>Next implementation checkpoints.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {queue.map((item) => (
                <div
                  key={item}
                  className="flex min-w-0 items-center gap-3 rounded-md border bg-card px-3 py-2 text-sm"
                >
                  <Database className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                  <span className="min-w-0 break-words">{item}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
