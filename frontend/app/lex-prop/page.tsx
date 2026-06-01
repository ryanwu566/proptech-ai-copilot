import Link from "next/link";

import { AssessmentForm } from "@/components/assessment-form";
import { Button } from "@/components/ui/button";

const fields = [
  { name: "owner_name", label: "Owner Name", type: "text", required: true },
  { name: "property_address", label: "Property Address", type: "text", required: true },
  { name: "title_number", label: "Title Number", type: "text", required: true },
  { name: "has_lien", label: "Lien Flag", type: "checkbox" },
  { name: "has_easement", label: "Easement Flag", type: "checkbox" },
  {
    name: "dispute_notes",
    label: "Dispute Notes",
    type: "textarea",
    placeholder: "Example: 漏水、管委會、佔用、非自然身故、共有物糾紛",
  },
] as const;

export default function LexPropPage() {
  return (
    <main className="mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6 sm:px-6 sm:py-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">PropGuard AI</p>
          <h1 className="break-words text-2xl font-semibold leading-tight">
            LexProp 產權風險
          </h1>
        </div>
        <Button asChild className="w-full sm:w-auto" variant="outline">
          <Link href="/">Dashboard</Link>
        </Button>
      </div>
      <AssessmentForm
        title="Title Risk Intake"
        description="Stores a local title risk record and returns a deterministic title risk result."
        endpoint="/api/lex-prop/assessments"
        fields={[...fields]}
        reportBasePath="/lex-prop/reports"
      />
    </main>
  );
}
