"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { ViewingDecisionCard } from "@/components/viewing-decision-card";
import {
  MODULE_LABELS,
  readStoredViewingAssessments,
  toViewingDecisionResult,
  writeStoredViewingAssessment,
  type ModuleSlug,
} from "@/lib/viewing-decision";

type Field =
  | {
      name: string;
      label: string;
      type: "text" | "number" | "textarea";
      placeholder?: string;
      required?: boolean;
    }
  | {
      name: string;
      label: string;
      type: "select";
      options: ReadonlyArray<{ label: string; value: string }>;
      required?: boolean;
    }
  | {
      name: string;
      label: string;
      type: "checkbox";
    };

type AnalysisResult = {
  id: number;
  module: string;
  result: {
    risk_level: "low" | "medium" | "high";
    score: number;
    summary: string;
    recommendations: string[];
    details: Record<string, unknown>;
  };
};

type AssessmentFormProps = {
  title: string;
  description: string;
  endpoint: string;
  fields: Field[];
  moduleSlug: ModuleSlug;
  reportBasePath: string;
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function AssessmentForm({
  title,
  description,
  endpoint,
  fields,
  moduleSlug,
  reportBasePath,
}: AssessmentFormProps) {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);
    setIsSubmitting(true);

    const formData = new FormData(event.currentTarget);
    const payload = fields.reduce<Record<string, string | number | boolean | null>>(
      (data, field) => {
        if (field.type === "checkbox") {
          data[field.name] = formData.get(field.name) === "on";
          return data;
        }

        const value = formData.get(field.name);
        if (field.type === "number") {
          data[field.name] = value === null || value === "" ? 0 : Number(value);
          return data;
        }

        data[field.name] = value?.toString() ?? null;
        return data;
      },
      {},
    );

    try {
      const response = await fetch(`${apiBaseUrl}${endpoint}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error(`Request failed with status ${response.status}`);
      }

      const savedResult = (await response.json()) as AnalysisResult;
      const viewingResult = toViewingDecisionResult(savedResult.result);
      setResult(savedResult);
      writeStoredViewingAssessment({
        assessmentId: savedResult.id,
        moduleName: savedResult.module,
        moduleSlug,
        result: viewingResult,
      });
      event.currentTarget.reset();
    } catch (requestError) {
      setError(
        requestError instanceof Error ? requestError.message : "Unable to submit assessment",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.8fr)]">
      <Card>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent>
          <form className="grid gap-4 sm:grid-cols-2" onSubmit={handleSubmit}>
            {fields.map((field) => (
              <div
                key={field.name}
                className={
                  field.type === "textarea" ? "grid gap-2 text-sm font-medium sm:col-span-2" : "grid gap-2 text-sm font-medium"
                }
              >
                {field.type === "checkbox" ? (
                  <label className="flex min-h-10 items-center gap-3 rounded-md border bg-background px-3 py-2">
                    {renderField(field)}
                    <span>{field.label}</span>
                  </label>
                ) : (
                  <label className="grid gap-2">
                    {field.label}
                    {renderField(field)}
                  </label>
                )}
              </div>
            ))}
            <Button className="w-full sm:col-span-2 sm:w-auto" type="submit" disabled={isSubmitting}>
              {isSubmitting ? "Saving..." : "Save Assessment"}
            </Button>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Mock Analysis Result</CardTitle>
          <CardDescription>Saved response from the local FastAPI endpoint.</CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <p className="rounded-md border border-destructive/40 bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </p>
          ) : null}
          {!error && !result ? (
            <div className="grid min-h-[220px] place-items-center rounded-md border border-dashed bg-muted/40 p-6 text-center text-sm text-muted-foreground">
              Submit the form to create a record and receive a rules-engine result.
            </div>
          ) : null}
          {result ? (
            <div className="space-y-4">
              <div className="rounded-md border bg-muted/40 p-4">
                <p className="text-sm text-muted-foreground">Record #{result.id}</p>
                <h2 className="mt-1 text-lg font-semibold">{result.module}</h2>
              </div>
              <Button asChild className="w-full sm:w-auto">
                <Link href={`${reportBasePath}/${result.id}`}>Open Report</Link>
              </Button>
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">Risk Level</p>
                  <p className="mt-1 text-base font-semibold capitalize">
                    {result.result.risk_level}
                  </p>
                </div>
                <div className="rounded-md border p-3">
                  <p className="text-xs text-muted-foreground">Score</p>
                  <p className="mt-1 text-base font-semibold">{result.result.score}</p>
                </div>
              </div>
              <p className="text-sm text-muted-foreground">{result.result.summary}</p>
              <div className="space-y-2">
                {result.result.recommendations.map((item) => (
                  <div key={item} className="rounded-md border px-3 py-2 text-sm">
                    {item}
                  </div>
                ))}
              </div>
              <pre className="max-h-72 max-w-full overflow-auto rounded-md border bg-muted/40 p-3 text-xs">
                {JSON.stringify(result.result.details, null, 2)}
              </pre>
              <ViewingDecisionCard
                assessments={readStoredViewingAssessments().length ? readStoredViewingAssessments() : [{
                  assessmentId: result.id,
                  moduleName: result.module,
                  moduleSlug,
                  result: toViewingDecisionResult(result.result),
                }]}
              />
            </div>
          ) : null}
          {!result ? (
            <div className="mt-4 rounded-md border bg-muted/30 p-3 text-sm text-muted-foreground">
              完成{MODULE_LABELS[moduleSlug]}後，這裡會整理目前已知提醒與下一步。
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  );
}

function renderField(field: Field) {
  const inputClass =
    "h-10 w-full min-w-0 rounded-md border border-input bg-background px-3 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring";

  if (field.type === "textarea") {
    return (
      <textarea
        className="min-h-28 w-full min-w-0 rounded-md border border-input bg-background px-3 py-2 text-sm outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring"
        name={field.name}
        placeholder={field.placeholder}
        required={field.required}
      />
    );
  }

  if (field.type === "select") {
    return (
      <select className={inputClass} name={field.name} required={field.required}>
        {field.options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    );
  }

  if (field.type === "checkbox") {
    return (
      <input
        className="size-4 shrink-0 rounded border-input text-primary focus-visible:ring-2 focus-visible:ring-ring"
        name={field.name}
        type="checkbox"
      />
    );
  }

  return (
    <input
      className={inputClass}
      name={field.name}
      placeholder={field.placeholder}
      required={field.required}
      step={field.type === "number" ? "0.01" : undefined}
      type={field.type}
    />
  );
}
