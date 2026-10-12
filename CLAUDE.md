# Unit-24

Two parts: a Python research corpus (`src/radiocorpus`, data in `data/`) and a static learner
web app (`web/`). Read `README.md`, `docs/architecture.md` and `docs/learning-app.md` first.

## Non-negotiable rules

* A missing fact stays UNKNOWN. Never infer a code meaning from neighbouring text, another
  agency, a shared dispatch centre or "common practice" (ADR 0004/0005).
* The app teaches only what `radiocorpus export-learning` emits from committed audit evidence.
  Never hand-edit `web/src/content/chp.json`; change the inputs and regenerate.
* Do not label anything human-verified or current unless the evidence says so.
* Do not point a web host at the Typer CLI (ADR 0007).

## Commands

```bash
uv sync && uv run pytest && uv run ruff check src tests scripts && uv run radiocorpus check-invariants
uv run radiocorpus export-learning      # regenerate the app's content bundle
cd web && npm ci && npm run typecheck && npm test && npm run build && npx playwright test
```

CI (`.github/workflows/ci.yml`) runs both: the `checks` job (Python) and the `web` job.
