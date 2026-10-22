"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { accountEntryCopy } from "@/lib/account-entry-copy";
import { authEntryHref, safeAuthReturn } from "@/lib/navigation/auth-return";
import { observeAuthSessionStatus, type SessionEntryState } from "@/lib/auth-session-status";

function PendingEntry() {
  const { copyFrom } = useExperienceLocale();
  return <span className="auth-entry-pending" aria-live="polite">{copyFrom(accountEntryCopy, "working")}</span>;
}

function SessionActions() {
  const pathname = usePathname();
  const search = useSearchParams();
  const { copyFrom } = useExperienceLocale();
  const c = (key: "entry" | "login" | "signup") => copyFrom(accountEntryCopy, key);
  const [state, setState] = useState<SessionEntryState>("pending");
  // Auth routes carry the original intent when users switch entry method.
  const destination = pathname === "/login" || pathname === "/signup" ? safeAuthReturn(search.get("next"))
    : safeAuthReturn(pathname === "/compare" && search.size ? `${pathname}?${search}` : pathname);

  useEffect(() => observeAuthSessionStatus(setState), []);

  return <div className="auth-entry-actions" data-testid="auth-entry-actions">
    {state === "pending" ? <PendingEntry /> : state === "anonymous" ? <>
      <Link prefetch={false} href={authEntryHref("login", destination)}>{c("login")}</Link>
      <Link prefetch={false} className="auth-entry-signup" href={authEntryHref("signup", destination)}>{c("signup")}</Link>
    </> : <Link prefetch={false} href="/account" aria-current={pathname === "/account" ? "page" : undefined}>{c("entry")}</Link>}
  </div>;
}

export function AuthEntryActions() {
  return <Suspense fallback={<PendingEntry />}><SessionActions /></Suspense>;
}
