import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync, readdirSync } from "node:fs";
// @ts-expect-error Native TS runner extension.
import { moneyCopy, moneyText } from "./money-copy.ts";

test("every Money label and validation message exists in all four locales", () => {
  for (const locale of ["zh-TW", "en", "ja", "ko"] as const) {
    for (const key of Object.keys(moneyCopy) as (keyof typeof moneyCopy)[]) {
      assert.ok(moneyText(locale, key).trim(), `${locale}: ${key}`);
      assert.doesNotMatch(moneyText(locale, key), /undefined|TODO|TaxOracle|Aegis|credit score|best offer|AI recommendation/i);
    }
  }
  assert.equal(moneyText("en", "title"), "Money");
  assert.equal(moneyText("zh-TW", "cash"), "所需現金");
  assert.match(moneyText("en", "taxProxy"), /price × entered-rate proxy/);
  assert.match(moneyText("en", "taxBoundary"), /repurchase/);
});

test("modern Money has no legacy brand, credit rating, recommendation engine or extra API usage", () => {
  const directory = new URL("../../components/workspace/finance/", import.meta.url);
  const sources = readdirSync(directory).filter(name => name.endsWith(".tsx") || name.endsWith(".ts"))
    .map(name => readFileSync(new URL(name, directory), "utf8")).join("\n");
  assert.doesNotMatch(sources, /TaxOracle|Aegis|credit.score|approval.probability|bestOffer|winner|recommendation|fetch\(/i);
  assert.deepEqual([...sources.matchAll(/api\.(\w+)\(/g)].map(match => match[1]).sort(), ["holdingCostCalculate", "loanCalculate"]);
  const projection = readFileSync(new URL("./money-workflow.ts", import.meta.url), "utf8");
  assert.doesNotMatch(projection, /fetch\(|api\.|https?:|loanCalculate|holdingCostCalculate/);
});
