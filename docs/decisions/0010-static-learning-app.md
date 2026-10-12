# ADR 0010 — the learner app is a static, client-only web app fed by a generated bundle

**Status:** accepted (2026-10-12)

## Context

The repository had no learner-facing surface (README; ADR 0007). The first product milestone
is one jurisdiction end to end: the California Highway Patrol, whose only source in the corpus
is the CHP 254 Aural Brevity Card. Its audited content is small (85 reviewed extractions, of
which 50 are source-matched) and read-only. Learners need lessons, exercises, spaced
repetition and progress that survives a reload.

ADR 0007 forbids aiming a web host at the Typer CLI and anticipates a separate deployable
surface. ADR 0006 records that the product must not inherit AGPL obligations from the
extraction path.

## Decision

* `web/` is a Vite + React + TypeScript single-page app. It has no server component.
* Content reaches it as one generated file, `web/src/content/chp.json`, written by
  `radiocorpus export-learning` (`src/radiocorpus/learning/content.py`) from committed audit
  artifacts. The app never reads the corpus database and never infers content.
* `radiocorpus check-invariants` (and `tests/test_learning_content.py`) fail when the
  committed bundle differs from a fresh build, so the app cannot drift from its evidence.
* Learner progress is stored in the browser (`localStorage`, versioned and validated, with a
  memory fallback). Learners can export and import it as a JSON file.

## Why no backend

* The content is a few dozen records that change only when the audit changes; shipping them
  with the app makes it fast and lets it work offline once loaded.
* Single-learner progress fits comfortably in browser storage. A server would add accounts,
  personal data, hosting cost and an attack surface without improving learning.
* A static build can be hosted anywhere at no cost and keeps the Python research pipeline,
  including its CLI, entirely off the network (ADR 0007).

## Consequences

* Progress does not follow a learner between browsers or devices except by export/import.
  Account sync would need a backend and is future work.
* Adding a jurisdiction means adding audited evidence and a lesson file, then extending the
  exporter. Nothing can be added to the app by hand-editing `chp.json`.
* The repository-level `vercel.json` still disables Git deployments. `web/vercel.json`
  describes how to build and serve the app if a Vercel project is pointed at `web/`; that is a
  deliberate, separate step and has not been taken.
