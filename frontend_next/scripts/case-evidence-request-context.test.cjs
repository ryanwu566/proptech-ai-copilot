const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');

// Execute the real cards with controlled hooks and a deferred provider boundary.
function harness(filename, api) {
  const slots = []; let cursor = 0; let effects = [];
  const hooks = {
    useState(initial) { const i = cursor++; if (!(i in slots)) slots[i] = typeof initial === 'function' ? initial() : initial; return [slots[i], value => { slots[i] = typeof value === 'function' ? value(slots[i]) : value; }]; },
    useRef(initial) { const i = cursor++; return slots[i] ??= { current: initial }; },
    useEffect(callback, dependencies) { const i = cursor++; if (!slots[i] || dependencies.some((value, j) => value !== slots[i][j])) { slots[i] = dependencies; effects.push(callback); } },
  };
  const module = { exports: {} };
  const source = fs.readFileSync(path.join(__dirname, '..', 'components', filename), 'utf8');
  const compiled = ts.transpileModule(source, { compilerOptions: { target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.CommonJS, jsx: ts.JsxEmit.ReactJSX } }).outputText;
  const requireCard = name => {
    if (name === 'react') return hooks;
    if (name === '@/lib/api') return { api };
    if (name === '@/components/ui') return { Button: () => null, Notice: () => null };
    if (name === '@/components/experience-locale-provider') return { useExperienceLocale: () => ({ copy: key => key }) };
    if (name === '@/lib/commercial/formatters') return { formatDistance: String, formatDuration: String, formatMissing: String };
    if (name === '@/lib/commute-livability-ui') return require('../lib/commute-livability-ui.ts');
    return require(name);
  };
  new Function('require', 'module', 'exports', compiled)(requireCard, module, module.exports);
  const Card = Object.values(module.exports).find(value => typeof value === 'function');
  return props => { cursor = 0; effects = []; const tree = Card(props); effects.forEach(effect => effect()); return tree; };
}
function action(node, name) {
  if (!node) return undefined;
  if (Array.isArray(node)) return node.map(child => action(child, name)).find(Boolean);
  if (node.props?.onClick?.name === name) return node.props.onClick;
  return action(node.props?.children, name);
}
const route = { status: 'resolved', reason_code: 'success', source: 'google_routes', mode: 'transit', origin: { latitude: 25, longitude: 121 }, destination: { address: 'Synthetic office' }, distance_m: 1000, duration_seconds: 300, duration_min: 5, checked_at: '2026-10-11T00:00:00Z', partial: false, fallback: false, message: '', disclaimer: 'Reference only' };

test('starting a route query retains the previous persisted evidence until a response arrives', async () => {
  let resolve; const callbacks = [];
  const render = harness('commute-route-card.tsx', { commuteRoute: () => new Promise(done => { resolve = done; }) });
  const pending = action(render({ originLatitude: 25, originLongitude: 121, initialEvidence: route, onEvidence: value => callbacks.push(value) }), 'lookupRoute')();
  assert.equal(callbacks.length, 0, 'loading must not clear the snapshot and invalidate its own pending response');
  resolve(route); await pending;
  assert.equal(callbacks.length, 1); assert.equal(callbacks[0].status, 'resolved');
});

for (const channel of ['route', 'transit']) test(`${channel} response retains its acquisition callback across a same-input case update`, async () => {
  const resolvers = []; let calls = 0; const original = []; const newer = [];
  const api = { [channel === 'route' ? 'commuteRoute' : 'commuteAddressLookup']: () => { calls++; return new Promise(resolve => resolvers.push(resolve)); } };
  const render = harness(channel === 'route' ? 'commute-route-card.tsx' : 'commute-livability-card.tsx', api);
  const callbackKey = channel === 'route' ? 'onEvidence' : 'onResult';
  const props = channel === 'route' ? { originLatitude: 25, originLongitude: 121, initialEvidence: route } : { address: 'Synthetic public test address' };
  const name = channel === 'route' ? 'lookupRoute' : 'lookupCommute';
  const next = channel === 'route' ? route : { status: 'resolved', source: 'tdx', station_name: 'Synthetic station', line_ids: [], distance_meters: 100, message: '' };
  const pending = action(render({ ...props, [callbackKey]: value => original.push(value) }), name)();
  render({ ...props, [callbackKey]: value => newer.push(value) });
  assert.equal(calls, 1, 'case rerender must not call providers');
  resolvers[0](next); await pending;
  assert.equal(original.filter(Boolean).length, 1);
  assert.equal(newer.length, 0, 'an old response cannot adopt the newer case write expectation');
  const second = action(render({ ...props, [callbackKey]: value => newer.push(value) }), name)();
  resolvers[1](next); await second;
  assert.equal(calls, 2); assert.equal(newer.filter(Boolean).length, 1, 'a new explicit request uses the new case context');
});
