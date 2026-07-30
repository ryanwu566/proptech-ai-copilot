# Experience Architecture v3 Phases 5-8

This document records the active contract for the multilingual, read-aloud,
voice-input, and release-evidence work. It is an interaction boundary, not a
new domain or provider integration.

## Phase 5: multilingual shell

- Supported runtime locales are `zh-TW`, `en`, `ja`, and `ko`.
- Resources live in `frontend_next/lib/experience-i18n.ts` and are keyed by
  stable UI translation keys.
- Unknown locale values fall back to `zh-TW`.
- Locale selection is runtime-only. It is not written to localStorage,
  sessionStorage, cookies, URL state, or an API request.
- Domain values, provider names, status enums, field names, and legal or risk
  meanings are not translated as data.
- Number, percent, and date display uses `Intl` through the locale provider.

## Phase 6: browser read-aloud

- `ReadAloudControls` uses the browser's native `speechSynthesis` only.
- There is no autoplay. The user must select the visible read button.
- Speech is built from an explicit `SafeSpeechSummary`; it does not scrape the
  DOM and does not include raw provider data, addresses, coordinates, tokens,
  or hidden content.
- The visible controls expose start, pause, resume, and stop. Unsupported
  browsers and missing language voices remain explicit non-success states.
- Unmount and locale changes cancel active speech.

## Phase 7: voice input

- `VoiceInputControls` uses browser-native `SpeechRecognition` when available.
- Listening starts only after an explicit click and never restarts itself.
- `parseVoiceCommand` is deterministic and locale-aware. It has no network,
  dynamic code execution, persistence, or model/provider dependency.
- Navigation, help, focus, bounded field-fill, read-aloud stop, and repeat
  summary are the only action shapes. Every recognized action requires visible
  confirmation before notification to the existing UI.
- Save, delete, export, print, comparison, valuation, loan, tax, market,
  provider refresh, purchase, safety, and other destructive or consequential
  actions are blocked from voice execution.
- Transcript text is visible only for the current interaction and is not persisted.

## Phase 8: acceptance and release boundary

- Existing domain API contracts and business calculations remain unchanged.
- Backend, provider, database, deployment, and secret configuration are not
  part of this package.
- Static tests cover resource fallback, `Intl` formatting, browser capability
  checks, explicit controls, allowlist and blocked voice commands, privacy
  boundaries, and active documentation.
- Browser matrix acceptance must still be completed manually for the target
  browsers and assistive technologies. Native speech availability varies by
  browser and operating system.
- This package is not a purchase recommendation, safety guarantee, legal
  opinion, loan approval, valuation, or provider freshness claim.
