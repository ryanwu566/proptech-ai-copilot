"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useRef, type ReactNode } from "react";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getPageLabelKey, type AppPage } from "@/components/sidebar";

const methods: AppPage[] = ["Map Insight Lite", "房價估算", "Market Insight Lite", "Terrain Risk", "TaxOracle", "Aegis-Credit Lite"];

export function CommercialGlobalHeader({ page, onNavigate, children }: { page?: AppPage; onNavigate?: (page: AppPage) => void; children?: ReactNode }) {
  const pathname = usePathname();
  const { t } = useExperienceLocale();
  const disclosure = useRef<HTMLDetailsElement>(null);
  if (pathname === "/" && !onNavigate) return null;
  function navigate(next: AppPage) {
    if (disclosure.current) disclosure.current.open = false;
    onNavigate?.(next);
  }
  return <header className="commercial-global-header" aria-label={t("app.currentView")}>
    <a className="commercial-skip-link" href="#main-content">{t("commercial.skip")}</a>
    <div className="commercial-global-header__inner">
      <Link href="/" className="commercial-brand" aria-label={t("app.productName")}><span className="commercial-brand__mark" aria-hidden="true">P</span><span>PropTech Copilot</span></Link>
      <nav aria-label={t("commercial.globalNav")} className="commercial-global-nav">
        {onNavigate ? <button type="button" aria-current={page === "儀表板" ? "page" : undefined} onClick={() => navigate("儀表板")}>{t("commercial.home")}</button> : <Link href="/">{t("commercial.home")}</Link>}
        <Link href="/cases" aria-current={pathname === "/cases" ? "page" : undefined}>{t("commercial.cases")}</Link>
      </nav>
      <div className="commercial-global-tools">
        <LocaleSwitcher />
        <details ref={disclosure} className="commercial-methods" onKeyDown={(event) => { if (event.key === "Escape" && disclosure.current) { disclosure.current.open = false; disclosure.current.querySelector("summary")?.focus(); } }}>
          <summary>{t("commercial.methods")}</summary>
          <div className="commercial-methods__panel">
            <p className="text-meta">{t("commercial.methodsNote")}</p>
            <nav aria-label={t("nav.tools")}>
              {methods.map((item) => onNavigate ? <button key={item} type="button" aria-current={page === item ? "page" : undefined} onClick={() => navigate(item)}>{t(getPageLabelKey(item))}</button> : <Link key={item} href={`/?tool=${encodeURIComponent(item)}`}>{t(getPageLabelKey(item))}</Link>)}
              <Link href="/vnext/property-identity">{t("commercial.identityMethod")}</Link>
              {onNavigate && <button type="button" onClick={() => navigate("Competition Demo" as AppPage)}>{t("commercial.referenceDemo")}</button>}
            </nav>
            {children}
          </div>
        </details>
      </div>
    </div>
  </header>;
}
