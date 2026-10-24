import type { DetailsHTMLAttributes, ReactNode, Ref } from "react";
import { joinClassNames } from "./types";

export function DetailsDisclosure({
  summary,
  children,
  variant = "standard",
  className,
  ...props
}: Omit<DetailsHTMLAttributes<HTMLDetailsElement>, "title"> & {
  summary: ReactNode;
  children: ReactNode;
  variant?: "standard" | "compact";
  ref?: Ref<HTMLDetailsElement>;
}) {
  return <details className={joinClassNames("ds-disclosure", `ds-disclosure--${variant}`, className)} {...props}>
    <summary className="ds-disclosure__summary">{summary}</summary>
    <div className="ds-disclosure__content">{children}</div>
  </details>;
}
