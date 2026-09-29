import type { ElementType, ReactNode } from "react";
import { joinClassNames } from "./types";

export function Section({
  title,
  description,
  children,
  className,
  headingLevel = 2,
}: {
  title?: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  className?: string;
  headingLevel?: 2 | 3 | 4;
}) {
  const Heading = `h${headingLevel}` as ElementType;
  return (
    <section className={joinClassNames("ds-section", className)}>
      {(title || description) && <header className="ds-section__header">
        {title && <Heading className={headingLevel === 2 ? "text-section" : "text-subsection"}>{title}</Heading>}
        {description && <div className="ds-section__description">{description}</div>}
      </header>}
      {children}
    </section>
  );
}

export function Panel({
  children,
  className,
  variant = "default",
  ...props
}: React.HTMLAttributes<HTMLElement> & { variant?: "default" | "plain" | "raised" }) {
  return <section className={joinClassNames("ds-panel", `ds-panel--${variant}`, className)} {...props}>{children}</section>;
}

export function EvidenceSection({ children, className, ...props }: React.HTMLAttributes<HTMLElement>) {
  return <section className={joinClassNames("ds-evidence-section", className)} {...props}>{children}</section>;
}

export function ActionSection({ children, className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={joinClassNames("ds-action-section", className)} {...props}>{children}</div>;
}
