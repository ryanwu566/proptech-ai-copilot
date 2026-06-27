import Link from "next/link";

import { AssessmentForm } from "@/components/assessment-form";
import { Button } from "@/components/ui/button";

const fields = [
  { name: "taxpayer_name", label: "Taxpayer Name", type: "text", required: true },
  { name: "property_address", label: "Property Address", type: "text", required: true },
  { name: "assessed_value", label: "Sold Property Value", type: "number", required: true },
  {
    name: "replacement_purchase_value",
    label: "Replacement Purchase Value",
    type: "number",
    required: true,
  },
  { name: "annual_rental_income", label: "Annual Rental Income", type: "number", required: true },
  { name: "holding_years", label: "Holding Years", type: "number", required: true },
  {
    name: "transaction_type",
    label: "Transaction Type",
    type: "select",
    required: true,
    options: [
      { label: "Purchase", value: "purchase" },
      { label: "Sale", value: "sale" },
      { label: "Rental", value: "rental" },
      { label: "Inheritance", value: "inheritance" },
    ],
  },
  { name: "is_self_use", label: "Self-use Property", type: "checkbox" },
  { name: "has_outstanding_tax_debt", label: "Outstanding Tax Debt", type: "checkbox" },
] as const;

export default function TaxOraclePage() {
  return (
    <main className="mx-auto grid min-h-screen max-w-7xl gap-6 px-4 py-6 sm:px-6 sm:py-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0">
          <p className="text-sm text-muted-foreground">PropGuard AI</p>
          <h1 className="break-words text-2xl font-semibold leading-tight">
            TaxOracle 稅務精算
          </h1>
        </div>
        <Button asChild className="w-full sm:w-auto" variant="outline">
          <Link href="/">Dashboard</Link>
        </Button>
      </div>
      <AssessmentForm
        title="Tax Scenario Intake"
        description="Stores a local tax scenario and returns a deterministic repurchase refund result."
        endpoint="/api/tax-oracle/assessments"
        fields={[...fields]}
        moduleSlug="tax-oracle"
        reportBasePath="/tax-oracle/reports"
      />
    </main>
  );
}
