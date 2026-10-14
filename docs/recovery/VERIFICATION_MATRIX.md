# Verification matrix — independently reproduced recovery

## Release evidence

Functional production SHA `6446fcc4ce74f04521b893b38ab44bf79925a687`; recovery PR head `a749d80441c253eb65805f5493e875c38eb486c8`.

| Gate | Actual result | Evidence / limit |
|---|---|---|
| Python | 259 passed | Exact-head CI checks; no new independent real-document accuracy implied |
| Ruff | Passed | src/tests/scripts; output-directory CLI line-length failure repaired |
| Corpus invariants | 14 sections, 0 violations | Includes normalized/fixture/export checks; empty DB portions do not prove coverage |
| Frontend unit/component | 79 passed | Nested corruption, contradictory answers, atomic writes, sequential tabs, SRS, sync lifecycle, config, worker lifecycle, canonical source questions and failed recovery backup |
| Typecheck / production build | Passed | Exact-head CI and Vercel |
| Firestore rules | 8 passed on emulator | Ownership/validation supporting evidence; not published-production rules or real Auth |
| Built-app browser | 252 passed | Seven projects, including 14 real-browser worker fixtures at controlled loopback origins |
| Immutable Preview | 238 passed, 14 explicitly skipped | Exact-head Preview URL; only origin-control worker fixtures skipped, all application journeys retained |
| Production smoke | 238 passed, 14 explicitly skipped | Actual released deployment, all seven projects |
| Actual baseline → production update | PASS in Cloud desktop Chrome | Old/new script identity and same 10-14 answer at 1/10; no storage clearing |
| Actual production lesson | PASS in Cloud desktop Chrome | All 9 cards, 5-question completion; card/feedback/completion reload continuity |
| Actual Firebase/Auth/two-device sync | BLOCKED | No deployed configuration; mocks/emulator do not establish readiness |
| Physical devices / screen reader | UNVERIFIED | No physical iPhone, Android or human assistive-technology run |

CI: https://github.com/club-paradiso/unit-24/actions/runs/38494501402
Main CI: https://github.com/club-paradiso/unit-24/actions/runs/38495723876
Production smoke: https://github.com/club-paradiso/unit-24/actions/runs/38495765818

## Browser matrix

| Project | Engine/environment | Result |
|---|---|---|
| desktop | Chromium, 1280×800 | PASS built / Preview / production |
| mobile | Chromium, Pixel 7 viewport | PASS built / Preview / production; emulation |
| firefox | Desktop Firefox | PASS built / Preview / production |
| webkit | Desktop WebKit | PASS built / Preview / production; not physical Safari |
| iphone | iPhone 13-sized WebKit | PASS built / Preview / production; emulation |
| tablet | Chromium, 768×1024 | PASS built / Preview / production |
| small-mobile | Chromium, 320×640 | PASS built / Preview / production |

Flows: homepage/CHP, every first-lesson card and assessment, source warnings/provenance, flashcard flip/swipe/grade, all practice modes including empty due/mistake queues, correct/incorrect feedback, mistake review, interrupted feedback resume, stats/progress, reference search/history, Korean/English persistence, valid export/import, invalid and source-tampered import rejection, recovery download, reset confirmation, human-review draft/export (test fixtures only), manifest/icons, offline deep links/reference, strict CSP/console assertions, dark-mode axe scans and viewport overflow. Serious accessibility assertions are not a complete human accessibility certification.

Worker fixture skips are explicit because tests replace the origin's worker script. Deployed offline journeys remain enabled on every engine. The actual legacy production migration was additionally observed in Cloud Chrome. Physical installation, iOS home-screen lifecycle, eviction and long-duration storage are not verified.

## Reproduce

```sh
uv sync
uv run pytest
uv run ruff check src tests scripts
uv run radiocorpus check-invariants
uv run radiocorpus export-learning
git diff --exit-code -- web/src/content/chp.json
cd web
npm ci
npm test
npm run build
npx playwright install --with-deps chromium firefox webkit
npx playwright test --workers=2
E2E_BASE_URL=https://DEPLOYMENT.vercel.app npx playwright test --workers=2
```

Use an immutable deployment URL and confirm its SHA before citing results. Local scratch browser downloads hit truncation/stale locks; newer local Firefox targets crashed under the execution host. Certificate verification was never disabled for proxy access. The authoritative seven-engine/viewport results were produced on GitHub's supported Linux hosts with OS dependencies, plus direct Cloud Chrome production interaction.

## Failed iterations retained

Baseline: 58 unit tests and 56 Chromium desktop/mobile browser tests passed, yet actual production lesson feedback was lost on reload. Eight new integrity cases failed before repair.

First seven-project CI (38427123487): 223 passed, 8 failed. WebKit offline/navigation automation, iPhone review overflow and 320px swipe coordinates were investigated. Playwright 1.64 contains the upstream fix documented at https://github.com/microsoft/playwright/issues/42775; application offline checks were not removed. Fieldsets shrink and commands wrap; swipe endpoints remain in the viewport.

Preview iteration 38491444205: 224 passed, 7 CSP failures from Vercel feedback injection. The optional toolbar was disabled and fresh Preview verified; CSP was preserved. These failed Previews were not released. No failing gate was force-merged.

React final review retained unconditional hooks, explicit incompatible-data branches, listener/timer cleanup, conditional SDK loading, existing styles and keyboard/axe coverage. No speculative framework/performance rewrite.
