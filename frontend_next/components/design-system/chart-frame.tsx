import type { ReactNode } from "react";
import { joinClassNames } from "./types";

export function ChartFrame({
  title,
  question,
  unit,
  period,
  source,
  summary,
  children,
  className,
}: {
  title: ReactNode;
  question?: ReactNode;
  unit?: ReactNode;
  period?: ReactNode;
  source?: ReactNode;
  summary: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return <figure className={joinClassNames("ds-analysis-frame", className)}>
    <figcaption className="ds-analysis-frame__header">
      <div><div className="text-subsection">{title}</div>{question && <div className="text-body">{question}</div>}</div>
      {(unit || period) && <div className="ds-analysis-frame__meta">{unit && <span>{unit}</span>}{period && <span>{period}</span>}</div>}
    </figcaption>
    {children}
    <div className="ds-analysis-frame__summary">{summary}</div>
    {source && <div className="text-evidence">{source}</div>}
  </figure>;
}
