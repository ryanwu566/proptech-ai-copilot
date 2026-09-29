import type { ReactNode } from "react";
import { joinClassNames } from "./types";

export function MapFrame({
  title,
  description,
  controls,
  attribution,
  detail,
  children,
  className,
}: {
  title: ReactNode;
  description?: ReactNode;
  controls?: ReactNode;
  attribution: ReactNode;
  detail?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return <section className={joinClassNames("ds-map-frame", className)} aria-label={typeof title === "string" ? title : undefined}>
    <div className="ds-map-frame__toolbar"><div><div className="text-subsection">{title}</div>{description && <div className="text-meta">{description}</div>}</div>{controls}</div>
    <div className="ds-map-frame__canvas">{children}</div>
    <div className="ds-map-frame__footer"><span>{attribution}</span>{detail}</div>
  </section>;
}
