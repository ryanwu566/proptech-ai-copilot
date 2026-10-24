import { expect, type Page } from "@playwright/test";

/** Supporting routes are behind the workspace's native Tools disclosure. */
export async function openWorkspaceTools(page: Page) {
  const tools = page.getByTestId("workspace-tools");
  await expect(tools).toBeVisible();
  if (!(await tools.evaluate((node) => (node as HTMLDetailsElement).open))) await tools.locator("summary").click();
  await expect(tools).toHaveAttribute("open", "");
}

// Legacy single-tool pages are no longer listed in public navigation; they keep their
// direct /?tool= URLs. Labels are the former menu names in every locale.
const LEGACY_TOOLS: [RegExp, string][] = [
  [/房價估算|Valuation|価格評価|가격 평가|価格/, "房價估算"],
  [/Market Insight/, "Market Insight Lite"],
  [/Map Insight/, "Map Insight Lite"],
  [/Terrain Risk/, "Terrain Risk"],
  [/TaxOracle/, "TaxOracle"],
  [/Aegis-Credit/, "Aegis-Credit Lite"],
];

/** Open a retained legacy tool in place, exactly as its former menu button did (no reload). */
export async function openMethod(page: Page, name: string | RegExp) {
  const label = typeof name === "string" ? name : name.source;
  const tool = LEGACY_TOOLS.find(([pattern]) => pattern.test(label))?.[1];
  if (!tool) throw new Error(`No retained legacy tool URL for ${label}`);
  // The App Router syncs useSearchParams by replacing history.pushState once it mounts; wait for
  // that hook (not focus, which may rest on <body> after a control unmounts) and a rendered page.
  await expect(page.locator("[data-page-heading]").first()).toBeAttached();
  await expect.poll(() => page.evaluate(() => !/\[native code\]/.test(Function.prototype.toString.call(window.history.pushState)))).toBe(true);
  if (new URL(page.url()).searchParams.get("tool") === tool) return;
  await page.evaluate((value) => {
    (window as unknown as { previousHeading?: Element | null }).previousHeading = document.querySelector("[data-page-heading]");
    const url = new URL(window.location.href);
    url.searchParams.set("tool", value);
    window.history.pushState(null, "", `${url.pathname}${url.search}`);
  }, tool);
  await expect.poll(() => new URL(page.url()).searchParams.get("tool")).toBe(tool);
  // The shell moves focus to the newly rendered page heading once the tool page mounts.
  await expect.poll(() => page.evaluate(() => {
    const active = document.activeElement;
    return Boolean(active?.hasAttribute("data-page-heading")) && active !== (window as unknown as { previousHeading?: Element | null }).previousHeading;
  })).toBe(true);
}

/** Official transaction search is an explicit optional entry from E10 Home. */
export async function openPropertyEntry(page: Page) {
  await page.locator(".commercial-home").getByRole("button", {
    name: /還沒有特定物件？搜尋官方成交資料|No property yet\? Search official transactions|物件が未定ですか？公式取引を検索|물건이 없나요\? 공식 거래 검색/,
  }).click();
  await expect(page.locator("#journey-stage-property")).toBeVisible();
}

const LEGACY_LOCATION_STEP = /^(位置與資料證據|Location and evidence|位置と根拠|위치와 근거) · /;

/**
 * Home Start now creates a local case. The legacy guided journey stays reachable
 * through its explicit deep link; this enters it and types the address in its
 * own Location step, exactly as a legacy user would.
 */
export async function openLegacyJourneyWithAddress(page: Page, address: string, url = "/?workflow=property") {
  await page.goto(url);
  await expect(page.locator("#journey-stage-property")).toBeVisible();
  const steps = page.locator("#guided-property-journey nav").first();
  const disclosure = steps.locator("details");
  if (await disclosure.isVisible() && !(await disclosure.evaluate((node) => (node as HTMLDetailsElement).open))) await disclosure.locator("summary").click();
  await steps.getByRole("button", { name: LEGACY_LOCATION_STEP }).filter({ visible: true }).click();
  await expect(page.locator("#journey-stage-location")).toBeVisible();
  const input = page.locator("#location-insight-calculator").getByRole("textbox").first();
  await input.fill(address);
  await expect(input).toHaveValue(address);
}

export const RETIRED_DEMO_REFERENCE = "Retired in competition cleanup v1: the TaxOracle demo reference and its closed-pilot entry are no longer linked from the public product; the implementation is retained.";

/** The former Methods "Demo reference" entry no longer exists; specs using it are skipped. */
export async function openDemoReference(_page: Page): Promise<never> {
  throw new Error(RETIRED_DEMO_REFERENCE);
}
