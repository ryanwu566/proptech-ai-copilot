import type { ButtonHTMLAttributes, ReactNode } from "react";
import { joinClassNames, type ButtonSize, type ButtonVariant } from "./types";

export type CommercialButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  loadingLabel?: string;
  iconOnly?: boolean;
  children: ReactNode;
};

export function CommercialButton({
  variant = "primary",
  size = "standard",
  loading = false,
  loadingLabel = "處理中",
  iconOnly = false,
  disabled,
  className,
  children,
  type = "button",
  ...props
}: CommercialButtonProps) {
  if (iconOnly && !props["aria-label"] && !props["aria-labelledby"]) {
    throw new Error("Icon-only buttons require an accessible name via aria-label or aria-labelledby.");
  }
  const content = loading ? loadingLabel : children;
  return (
    <button
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={joinClassNames("ds-button", `ds-button--${variant}`, `ds-button--${size}`, iconOnly && "ds-button--icon", className)}
      {...props}
    >
      {loading && <span className="ds-spinner" aria-hidden="true" />}
      {content}
    </button>
  );
}
