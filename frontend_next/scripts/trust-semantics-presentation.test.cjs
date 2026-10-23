const assert = require('node:assert/strict');
const test = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const ts = require('typescript');
const React = require('react');
const { renderToStaticMarkup } = require('react-dom/server');

const root = path.resolve(__dirname, '..');
const cache = new Map();
let locale = 'zh-TW';
let activeWorkspace;
// Render the actual presentation with a locale context and no browser effects.
// Domain evidence selection, citations, copy and date formatting remain real.
function load(relative) {
  const file = path.resolve(root, relative);
  if (cache.has(file)) return cache.get(file).exports;
  const module = { exports: {} }; cache.set(file, module);
  const output = ts.transpileModule(fs.readFileSync(file, 'utf8'), {
    fileName: file,
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true },
  }).outputText;
  const requireLocal = (name) => {
    if (name.endsWith('.css')) return {};
    if (name === '../workspace-provider') return {};
    if (name === '@/components/workspace/workspace-provider') return { useWorkspace: () => activeWorkspace };
    if (name === '@/lib/case-storage') return { readSavedCases: () => [e9Case()] };
    if (name === '@/lib/api') return {};
    if (['./risk-evidence-map', '@/components/map/explicit-map', '@/components/satellite-evidence'].includes(name)) return {
      RiskEvidenceMap: () => null, ExplicitMap: () => null, SatelliteEvidence: () => null,
    };
    if (name === '@/components/experience-locale-provider') return { useExperienceLocale: () => ({
      locale, formatDate: value => load('lib/experience-i18n.ts').formatExperienceDate(value, locale),
    }) };
    if (!name.startsWith('.') && !name.startsWith('@/')) return require(name);
    const target = name.startsWith('@/') ? path.join(root, name.slice(2)) : path.resolve(path.dirname(file), name);
    const resolved = [target, `${target}.ts`, `${target}.tsx`].find(candidate => fs.existsSync(candidate));
    assert.ok(resolved, `Cannot resolve ${name} from ${file}`);
    return load(path.relative(root, resolved));
  };
  // Expose private render functions in this loader only, without production hooks.
  const expose = file.endsWith('copilot-conversation.tsx') ? '\nmodule.exports = { Conversation, Answer };'
    : file.endsWith('risk-environment-view.tsx') ? '\nmodule.exports = { RiskEnvironmentView, EvidenceTable };' : '';
  new Function('require', 'module', 'exports', output + expose)(requireLocal, module, module.exports);
  return module.exports;
}
const { e9Case } = load('lib/workspace/e9-test-fixtures.ts');
const { adaptSavedCaseToWorkspace } = load('lib/workspace/legacy-case-adapter.ts');
const { assembleCopilotContext, answerQuestion } = load('lib/workspace/grounded-copilot.ts');
const { Conversation, Answer } = load('components/workspace/copilot/copilot-conversation.tsx');
const visible = html => html.replace(/<[^>]*>/g, '');
const context = () => assembleCopilotContext(adaptSavedCaseToWorkspace(e9Case()));

test('Copilot context displays a localized saved date without exposing the internal case ID', () => {
  for (locale of ['zh-TW', 'en', 'ja', 'ko']) {
    const ctx = context();
    const text = visible(renderToStaticMarkup(React.createElement(Conversation, { context: ctx })));
    assert.ok(text.includes(ctx.title));
    assert.ok(text.includes(load('lib/experience-i18n.ts').formatExperienceDate(ctx.savedAt, locale)));
    assert.ok(!text.includes(ctx.caseId));
    assert.ok(!text.includes(ctx.savedAt));
  }
});

test('Copilot provenance formats dates and keeps unknown dates and source vintages distinct', () => {
  for (locale of ['zh-TW', 'en', 'ja', 'ko']) {
    const ctx = context();
    const market = ctx.evidence.find(row => row.id === 'market-total');
    market.checkedAt = 'not-a-date';
    market.updatedAt = '2026 年版';
    const answer = answerQuestion(ctx, 'summary');
    const html = renderToStaticMarkup(React.createElement(Answer, { answer, context: ctx, index: 0, pending: false, onFollowup() {} }));
    const text = visible(html);
    assert.ok(text.includes('2026 年版'));
    assert.ok(!text.includes('not-a-date'));
    assert.ok(!/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(text));
    // Display changes must not replace deterministic citation bindings.
    assert.ok(html.includes('data-evidence-ref="case-a:market-total"'));
    assert.ok(text.includes(load('lib/workspace/copilot-copy.ts').copilotCopy(locale).unknown));
  }
});

test('Risk query date is readable without changing the stored timestamp', () => {
  const { RiskEnvironmentView } = load('components/workspace/risk/risk-environment-view.tsx');
  locale = 'zh-TW';
  activeWorkspace = adaptSavedCaseToWorkspace(e9Case());
  const html = renderToStaticMarkup(React.createElement(RiskEnvironmentView));
  const summary = visible(html.split('data-testid="risk-buyer-summary"')[1].split('</section>')[0]);
  assert.ok(!/\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(summary));
  assert.equal(activeWorkspace.risk.freshness.checkedAt, e9Case().data.riskEvidenceCheckedAt);
});

test('Risk table uses existing localized states rather than raw codes', () => {
  const { EvidenceTable } = load('components/workspace/risk/risk-environment-view.tsx');
  locale = 'zh-TW';
  const model = adaptSavedCaseToWorkspace(e9Case()).risk;
  const html = renderToStaticMarkup(React.createElement(EvidenceTable, { model, onSelect() {} }));
  // Source cards belong to PR #224; this checks the table's own state column.
  const states = [...html.matchAll(/<td[^>]*>(.*?)<\/td>/gs)].filter((_, index) => index % 6 === 1).map(match => visible(match[1]));
  assert.ok(states.length > 0);
  assert.ok(states.every(text => !/\b(?:LIMITED|UNKNOWN|UNAVAILABLE|NO MATCH|UNSUPPORTED)\b/.test(text)));
});
