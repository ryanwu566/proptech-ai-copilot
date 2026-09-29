import type { ReactNode } from "react";
import { joinClassNames, type MessageVariant, type VisualRole } from "./types";

const roles: Record<MessageVariant, VisualRole> = {
  inline: "neutral",
  information: "information",
  warning: "warning",
  confirmation: "warning",
  error: "error",
  success: "success",
};

export function Message({
  variant = "information",
  title,
  children,
  action,
  className,
}: {
  variant?: MessageVariant;
  title?: ReactNode;
  children: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  const visualRole = roles[variant];
  return (
    <div
      className={joinClassNames("ds-message", `ds-role-${visualRole}`, className)}
      role={variant === "error" ? "alert" : undefined}
      data-message-variant={variant}
    >
      <span className="ds-status__icon" aria-hidden="true">{visualRole === "error" ? "×" : visualRole === "warning" ? "!" : "i"}</span>
      <div className="ds-message__content">
        {title && <strong className="ds-message__title">{title}</strong>}
        <div>{children}</div>
        {action && <div className="ds-action-section">{action}</div>}
      </div>
    </div>
  );
}
