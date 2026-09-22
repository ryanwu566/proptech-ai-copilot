import assert from "node:assert/strict";
import test from "node:test";

import { runProviderHealth } from "../app/api/provider-health/provider-health.ts";

const env = {
  MOENV_API_KEY: "test-moenv-key",
  TDX_CLIENT_ID: "test-client-id",
  TDX_CLIENT_SECRET: "test-client-secret",
};

test("reports successful MOENV and existing TDX MRT provider checks without exposing credentials", async () => {
  const calls: Array<{ url: string; init: RequestInit | undefined }> = [];
  const fetchImpl = async (input: string | URL | Request, init?: RequestInit) => {
    const url = String(input);
    calls.push({ url, init });

    if (url.startsWith("https://data.moenv.gov.tw/api/v2/aqx_p_432")) {
      return Response.json({ records: [{ sitename: "sample" }] });
    }
    if (url.includes("openid-connect/token")) {
      return Response.json({ access_token: "test-access-token" });
    }
    return Response.json([{ StationID: "sample-station" }]);
  };

  const result = await runProviderHealth({ env, fetchImpl });

  assert.deepEqual(result.moenv.configured, true);
  assert.deepEqual(result.moenv.ok, true);
  assert.deepEqual(result.moenv.http_status, 200);
  assert.deepEqual(result.moenv.records_received, 1);
  assert.deepEqual(result.tdx.configured, true);
  assert.deepEqual(result.tdx.auth_ok, true);
  assert.deepEqual(result.tdx.api_ok, true);
  assert.deepEqual(result.tdx.http_status, 200);
  assert.equal(calls.length, 3);

  const moenvUrl = new URL(calls[0].url);
  assert.equal(moenvUrl.searchParams.get("format"), "json");
  assert.equal(moenvUrl.searchParams.get("offset"), "0");
  assert.equal(moenvUrl.searchParams.get("limit"), "1");
  assert.equal(moenvUrl.searchParams.get("api_key"), env.MOENV_API_KEY);

  assert.equal(calls[1].init?.method, "POST");
  assert.equal(calls[1].init?.headers instanceof Headers, true);
  assert.equal((calls[1].init?.headers as Headers).get("content-type"), "application/x-www-form-urlencoded");
  assert.equal(String(calls[1].init?.body), "grant_type=client_credentials&client_id=test-client-id&client_secret=test-client-secret");

  const tdxUrl = new URL(calls[2].url);
  assert.equal(tdxUrl.origin + tdxUrl.pathname, "https://tdx.transportdata.tw/api/basic/v2/Rail/Metro/Station/TRTC");
  assert.equal(tdxUrl.searchParams.get("$format"), "JSON");
  assert.equal(tdxUrl.searchParams.get("$top"), "1");
  assert.equal((calls[2].init?.headers as Headers).get("authorization"), "Bearer test-access-token");

  const serialized = JSON.stringify(result);
  assert.equal(serialized.includes(env.MOENV_API_KEY), false);
  assert.equal(serialized.includes(env.TDX_CLIENT_ID), false);
  assert.equal(serialized.includes(env.TDX_CLIENT_SECRET), false);
  assert.equal(serialized.includes("test-access-token"), false);
});

test("does not call providers when required environment variables are absent", async () => {
  let callCount = 0;
  const result = await runProviderHealth({
    env: {},
    fetchImpl: async () => {
      callCount += 1;
      throw new Error("must not be called");
    },
  });

  assert.equal(callCount, 0);
  assert.deepEqual(result, {
    moenv: {
      configured: false,
      ok: false,
      http_status: null,
      records_received: 0,
      latency_ms: 0,
    },
    tdx: {
      configured: false,
      auth_ok: false,
      api_ok: null,
      http_status: null,
      latency_ms: 0,
    },
  });
});

test("isolates provider failures and does not retry failed requests", async () => {
  const calls: string[] = [];
  const fetchImpl = async (input: string | URL | Request) => {
    const url = String(input);
    calls.push(url);
    if (url.includes("data.moenv.gov.tw")) {
      throw new Error("provider unavailable with sensitive diagnostics");
    }
    if (url.includes("openid-connect/token")) {
      return Response.json({ access_token: "test-access-token" });
    }
    return Response.json([{ StationID: "sample-station" }]);
  };

  const result = await runProviderHealth({ env, fetchImpl });

  assert.deepEqual(result.moenv.ok, false);
  assert.deepEqual(result.moenv.http_status, null);
  assert.deepEqual(result.tdx.auth_ok, true);
  assert.deepEqual(result.tdx.api_ok, true);
  assert.equal(calls.filter((url) => url.includes("data.moenv.gov.tw")).length, 1);
  assert.equal(calls.length, 3);
  assert.equal(JSON.stringify(result).includes("sensitive diagnostics"), false);
});

test("rejects HTTP 200 responses that do not contain usable provider records", async () => {
  const fetchImpl = async (input: string | URL | Request) => {
    const url = String(input);
    if (url.includes("data.moenv.gov.tw")) {
      return Response.json({ records: [{}] });
    }
    if (url.includes("openid-connect/token")) {
      return Response.json({ access_token: "test-access-token" });
    }
    return Response.json([]);
  };

  const result = await runProviderHealth({ env, fetchImpl });

  assert.equal(result.moenv.ok, false);
  assert.equal(result.moenv.records_received, 0);
  assert.equal(result.tdx.auth_ok, true);
  assert.equal(result.tdx.api_ok, false);
});

test("aborts each provider after its timeout budget without retrying", async () => {
  let callCount = 0;
  const fetchImpl = (_input: string | URL | Request, init?: RequestInit) =>
    new Promise<Response>((_resolve, reject) => {
      callCount += 1;
      init?.signal?.addEventListener("abort", () => reject(init.signal?.reason), { once: true });
    });

  const started = performance.now();
  const result = await runProviderHealth({ env, fetchImpl, timeoutMs: 10 });
  const elapsed = performance.now() - started;

  assert.equal(result.moenv.ok, false);
  assert.equal(result.tdx.auth_ok, false);
  assert.equal(result.tdx.api_ok, null);
  assert.equal(callCount, 2);
  assert.ok(elapsed < 500, `expected prompt timeout, got ${elapsed}ms`);
});

test("keeps successful TDX authentication distinct from a failed data request", async () => {
  const fetchImpl = async (input: string | URL | Request) => {
    const url = String(input);
    if (url.includes("data.moenv.gov.tw")) {
      return Response.json({ records: [{ sitename: "sample" }] });
    }
    if (url.includes("openid-connect/token")) {
      return Response.json({ access_token: "test-access-token" });
    }
    throw new Error("TDX data request failed");
  };

  const result = await runProviderHealth({ env, fetchImpl });

  assert.equal(result.tdx.auth_ok, true);
  assert.equal(result.tdx.api_ok, false);
  assert.equal(JSON.stringify(result).includes("TDX data request failed"), false);
});
