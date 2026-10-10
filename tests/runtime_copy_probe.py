"""Resolve frontend localization contracts through the actual TypeScript runtime."""

import json
import re
import subprocess
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCALES = ("zh-TW", "en", "ja", "ko")
CONFIDENCE_KEYS = (
    "riskSummary.confidenceHighMessage",
    "riskSummary.confidenceMediumMessage",
    "riskSummary.confidenceLowMessage",
)
LOCATION_PRICE_KEYS = (
    "riskSummary.titleLocationSupportsPrice",
    "riskSummary.titleLocationNotSupportsPrice",
)
MAP_KEYS = (
    "map.baseStandard", "map.baseLight", "map.baseSatellite",
    "map.selected", "map.distance", "map.rating",
)
SURFACE_KEYS = ("location.title", "commute.title", "loan.title", "tax.title", "case.title")
REQUIRED_RUNTIME_KEYS = CONFIDENCE_KEYS + LOCATION_PRICE_KEYS + MAP_KEYS + SURFACE_KEYS
EXPERIENCE_KEYS = ("page.terrain", "journey.location.title", "trust.referenceOnly")


@lru_cache(maxsize=1)
def probe_runtime_copy() -> dict:
    # Compile/import the real modules, including prefix expansion and overrides.
    # Never parse source literals or recreate the localization algorithm in Python.
    script = r"""
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve('frontend_next');
const ts = require(path.join(root, 'node_modules/typescript'));
const cache = new Map();
function load(file) {
  if (cache.has(file)) return cache.get(file).exports;
  const module = { exports: {} };
  cache.set(file, module);
  const source = fs.readFileSync(file, 'utf8') + (file === path.join(root, 'lib/experience-i18n.ts')
    ? '\nexports.contractResources = resources;' : '');
  const js = ts.transpileModule(source, {
    compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2022 },
  }).outputText;
  const localRequire = name => {
    if (!name.startsWith('@/') && !name.startsWith('.')) throw new Error(`Unexpected import: ${name}`);
    const target = name.startsWith('@/') ? path.join(root, name.slice(2)) : path.resolve(path.dirname(file), name);
    return load(`${target}.ts`);
  };
  vm.runInNewContext(js, { module, exports: module.exports, require: localRequire, Intl }, { filename: file });
  return module.exports;
}
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const runtime = load(path.join(root, 'lib/runtime-copy.ts'));
const experience = load(path.join(root, 'lib/experience-i18n.ts'));
const experienceOverrides = load(path.join(root, 'lib/experience-i18n-overrides.ts'));
const values = { confidence: 87, name: 'Example', distance: 100, rating: 4.5 };
console.log(JSON.stringify({
  locales: experience.SUPPORTED_LOCALES,
  registered: runtime.RUNTIME_COPY_KEYS,
  coverage: runtime.getRuntimeCopyCoverage(),
  experienceOwnKeys: Object.fromEntries(experience.SUPPORTED_LOCALES.map(locale => [locale,
    request.experience.filter(key => Boolean(experienceOverrides.getExperienceOverride(locale, key)
      ?? experience.contractResources[locale][key])),
  ])),
  runtime: Object.fromEntries(experience.SUPPORTED_LOCALES.map(locale => [locale,
    Object.fromEntries(request.runtime.map(key => [key, runtime.translateRuntimeCopy(locale, key, values)])),
  ])),
  experience: Object.fromEntries(experience.SUPPORTED_LOCALES.map(locale => [locale,
    Object.fromEntries(request.experience.map(key => [key, experience.translateExperience(locale, key)])),
  ])),
}));
"""
    result = subprocess.run(
        ["node", "-e", script], cwd=ROOT,
        input=json.dumps({"runtime": REQUIRED_RUNTIME_KEYS, "experience": EXPERIENCE_KEYS}),
        text=True, encoding="utf-8", capture_output=True, check=False,
    )
    assert result.returncode == 0, f"Runtime copy probe failed:\n{result.stderr}"
    return json.loads(result.stdout)


def _assert_resolved_value(locale: str, key: str, value: str) -> None:
    assert isinstance(value, str) and value.strip(), f"Empty copy: {locale}:{key}"
    assert value != key, f"Raw key rendered: {locale}:{key}"
    assert "{{" not in value, f"Unresolved interpolation: {locale}:{key}: {value}"


def _assert_localized_value(locale: str, key: str, value: str) -> None:
    _assert_resolved_value(locale, key, value)
    script_patterns = {
        "zh-TW": r"[\u3400-\u9fff]", "ja": r"[\u3040-\u30ff\u3400-\u9fff]",
        "ko": r"[\uac00-\ud7a3]", "en": r"[A-Za-z]",
    }
    assert re.search(script_patterns[locale], value), f"Wrong locale script: {locale}:{key}: {value}"
    if locale == "en":
        assert not re.search(r"[\u3400-\u9fff\u3040-\u30ff\uac00-\ud7a3]", value), value


def assert_runtime_keys_localized(keys: tuple[str, ...]) -> None:
    probe = probe_runtime_copy()
    assert tuple(probe["locales"]) == LOCALES
    for key in keys:
        assert key in probe["registered"], f"Unregistered runtime key: {key}"
        for locale in LOCALES:
            # Coverage checks own-locale data, so canonical fallback cannot mask a missing entry.
            assert key not in probe["coverage"][locale]["missing"], f"Missing locale entry: {locale}:{key}"
            _assert_localized_value(locale, key, probe["runtime"][locale][key])


def assert_experience_keys_localized(keys: tuple[str, ...]) -> None:
    probe = probe_runtime_copy()
    for key in keys:
        for locale in LOCALES:
            # Explicit entries may legitimately share wording (e.g. "Terrain Risk").
            assert key in probe["experienceOwnKeys"][locale], f"Missing experience copy: {locale}:{key}"
            _assert_resolved_value(locale, key, probe["experience"][locale][key])
