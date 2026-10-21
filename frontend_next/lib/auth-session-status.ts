// Shared entry controls depend only on this adapter. The provider SDK is loaded
// for a possible session, or owned by an auth route that publishes its reader.
export type SessionEntryState = "pending" | "anonymous" | "authenticated" | "unknown";
type SessionReader = () => Promise<boolean>;
type StatusEnvironment = {
  hasStoredSession: () => boolean;
  loadSessionReader: () => Promise<SessionReader>;
  subscribeStorage: (listener: () => void) => () => void;
  subscribeExpired: (listener: () => void) => () => void;
  deadlineMs?: number;
};

export const V_NEXT_SESSION_EXPIRED_EVENT = "vnext-session-expired";

export function createSessionStatusAdapter(environment: StatusEnvironment) {
  let reader: SessionReader | undefined;
  const listeners = new Set<() => void>();
  return {
    // Readers validate through the existing session implementation. Neither
    // storage presence nor SDK events are proof of authentication.
    publish(nextReader: SessionReader) {
      reader = nextReader;
      listeners.forEach(listener => listener());
    },
    observe(onChange: (state: SessionEntryState) => void) {
      let disposed = false;
      let version = 0;
      let deferred: ReturnType<typeof setTimeout> | undefined;
      let deadline: ReturnType<typeof setTimeout> | undefined;
      const invalidate = () => { version++; clearTimeout(deferred); clearTimeout(deadline); };
      const restore = () => {
        invalidate();
        const ownVersion = version;
        let possibleSession = !!reader;
        // Inaccessible storage could hide an in-memory or persisted session.
        try { possibleSession ||= environment.hasStoredSession(); } catch { possibleSession = true; }
        if (!possibleSession) { onChange("anonymous"); return; }
        onChange("pending");
        deadline = setTimeout(() => {
          if (!disposed && ownVersion === version) onChange("unknown");
        }, environment.deadlineMs ?? 12_000);
        // Defer SDK calls beyond auth callbacks, which hold its session lock.
        deferred = setTimeout(() => {
          void (async () => {
            try {
              const check = reader ?? await environment.loadSessionReader();
              if (disposed || ownVersion !== version) return;
              const authenticated = await check();
              if (!disposed && ownVersion === version) {
                clearTimeout(deadline);
                onChange(authenticated ? "authenticated" : "anonymous");
              }
            } catch {
              if (!disposed && ownVersion === version) { clearTimeout(deadline); onChange("unknown"); }
            }
          })();
        }, 0);
      };
      const expired = () => { invalidate(); onChange("anonymous"); };
      listeners.add(restore);
      const unsubscribeStorage = environment.subscribeStorage(restore);
      const unsubscribeExpired = environment.subscribeExpired(expired);
      restore();
      return () => {
        disposed = true; invalidate(); listeners.delete(restore);
        unsubscribeStorage(); unsubscribeExpired();
      };
    },
  };
}

export function authSessionStorageKey(url: string | undefined): string | null {
  try { return `sb-${new URL(url ?? "").hostname.split(".")[0]}-auth-token`; } catch { return null; }
}

const browserStatus = createSessionStatusAdapter({
  hasStoredSession: () => {
    const key = authSessionStorageKey(process.env.NEXT_PUBLIC_SUPABASE_URL);
    return key !== null && window.localStorage.getItem(key) !== null;
  },
  loadSessionReader: async () => {
    const auth = await import("./vnext-auth-session");
    return async () => (await auth.getVNextAccessToken()).status === "authenticated";
  },
  subscribeStorage: listener => {
    const key = authSessionStorageKey(process.env.NEXT_PUBLIC_SUPABASE_URL);
    const changed = (event: StorageEvent) => { if (event.key === null || event.key === key) listener(); };
    window.addEventListener("storage", changed);
    return () => window.removeEventListener("storage", changed);
  },
  subscribeExpired: listener => {
    window.addEventListener(V_NEXT_SESSION_EXPIRED_EVENT, listener);
    return () => window.removeEventListener(V_NEXT_SESSION_EXPIRED_EVENT, listener);
  },
});

export const observeAuthSessionStatus = browserStatus.observe;
export const publishAuthSessionStatus = browserStatus.publish;
