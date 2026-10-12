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
  const requireLocal = name => {
    if (!name.startsWith('.') && !name.startsWith('@/')) return require(name);
    const target = name.startsWith('@/') ? path.join(root, name.slice(2)) : path.resolve(path.dirname(file), name);
    const resolved = fs.existsSync(target) ? target : `${target}.ts`;
    if (resolved.endsWith('.json')) return JSON.parse(fs.readFileSync(resolved, 'utf8'));
    return load(path.relative(root, resolved));
  };
  new Function('require', 'module', 'exports', output)(requireLocal, module, module.exports);
  return module.exports;
}
const { getJourneyValuationFormInputs, getJourneyValuationInputPatch, journeyValuationInputsMatchContext, getSubmittedJourneyValuationInputs } = load('lib/journey-valuation-inputs.ts');
const { e9Case } = load('lib/workspace/e9-test-fixtures.ts');
const { createClosedLoopJourneyState, updateJourneyProperty } = load('lib/closed-loop-journey.ts');
const { buildJourneySaveCase } = load('lib/journey-case-snapshot.ts');
const { compactCaseData } = load('lib/case-storage.ts');
const { parseSavedCasesDiagnostic } = load('lib/workspace/saved-case-diagnostics.ts');
const { adaptSavedCaseToWorkspace } = load('lib/workspace/legacy-case-adapter.ts');
const { buildValuationRefreshContext } = load('lib/workspace/market-price-refresh.ts');
const availableValuation = JSON.parse(fs.readFileSync(path.resolve(root, '../tests/fixtures/comparable-explanation-result.json'), 'utf8'));
function unknownJourney() {
  const seed = e9Case();
  const context = { ...seed.data.journeyContext.propertyContext };
  delete context.buildingAgeYears; delete context.floor;
  const journey = createClosedLoopJourneyState(context);
  journey.identityAnchor = seed.data.propertyIdentityAnchor;
  return journey;
}
function roundtrip(journey) {
  const row = { ...e9Case(), ...buildJourneySaveCase(journey) };
  const diagnostic = parseSavedCasesDiagnostic(JSON.stringify([row]), value => ({ ...value, data: compactCaseData(value.data) }));
  assert.equal(diagnostic.status, 'ready');
  const saved = diagnostic.cases[0];
  return { saved, refresh: buildValuationRefreshContext(adaptSavedCaseToWorkspace(saved), saved) };
}
test('displaying valuation defaults preserves unknown facts until an explicit edit or submission', () => {
  const journey = unknownJourney();
  const form = getJourneyValuationFormInputs(journey.propertyContext);
  assert.equal(form.building_age_years, 15); assert.equal(form.floor, 8);
  assert.equal(journey.propertyContext.buildingAgeYears, undefined);
  assert.equal(journey.propertyContext.floor, undefined);
  assert.equal(roundtrip(journey).refresh, null);
});
test('editing only age never promotes the untouched floor default into a known fact', () => {
  const journey = updateJourneyProperty(unknownJourney(), getJourneyValuationInputPatch({ building_age_years: 9 }));
  const { saved, refresh } = roundtrip(journey);
  assert.equal(saved.data.inputs.building_age_years, 9);
  assert.equal(saved.data.journeyContext.propertyContext.floor, undefined);
  assert.equal(refresh, null);
});
for (const [age, floor] of [[15, 8], [9, 12], [0, 0]]) test(`explicit ${age}/${floor} submission survives Save/read/adapter/refresh with its accepted property identity`, () => {
  const original = unknownJourney();
  const submitted = { ...getJourneyValuationFormInputs(original.propertyContext), building_age_years: age, floor };
  const journey = updateJourneyProperty(original, getJourneyValuationInputPatch(submitted));
  assert.deepEqual(journey.identityAnchor, original.identityAnchor);
  const { saved, refresh } = roundtrip(journey);
  assert.equal(saved.data.inputs.building_age_years, age); assert.equal(saved.data.inputs.floor, floor);
  assert.ok(refresh); assert.equal(refresh.payload.building_age_years, age); assert.equal(refresh.payload.floor, floor);
});
test('parent echo of submitted inputs preserves the result; a later actual edit invalidates valuation and affordability', () => {
  const submitted = { ...getJourneyValuationFormInputs(unknownJourney().propertyContext), building_age_years: 9, floor: 12 };
  let journey = updateJourneyProperty(unknownJourney(), getJourneyValuationInputPatch(submitted));
  assert.equal(journeyValuationInputsMatchContext(submitted, journey.propertyContext), true);
  journey = { ...journey, valuationResult: availableValuation, valuationStatus: 'available', loanResult: { monthly_payment: 2 }, loanStatus: 'available', priceBasis: 'valuation', activePriceWan: 1000 };
  const echoed = updateJourneyProperty(journey, getJourneyValuationInputPatch(submitted));
  assert.deepEqual(echoed.valuationResult, journey.valuationResult);
  assert.equal(echoed.valuationResult.is_actionable, true);
  const edited = updateJourneyProperty(journey, getJourneyValuationInputPatch({ building_age_years: 10 }));
  assert.equal(edited.valuationResult, undefined); assert.equal(edited.loanResult, undefined); assert.equal(edited.activePriceWan, undefined);
});
test('switching to another property with missing age/floor resets displayed assumptions and preserves its unknown metadata', () => {
  const first = { ...getJourneyValuationFormInputs(unknownJourney().propertyContext), building_age_years: 9, floor: 12 };
  const second = { ...unknownJourney().propertyContext, addressSummary: 'Synthetic second property', road: 'Synthetic second road' };
  assert.equal(journeyValuationInputsMatchContext(first, second), false);
  const nextForm = getJourneyValuationFormInputs(second);
  assert.equal(nextForm.building_age_years, 15); assert.equal(nextForm.floor, 8);
  assert.equal(second.buildingAgeYears, undefined); assert.equal(second.floor, undefined);
});
test('editing an address invalidates prior accepted coordinates and property evidence instead of attaching another property valuation', () => {
  const original = { ...unknownJourney(), valuationResult: availableValuation, valuationStatus: 'available' };
  const edited = updateJourneyProperty(original, getJourneyValuationInputPatch({ address_text: 'Synthetic other address' }));
  assert.notDeepEqual(edited.identityAnchor, original.identityAnchor);
  assert.equal(edited.identityAnchor.coordinates, null);
  assert.equal(edited.valuationResult, undefined); assert.equal(edited.locationResult, undefined);
});
test('cleared or invalid age/floor stays unknown and blocks submission while deliberately typed zero remains valid', () => {
  for (const key of ['building_age_years', 'floor']) for (const value of [undefined, NaN, -1]) {
    const original = updateJourneyProperty(unknownJourney(), getJourneyValuationInputPatch({ building_age_years: 9, floor: 12 }));
    const form = { ...getJourneyValuationFormInputs(original.propertyContext), [key]: value };
    const edited = updateJourneyProperty(original, getJourneyValuationInputPatch({ [key]: value }));
    assert.equal(edited.propertyContext[key === 'floor' ? 'floor' : 'buildingAgeYears'], undefined);
    assert.equal(journeyValuationInputsMatchContext(form, edited.propertyContext), true);
    assert.equal(getSubmittedJourneyValuationInputs(form), null);
    assert.equal(roundtrip(edited).refresh, null);
  }
  const validZero = getSubmittedJourneyValuationInputs({ ...getJourneyValuationFormInputs(unknownJourney().propertyContext), building_age_years: 0, floor: 0 });
  assert.ok(validZero); assert.equal(validZero.building_age_years, 0); assert.equal(validZero.floor, 0);
});
test('equivalent city spelling preserves accepted identity; a different district still invalidates it', () => {
  const original = unknownJourney();
  const alias = original.propertyContext.city.replaceAll('臺', '台');
  const same = updateJourneyProperty(original, getJourneyValuationInputPatch({ city: alias }, original.propertyContext));
  assert.deepEqual(same.identityAnchor, original.identityAnchor);
  assert.equal(journeyValuationInputsMatchContext({ ...getJourneyValuationFormInputs(same.propertyContext), city: alias }, same.propertyContext), true);
  const other = updateJourneyProperty(original, getJourneyValuationInputPatch({ city: alias, district: 'Synthetic other district' }, original.propertyContext));
  assert.equal(other.identityAnchor.coordinates, null);
});
