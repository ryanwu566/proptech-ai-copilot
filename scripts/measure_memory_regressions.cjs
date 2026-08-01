/* Repeat local browser workflows and report bounded listener/heap observations. */
const path = require("node:path");
const { chromium } = require(require.resolve("@playwright/test", { paths: [path.join(process.cwd(), "node_modules")] }));
const port = Number(process.env.PERF_PORT || 3100);

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
  const page = await context.newPage();
  await page.addInitScript(() => {
    const originalAdd = EventTarget.prototype.addEventListener;
    const originalRemove = EventTarget.prototype.removeEventListener;
    let active = 0;
    EventTarget.prototype.addEventListener = function (...args) { active += 1; return originalAdd.apply(this, args); };
    EventTarget.prototype.removeEventListener = function (...args) { active = Math.max(0, active - 1); return originalRemove.apply(this, args); };
    window.__listenerCount = () => active;
  });
  const observations = [];
  for (let iteration = 0; iteration < 5; iteration += 1) {
    await page.goto(`http://127.0.0.1:${port}/`, { waitUntil: "domcontentloaded", timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(250);
    await page.goto(`http://127.0.0.1:${port}/cases/synthetic`, { waitUntil: "domcontentloaded", timeout: 10000 }).catch(() => {});
    await page.waitForTimeout(250);
    observations.push(await page.evaluate(() => ({
      listeners: window.__listenerCount ? window.__listenerCount() : null,
      heap_used_bytes: performance.memory ? performance.memory.usedJSHeapSize : null,
      utterances: window.speechSynthesis ? window.speechSynthesis.pending + window.speechSynthesis.speaking : null,
    })));
  }
  await context.close();
  await browser.close();
  const listenerValues = observations.map((item) => item.listeners).filter((item) => item !== null);
  const heapValues = observations.map((item) => item.heap_used_bytes).filter((item) => item !== null);
  const result = { status: "pass", repetitions: 5, observations, listener_growth_initial_hydration: listenerValues.length > 1 ? listenerValues[1] - listenerValues[0] : null, listener_growth_after_warmup: listenerValues.length > 2 ? listenerValues.at(-1) - listenerValues[1] : null, heap_growth_bytes: heapValues.length > 1 ? heapValues.at(-1) - heapValues[0] : null, speech_queue_growth: observations.length > 1 ? observations.at(-1).utterances - observations[0].utterances : null };
  process.stdout.write(`${JSON.stringify(result)}\n`);
}

main().catch(() => { process.stderr.write("memory regression measurement failed\n"); process.exitCode = 1; });
