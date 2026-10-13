# Unit-24

Two parts: a Python research corpus (`src/radiocorpus`, data in `data/`) and a static learner
web app (`web/`). Read `README.md`, `docs/architecture.md` and `docs/learning-app.md` first.

## Non-negotiable rules

* A missing fact stays UNKNOWN. Never infer a code meaning from neighbouring text, another
  agency, a shared dispatch centre or "common practice" (ADR 0004/0005).
* The app teaches only what `radiocorpus export-learning` emits from committed audit evidence.
  Never hand-edit `web/src/content/chp.json`; change the inputs and regenerate.
* Do not label anything human-verified or current unless the evidence says so. Human decisions
  enter only through `data/adjudication/human/` (written by people via the app's `/review`
  page); never create or edit review records on a reviewer's behalf.
* Do not point a web host at the Typer CLI (ADR 0007).
* Every interface string goes through the i18n dictionaries (`web/src/i18n/ko.ts` is the source,
  `en.ts` must match; the compiler checks). Learning content stays in the original English.
* Progress is device-first; sync and statistics are optional (ADR 0012). Never send identifiers
  with statistics, and keep `web/firestore.rules` and its emulator tests in step.

## Commands

```bash
uv sync && uv run pytest && uv run ruff check src tests scripts && uv run radiocorpus check-invariants
uv run radiocorpus export-learning      # regenerate the app's content bundle
cd web && npm ci && npm run typecheck && npm test && npm run build && npx playwright test
cd web && npm run test:rules            # Firestore rules on the emulator (Java + npx firebase-tools)
```

CI (`.github/workflows/ci.yml`) runs the `checks` job (Python), the `web` job and the
`firestore-rules` job. Production: https://unit-24.vercel.app (ADR 0011).
