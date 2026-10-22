# ENCOUNTER FOUNDATION · UNIT-24 R2.0

Implementation branch: `feat/encounter-foundation` (Phase 1 scaffold).

## Scope
- `/encounters`: bilingual Korean/English entry screen with six expandable scenario previews and learning goals.
- Home page entry, preserving the existing CHP radio course, links and progress.
- Dedicated `web/src/encounters/types.ts` and `catalog.ts` for future dialogue nodes/choices/branch links.
- Catalog validation and browser navigation/localization regression checks.
- **No interactive dialogue engine, voice recording, police-advice engine, account sync, or new progress writes yet.** The six topics are explicitly marked planned.

## Separation rules
- Never add encounter data to `web/src/content/chp.json`: that is a generated research-only CHP radio source bundle.
- Never mutate or reinterpret `unit24.progress` (legacy state version 1) in this release.
- A future encounter progress store must be versioned independently (proposed `unit24.encounters.v1`) and tested for corruption, backup, recovery, cross-tab interactions and migrations.
- A scenario cannot be marked playable without editorial review, evidence sources, and complete, internally consistent dialogue paths. This is a structural gate, **not** an assertion that specific legal facts are verified.
- American police contact rules vary by place and circumstance. Educational English training must not masquerade as jurisdiction-specific legal instructions.
- Current `Permissions-Policy` disables microphone access. Do not loosen it until a concrete speech feature is implemented and tested.

## Acceptance checks
1. `cd web && npm ci && npm run typecheck && npm test && npm run build`.
2. `cd web && npx playwright test --workers=2`, including new `encounters.spec.ts` across seven projects.
3. CI `checks`, `web`, `firestore-rules`, `preview` all green for exact PR head.
4. Test the immutable Vercel Preview on iPad Safari; inspect 6 cards, language, accessibility, radio lesson persistence and PWA update.
5. Do not merge directly without evidence and owner approval; `main` branch protection is currently absent (see issue #12).

Follow-on phase: implement `ScenarioPlayer` with reviewed turns and options, then a separate progress store and speech layer.

## iPad manual QA follow-up (user report, 2026-10-22 KST)

These are **user-reported**, not assistant-reproduced results for the immutable Preview `a2435cd0`:
- PASS: Preview loaded and ENCOUNTER heading visible.
- PASS: All six scenario cards visible.
- NOT CHECKED: Traffic Stop card expansion and learning goals.
- NOT CHECKED: Switching Korean and English in Settings.
- NOT CHECKED: Preservation of existing RADIO progress.

Follow-on coverage added in this branch:
- Expand Traffic Stop and assert its specific learning goal is visible (not a vacuous hidden-text check).
- Toggle Korean/English via Settings, navigate back, reload, and confirm translations persist.
- Record an actual RADIO flashcard answer, visit ENCOUNTER, then assert the exact existing `unit24.progress` value survives navigation and reload.
- Check page width and card expansion at iPad portrait viewport size; run browser tests on an additional `ipad-webkit` WebKit-emulated project.

**Automated checks are still blocked:** GitHub Actions jobs ended without runner assignment or steps on PR #13 (even after one rerun). Vercel `READY` validates TypeScript/Vite build, not Playwright. The iPad WebKit project is browser emulation, not a physical iPad. Neither should be recorded as a passed on-device check.
