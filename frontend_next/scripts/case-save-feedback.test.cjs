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
const { getCaseSaveFailureFeedback } = load('lib/case-save-feedback.ts');
const { translateRuntimeCopy } = load('lib/runtime-copy.ts');
const key = storage.SAVED_CASES_STORAGE_KEY;
const failurePatterns = { 'zh-TW': /案件未保存.*儲存/, en: /Case was not saved.*storage/, ja: /保存できません.*保存領域/, ko: /저장되지 않았습니다.*저장소/ };
function completeInput() { const row = e9Case(); delete row.data.financeEvidence; return row; }
async function withStorage(fault, run) {
  const records = fault === 'full' ? Array.from({ length: storage.MAX_SAVED_CASES }, (_, i) => ({ ...completeInput(), id: `case-${i}` })) : [e9Case()];
  const original = JSON.stringify(records);
  const values = new Map([[key, original]]);
  let events = 0;
  const previous = global.window;
  global.window = {
    navigator: fault === 'missing-locks' ? {} : { locks: { request: async (_name, _options, callback) => callback() } },
    localStorage: { getItem: name => { if (fault === 'unavailable') throw new Error('denied'); return values.get(name) ?? null; }, setItem: (name, value) => { if (fault === 'quota') throw new Error('quota'); values.set(name, value); } },
    dispatchEvent: () => { events++; return true; },
  };
  try { await run({ values, original, events: () => events }); }
  finally { if (previous) global.window = previous; else delete global.window; }
}
for (const locale of Object.keys(failurePatterns)) for (const fault of ['quota', 'full', 'unavailable', 'missing-locks']) {
  test(`${locale} complete draft ${fault} failure reports storage failure and preserves the original`, async () => withStorage(fault, async browser => {
    const input = completeInput();
    assert.deepEqual(storage.getDraftSaveMissingFields(input), []);
    assert.equal(await storage.saveCase(input), null);
    assert.equal(browser.values.get(key), browser.original); assert.equal(browser.events(), 0);
    assert.match(getCaseSaveFailureFeedback(input, locale), failurePatterns[locale]);
  }));
}
for (const locale of Object.keys(failurePatterns)) test(`${locale} incomplete draft reports only the genuinely missing case name`, async () => withStorage('quota', async browser => {
  const input = completeInput(); input.title = '';
  assert.deepEqual(storage.getDraftSaveMissingFields(input), ['case_name']);
  assert.equal(await storage.saveCase(input), null);
  assert.equal(getCaseSaveFailureFeedback(input, locale), translateRuntimeCopy(locale, 'case.missing', { items: translateRuntimeCopy(locale, 'case.title') }));
  assert.equal(browser.values.get(key), browser.original); assert.equal(browser.events(), 0);
}));
