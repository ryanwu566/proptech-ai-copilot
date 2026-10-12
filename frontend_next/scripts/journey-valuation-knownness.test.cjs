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
const { e9Case } = load('lib/workspace/e9-test-fixtures.ts');
const { createClosedLoopJourneyState } = load('lib/closed-loop-journey.ts');
const { buildJourneySaveCase } = load('lib/journey-case-snapshot.ts');
const { compactCaseData } = load('lib/case-storage.ts');
const { parseSavedCasesDiagnostic } = load('lib/workspace/saved-case-diagnostics.ts');
const { adaptSavedCaseToWorkspace } = load('lib/workspace/legacy-case-adapter.ts');
const { buildValuationRefreshContext } = load('lib/workspace/market-price-refresh.ts');
function knownContext() {
  return { ...e9Case().data.journeyContext.propertyContext, buildingType: '住宅大樓', areaPing: 30, buildingAgeYears: 8, floor: 12 };
}
function roundtrip(context) {
  const seed = e9Case();
  const journey = createClosedLoopJourneyState(context);
  journey.identityAnchor = seed.data.propertyIdentityAnchor;
  const row = { ...seed, ...buildJourneySaveCase(journey) };
  const diagnostic = parseSavedCasesDiagnostic(JSON.stringify([row]), value => ({ ...value, data: compactCaseData(value.data) }));
  assert.equal(diagnostic.status, 'ready');
  return diagnostic.cases[0];
}
test('missing age or floor retains unknown journey metadata and blocks refresh after serialize/read/adapter', () => {
  for (const field of ['buildingAgeYears', 'floor']) {
    const context = knownContext();
    delete context[field];
    const saved = roundtrip(context);
    assert.equal(saved.data.journeyContext.propertyContext[field], undefined);
    assert.equal(buildValuationRefreshContext(adaptSavedCaseToWorkspace(saved), saved), null);
  }
});
test('explicit zero age and floor remain known and usable after the same roundtrip', () => {
  const saved = roundtrip({ ...knownContext(), buildingAgeYears: 0, floor: 0 });
  const refresh = buildValuationRefreshContext(adaptSavedCaseToWorkspace(saved), saved);
  assert.ok(refresh);
  assert.equal(refresh.payload.building_age_years, 0);
  assert.equal(refresh.payload.floor, 0);
});

test('legacy positive age and floor remain usable when journey metadata predates those fields', () => {
  const saved = e9Case();
  saved.data.inputs.building_age_years = 15;
  saved.data.inputs.floor = 8;
  const refresh = buildValuationRefreshContext(adaptSavedCaseToWorkspace(saved), saved);
  assert.ok(refresh);
  assert.equal(refresh.payload.building_age_years, 15);
  assert.equal(refresh.payload.floor, 8);
});

test('missing journey facts never promote legacy zero defaults to known values', () => {
  for (const field of ['building_age_years', 'floor']) {
    const saved = e9Case();
    saved.data.inputs[field] = 0;
    assert.equal(buildValuationRefreshContext(adaptSavedCaseToWorkspace(saved), saved), null);
  }
});

test('explicit journey facts take precedence over conflicting legacy inputs', () => {
  const saved = e9Case();
  Object.assign(saved.data.journeyContext.propertyContext, { buildingAgeYears: 0, floor: 0 });
  const refresh = buildValuationRefreshContext(adaptSavedCaseToWorkspace(saved), saved);
  assert.ok(refresh);
  assert.equal(refresh.payload.building_age_years, 0);
  assert.equal(refresh.payload.floor, 0);
  saved.data.journeyContext.propertyContext.floor = -1;
  assert.equal(buildValuationRefreshContext(adaptSavedCaseToWorkspace(saved), saved), null);
});
