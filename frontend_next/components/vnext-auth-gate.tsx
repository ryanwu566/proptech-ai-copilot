"use client";

import { useEffect, useState, type FormEvent, type ReactNode } from "react";
import {
  V_NEXT_SESSION_EXPIRED_EVENT, getVNextAccessToken, getVNextAuthClient, signInVNext, signOutVNext,
} from "@/lib/vnext-auth-session";
import styles from "./vnext-auth-gate.module.css";

type AuthState = "loading" | "signed_out" | "signing_in" | "authenticated" | "expired" | "configuration_error";

export function VNextAuthGate({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>("loading");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loginFailed, setLoginFailed] = useState(false);

  useEffect(() => {
    let active = true;
    let checkNumber = 0;
    const expired = () => { if (active) setState("expired"); };
    window.addEventListener(V_NEXT_SESSION_EXPIRED_EVENT, expired);
    const checkSession = async () => {
      const currentCheck = ++checkNumber;
      const result = await getVNextAccessToken();
      if (!active || currentCheck !== checkNumber) return;
      setState(result.status === "authenticated" ? "authenticated"
        : result.status === "configuration_error" ? "configuration_error"
          : result.status === "expired_session" ? "expired" : "signed_out");
    };
    const subscription = getVNextAuthClient()?.auth.onAuthStateChange((event) => {
      if (!active) return;
      if (event === "SIGNED_OUT") {
        checkNumber += 1;
        setState((current) => current === "expired" ? current : "signed_out");
      }
      if (event === "SIGNED_IN") {
        checkNumber += 1;
        setState("loading");
        // Supabase recommends deferring client calls from auth-state callbacks.
        window.setTimeout(() => { if (active) void checkSession(); }, 0);
      }
    });
    void checkSession();
    return () => {
      active = false;
      window.removeEventListener(V_NEXT_SESSION_EXPIRED_EVENT, expired);
      subscription?.data.subscription.unsubscribe();
    };
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (state === "signing_in") return;
    setState("signing_in");
    setLoginFailed(false);
    const signedIn = await signInVNext(email.trim(), password);
    setPassword("");
    if (signedIn) setState("authenticated");
    else { setState("signed_out"); setLoginFailed(true); }
  }

  async function logout() {
    setState("loading");
    await signOutVNext();
    setPassword("");
    setState("signed_out");
  }

  if (state === "authenticated") return <>
    <div className={styles.accountBar}><span>已登入，可查看授權工作空間中的房產。</span><button type="button" onClick={() => void logout()}>登出</button></div>
    {children}
  </>;

  return <main className={styles.page}>
    <section className={styles.card} aria-labelledby="identity-signin-title">
      <p className={styles.eyebrow}>PROPERTY IDENTITY</p>
      <h1 id="identity-signin-title">登入後查看房產識別</h1>
      <p>使用已開通的帳號登入，再查看您有權存取的工作空間與房產。</p>
      {state === "loading" && <p role="status">正在確認登入狀態…</p>}
      {state === "configuration_error" && <p role="alert">登入服務尚未設定，請稍後再試。</p>}
      {state === "expired" && <p role="alert">登入已逾期，請重新登入。</p>}
      {loginFailed && <p role="alert">登入失敗，請確認帳號資訊後再試。</p>}
      {(state === "signed_out" || state === "expired" || state === "signing_in") && <form onSubmit={(event) => void submit(event)}>
        <label>電子郵件<input type="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="username" required disabled={state === "signing_in"} /></label>
        <label>密碼<input type="password" name="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="current-password" required disabled={state === "signing_in"} /></label>
        <button type="submit" disabled={state === "signing_in"}>{state === "signing_in" ? "登入中…" : "登入"}</button>
      </form>}
    </section>
  </main>;
}
