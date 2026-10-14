"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { useExperienceLocale } from "@/components/experience-locale-provider";
import { accountCopy } from "@/lib/account-copy";
import { restoreConsumerAccount, type AccountState } from "@/lib/account-client";
import { getVNextAuthClient, requestPasswordResetVNext, signInVNext, signOutVNext, signUpVNext, validConsumerEmail, V_NEXT_SESSION_EXPIRED_EVENT } from "@/lib/vnext-auth-session";
import styles from "./consumer-account.module.css";

type MessageKey = keyof typeof accountCopy.en;
export function ConsumerAccount({ mode }: { mode: "login" | "signup" | "account" }) {
  const { copyFrom, formatDate } = useExperienceLocale();
  const c = (key: MessageKey) => copyFrom(accountCopy, key);
  const router = useRouter();
  const [account, setAccount] = useState<AccountState | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<{ key: MessageKey; error: boolean } | null>(null);
  const version = useRef(0);
  const statusRef = useRef<HTMLParagraphElement>(null);
  const configured = account?.status !== "configuration_unavailable";

  useEffect(() => {
    let disposed = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function load() {
      const ownVersion = ++version.current;
      const result = await restoreConsumerAccount();
      if (disposed || ownVersion !== version.current) return;
      setAccount(result);
      if (result.status === "ready" && mode !== "account") router.replace("/account");
    }
    void load();
    const subscription = getVNextAuthClient()?.auth.onAuthStateChange((event) => {
      if (event === "SIGNED_OUT") {
        version.current += 1;
        setAccount({ status: "missing_session" });
      } else if (["SIGNED_IN", "TOKEN_REFRESHED"].includes(event)) {
        version.current += 1;
        setAccount(null);
        // Defer SDK reads until the auth callback releases its session lock.
        clearTimeout(timer);
        timer = setTimeout(() => { void load(); }, 0);
      }
    }).data.subscription;
    const expired = () => {
      version.current += 1;
      setAccount({ status: "expired_session" });
    };
    window.addEventListener(V_NEXT_SESSION_EXPIRED_EVENT, expired);
    return () => {
      disposed = true; version.current += 1; clearTimeout(timer);
      subscription?.unsubscribe(); window.removeEventListener(V_NEXT_SESSION_EXPIRED_EVENT, expired);
    };
  }, [mode, router]);

  useEffect(() => { if (message) statusRef.current?.focus(); }, [message]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    setMessage(null);
    if (!validConsumerEmail(email) || password.length < (mode === "signup" ? 8 : 1) || password.length > 1024) {
      setMessage({ key: "validation", error: true }); return;
    }
    setBusy(true);
    try {
      const result = mode === "signup" ? await signUpVNext(email, password)
        : { status: await signInVNext(email.trim(), password) ? "authenticated" : getVNextAuthClient() ? "provider_error" : "configuration_unavailable" };
      setPassword("");
      if (result.status === "authenticated") router.replace("/account");
      else setMessage({ key: result.status === "configuration_unavailable" ? "unavailable" : result.status === "validation_error" ? "validation" : result.status === "provider_error" ? "provider" : "accepted", error: ["configuration_unavailable", "validation_error", "provider_error"].includes(result.status) });
    } finally { setBusy(false); }
  }

  async function reset() {
    if (busy) return;
    if (!validConsumerEmail(email)) { setMessage({ key: "resetValidation", error: true }); return; }
    setBusy(true); setPassword(""); setMessage(null);
    try {
      const result = await requestPasswordResetVNext(email);
      setMessage({ key: result.status === "request_accepted" ? "resetAccepted" : result.status === "configuration_unavailable" ? "unavailable" : "provider", error: result.status !== "request_accepted" });
    } finally { setBusy(false); }
  }

  async function logout() {
    if (busy) return;
    setBusy(true); version.current += 1;
    setAccount({ status: "missing_session" });
    try { const cleared = await signOutVNext(); setMessage({ key: cleared ? "signedOut" : "provider", error: !cleared }); }
    finally { setBusy(false); }
  }

  async function retry() {
    setBusy(true); const ownVersion = ++version.current;
    try { const value = await restoreConsumerAccount(); if (version.current === ownVersion) setAccount(value); }
    finally { setBusy(false); }
  }

  const stateKey: MessageKey | null = account?.status === "expired_session" ? "expired"
    : account?.status === "configuration_unavailable" || account?.status === "account_unavailable" ? "unavailable"
    : mode === "account" && account?.status === "missing_session" ? "missing" : null;

  return <main id="main-content" className={styles.page}>
    <section className={styles.intro}>
      <span className={styles.eyebrow}>PropTech Copilot</span>
      <h1 className="text-page-title">{c(mode)}</h1>
      <p className={styles.lead}>{c("intro")}</p>
      {mode !== "account" && <p>{c(mode === "login" ? "loginNote" : "signupNote")}</p>}
      <Link className={styles.explore} href="/">{c("explore")} <span aria-hidden="true">→</span></Link>
    </section>
    <div className={styles.content}>
      <section className={styles.card} aria-label={c(mode)} aria-busy={busy || account === null}>
        {stateKey && <p role={account?.status === "configuration_unavailable" || account?.status === "account_unavailable" ? "alert" : "status"} className={styles.notice}>{c(stateKey)}</p>}
        {message && <p id="account-message" ref={statusRef} tabIndex={-1} role={message.error ? "alert" : "status"} className={styles.notice}>{c(message.key)}</p>}
        {mode !== "account" ? <>
          <form className={styles.form} onSubmit={submit} noValidate>
            <label htmlFor="consumer-email">{c("email")}</label>
            <input id="consumer-email" name="email" type="email" autoComplete="email" autoCapitalize="none" spellCheck={false} maxLength={254} required value={email} disabled={busy || !configured} aria-invalid={message?.error && ["validation", "resetValidation"].includes(message.key) || undefined} aria-describedby={message?.error ? "account-message" : undefined} onChange={e => setEmail(e.target.value)} />
            <label htmlFor="consumer-password">{c("password")}</label>
            <input id="consumer-password" name="password" type="password" autoComplete={mode === "signup" ? "new-password" : "current-password"} maxLength={1024} required value={password} disabled={busy || !configured} aria-invalid={message?.key === "validation" || undefined} aria-describedby={message?.error ? "account-message" : mode === "signup" ? "password-hint" : undefined} onChange={e => setPassword(e.target.value)} />
            {mode === "signup" && <p id="password-hint" className={styles.hint}>{c("passwordHint")}</p>}
            <button className={styles.primary} type="submit" disabled={busy || !configured}>{busy ? c("working") : c(mode === "login" ? "submitLogin" : "submitSignup")}</button>
          </form>
          {mode === "login" && <button className={styles.textButton} type="button" disabled={busy || !configured} onClick={() => void reset()}>{c("reset")}</button>}
          <p className={styles.hint}>{c("privacy")}</p>
          <p>{c(mode === "login" ? "noAccount" : "hasAccount")} <Link href={mode === "login" ? "/signup" : "/login"}>{c(mode === "login" ? "signup" : "login")}</Link></p>
        </> : account?.status === "ready" ? <>
          {account.email && <p className={styles.email}>{account.email}</p>}
          <dl className={styles.facts}>
            <div><dt>{c("status")}</dt><dd data-testid="account-status" className={styles.badge}>{c(account.account.status)}</dd></div>
            <div><dt>{c("memberSince")}</dt><dd>{formatDate(account.account.created_at)}</dd></div>
          </dl>
          {account.account.status === "suspended" && <p role="alert" className={styles.notice}>{c("suspensionNote")}</p>}
          <button className={styles.secondary} type="button" disabled={busy} onClick={() => void logout()}>{busy ? c("working") : c("signout")}</button>
        </> : <div className={styles.actions}>
          {account === null ? <p role="status">{c("working")}</p> : <>
            <Link className={styles.primary} href="/login">{c("login")}</Link>
            {account.status === "account_unavailable" && <button className={styles.secondary} type="button" disabled={busy} onClick={() => void retry()}>{c("retry")}</button>}
            {account.status === "account_unavailable" && <button className={styles.textButton} type="button" disabled={busy} onClick={() => void logout()}>{c("signout")}</button>}
          </>}
        </div>}
      </section>
      <section className={styles.local}>
        <h2 className="text-section-title">{c("localTitle")}</h2><p>{c("localNote")}</p><Link href="/cases">{c("cases")} <span aria-hidden="true">→</span></Link>
      </section>
    </div>
  </main>;
}
