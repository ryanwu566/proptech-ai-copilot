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
  new Function('require', 'module', 'exports', output)((name) => {
    if (!name.startsWith('.') && !name.startsWith('@/')) return require(name);
    const target = name.startsWith('@/') ? path.join(root, name.slice(2)) : path.resolve(path.dirname(file), name);
    return load(path.relative(root, fs.existsSync(target) ? target : `${target}.ts`));
  }, module, module.exports);
  return module.exports;
}
test('simulation reuses seven existing semantic stages and its fixture cannot be saved as a production case', () => {
  const { DEMO_CASE, DEMO_STAGES } = load('lib/guided-case-simulation.ts');
  const { TOUR_STEPS } = load('lib/guided-tour.ts');
  assert.deepEqual(DEMO_STAGES.map(s => s.id), TOUR_STEPS.map(s => s.id));
  assert.equal(DEMO_STAGES.length, 7);
  assert.equal(DEMO_CASE.demoId, 'demo:guided-case:v1');
  assert.equal(DEMO_CASE.synthetic, true);
  assert.equal(Object.isFrozen(DEMO_CASE), true);
  assert.equal(DEMO_CASE.risk, 'unknown');
  for (const forbidden of ['caseId', 'coordinates', 'updatedAt', 'data', 'identity', 'provider']) assert.equal(forbidden in DEMO_CASE, false);
});
test('every demo key is localized through the shared catalogue renderer', () => {
  const { DEMO_COPY } = load('lib/guided-case-simulation-copy.ts');
  const { translateCopyCatalogue } = load('lib/copy-catalogue.ts');
  const keys = Object.keys(DEMO_COPY.en);
  for (const locale of ['zh-TW', 'en', 'ja', 'ko']) {
    assert.deepEqual(Object.keys(DEMO_COPY[locale]).sort(), [...keys].sort());
    for (const key of keys) {
      const text = translateCopyCatalogue(locale, DEMO_COPY, key, { amount: 18 });
      assert.ok(text?.trim(), `${locale}:${key}`);
      assert.ok(!text.includes('{{'), `${locale}:${key}`);
      if (locale !== 'en') assert.match(text, locale === 'ko' ? /[가-힣]/ : /[\u3040-\u30ff\u3400-\u9fff]/);
    }
  }
});
