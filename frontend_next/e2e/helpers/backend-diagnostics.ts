/** Test-only error boundaries: never pass credential-bearing API logs to reporters. */
export function connectionErrorCategory(error: unknown): "refused" | "reset" | "timeout" | "other" {
  const message = error instanceof Error ? error.message : "";
  return /ECONNREFUSED/.test(message) ? "refused"
    : /ECONNRESET|socket hang up/i.test(message) ? "reset"
    : /timeout|timed out/i.test(message) ? "timeout" : "other";
}

export async function safeBackendCall<T>(
  operation: "fixture-session" | "forwarded-api" | "direct-api" | "denied-api"
    | "browser-session" | "account-navigation" | "account-reload",
  action: () => Promise<T>,
): Promise<T> {
  try {
    return await action();
  } catch (error) {
    // No raw message, call log, response, headers, or original cause survives.
    throw new Error(`Local acceptance ${operation} failed (${connectionErrorCategory(error)})`);
  }
}
