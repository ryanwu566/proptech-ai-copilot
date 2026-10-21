"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { accountCopy } from "@/lib/account-copy";
import { authEntryHref, safeAuthReturn } from "@/lib/navigation/auth-return";
import { getVNextAccessToken, getVNextAuthClient, V_NEXT_SESSION_EXPIRED_EVENT } from "@/lib/vnext-auth-session";

function PendingEntry() {
  const { copyFrom } = useExperienceLocale();
  return <span className="auth-entry-pending" aria-live="polite">{copyFrom(accountCopy, "working")}</span>;
}

function SessionActions() {
  const pathname = usePathname();
  const search = useSearchParams();
  const { copyFrom } = useExperienceLocale();
  const c = (key: "entry" | "login" | "signup") => copyFrom(accountCopy, key);
  const [state, setState] = useState<"pending" | "anonymous" | "authenticated" | "unknown">("pending");
  // Auth routes carry the original intent when users switch entry method.
  const destination = pathname === "/login" || pathname === "/signup" ? safeAuthReturn(search.get("next"))
    : safeAuthReturn(pathname === "/compare" && search.size ? `${pathname}?${search}` : pathname);

  useEffect(() => {
    let disposed = false;
    let version = 0;
    let deferred: ReturnType<typeof setTimeout> | undefined;
    let deadline: ReturnType<typeof setTimeout> | undefined;
    const restore = () => {
      const ownVersion = ++version;
      clearTimeout(deadline);
      deadline = setTimeout(() => { if (!disposed && ownVersion === version) setState("unknown"); }, 12_000);
      void getVNextAccessToken().then(result => {
        if (!disposed && ownVersion === version) {
          clearTimeout(deadline);
          setState(result.status === "authenticated" ? "authenticated" : "anonymous");
        }
      });
    };
    const subscription = getVNextAuthClient()?.auth.onAuthStateChange(event => {
      if (event === "SIGNED_OUT") {
        version++; clearTimeout(deadline); setState("anonymous");
      } else if (["SIGNED_IN", "TOKEN_REFRESHED"].includes(event)) {
        version++; setState("pending");
        clearTimeout(deferred);
        // Never read the SDK while its auth callback holds the session lock.
        deferred = setTimeout(restore, 0);
      }
    }).data.subscription;
    const expired = () => { version++; clearTimeout(deadline); setState("anonymous"); };
    window.addEventListener(V_NEXT_SESSION_EXPIRED_EVENT, expired);
    restore();
    return () => {
      disposed = true; version++; clearTimeout(deadline); clearTimeout(deferred);
      subscription?.unsubscribe(); window.removeEventListener(V_NEXT_SESSION_EXPIRED_EVENT, expired);
    };
  }, []);

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
