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

test('active locale resolves tour controls without English or Chinese fallback', () => {
  const { translateRuntimeCopy } = load('lib/runtime-copy.ts');
  const expected = { 'zh-TW': '下一步', en: 'Next', ja: '次へ', ko: '다음' };
  for (const [locale, label] of Object.entries(expected)) assert.equal(translateRuntimeCopy(locale, 'guide.next'), label);
});

test('every supported locale explicitly covers all rendered tour keys and interpolation', () => {
  const { SUPPORTED_LOCALES } = load('lib/experience-i18n.ts');
  const { GUIDED_TOUR_COPY, GUIDED_TOUR_COPY_KEYS } = load('lib/guided-tour-copy.ts');
  const { translateRuntimeCopy, getRuntimeCopyCoverage } = load('lib/runtime-copy.ts');
  for (const locale of SUPPORTED_LOCALES) {
    for (const key of GUIDED_TOUR_COPY_KEYS) {
      assert.ok(GUIDED_TOUR_COPY[locale][key]?.trim(), `${locale}:${key}`);
      const rendered = translateRuntimeCopy(locale, key, { current: 3, total: 7 });
      assert.notEqual(rendered, key);
      assert.ok(!rendered.includes('{{'), `${locale}:${key}`);
      if (locale !== 'en') assert.match(rendered, locale === 'ko' ? /[가-힣]/ : /[\u3040-\u30ff\u3400-\u9fff]/);
    }
    assert.deepEqual(getRuntimeCopyCoverage()[locale].missing, []);
  }
});

test('bounded persistence distinguishes skip and completion, ignores obsolete/malformed records, and handles blocked storage', () => {
  const { readTourStatus, writeTourStatus, TOUR_STORAGE_KEY } = load('lib/guided-tour.ts');
  const values = new Map();
  const storage = { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
  assert.equal(readTourStatus(storage), null);
  writeTourStatus(storage, 'skipped');
  assert.equal(readTourStatus(storage), 'skipped');
  assert.deepEqual(JSON.parse(values.get(TOUR_STORAGE_KEY)), { version: '3', status: 'skipped' });
  writeTourStatus(storage, 'completed');
  assert.equal(readTourStatus(storage), 'completed');
  values.set(TOUR_STORAGE_KEY, '{broken'); assert.equal(readTourStatus(storage), null);
  values.set(TOUR_STORAGE_KEY, JSON.stringify({ version: '2', status: 'completed' })); assert.equal(readTourStatus(storage), null);
  values.set(TOUR_STORAGE_KEY, JSON.stringify({ version: '3', status: 'completed', locale: 'en', prose: 'private' })); assert.equal(readTourStatus(storage), null);
  const blocked = { getItem() { throw Error('denied'); }, setItem() { throw Error('denied'); } };
  assert.equal(readTourStatus(blocked), null);
  assert.doesNotThrow(() => writeTourStatus(blocked, 'completed'));
});

test('semantic steps resolve copy in the new locale without changing step identity or completion', () => {
  const { TOUR_STEPS, readTourStatus, writeTourStatus } = load('lib/guided-tour.ts');
  const { translateRuntimeCopy } = load('lib/runtime-copy.ts');
  const values = new Map();
  const storage = { getItem: (key) => values.get(key) ?? null, setItem: (key, value) => values.set(key, value) };
  writeTourStatus(storage, 'completed');
  const current = TOUR_STEPS.find((step) => step.id === 'locationCommute');
  assert.ok(current);
  for (const locale of ['zh-TW', 'en', 'ja', 'ko']) {
    assert.ok(translateRuntimeCopy(locale, current.heading));
    assert.equal(current.id, 'locationCommute');
    assert.equal(readTourStatus(storage), 'completed');
  }
  assert.equal(new Set(TOUR_STEPS.map((step) => step.id)).size, 7);
});
