import type { ReactNode } from "react";
import { joinClassNames } from "./types";

export function SummaryStrip({ children, className, label }: { children: ReactNode; className?: string; label?: string }) {
  return <div className={joinClassNames("ds-summary-strip", className)} aria-label={label}>{children}</div>;
}

export function MetricItem({
  label,
  value,
  unit,
  note,
  primary = false,
  className,
}: {
  label: ReactNode;
  value: ReactNode;
  unit?: ReactNode;
  note?: ReactNode;
  primary?: boolean;
  className?: string;
}) {
  return <div className={joinClassNames("ds-metric", className)}>
    <div className="ds-metric__label">{label}</div>
    <div className={joinClassNames("ds-metric__value", primary && "text-kpi")} data-numeric>
      <span className="ds-value"><span>{value}</span>{unit && <span>{unit}</span>}</span>
    </div>
    {note && <div className="ds-metric__note">{note}</div>}
  </div>;
}

export function MetricRow({ label, value, unit, className }: { label: ReactNode; value: ReactNode; unit?: ReactNode; className?: string }) {
  return <div className={joinClassNames("ds-metric-row", className)}>
    <span>{label}</span>
    <span className="ds-value ds-numeric"><span>{value}</span>{unit && <span>{unit}</span>}</span>
  </div>;
}
