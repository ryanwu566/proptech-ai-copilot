import Link from "next/link";

import { AssessmentForm } from "@/components/assessment-form";
import { Button } from "@/components/ui/button";

const fields = [
  { name: "applicant_name", label: "Applicant Name", type: "text", required: true },
  { name: "property_address", label: "Property Address", type: "text", required: true },
  { name: "property_value", label: "Property Value", type: "number", required: true },
  { name: "loan_amount", label: "Loan Amount", type: "number", required: true },
  { name: "monthly_income", label: "Monthly Income", type: "number", required: true },
  { name: "existing_debt", label: "Existing Monthly Debt", type: "number", required: true },
  { name: "loan_term_years", label: "Loan Term Years", type: "number", required: true },
] as const;

export default function AegisCreditPage() {
  return (
    <main className="mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6 sm:px-6 sm:py-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">PropGuard AI</p>
          <h1 className="break-words text-2xl font-semibold leading-tight">
            Aegis-Credit 房貸風險
          </h1>
        </div>
        <Button asChild className="w-full sm:w-auto" variant="outline">
          <Link href="/">Dashboard</Link>
        </Button>
      </div>
      <AssessmentForm
        title="Mortgage Risk Intake"
        description="Stores a local assessment record and returns a deterministic mortgage risk result."
        endpoint="/api/aegis-credit/assessments"
        fields={[...fields]}
        moduleSlug="aegis-credit"
        reportBasePath="/aegis-credit/reports"
      />
    </main>
  );
}
