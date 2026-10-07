import Link from "next/link";
import type { ReactNode } from "react";
import { ActionSection, Section } from "@/components/design-system/section";
import styles from "./overview-view.module.css";

export function OverviewSection({
  title,
  description,
  href,
  linkLabel,
  children,
  testId,
}: {
  title: string;
  description: string;
  href: string;
  linkLabel: string;
  children: ReactNode;
  testId: string;
}) {
  return <Section title={title} description={description} className={styles.domain}>
    <div className={styles.domainBody} data-testid={testId}>{children}</div>
    <ActionSection className={styles.domainAction}>
      <Link className="ds-button ds-button--secondary ds-button--compact" href={href}>{linkLabel}</Link>
    </ActionSection>
  </Section>;
}
