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
