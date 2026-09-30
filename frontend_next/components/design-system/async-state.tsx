import type { ReactNode } from "react";
import { resolveAsyncStateRole } from "@/lib/commercial/state";
import { joinClassNames, type AsyncStateKind } from "./types";

export function AsyncState({
  kind,
  title,
  detail,
  action,
  className,
}: {
  kind: AsyncStateKind;
  title: ReactNode;
  detail?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  const visualRole = resolveAsyncStateRole(kind);
  return (
    <div
      className={joinClassNames("ds-async-state", `ds-role-${visualRole}`, className)}
      role={kind === "error" ? "alert" : kind === "loading" ? "status" : undefined}
      aria-live={kind === "loading" ? "polite" : undefined}
      data-async-state={kind}
    >
      {kind === "loading" ? <span className="ds-spinner" aria-hidden="true" /> : <span className="ds-status__icon" aria-hidden="true">{visualRole === "error" ? "×" : visualRole === "warning" ? "!" : "—"}</span>}
      <div className="ds-async-state__body">
        <div className="ds-async-state__title">{title}</div>
        {detail && <div className="text-body">{detail}</div>}
        {action && <div className="ds-action-section">{action}</div>}
      </div>
    </div>
  );
}
