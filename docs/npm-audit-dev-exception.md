# Temporary npm development-audit exception

CI temporarily accepts npm advisory `GHSA-vfj7-8cjw-p6xm` (npm source
`1240992`) for `braces@3.0.3`. The advisory affects `braces <=3.0.3`, and
`3.0.3` is currently the newest published release. npm's available automatic
remediation changes direct tooling incompatibly, including a Tailwind 4
upgrade.

The reviewed package is present only below the direct development dependencies
`tailwindcss@3.4.19` and `@next/eslint-plugin-next@16.3.1`, through the exact
`chokidar` / `fast-glob` / `micromatch` paths recorded in
`.github/security/npm-audit-exceptions.json`. `npm ls --omit=dev braces` is
empty, and the production audit reports zero vulnerabilities.

This is a temporary dev-tooling exception, not a claim that the vulnerability
is harmless. Production dependencies remain zero-tolerance at high and
critical severity through `npm audit --omit=dev --audit-level=high`. The full
audit gate accepts only the recorded advisory identity and dependency graph;
changed or additional high/critical findings fail.

The exception expires on `2026-11-04`. It is invalid on and after that date,
so CI fails closed if it is still needed. Before expiry, evaluate migration
away from the affected Tailwind 3 tooling chain and the related lint tooling,
or remove the exception as soon as a compatible upstream remediation becomes
available.
