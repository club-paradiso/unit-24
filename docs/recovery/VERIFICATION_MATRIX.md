# Recovery verification matrix

## Reproduction

```sh
uv sync
uv run pytest
uv run ruff check src tests scripts
uv run radiocorpus check-invariants
cd web
npm ci
npm test
npm run build
npx playwright install --with-deps chromium firefox webkit
npx playwright test --workers=2
# Immutable deployment validation:
E2E_BASE_URL=https://DEPLOYMENT.vercel.app npx playwright test --workers=2
```

| Check | Baseline | Recovery | Limits |
|---|---|---|---|
| Python tests | 259 passed | Pipeline unchanged | Does not establish real-PDF accuracy |
| Ruff | Passed | Pipeline unchanged | Static lint only |
| Corpus invariant checks | 14 sections, 0 violations | Pipeline unchanged | Empty DB portions do not prove corpus coverage |
| Frontend unit tests | 58 passed | 70 passed in initial recovery run; fresh rerun in progress | Mocks do not prove Firebase production |
| Baseline browser tests | 56 passed desktop/mobile Chromium | Expanded suite pending | Prior smoke missed lesson reload loss |
| New data-integrity tests | 8 failed before repair | 8 passed after repair | Sequential two-store behavior, not true simultaneous atomicity |
| Live production lesson reload | Failed; assessment returned to first card | Not deployed | Direct browser observation |
| Desktop Firefox | Not previously measured | Pending | Must record actual run |
| Desktop WebKit / iPhone-sized WebKit | Not previously measured | Pending CI host dependencies | Emulation is not physical Safari |
| Android-sized / tablet / 320px | Prior mobile Chromium only | Pending expanded run | Viewports, not physical hardware |
| Offline and service-worker upgrade | Existing tests cover basic offline | Upgrade gate pending | Must not claim long-term persistence or physical iOS |
| Firebase production | Disabled | BLOCKED | No configuration or operational access verified |
| Physical devices | UNVERIFIED | UNVERIFIED | No physical iPhone/Android available |

Local browser runtime reinstall encountered a truncated download and stale installation lock after session resumption. Retrying into a separate cache; this is an execution-environment problem, not an application test result. Earlier WebKit could not launch because host libraries were missing. CI installs supported OS dependencies.

## Recovery iteration evidence

- Initial recovery CI `38427123487`: Python/rules passed; browser 223 passed, 8 failed. Failures were retained, not skipped or force-merged. WebKit navigation/offline, iPhone review overflow and the 320px swipe test were investigated.
- Playwright upgraded from 1.56.1 to 1.64.0. Upstream issue https://github.com/microsoft/playwright/issues/42775 documents WebKit offline navigation failure and its v1.64 fix. No application offline check was removed.
- The swipe endpoint now stays inside a 320px viewport. Review fieldsets can shrink and long command text wraps. Overflow assertions now identify the route and overflowing elements.
- Current local unit run: 74 passed; typecheck/build passed. First-install/update lifecycle tests cover false update banners and another tab's activation.
- `update.spec.ts` uses the actual built app with a synthetic previous worker at a loopback origin. It checks explicit activation, exact feedback/progress preservation, offline reload and reference. It is intentionally skipped for deployed URLs because that fixture controls the origin; deployed offline tests remain enabled on all seven projects. This is not physical-device evidence.
- Exact-head Preview gate added to CI. It resolves successful non-production deployment metadata for the PR head SHA, validates its Vercel hostname, and runs the full browser suite against that immutable deployment. No older Preview can satisfy this gate.
- Local deployed-browser access through the environment proxy hit certificate-authority errors. Certificate verification was not disabled. Cloud-browser interaction independently confirmed Preview card-2 reload continuity. GitHub-hosted Preview tests provide the broader deployed matrix.

Final release results must be appended before claiming production recovery.

- Commit `a468d5dc5e88feffbe9253d015583b4e6077b79f`: local-build browser gate passed **245 tests**, including both worker lifecycle fixtures on all seven projects. CI: https://github.com/club-paradiso/unit-24/actions/runs/38492017324. Its deployed Preview gate failed only on the old immutable Preview's injected Vercel feedback-script CSP errors; that deployment was not released.
- New Preview `dpl_JBwhCtXLkB5sRaA75xyW1VN2qb2K` for `d57366c1d3fda35efe128949aec54a471c589544` returned HTML without feedback-script injection. CSP remains unchanged. Latest canonical-question guards bring local unit count to 77; exact-head browser/Preview gates are rerunning.
