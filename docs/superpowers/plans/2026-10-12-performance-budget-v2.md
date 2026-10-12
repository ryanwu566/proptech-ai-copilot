# Performance Budget v2 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan inline. The user requires exactly one final commit.

**Goal:** Budget the client assets loaded by each route without charging independent route chunks to the homepage.

**Architecture:** Use Next manifests for route discovery and complete eager asset lists. When the build does not describe the loaded asset graph, record repeatable, cold-context local production browser requests, including runtime, CSS, fonts, redirects and rendered lazy modules. Bind evidence to the build; never substitute the global total or zero for unknown attribution.

**Tech Stack:** Python, Next production manifests, existing Playwright Chromium.

**Spec:** User's Performance Budget v2 requirements in this session.

## Global Constraints

- Preserve total static <= 8,000,000 bytes and largest client JS <= 900,000 bytes.
- Support all eleven requested routes, retaining absent routes as explicitly absent.
- Derive ceilings from pinned current origin/main measurements plus documented bounded headroom. Record supplemental feature measurements when a route is absent on main.
- Block provider/API calls in local browser measurement. Keep existing security checks.
- Run the requested checks; create exactly one commit; do not push or merge.

## Review Focus

- Shared chunks counted once per route; independent chunks never charged to homepage.
- Missing/malformed manifests, missing assets, stale browser evidence and failed loads fail closed.
- Browser prefetch excluded; actual route redirects and rendered lazy imports included.
- Unavailable routes never reported as zero-byte measurements or passing measurements.
- Both global protections remain mandatory even when every route fits its budget.

## Implementation

- [x] Add failing fixture regression tests for independent/shared assets, global limits and incomplete attribution.
- [x] Extend analyze_next_bundle.py and add a bounded production browser fallback with build-bound evidence.
- [x] Measure pinned origin/main 8b1367a, current preference build ec641ea and isolated Scenario Lab a227a18; record explicit bounded route ceilings.
- [x] Replace checker accounting, retain mandatory global protection, update CI and baseline/release docs.
- [x] Run full Python, production build, route/global budgets, release gate, hygiene and diff checks; review.
- [x] Create exactly one final commit; do not push or merge.
