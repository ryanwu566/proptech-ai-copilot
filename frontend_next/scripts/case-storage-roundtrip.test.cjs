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
const storage = load('lib/case-storage.ts');
const { e9Case } = load('lib/workspace/e9-test-fixtures.ts');
const { createBrowserCaseRepository } = load('lib/workspace/case-repository.ts');
const { projectCaseEvidence } = load('lib/workspace/case-evidence.ts');
const { buildReportModel, buildComparisonModel } = load('lib/workspace/compare-report-model.ts');
const { buildMarketRefreshContext, canCommitMarketPriceResponse } = load('lib/workspace/market-price-refresh.ts');
const { SAVED_CASES_STORAGE_KEY: key } = storage;
const { captureNearbyFacilities } = load('lib/workspace/nearby-facilities.ts');
const { buildAddressDraftCase } = load('lib/workspace/case-draft.ts');
const { interpretLocationResolution, buildConfirmedLocationAnchor } = load('lib/workspace/location-confirmation.ts');
const pendingAddress = '臺北市信義區市府路1號';
const pendingDraft = (id = 'pending-a') => buildAddressDraftCase(pendingAddress, { id, now: '2026-10-21T00:00:00Z' });
const pendingCandidate = () => interpretLocationResolution({ status: 'resolved', source: 'google', confidence: 'high', latitude: 25.0375, longitude: 121.5637, formatted_address: pendingAddress }, pendingAddress).candidate;

test('pending candidate roundtrip stays separate from identity, isolates cases and promotes only on confirmation', async () => browser(JSON.stringify([pendingDraft(), pendingDraft('pending-b')]), async values => {
  const repo = createBrowserCaseRepository();
  const version = repo.getCase('pending-a').storageVersion;
  assert.equal((await storage.savePendingLocationCandidate('pending-a', { ...pendingCandidate(), rawProviderPayload: 'must not persist' }, version)).status, 'saved');
  const reopened = repo.getCase('pending-a');
  assert.deepEqual(reopened.pendingLocationCandidate, pendingCandidate());
  assert.equal(reopened.identity.state, 'unconfirmed');
  assert.equal(reopened.identity.anchor, null);
  assert.equal(reopened.location.property.coordinates, null);
  assert.equal(repo.getCase('pending-b').pendingLocationCandidate, undefined);
  assert.equal(values.get(key).includes('rawProviderPayload'), false);
  assert.equal(buildMarketRefreshContext(reopened, storage.readSavedCases()[0]), null);
  const before = values.get(key);
  const evidence = projectCaseEvidence(reopened);
  assert.equal(buildReportModel(evidence).sections.length, 0);
  buildComparisonModel([evidence, projectCaseEvidence(repo.getCase('pending-b'))], ['pending-a', 'pending-b']);
  assert.equal(values.get(key), before);
  const anchor = buildConfirmedLocationAnchor(pendingCandidate(), { now: () => '2026-10-21T01:00:00Z', idFactory: () => '11111111-2222-4333-8444-555555555555' });
  assert.equal((await storage.confirmSavedCaseIdentity('pending-a', anchor, reopened.storageVersion)).status, 'confirmed');
  assert.equal(repo.getCase('pending-a').identity.state, 'confirmed');
  assert.equal(repo.getCase('pending-a').pendingLocationCandidate, undefined);
  assert.equal(storage.readSavedCases()[0].data.pendingLocationCandidate, undefined);
}));

test('pending restore rejects changed address, foreign case, malformed candidate and existing identity', async () => browser(JSON.stringify([pendingDraft(), e9Case()]), async values => {
  const repo = createBrowserCaseRepository();
  const version = repo.getCase('pending-a').storageVersion;
  assert.equal((await storage.savePendingLocationCandidate('pending-a', pendingCandidate(), version)).status, 'saved');
  const rows = JSON.parse(values.get(key));
  const original = structuredClone(rows[0]);
  for (const alter of [
    row => { row.data.journeyContext.propertyContext.addressSummary = '另一個地址'; },
    row => { row.inputSummary.road = '新地址'; },
    row => { row.id = 'foreign-case'; },
    row => { row.data.pendingLocationCandidate.candidate.latitude = 35; },
    row => { row.data.pendingLocationCandidate.state = 'confirmed'; },
    row => { row.data.propertyIdentityAnchor = e9Case().data.propertyIdentityAnchor; },
  ]) {
    const changed = structuredClone(original); alter(changed);
    values.set(key, JSON.stringify([changed]));
    assert.ok(repo.getCase(changed.id), 'invalid pending data must not destroy the case');
    assert.equal(repo.getCase(changed.id).pendingLocationCandidate, undefined);
  }
  values.set(key, JSON.stringify(rows));
  assert.equal((await storage.savePendingLocationCandidate('pending-a', pendingCandidate(), version)).status, 'blocked');
  assert.equal((await storage.savePendingLocationCandidate('case-a', pendingCandidate(), repo.getCase('case-a').storageVersion)).status, 'blocked');
}));

test('pending write failure preserves the case and typed address', async () => browser(JSON.stringify([pendingDraft()]), async values => {
  const before = values.get(key);
  assert.equal((await storage.savePendingLocationCandidate('pending-a', pendingCandidate(), createBrowserCaseRepository().getCase('pending-a').storageVersion)).status, 'blocked');
  assert.equal(values.get(key), before);
}, true));

const { api } = load('lib/api.ts');
const { acquireCaseLocation } = load('lib/workspace/location-acquisition.ts');
const incidentAddress = '新北市新莊區中正路191號';
const googleResult = formatted => ({ status: 'resolved', source: 'google', confidence: 'high', latitude: 25.0359, longitude: 121.4326, county: '新北市', district: formatted.includes('樹林區') ? '樹林區' : '新莊區', formatted_address: formatted });
async function withResolver(resolve, run) {
  const original = api.locationResolve;
  let calls = 0;
  api.locationResolve = (address, signal) => { calls++; return resolve(address, signal); };
  try { return await run(() => calls); } finally { api.locationResolve = original; }
}

test('strict resolver result is the only thing persisted as pending, and reads never resolve again', async () => browser(JSON.stringify([buildAddressDraftCase(incidentAddress, { id: 'incident', now: '2026-10-21T00:00:00Z' })]), async values => withResolver(async () => googleResult('238台灣新北市樹林區金寮里中正路191號'), async calls => {
  const before = values.get(key);
  assert.deepEqual(await acquireCaseLocation('incident', incidentAddress), { kind: 'blocked', reason: 'invalid' });
  assert.equal(values.get(key), before, 'a contradicted district must never be stored as a pending candidate');
  api.locationResolve = async () => googleResult('242台灣新北市新莊區中正路191號');
  const accepted = await acquireCaseLocation('incident', incidentAddress);
  assert.equal(accepted.kind, 'candidate');
  const repo = createBrowserCaseRepository();
  for (let i = 0; i < 5; i++) {
    const reopened = repo.getCase('incident');
    assert.deepEqual(reopened.pendingLocationCandidate, accepted.candidate);
    assert.equal(reopened.identity.state, 'unconfirmed');
    assert.equal(reopened.identity.anchor, null);
    projectCaseEvidence(reopened);
  }
  assert.equal(calls(), 1, 'reopen/read paths make zero resolver calls');
})));

test('incompatible pending record from an older resolver contract fails closed without losing the case', async () => browser(JSON.stringify([buildAddressDraftCase(incidentAddress, { id: 'legacy', now: '2026-10-21T00:00:00Z' })]), async values => {
  const valid = interpretLocationResolution(googleResult('新北市新莊區中正路191號'), incidentAddress).candidate;
  assert.equal((await storage.savePendingLocationCandidate('legacy', valid, createBrowserCaseRepository().getCase('legacy').storageVersion)).status, 'saved');
  const rows = JSON.parse(values.get(key));
  Object.assign(rows[0].data.pendingLocationCandidate.candidate, { interpretedAddress: '238台灣新北市樹林區金寮里中正路191號', district: '樹林區' });
  values.set(key, JSON.stringify(rows));
  const reopened = createBrowserCaseRepository().getCase('legacy');
  assert.ok(reopened);
  assert.equal(reopened.pendingLocationCandidate, undefined);
  assert.equal(reopened.identity.anchor, null);
  assert.equal(storage.readSavedCases()[0].data.pendingLocationCandidate, undefined);
  assert.equal((await storage.savePendingLocationCandidate('legacy', { ...valid, interpretedAddress: '238台灣新北市樹林區金寮里中正路191號', district: '樹林區' }, reopened.storageVersion)).status, 'blocked');
}));

test('timeout and provider/capacity failures store nothing; explicit retry replaces pending only with a fresh valid result', async (t) => browser(JSON.stringify([pendingDraft()]), async values => withResolver(async () => { throw Object.assign(new Error('busy'), { status: 503 }); }, async calls => {
  const before = values.get(key);
  assert.deepEqual(await acquireCaseLocation('pending-a', pendingAddress), { kind: 'blocked', reason: 'provider_unavailable' });
  api.locationResolve = async () => { throw Object.assign(new Error('rate'), { status: 429 }); };
  assert.deepEqual(await acquireCaseLocation('pending-a', pendingAddress), { kind: 'blocked', reason: 'capacity_unavailable' });
  assert.equal(values.get(key), before);
  t.mock.timers.enable({ apis: ['setTimeout'] });
  let transport;
  api.locationResolve = (_address, signal) => { transport = signal; return new Promise(() => {}); };
  const hung = acquireCaseLocation('pending-a', pendingAddress);
  await Promise.resolve();
  t.mock.timers.tick(10_000);
  assert.deepEqual(await hung, { kind: 'blocked', reason: 'unavailable' });
  assert.equal(transport.aborted, true);
  t.mock.timers.reset();
  assert.equal(values.get(key), before, 'a timeout must not persist a fake candidate');
  api.locationResolve = async () => ({ status: 'resolved', source: 'google', confidence: 'high', latitude: 25.0375, longitude: 121.5637, formatted_address: pendingAddress });
  const first = await acquireCaseLocation('pending-a', pendingAddress);
  assert.equal(first.kind, 'candidate');
  api.locationResolve = async () => { throw Object.assign(new Error('busy'), { status: 503 }); };
  assert.equal((await acquireCaseLocation('pending-a', pendingAddress)).kind, 'blocked');
  assert.deepEqual(createBrowserCaseRepository().getCase('pending-a').pendingLocationCandidate, first.candidate, 'a failed retry keeps the earlier unconfirmed candidate');
  api.locationResolve = async () => ({ status: 'resolved', source: 'tgos', confidence: 'high', latitude: 25.0376, longitude: 121.5638, formatted_address: pendingAddress });
  const fresh = await acquireCaseLocation('pending-a', pendingAddress);
  assert.equal(fresh.kind, 'candidate');
  assert.deepEqual(createBrowserCaseRepository().getCase('pending-a').pendingLocationCandidate, fresh.candidate);
  assert.equal(calls(), 1);
})));
function nearby() {
  const origin = { lat: 24.16525, lng: 120.64555 };
  return captureNearbyFacilities({ center: origin, radius_m: 800, source: 'google_places', categories: [{ category: 'park', places: [{ place_id: 'park', name: 'Local park', ...origin }] }] }, origin);
}

test('nearby acquisition persists bounded details across snapshot save, reopen, report and compare reads', async () => browser(JSON.stringify([e9Case()]), async values => {
  const repo = createBrowserCaseRepository();
  const workspace = repo.getCase('case-a');
  const row = storage.readSavedCases()[0];
  const evidence = nearby();
  assert.equal(await storage.updateSavedCaseLocationEvidence(row.id, { nearbyFacilities: evidence }, { ...expectation(row), snapshotVersion: workspace.storageVersion }), true);
  assert.deepEqual(repo.getCase(row.id).location.nearbyFacilities, evidence);
  assert.equal((await repo.saveSnapshot(repo.getCase(row.id))).status, 'saved');
  const reopened = repo.getCase(row.id);
  assert.deepEqual(reopened.location.nearbyFacilities, evidence);
  const before = values.get(key);
  const projected = projectCaseEvidence(reopened);
  buildReportModel(projected);
  buildComparisonModel([projected], [reopened.caseId]);
  assert.equal(values.get(key), before);
}));

test('nearby evidence rejects mismatched origin and failed storage without erasing prior evidence', async () => {
  const row = e9Case();
  row.data.nearbyFacilities = nearby();
  const original = JSON.stringify([row]);
  await browser(original, async values => {
    const foreign = nearby(); foreign.origin.lat += 0.1;
    assert.equal(await storage.updateSavedCaseLocationEvidence(row.id, { nearbyFacilities: foreign }, expectation(row)), false);
    assert.equal(values.get(key), original);
  });
  await browser(original, async values => {
    assert.equal(await storage.updateSavedCaseLocationEvidence(row.id, { nearbyFacilities: nearby() }, expectation(row)), false);
    assert.equal(values.get(key), original);
  }, true);
});
function input() {
  const row = e9Case();
  delete row.data.financeEvidence;
  return row;
}
async function browser(raw, run, failWrite = false) {
  const values = new Map(raw === undefined ? [] : [[key, raw]]);
  const previous = global.window;
  global.window = { navigator: { locks: memoryLocks() }, localStorage: { getItem: k => values.get(k) ?? null, setItem: (k, v) => { if (failWrite) throw new Error('quota'); values.set(k, v); }, removeItem: k => values.delete(k) }, dispatchEvent: () => true };
  try { return await run(values); } finally { if (previous) global.window = previous; else delete global.window; }
}

// Only the browser test double supplies this shim; production requires Web Locks.
function memoryLocks() {
  let tail = Promise.resolve();
  return { request: (name, options, callback) => {
    assert.equal(name, key);
    assert.equal(options.mode, 'exclusive');
    const result = tail.then(() => callback({}));
    tail = result.catch(() => {});
    return result;
  } };
}

function expectation(row) {
  const anchor = row.data.propertyIdentityAnchor;
  return { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates: anchor.coordinates };
}

function writeEvidence(channel, row, expected) {
  if (channel === 'market') return storage.updateSavedCaseMarketEvidence(row.id, { ...row.data.marketInsight, summary: 'older response' }, expected, () => true);
  if (channel === 'risk') return storage.updateSavedCaseRiskEvidence(row.id, row.data.terrainReference, expected, () => true);
  if (channel === 'location') return storage.updateSavedCaseLocationEvidence(row.id, { commuteRoute: row.data.commuteRoute }, expected, () => true);
  if (channel === 'finance') return storage.updateSavedCaseFinanceEvidence(row.id, row.data.financeEvidence, expected, () => true);
  return storage.updateSavedCaseValuationEvidence(row.id, JSON.parse(fs.readFileSync(path.join(root, '../tests/fixtures/comparable-explanation-result.json'), 'utf8')), expected, () => true);
}

for (const channel of ['market', 'valuation', 'risk', 'location', 'finance']) {
  test(`${channel} rejects a competing same-case write queued ahead of its response`, async () => browser(JSON.stringify([e9Case()]), async values => {
    const row = storage.readSavedCases()[0];
    let release; let events = 0;
    global.window.dispatchEvent = () => { events++; return true; };
    const held = new Promise(resolve => { release = resolve; });
    const blocker = global.window.navigator.locks.request(key, { mode: 'exclusive' }, () => held);
    await Promise.resolve();
    const newer = storage.updateSavedCaseMarketEvidence(row.id, { ...row.data.marketInsight, summary: 'newer evidence' }, expectation(row));
    const older = writeEvidence(channel, row, expectation(row));
    release(); await blocker;
    assert.equal(await newer, true);
    const newerRaw = values.get(key);
    assert.equal(await older, false);
    assert.equal(values.get(key), newerRaw);
    assert.equal(storage.readSavedCases()[0].data.marketInsight.summary, 'newer evidence');
    assert.equal(events, 2, 'only the successful write publishes its existing generic and detail events');
  }));

  test(`${channel} rejects an acquisition captured before a same-millisecond snapshot change`, async () => browser(JSON.stringify([e9Case()]), async values => {
    const row = storage.readSavedCases()[0];
    const expected = { ...expectation(row), snapshotVersion: JSON.stringify(row) };
    const newer = JSON.parse(values.get(key));
    newer[0].data.marketInsight.summary = 'newer same-millisecond evidence';
    values.set(key, JSON.stringify(newer));
    const newerRaw = values.get(key); let events = 0;
    global.window.dispatchEvent = () => { events++; return true; };
    assert.equal(await writeEvidence(channel, row, expected), false);
    assert.equal(values.get(key), newerRaw);
    assert.equal(events, 0);
  }));

  test(`${channel} still accepts an unchanged case snapshot`, async () => browser(JSON.stringify([e9Case()]), async () => {
    const row = storage.readSavedCases()[0];
    assert.equal(await writeEvidence(channel, row, { ...expectation(row), snapshotVersion: JSON.stringify(row) }), true);
  }));
}

test('Market request captures the stored snapshot separately from its input fingerprint', async () => browser(JSON.stringify([e9Case()]), async () => {
  const row = storage.readSavedCases()[0];
  const repository = createBrowserCaseRepository();
  const before = buildMarketRefreshContext(repository.getCase(row.id), row);
  assert.equal(before.identity.snapshotVersion, JSON.stringify(row));
  assert.equal(repository.getCase(row.id).storageVersion, JSON.stringify(row));
  assert.equal(await storage.updateSavedCaseMarketEvidence(row.id, { ...row.data.marketInsight, summary: 'newer evidence' }, before.identity), true);
  const afterRow = storage.readSavedCases()[0];
  const after = buildMarketRefreshContext(repository.getCase(row.id), afterRow);
  assert.equal(canCommitMarketPriceResponse(after, before), true, 'successful persistence must not self-invalidate request inputs');
  assert.notEqual(after.identity.snapshotVersion, before.identity.snapshotVersion);
  assert.equal(await storage.updateSavedCaseMarketEvidence(row.id, { ...row.data.marketInsight, summary: 'older response' }, before.identity), false);
}));

for (const action of ['snapshot', 'checklist']) test(`${action} refuses same-timestamp changed storage from its original workspace`, async () => browser(JSON.stringify([e9Case()]), async values => {
  const repository = createBrowserCaseRepository(); const workspace = repository.getCase('case-a');
  const newer = JSON.parse(values.get(key)); newer[0].title = 'Newer case title';
  values.set(key, JSON.stringify(newer)); const newerRaw = values.get(key);
  const result = action === 'snapshot' ? await repository.saveSnapshot(workspace) : await repository.saveChecklist(workspace, workspace.checklistReview);
  assert.equal(result.status, 'blocked'); assert.equal(result.reason, 'revision_mismatch');
  assert.equal(values.get(key), newerRaw);
}));

test('an unrelated case write does not invalidate the target case snapshot', async () => browser(JSON.stringify([e9Case(), e9Case('case-b')]), async () => {
  const [a, b] = storage.readSavedCases();
  const expected = { ...expectation(a), snapshotVersion: JSON.stringify(a) };
  assert.equal(await storage.updateSavedCaseMarketEvidence(b.id, { ...b.data.marketInsight, summary: 'case B newer' }, expectation(b)), true);
  assert.equal(await writeEvidence('market', a, expected), true);
  assert.equal(storage.readSavedCases().find(row => row.id === b.id).data.marketInsight.summary, 'case B newer');
}));

test('serialized saves preserve a second tab mutation started after the final storage read', async () => {
  const previous = global.window;
  const values = new Map([[key, JSON.stringify([e9Case()])]]);
  let reads = 0;
  let second;
  const firstInput = input(); firstInput.title = 'First tab';
  const secondInput = input(); secondInput.title = 'Second tab';
  global.window = {
    navigator: { locks: memoryLocks() },
    localStorage: {
      getItem: k => {
        const captured = values.get(k) ?? null;
        if (k === key && ++reads === 2) second = storage.saveCase(secondInput);
        return captured;
      },
      setItem: (k, value) => values.set(k, value),
    },
    dispatchEvent: () => true,
  };
  try {
    const firstSaved = await storage.saveCase(firstInput);
    const secondSaved = await second;
    assert.ok(firstSaved && secondSaved);
    assert.deepEqual(new Set(storage.readSavedCases().map(row => row.title)), new Set(['案件 A', 'First tab', 'Second tab']));
  } finally { if (previous) global.window = previous; else delete global.window; }
});

test('mutation fails closed without Web Locks and publishes no success event', async () => browser(undefined, async values => {
  delete global.window.navigator;
  let events = 0;
  global.window.dispatchEvent = () => { events++; return true; };
  assert.equal(await storage.saveCase(input()), null);
  assert.equal(values.get(key), undefined);
  assert.equal(events, 0);
}));

test('missing or denied locks preserve existing cases for every mutation without publishing success', async () => {
  for (const availability of ['missing', 'denied']) await browser(JSON.stringify([e9Case()]), async values => {
    const row = e9Case(); const anchor = row.data.propertyIdentityAnchor;
    const expected = { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates: anchor.coordinates };
    const repository = createBrowserCaseRepository(); const workspace = repository.getCase(row.id);
    const original = values.get(key); let events = 0;
    global.window.dispatchEvent = () => { events++; return true; };
    global.window.navigator = availability === 'missing' ? {} : { locks: { request: async () => { throw new Error('lock unavailable'); } } };
    assert.equal(await storage.saveCase(input()), null);
    assert.equal((await repository.saveSnapshot(workspace)).status, 'blocked');
    assert.equal(await storage.deleteSavedCase(row.id), false);
    assert.equal(await storage.clearSavedCases(), false);
    assert.equal(await storage.updateSavedCaseMarketEvidence(row.id, row.data.marketInsight, expected), false);
    assert.equal(await storage.updateSavedCaseFinanceEvidence(row.id, row.data.financeEvidence, expected), false);
    assert.equal(await storage.updateSavedCaseLocationEvidence(row.id, { commuteRoute: row.data.commuteRoute }, expected), false);
    assert.equal(await storage.updateSavedCaseRiskEvidence(row.id, row.data.terrainReference, expected), false);
    assert.equal(await storage.updateSavedCaseValuationEvidence(row.id, {}, expected), false);
    assert.equal(values.get(key), original);
    assert.equal(events, 0);
  });
});

for (const channel of ['market', 'valuation', 'risk', 'location', 'finance']) {
  test(`cancelled ${channel} response waiting for the storage lock cannot replace frozen evidence`, async () => browser(JSON.stringify([e9Case()]), async values => {
    const row = e9Case(); const anchor = row.data.propertyIdentityAnchor;
    const expected = { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates: anchor.coordinates };
    const original = values.get(key); let events = 0; let accept = true; let release;
    global.window.dispatchEvent = () => { events++; return true; };
    const held = new Promise(resolve => { release = resolve; });
    const blocker = global.window.navigator.locks.request(key, { mode: 'exclusive' }, () => held);
    await Promise.resolve();
    const guard = () => accept;
    const result = channel === 'market'
      ? storage.updateSavedCaseMarketEvidence(row.id, { ...row.data.marketInsight, summary: 'cancelled response' }, expected, guard)
      : channel === 'risk'
        ? storage.updateSavedCaseRiskEvidence(row.id, row.data.terrainReference, expected, guard)
        : channel === 'location'
          ? storage.updateSavedCaseLocationEvidence(row.id, { commuteRoute: row.data.commuteRoute }, expected, guard)
          : channel === 'finance'
            ? storage.updateSavedCaseFinanceEvidence(row.id, row.data.financeEvidence, expected, guard)
            : storage.updateSavedCaseValuationEvidence(row.id, JSON.parse(fs.readFileSync(path.join(root, '../tests/fixtures/comparable-explanation-result.json'), 'utf8')), expected, guard);
    accept = false; release(); await blocker;
    assert.equal(await result, false);
    assert.equal(values.get(key), original);
    assert.equal(events, 0);
  }));
}
test('two created snapshots have stable isolated identities across serialized read, compare and report', async () => await browser(undefined, async () => {
  const a = await storage.saveCase(input());
  const second = input(); second.title = 'Case B'; second.inputSummary.road = '臺灣大道三段200號';
  second.data.propertyIdentityAnchor = e9Case('case-b').data.propertyIdentityAnchor;
  second.data.journeyContext = e9Case('case-b').data.journeyContext;
  second.data.journeyContext.priceBasis = 'manual'; second.data.journeyContext.activePriceWan = 3200; second.data.journeyContext.manualPriceWan = 3200;
  const b = await storage.saveCase(second);
  assert.ok(a && b); assert.notEqual(a.id, b.id);
  const repository = createBrowserCaseRepository();
  assert.equal(repository.readDiagnostic().status, 'ready');
  assert.deepEqual(new Set(repository.listCases().map(c => c.caseId)), new Set([a.id, b.id]));
  const ea = projectCaseEvidence(repository.getCase(a.id)); const eb = projectCaseEvidence(repository.getCase(b.id));
  assert.equal(repository.getCase(a.id).assumptions.activePriceWan, 2480);
  assert.equal(repository.getCase(b.id).assumptions.manualPriceWan, 3200);
  assert.ok(buildComparisonModel([ea, eb], [a.id, b.id]).sections.length);
  assert.ok(buildReportModel(ea).sections.length); assert.ok(buildReportModel(eb).sections.length);
}));
test('saving alongside quarantined records preserves every original invalid and unsupported row', async () => {
  const invalid = { id: 'broken-case', version: 99, privateValue: 'preserve-original' };
  await browser(JSON.stringify([e9Case(), invalid]), async values => {
    assert.ok(await storage.saveCase(input()));
    assert.equal(storage.readSavedCasesDiagnostic().cases.length, 2);
    assert.equal(storage.readSavedCasesDiagnostic().status, 'partial');
    assert.deepEqual(JSON.parse(values.get(key)).find(row => row.id === invalid.id), invalid);
  });
});
test('saving alongside duplicate IDs preserves both conflicting records without assigning replacement IDs', async () => {
  const a = e9Case(); const conflict = { ...a, title: 'Conflicting snapshot' };
  await browser(JSON.stringify([a, conflict]), async values => {
    assert.ok(await storage.saveCase(input()));
    assert.equal(storage.readSavedCasesDiagnostic().cases.length, 1);
    assert.deepEqual(JSON.parse(values.get(key)).filter(row => row.id === a.id), [a, conflict]);
    assert.equal(storage.readSavedCasesDiagnostic().issues[0].reason, 'duplicate_id');
  });
});
test('valid snapshot updates work alongside corrupt unrelated records and preserve those records', async () => {
  const invalid = { id: 'unsupported', version: 42 };
  await browser(JSON.stringify([e9Case(), invalid]), async values => {
    const repository = createBrowserCaseRepository();
    assert.equal((await repository.saveSnapshot(repository.getCase('case-a'))).status, 'saved');
    assert.deepEqual(JSON.parse(values.get(key)).find(row => row.id === invalid.id), invalid);
  });
});
test('deleting a valid case preserves quarantined unrelated records', async () => {
  const invalid = { id: 'unsupported', version: 42 };
  await browser(JSON.stringify([e9Case(), invalid]), async values => {
    await storage.deleteSavedCase('case-a'); assert.deepEqual(JSON.parse(values.get(key)), [invalid]);
  });
});
test('parse corruption blocks Save without overwriting the partial storage write', async () => await browser('[{"id":', async values => {
  assert.equal(await storage.saveCase(input()), null); assert.equal(values.get(key), '[{"id":');
}));
test('storage quota failure cannot report a successful Save', async () => await browser(JSON.stringify([e9Case()]), async values => {
  assert.equal(await storage.saveCase(input()), null); assert.equal(JSON.parse(values.get(key)).length, 1);
}, true));
test('storage quota failure returns a blocked snapshot update and preserves the original', async () => await browser(JSON.stringify([e9Case()]), async values => {
  const repository = createBrowserCaseRepository(); const original = values.get(key);
  assert.equal((await repository.saveSnapshot(repository.getCase('case-a'))).status, 'blocked');
  assert.equal(values.get(key), original);
}, true));
test('full storage refuses a new case without silently removing the oldest case', async () => {
  const rows = Array.from({ length: 10 }, (_, i) => e9Case(`case-${i}`));
  await browser(JSON.stringify(rows), async values => {
    assert.equal(await storage.saveCase(input()), null); assert.deepEqual(JSON.parse(values.get(key)), rows);
  });
});
test('serializer output must be readable before Save can report success', async () => await browser(undefined, async values => {
  const draft = input(); draft.progress = 101;
  assert.equal(await storage.saveCase(draft), null); assert.equal(values.get(key), undefined);
}));
test('same property and title with distinct scenario IDs are independent cases, not duplicate identity', async () => await browser(undefined, async () => {
  const a = await storage.saveCase(input()); const b = await storage.saveCase(input());
  assert.ok(a && b); assert.notEqual(a.id, b.id);
  assert.equal(storage.readSavedCasesDiagnostic().status, 'ready');
  assert.equal(storage.readSavedCasesDiagnostic().cases.length, 2);
}));
test('creating from finance bound to another saved case is rejected without rebinding or silently dropping its provenance', async () => await browser(undefined, async values => {
  assert.equal(await storage.saveCase(e9Case()), null);
  assert.equal(values.get(key), undefined);
}));
test('old identity-free saved cases remain usable without synthesizing official verification', async () => {
  const old = input(); delete old.data.propertyIdentityAnchor; delete old.data.journeyContext; delete old.data.terrainReference;
  await browser(JSON.stringify([old]), async () => {
    const repository = createBrowserCaseRepository();
    assert.equal(repository.readDiagnostic().status, 'ready');
    assert.equal(repository.getCase(old.id).identity.state, 'unconfirmed');
    assert.equal(repository.getCase(old.id).risk, null);
  });
});
test('unavailable browser storage cannot claim Save success', async () => {
  const previous = global.window;
  global.window = { navigator: { locks: memoryLocks() }, get localStorage() { throw new Error('storage-disabled'); } };
  try { assert.equal(await storage.saveCase(input()), null); assert.equal(storage.readSavedCasesDiagnostic().status, 'storage_unavailable'); }
  finally { if (previous) global.window = previous; else delete global.window; }
});
test('evidence updates return failure on quota exhaustion without publishing an updated case', async () => await browser(JSON.stringify([e9Case()]), async values => {
  const row = e9Case(); const anchor = row.data.propertyIdentityAnchor;
  const expected = { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates: anchor.coordinates };
  const original = values.get(key);
  assert.equal(await storage.updateSavedCaseMarketEvidence(row.id, row.data.marketInsight, expected), false);
  assert.equal(await storage.updateSavedCaseFinanceEvidence(row.id, row.data.financeEvidence, expected), false);
  assert.equal(await storage.updateSavedCaseLocationEvidence(row.id, { commuteRoute: row.data.commuteRoute }, expected), false);
  assert.equal(await storage.updateSavedCaseRiskEvidence(row.id, row.data.terrainReference, expected), false);
  assert.equal(values.get(key), original);
}, true));
for (const operation of ['create', 'snapshot', 'market', 'delete']) {
  test(`a newer cross-tab storage write blocks stale ${operation} without losing the other case`, async () => await browser(JSON.stringify([e9Case()]), async values => {
    const row = e9Case(); const anchor = row.data.propertyIdentityAnchor;
    const expected = { journeyAnchorId: anchor.journey_anchor_id, normalizedAddress: anchor.normalized_address, coordinates: anchor.coordinates };
    const workspace = createBrowserCaseRepository().getCase(row.id);
    const newer = JSON.stringify([row, e9Case('case-b')]);
    let reads = 0;
    global.window.localStorage.getItem = k => {
      if (k === key && ++reads === 2) values.set(key, newer);
      return values.get(k) ?? null;
    };
    if (operation === 'create') assert.equal(await storage.saveCase(input()), null);
    if (operation === 'snapshot') assert.equal((await createBrowserCaseRepository().saveSnapshot(workspace)).status, 'blocked');
    if (operation === 'market') assert.equal(await storage.updateSavedCaseMarketEvidence(row.id, row.data.marketInsight, { ...expected, snapshotVersion: workspace.storageVersion }), false);
    if (operation === 'delete') assert.equal(await storage.deleteSavedCase(row.id), false);
    assert.equal(values.get(key), newer);
  }));
}
