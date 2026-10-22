# UNIT-24 · Traffic Stop language beta

Branch: `feat/traffic-stop-pilot` based on draft PR #13 (`feat/encounter-foundation`).

## Scope
- Deterministic interactive dialogue pilot, with officer utterances, branching responses, Korean/English explanations and pragmatic language-only feedback.
- Starting prompt, optional repetition, explanation of a faulty brake light and optional clarification. Multiple paths finish; reset is supported.
- Six-scenario catalog remains; one traffic-stop scenario is clearly marked **pilot**; other five are **planned**.
- No microphone, no personal data transmission, no new account state, and no persistent encounter scoring; existing `unit24.progress` remains unchanged.
- `/encounters/traffic-stop` is the player; unlaunched scenarios respond with a non-playable holding screen.

## Provenance and legal accuracy
- Fictional lesson language, **not** legal instructions, legal judgments, verified rights material or a recording of an actual stop.
- Sources in the catalog give procedural/educational context (US DOJ example, ACLU overview) and are **not** evidence that the synthetic dialogue is an official script.
- Scenario stage `pilot` explicitly requires `legalReview: "pending"`; only independently reviewed material may later be promoted to `playable`.
- Clarity/tone feedback should never be conflated with safety or legal appropriateness. State-specific rules and immigration considerations are out of scope.

## Exit gates
- Typecheck, Vitest, build, cross-browser E2E and source checks.
- Immutable Vercel Preview and iPad Safari manual inspection.
- PR #13 remains draft until GitHub Actions hosted-runner dispatch is fixed. Do not merge either PR through a failing gate.

## Temporary restrictions
This pilot stores no encounter progress, has no speech engine, and does not claim all six scenarios are available.
