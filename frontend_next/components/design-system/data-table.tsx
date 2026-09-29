import type { ReactNode, TableHTMLAttributes, ThHTMLAttributes, TdHTMLAttributes } from "react";
import { joinClassNames } from "./types";

export function DataTable({
  caption,
  children,
  className,
  responsiveStrategy = "scroll",
  regionLabel,
  ...props
}: TableHTMLAttributes<HTMLTableElement> & {
  caption: ReactNode;
  responsiveStrategy?: "scroll";
  regionLabel?: string;
}) {
  if (responsiveStrategy !== "scroll") {
    throw new Error("DataTable currently only supports the scroll strategy.");
  }
  const accessibleRegionLabel = regionLabel ?? (typeof caption === "string" ? caption : undefined);
  return <div className="ds-table-wrap" data-table-strategy="scroll" tabIndex={0} role="region" aria-label={accessibleRegionLabel}>
    <table className={joinClassNames("ds-table", className)} {...props}>
      <caption>{caption}</caption>
      {children}
    </table>
  </div>;
}

export function DataTableHeader({ numeric, unit, className, children, scope = "col", ...props }: ThHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean; unit?: ReactNode }) {
  return <th scope={scope} data-align={numeric ? "numeric" : undefined} className={className} {...props}>
    {children}{unit && <span className="text-meta"> ({unit})</span>}
  </th>;
}

export function DataTableCell({ numeric, className, children, ...props }: TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return <td data-align={numeric ? "numeric" : undefined} data-numeric={numeric || undefined} className={className} {...props}>{children}</td>;
}
