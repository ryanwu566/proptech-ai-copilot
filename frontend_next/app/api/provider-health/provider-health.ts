const MOENV_AQI_URL = "https://data.moenv.gov.tw/api/v2/aqx_p_432";
const TDX_TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token";
const TDX_STATION_URL = "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Station/TRTC";
const DEFAULT_TIMEOUT_MS = 5_000;

type ProviderEnvironment = Readonly<Record<string, string | undefined>>;

type FetchLike = (input: string | URL | Request, init?: RequestInit) => Promise<Response>;

type ProviderHealthOptions = {
  env: ProviderEnvironment;
  fetchImpl: FetchLike;
  timeoutMs?: number;
};

type MoenvHealth = {
  configured: boolean;
  ok: boolean;
  http_status: number | null;
  records_received: number;
  latency_ms: number;
};

type TdxHealth = {
  configured: boolean;
  auth_ok: boolean;
  api_ok: boolean | null;
  http_status: number | null;
  latency_ms: number;
};

export type ProviderHealth = {
  moenv: MoenvHealth;
  tdx: TdxHealth;
};

function elapsedMilliseconds(startedAt: number): number {
  return Math.max(0, Math.round(performance.now() - startedAt));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function isMoenvAqiRecord(value: unknown): value is Record<string, unknown> {
  if (!isRecord(value)) {
    return false;
  }
  return [value.sitename, value.siteid].some(
    (field) => typeof field === "string" && field.trim().length > 0,
  );
}

async function checkMoenv(
  apiKey: string,
  fetchImpl: FetchLike,
  signal: AbortSignal,
): Promise<MoenvHealth> {
  const startedAt = performance.now();
  let httpStatus: number | null = null;

  try {
    const url = new URL(MOENV_AQI_URL);
    url.search = new URLSearchParams({
      format: "json",
      offset: "0",
      limit: "1",
      api_key: apiKey,
    }).toString();
    const response = await fetchImpl(url, { cache: "no-store", signal });
    httpStatus = response.status;
    if (!response.ok) {
      throw new Error("MOENV request failed");
    }

    const payload: unknown = await response.json();
    const records = isRecord(payload) && Array.isArray(payload.records) ? payload.records : [];
    const validRecords = records.filter(isMoenvAqiRecord);
    return {
      configured: true,
      ok: validRecords.length > 0,
      http_status: httpStatus,
      records_received: validRecords.length,
      latency_ms: elapsedMilliseconds(startedAt),
    };
  } catch {
    return {
      configured: true,
      ok: false,
      http_status: httpStatus,
      records_received: 0,
      latency_ms: elapsedMilliseconds(startedAt),
    };
  }
}

async function checkTdx(
  clientId: string,
  clientSecret: string,
  fetchImpl: FetchLike,
  signal: AbortSignal,
): Promise<TdxHealth> {
  const startedAt = performance.now();
  let httpStatus: number | null = null;
  let authOk = false;

  try {
    const tokenResponse = await fetchImpl(TDX_TOKEN_URL, {
      method: "POST",
      headers: new Headers({ "content-type": "application/x-www-form-urlencoded" }),
      body: new URLSearchParams({
        grant_type: "client_credentials",
        client_id: clientId,
        client_secret: clientSecret,
      }),
      cache: "no-store",
      signal,
    });
    httpStatus = tokenResponse.status;
    if (!tokenResponse.ok) {
      throw new Error("TDX authentication failed");
    }

    const tokenPayload: unknown = await tokenResponse.json();
    const accessToken = isRecord(tokenPayload) ? tokenPayload.access_token : null;
    if (typeof accessToken !== "string" || accessToken.trim().length === 0) {
      throw new Error("TDX authentication response was invalid");
    }
    authOk = true;

    const dataUrl = new URL(TDX_STATION_URL);
    dataUrl.search = new URLSearchParams({ "$format": "JSON", "$top": "1" }).toString();
    const dataResponse = await fetchImpl(dataUrl, {
      headers: new Headers({ authorization: `Bearer ${accessToken}` }),
      cache: "no-store",
      signal,
    });
    httpStatus = dataResponse.status;
    if (!dataResponse.ok) {
      return {
        configured: true,
        auth_ok: true,
        api_ok: false,
        http_status: httpStatus,
        latency_ms: elapsedMilliseconds(startedAt),
      };
    }

    const payload: unknown = await dataResponse.json();
    const apiOk = Array.isArray(payload) && payload.some(isRecord);
    return {
      configured: true,
      auth_ok: true,
      api_ok: apiOk,
      http_status: httpStatus,
      latency_ms: elapsedMilliseconds(startedAt),
    };
  } catch {
    return {
      configured: true,
      auth_ok: authOk,
      api_ok: authOk ? false : null,
      http_status: httpStatus,
      latency_ms: elapsedMilliseconds(startedAt),
    };
  }
}

export async function runProviderHealth({
  env,
  fetchImpl,
  timeoutMs = DEFAULT_TIMEOUT_MS,
}: ProviderHealthOptions): Promise<ProviderHealth> {
  const moenvApiKey = env.MOENV_API_KEY?.trim() ?? "";
  const tdxClientId = env.TDX_CLIENT_ID?.trim() ?? "";
  const tdxClientSecret = env.TDX_CLIENT_SECRET?.trim() ?? "";
  const tdxConfigured = Boolean(tdxClientId && tdxClientSecret);

  const moenvPromise: Promise<MoenvHealth> = moenvApiKey
    ? checkMoenv(moenvApiKey, fetchImpl, AbortSignal.timeout(timeoutMs))
    : Promise.resolve({
        configured: false,
        ok: false,
        http_status: null,
        records_received: 0,
        latency_ms: 0,
      });
  const tdxPromise: Promise<TdxHealth> = tdxConfigured
    ? checkTdx(tdxClientId, tdxClientSecret, fetchImpl, AbortSignal.timeout(timeoutMs))
    : Promise.resolve({
        configured: false,
        auth_ok: false,
        api_ok: null,
        http_status: null,
        latency_ms: 0,
      });

  const [moenv, tdx] = await Promise.all([moenvPromise, tdxPromise]);
  return { moenv, tdx };
}
