import type { AnchorHTMLAttributes, ButtonHTMLAttributes, ReactNode } from "react";
import { joinClassNames } from "./types";

export function WorkspaceNavigation({ label, children, className }: { label: string; children: ReactNode; className?: string }) {
  return <nav aria-label={label} className={joinClassNames("ds-navigation", className)}>{children}</nav>;
}

type NavigationLinkProps = Omit<AnchorHTMLAttributes<HTMLAnchorElement>, "children"> & {
  href: string;
  current?: boolean;
  icon?: ReactNode;
  children: ReactNode;
};

type NavigationButtonProps = Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> & {
  href?: undefined;
  current?: boolean;
  icon?: ReactNode;
  children: ReactNode;
};

export function NavigationItem(props: NavigationLinkProps | NavigationButtonProps) {
  if (props.href !== undefined) {
    const { href, current = false, icon, children, className, ...anchorProps } = props;
    const content = <>{icon && <span aria-hidden="true">{icon}</span>}<span>{children}</span></>;
    return <a href={href} className={joinClassNames("ds-navigation-item", className)} aria-current={current ? "page" : undefined} {...anchorProps}>{content}</a>;
  }
  const { current = false, icon, children, className, type = "button", ...buttonProps } = props;
  const content = <>{icon && <span aria-hidden="true">{icon}</span>}<span>{children}</span></>;
  return <button type={type} className={joinClassNames("ds-navigation-item", className)} aria-current={current ? "page" : undefined} {...buttonProps}>{content}</button>;
}
