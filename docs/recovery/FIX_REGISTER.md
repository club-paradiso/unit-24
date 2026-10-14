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

R10: Corruption introduced by another open tab is now backed up before a subsequent valid write. If the recovery backup cannot be saved, the store keeps learning in memory and preserves the original storage value. A regression verifies retained valid item records and the exact corrupt backup.

R11: First service-worker installation no longer presents a false update prompt. Waiting-worker state is rechecked after activation. Three lifecycle regressions passed; real worker activation is covered by the loopback update journey.

R12: CI gains an exact-commit Preview job; Playwright 1.64 fixes the documented upstream WebKit offline automation defect. Review fieldset sizing/command wrapping and small-screen swipe coordinates address failures from the first seven-project run.

R13: Legacy installed shells have no waiting-worker button. `legacy-worker-migration.js` checks only Workbox precaches for the old `registerSW.js` marker and activates the recovery worker in that case. It does not force a page reload or touch localStorage. A normal reload escapes the old shell; later workers use the explicit prompt. The production baseline worker was fetched and confirmed to precache that marker. Two lifecycle browser fixtures cover legacy and current shells; actual old production shell upgrade is a separate release observation.

R14: Disable the optional Preview feedback toolbar at the Vercel project level after reproducing its CSP violation on every Preview route. Preserve CSP. Remove the web-only build-ignore optimization so changed deployment settings and documentation commits can receive exact-head Preview verification rather than silently reusing an older release.

R15: Structural validation does not authenticate imported question content. Added canonical subject/answer/distractor and lesson-reference checks. Tampered backups are rejected before any progress write. Already-stored incompatible sessions/drafts are held and not displayed as teaching material; the learner can back up and explicitly replace them. Previously earned item progress stays intact. Unit and browser regressions inject invented answers using real item IDs.

R16: Storage notices now distinguish successful corruption backups from recovery-write failure and do not falsely say a retained open state was reset. If backup storage fails, the original is never overwritten and remains downloadable from memory. Settings exposes a recovery-copy download for unreadable originals or pre-import state without replacing current progress. Two additional unit regressions and the existing browser import journey verify this behavior.
