"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, type ReactNode } from "react";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import type { AppPage } from "@/components/sidebar";
import { AuthEntryActions } from "@/components/account/auth-entry-actions";
import { navigationCopy } from "@/lib/navigation/copy";

/** Global navigation keeps the case workflow and explicit session-aware account actions. */
export function CommercialGlobalHeader({ page, onNavigate, children }: { page?: AppPage; onNavigate?: (page: AppPage) => void; children?: ReactNode }) {
  const pathname = usePathname();
  const { t, copyFrom } = useExperienceLocale();
  const disclosure = useRef<HTMLDetailsElement>(null);
  useEffect(() => {
    const close = (event: PointerEvent) => {
      if (disclosure.current && !disclosure.current.contains(event.target as Node)) disclosure.current.open = false;
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  if (pathname === "/" && (!onNavigate || page === "儀表板")) return null;
  function navigate(next: AppPage) {
    if (disclosure.current) disclosure.current.open = false;
    onNavigate?.(next);
  }
  return <header className="commercial-global-header" aria-label={t("app.currentView")}>
    <a className="commercial-skip-link" href="#main-content" onClick={() => { const main = document.getElementById("main-content") ?? document.querySelector("main"); if (main) { main.id = "main-content"; main.tabIndex = -1; main.focus(); } }}>{t("commercial.skip")}</a>
    <div className="commercial-global-header__inner">
      <Link href="/" className="commercial-brand" aria-label={t("app.productName")}><span className="commercial-brand__mark" aria-hidden="true">P</span><span>PropTech Copilot</span></Link>
      <nav aria-label={t("commercial.globalNav")} className="commercial-global-nav">
        {onNavigate ? <button type="button" aria-current={page === "儀表板" ? "page" : undefined} onClick={() => navigate("儀表板")}>{t("commercial.home")}</button> : <Link href="/">{t("commercial.home")}</Link>}
        <Link prefetch={false} href="/cases" aria-current={pathname === "/cases" ? "page" : undefined}>{copyFrom(navigationCopy, "cases")}</Link>
        <Link prefetch={false} href="/compare" aria-current={pathname === "/compare" ? "page" : undefined}>{copyFrom(navigationCopy, "compare")}</Link>
      </nav>
      <div className="commercial-global-tools">
        <AuthEntryActions />
        <LocaleSwitcher />
      </div>
      {children && <details ref={disclosure} className="commercial-methods" onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) event.currentTarget.open = false; }} onKeyDown={(event) => { if (event.key === "Escape" && disclosure.current?.open) { event.preventDefault(); event.stopPropagation(); disclosure.current.open = false; disclosure.current.querySelector("summary")?.focus(); } }}>
        <summary>{t("commercial.accessibility")}</summary>
        <div className="commercial-methods__panel">{children}</div>
      </details>}
    </div>
  </header>;
}
