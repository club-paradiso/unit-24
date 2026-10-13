# Recovery fix register

Changes below are implemented on the recovery branch. A local test does not imply release; see DEPLOYMENT_REPORT.md.

| ID | Change | Files | Regression evidence | Release state |
|---|---|---|---|---|
| R01 | Persist lesson study position, exact quiz, feedback and completion; prevent repeated completion credit | pages/Lesson.tsx, lib/progress.ts | browser reload journey | Pending browser gate |
| R02 | Strict nested progress validation, additive v1 migration and pre-import backup | lib/progress.ts | recovery.test.ts; progress.test.ts | Unit verified |
| R03 | Atomic answer persistence and contradictory-answer rejection | lib/progress.ts | recovery.test.ts | Unit verified |
| R04 | Refresh before mutations; storage event propagation between tabs | lib/progress.ts, state.tsx | two-store regression and two-tab journey | Unit verified; browser pending |
| R05 | Preserve due date after early successful recall | lib/srs.ts | recovery.test.ts | Unit verified |
| R06 | Single-flight sync, lifecycle cancellation, pull before push, transactional Firestore merge, malformed remote rejection | sync/engine.ts, firebase.ts, context.ts, merge.ts | engine.test.ts, merge.test.ts | Mock/unit only; actual Firebase blocked |
| R07 | Explicit public Firebase build configuration, fail closed if incomplete | sync/config.ts | config.test.ts | Disabled in production until configured and verified |
| R08 | User-controlled waiting-worker update prompt | components/AppUpdate.tsx, Layout.tsx, vite.config.ts, i18n | Build verified; update browser test pending | Not release verified |
| R09 | Seven browser/viewport projects, regression journeys | playwright.config.ts, e2e/recovery.spec.ts, workflows | Expanded CI required | Pending |

Known limits: localStorage read-before-write preserves sequential completed writes but is not a distributed transaction for truly simultaneous writes. Sync merges per-item latest state and max daily counts; it is not an additive event log. Same-item simultaneous work can be undercounted. Do not describe it as lossless. Flashcard answers persist, but a deck's exact cursor is not resumable.
