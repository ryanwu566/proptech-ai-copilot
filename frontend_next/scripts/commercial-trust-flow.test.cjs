const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const root = path.resolve(__dirname, '..');
const cache = new Map();
function load(relative) {
  const file = path.resolve(root, relative);
  if (cache.has(file)) return cache.get(file).exports;
  const module = { exports: {} }; cache.set(file, module);
  const output = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 } }).outputText;
  const requireLocal = (name) => {
    if (!name.startsWith('.') && !name.startsWith('@/')) return require(name);
    const target = name.startsWith('@/') ? path.join(root, name.slice(2)) : path.resolve(path.dirname(file), name);
    const resolved = fs.existsSync(target) ? target : `${target}.ts`;
    if (resolved.endsWith('.json')) return JSON.parse(fs.readFileSync(resolved, 'utf8'));
    return load(path.relative(root, resolved));
  };
  new Function('require', 'module', 'exports', output)(requireLocal, module, module.exports);
  return module.exports;
}
const journey = load('lib/closed-loop-journey.ts');
const { e9Case } = load('lib/workspace/e9-test-fixtures.ts');
const { adaptSavedCaseToWorkspace } = load('lib/workspace/legacy-case-adapter.ts');
const { projectCaseEvidence } = load('lib/workspace/case-evidence.ts');

test('manual calculator input records canonical source without changing asking price through Save/Reopen/Compare/Report', () => {
  const seed = e9Case();
  const loan = { ...seed.data.financeEvidence.loan, property_price_wan: 3000, loan_amount_wan: 2400, down_payment_wan: 600, monthly_payment: 91117, total_payment: 32802120, total_interest: 8802120, sensitivity: [], affordability_level: 'unknown', income_burden_ratio: null, disclaimer: '' };
  let state = journey.createClosedLoopJourneyState({ ...seed.data.journeyContext.propertyContext, askingPriceWan: undefined });
  state.identityAnchor = seed.data.propertyIdentityAnchor;
  state = journey.setJourneyLoanResult(state, loan, () => '2026-10-09T01:00:00.000Z');
  assert.equal(state.propertyContext.askingPriceWan, undefined);
  assert.equal(state.financePriceEvidence.price_twd, 30000000);
  assert.equal(state.financePriceEvidence.source, 'MANUAL_SCENARIO');
  const { buildJourneySaveCase } = load('lib/journey-case-snapshot.ts');
  const { saveCase, readSavedCases } = load('lib/case-storage.ts');
  const values = new Map();
  global.window = { localStorage: { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) }, dispatchEvent: () => {} };
  const saved = saveCase(buildJourneySaveCase(state));
  assert.ok(saved);
  const workspace = adaptSavedCaseToWorkspace(readSavedCases()[0]);
  const evidence = projectCaseEvidence(workspace);
  assert.equal(workspace.assumptions.askingPriceWan, undefined);
  assert.equal(evidence.finance.basis.value, '手動試算情境');
  assert.equal(evidence.finance.price.value, 3000);
  assert.equal(evidence.finance.monthlyPayment.value, 91117);
  assert.equal(workspace.finance.overview.activePriceBasis, 'manual');
  const { buildReportModel, buildComparisonModel } = load('lib/workspace/compare-report-model.ts');
  assert.equal(buildReportModel(evidence).sections.find(s => s.id === 'finance').evidenceSection.rows.find(r => r.id === 'finance-basis').cells[0].value, '手動試算情境');
  const other = projectCaseEvidence(adaptSavedCaseToWorkspace(e9Case('case-b')));
  assert.equal(buildComparisonModel([evidence, other], [evidence.caseId, other.caseId]).sections.find(s => s.id === 'finance').rows.find(r => r.id === 'finance-basis').cells[0].value, '手動試算情境');
  delete global.window;
});

test('matching explicitly selected asking and comparable estimates retain distinct provenance', () => {
  const seed = e9Case();
  const loan = { property_price_wan: 2480 };
  const state = journey.createClosedLoopJourneyState(seed.data.journeyContext.propertyContext);
  assert.equal(journey.setJourneyLoanResult(state, loan).financePriceEvidence.source, 'ASKING_PRICE');
  assert.equal(journey.setJourneyLoanResult({ ...state, priceBasis: 'valuation' }, loan).financePriceEvidence.source, 'COMPARABLE_ESTIMATE');
  assert.equal(journey.setJourneyLoanResult(state, { property_price_wan: 3000 }).financePriceEvidence.source, 'MANUAL_SCENARIO');
});

test('accepted Taiwan addresses strip country, equivalent city spelling and village before road selection', () => {
  const { deriveJourneyRoadFromAcceptedAddress } = load('lib/location-market-journey.ts');
  for (const address of ['台灣臺中市西屯區潮洋里臺灣大道三段100號', 'Taiwan 台中市西屯區潮洋里臺灣大道三段100號', '407 台灣台中市西屯區臺灣大道三段100號']) {
    assert.equal(deriveJourneyRoadFromAcceptedAddress(address, '臺中市', '西屯區', '潮洋里'), '臺灣大道三段');
  }
  assert.equal(deriveJourneyRoadFromAcceptedAddress('臺中市西屯區里仁路100號', '臺中市', '西屯區'), '里仁路');
  assert.equal(deriveJourneyRoadFromAcceptedAddress('臺中市西屯區新村路100號', '臺中市', '西屯區'), '新村路');
});

test('manual mortgage differs from an existing asking price without becoming stale or overwriting it', () => {
  const { buildJourneySaveCase } = load('lib/journey-case-snapshot.ts');
  const { saveCase, readSavedCases } = load('lib/case-storage.ts');
  const seed = e9Case();
  let state = journey.createClosedLoopJourneyState(seed.data.journeyContext.propertyContext);
  state.identityAnchor = seed.data.propertyIdentityAnchor;
  const loan = { property_price_wan: 3000, down_payment_ratio: .2, down_payment_wan: 600, loan_amount_wan: 2400, annual_interest_rate: 2.2, loan_years: 30, grace_period_years: 0, monthly_income_wan: null, monthly_payment: 91117, total_payment: 32802120, total_interest: 8802120, sensitivity: [], income_burden_ratio: null };
  state = journey.setJourneyLoanResult(state, loan, () => '2026-10-09T01:00:00Z');
  const values = new Map();
  global.window = { localStorage: { getItem: k => values.get(k) ?? null, setItem: (k, v) => values.set(k, v) }, dispatchEvent: () => {} };
  saveCase(buildJourneySaveCase(state));
  const saved = readSavedCases()[0];
  const workspace = adaptSavedCaseToWorkspace(saved);
  const evidence = projectCaseEvidence(workspace);
  assert.equal(evidence.price.asking.value, 2480);
  assert.equal(evidence.finance.price.value, 3000);
  assert.equal(evidence.finance.monthlyPayment.value, 91117);
  assert.equal(evidence.finance.basis.value, '手動試算情境');
  saved.data.journeyContext.activePriceWan = 2600;
  assert.equal(adaptSavedCaseToWorkspace(saved).finance.freshness.status, 'stale');
  delete global.window;
});

test('holding calculation preserves its actual area independently of unchanged case area', () => {
  const { captureJourneyFinanceEvidence } = load('lib/workspace/finance-persistence.ts');
  const saved = e9Case(); delete saved.data.financeEvidence;
  saved.data.financePriceEvidence = { price_twd: 30000000, source: 'MANUAL_SCENARIO', calculated_at: saved.updatedAt };
  saved.data.holdingCost = { property_price_wan: 3000, loan_monthly_payment: 0, monthly_total_holding_cost: 2500, annual_total_holding_cost: 30000, income_burden_ratio: null,
    input: { property_price_wan: 3000, area_ping: 25, loan_monthly_payment: 0, monthly_income_wan: null, management_fee_per_ping: 100, repair_reserve_per_ping: 0, annual_home_tax_rate: 0, annual_land_tax_rate: 0, annual_insurance: 0 },
    cost_breakdown: [{ key: 'management', monthly_amount: 2500 }, { key: 'repair_reserve', monthly_amount: 0 }] };
  const snapshot = captureJourneyFinanceEvidence(saved);
  assert.equal(snapshot.assumptions.area_ping, 25);
  assert.equal(snapshot.holding.assumptions.area_ping, 25);
  assert.match(snapshot.case_input_fingerprint, /\|30$/);
  saved.data.financeEvidence = snapshot;
  assert.equal(adaptSavedCaseToWorkspace(saved).finance.freshness.status, 'current');
});

test('malformed source price cannot write a self-inconsistent finance snapshot', () => {
  const { captureJourneyFinanceEvidence } = load('lib/workspace/finance-persistence.ts');
  const seed = e9Case();
  const original = seed.data.financeEvidence; delete seed.data.financeEvidence;
  seed.data.financePriceEvidence = { price_twd: 10000000, source: 'MANUAL_SCENARIO', calculated_at: seed.updatedAt };
  seed.data.loan = { ...original.loan, loan_amount_wan: 1984, monthly_payment: 55111, total_payment: 19840000, total_interest: 0, income_burden_ratio: null, sensitivity: [] };
  assert.equal(captureJourneyFinanceEvidence(seed), null);
});

test('malformed holding input does not throw during Save projection', () => {
  const { captureJourneyFinanceEvidence } = load('lib/workspace/finance-persistence.ts');
  const seed = e9Case(); delete seed.data.financeEvidence;
  seed.data.financePriceEvidence = { price_twd: 30000000, source: 'MANUAL_SCENARIO', calculated_at: seed.updatedAt };
  seed.data.holdingCost = { property_price_wan: 3000, monthly_total_holding_cost: 2500 };
  assert.equal(captureJourneyFinanceEvidence(seed), null);
});

test('guided holding overrides discard a mortgage calculated from another payment assumption', () => {
  const state = journey.createClosedLoopJourneyState({ askingPriceWan: 3000 });
  const calculated = journey.setJourneyLoanResult(state, { property_price_wan: 3000, monthly_payment: 91117 });
  const updated = journey.setJourneyHoldingResult(calculated, { property_price_wan: 3000, input: { loan_monthly_payment: 99999 } });
  assert.equal(updated.loanResult, undefined);
  assert.equal(updated.holdingResult.input.loan_monthly_payment, 99999);
});
