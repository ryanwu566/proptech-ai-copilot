"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { getPageLabelKey, type AppPage } from "@/components/sidebar";
import { accountEntryCopy } from "@/lib/account-entry-copy";
import { PRODUCT_ENTRIES, PRODUCT_GROUPS, caseIdFromPath, filterEntries, productHref, type ProductId } from "@/lib/navigation/model";
import { navigationCopy } from "@/lib/navigation/copy";

export function CommercialGlobalHeader({ page, onNavigate, children }: { page?: AppPage; onNavigate?: (page: AppPage) => void; children?: ReactNode }) {
  const pathname = usePathname();
  const { t, copyFrom } = useExperienceLocale();
  const disclosure = useRef<HTMLDetailsElement>(null);
  const [query, setQuery] = useState("");
  const caseId = caseIdFromPath(pathname);
  const label = (id: ProductId) => {
    const entry = PRODUCT_ENTRIES.find((entry) => entry.id === id);
    return entry && "tool" in entry && entry.tool ? t(getPageLabelKey(entry.tool)) : copyFrom(navigationCopy, id);
  };
  const entries = filterEntries(PRODUCT_ENTRIES, query, (id) => `${label(id)} ${copyFrom(navigationCopy, id)}`);
  useEffect(() => {
    const close = (event: PointerEvent) => {
      if (disclosure.current && !disclosure.current.contains(event.target as Node)) disclosure.current.open = false;
    };
    document.addEventListener("pointerdown", close);
    return () => document.removeEventListener("pointerdown", close);
  }, []);
  if (pathname === "/" && !onNavigate) return null;
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
        <Link prefetch={false} href="/account" aria-current={pathname === "/account" ? "page" : undefined}>{copyFrom(accountEntryCopy, "entry")}</Link>
        <LocaleSwitcher />
      </div>
        <details ref={disclosure} className="commercial-methods" onToggle={() => setQuery("")} onBlur={(event) => { if (!event.currentTarget.contains(event.relatedTarget as Node)) event.currentTarget.open = false; }} onKeyDown={(event) => { if (event.key === "Escape" && disclosure.current?.open) { event.preventDefault(); event.stopPropagation(); disclosure.current.open = false; disclosure.current.querySelector("summary")?.focus(); } }}>
          <summary>{copyFrom(navigationCopy, "menu")}</summary>
          <div className="commercial-methods__panel">
            <label className="product-search">{copyFrom(navigationCopy, "search")}<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} /></label>
            <p className="text-meta">{copyFrom(navigationCopy, "menuHint")}</p>
            {!caseId && <p className="text-meta">{copyFrom(navigationCopy, "caseHint")}</p>}
            {PRODUCT_GROUPS.map((group) => {
              const items = entries.filter((entry) => entry.group === group);
              return items.length ? <nav key={group} aria-label={copyFrom(navigationCopy, group)}>
                <h2 className="text-meta">{copyFrom(navigationCopy, group)}</h2>
                {items.map((entry) => {
                  const name = label(entry.id);
                  const description = "tool" in entry && name !== copyFrom(navigationCopy, entry.id) ? copyFrom(navigationCopy, entry.id) : undefined;
                  const descriptionId = description ? `product-description-${entry.id}` : undefined;
                  const content = <><span>{name}</span>{description && <span id={descriptionId} className="product-tool-caption">{description}</span>}</>;
                  return "tool" in entry && onNavigate
                    ? <button key={entry.id} type="button" aria-label={name} aria-describedby={descriptionId} aria-current={page === entry.tool ? "page" : undefined} onClick={() => navigate(entry.tool)}>{content}</button>
                    : <Link prefetch={false} key={entry.id} href={productHref(entry, caseId)} aria-label={name} aria-describedby={descriptionId} onClick={() => { if (disclosure.current) disclosure.current.open = false; }} aria-current={pathname === productHref(entry, caseId) && pathname !== "/" ? "page" : undefined}>{content}</Link>;
                })}
              </nav> : null;
            })}
            {!entries.length && <p role="status">{copyFrom(navigationCopy, "noResults")}</p>}
            {onNavigate && !query && <button className="ds-button ds-button--tertiary" type="button" onClick={() => navigate("Competition Demo" as AppPage)}>{t("commercial.referenceDemo")}</button>}
            {children}
          </div>
        </details>
    </div>
  </header>;
}
