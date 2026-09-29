import type { ReactNode } from "react";
import { joinClassNames, type VisualRole } from "./types";

const defaultIcons: Record<VisualRole, string> = {
  neutral: "—",
  information: "i",
  warning: "!",
  error: "×",
  success: "✓",
  disabled: "—",
};

export function StatusLabel({
  semanticRole = "neutral",
  icon,
  children,
  className,
}: {
  semanticRole?: VisualRole;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <span className={joinClassNames("ds-status", `ds-role-${semanticRole}`, className)} data-visual-role={semanticRole}>
      <span className="ds-status__icon" aria-hidden="true">{icon ?? defaultIcons[semanticRole]}</span>
      <span>{children}</span>
    </span>
  );
}
