import assert from "node:assert/strict";
import test from "node:test";

// @ts-expect-error Node's native TypeScript test runner requires the source extension.
import { monthlyPaymentTwdToWan, monthlyPaymentWanToTwd, optionalNonNegativeNumber } from "./monetary-units.ts";

test("manual 3.0376 wan monthly payment becomes 30,376 TWD at the API boundary", () => {
  assert.equal(monthlyPaymentWanToTwd(3.0376), 30_376);
});

test("loan-generated 30,376 TWD prefill survives the display round trip without double conversion", () => {
  const displayedWan = monthlyPaymentTwdToWan(30_376);

  assert.equal(displayedWan, 3.0376);
  assert.equal(monthlyPaymentWanToTwd(displayedWan), 30_376);
});

test("invalid monetary input is rejected instead of becoming zero", () => {
  assert.equal(monthlyPaymentWanToTwd(Number.NaN), null);
  assert.equal(monthlyPaymentTwdToWan(Number.POSITIVE_INFINITY), null);
});

test("optional monetary inputs preserve missing separately from legitimate zero", () => {
  assert.equal(optionalNonNegativeNumber(undefined), null);
  assert.equal(optionalNonNegativeNumber(null), null);
  assert.equal(optionalNonNegativeNumber(""), null);
  assert.equal(optionalNonNegativeNumber(0), 0);
  assert.equal(optionalNonNegativeNumber("0"), 0);
});
